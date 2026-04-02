import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.database import engine
from app.models import ActivityLog, BatchJob, JobStatus, Lead, LeadStatus, MessageTemplate, ActionType
from app.services.browser import BrowserManager
from app.services.warming import warm_lead
from app.services.outreach import send_dm
from app.services.spintax import spin, personalize
from app.utils.jitter import gaussian_delay
from app.config import settings

logger = logging.getLogger(__name__)

async def execute_job(job_id: int):
    """
    Background worker that executes a batch job.
    Processes leads one by one with human-like delays.
    """
    page = None

    try:
        # 1. Setup
        with Session(engine) as session:
            job = session.get(BatchJob, job_id)
            if not job or job.status != JobStatus.running:
                return

            log_activity(session, job_id, None, "info", f"🤖 Iniciando Job #{job_id}", ActionType.dm_sent)

            # Fetch eligible leads (priority: dm_pending)
            leads = session.exec(
                select(Lead).where(Lead.status == LeadStatus.dm_pending).limit(job.total_leads)
            ).all()

            if not leads:
                log_activity(session, job_id, None, "warning", "⚠️ No hay leads disponibles con estatus 'dm_pending'", ActionType.error)
                job.status = JobStatus.completed
                job.finished_at = datetime.now(timezone.utc)
                session.add(job)
                session.commit()
                return

            # Fetch a default template
            template = session.exec(select(MessageTemplate)).first()
            if not template:
                log_activity(session, job_id, None, "error", "❌ No hay plantillas configuradas", ActionType.error)
                job.status = JobStatus.cancelled
                session.add(job)
                session.commit()
                return

        # 2. Open Browser
        log_activity_external(job_id, None, "info", "🌐 Abriendo navegador (Modo Persistente)...", ActionType.profile_visited)
        from app.services.browser import get_browser_page
        page = await get_browser_page()

        # 3. Automation Loop
        processed_count = 0
        for lead in leads:
            # Check for pause/cancel before processing each lead
            if not await check_job_status(job_id):
                log_activity_external(job_id, lead.id, "warning", "⏸️ Job pausado o cancelado. Deteniendo loop.", ActionType.error)
                break

            log_activity_external(job_id, lead.id, "info", f"👤 Procesando lead: @{lead.username}", ActionType.profile_visited)

            try:
                # Step A: Warming
                log_activity_external(job_id, lead.id, "info", f"🔥 Calentando perfil de @{lead.username}...", ActionType.profile_visited)
                warm_res = await warm_lead(page, lead)
                if warm_res.get("challenge_detected"):
                    log_activity_external(
                        job_id,
                        lead.id,
                        "warning",
                        f"⛔ TikTok: verificación/puzzle en @{lead.username} — job detenido",
                        ActionType.error,
                    )
                    break

                # Step B: Personalization — pass lead as dict so {{variable}} placeholders resolve
                raw_content = spin(template.content)
                final_message = personalize(raw_content, lead.model_dump())

                # Step C: Outreach
                log_activity_external(job_id, lead.id, "info", f"📨 Enviando DM a @{lead.username}...", ActionType.dm_sent)
                result = await send_dm(page, lead, final_message)

                if result.get("challenge_detected"):
                    log_activity_external(
                        job_id,
                        lead.id,
                        "warning",
                        f"⛔ TikTok: verificación/puzzle al enviar a @{lead.username} — job detenido",
                        ActionType.error,
                    )
                    break
                if result["success"]:
                    update_lead_status(lead.id, LeadStatus.dm_sent)
                    processed_count += 1
                    log_activity_external(job_id, lead.id, "success", f"✅ DM enviado con éxito a @{lead.username}", ActionType.dm_sent)
                else:
                    update_lead_status(lead.id, LeadStatus.excluded)
                    error_detail = result.get("error", "unknown")
                    log_activity_external(job_id, lead.id, "error", f"❌ Falló el envío de DM a @{lead.username}: {error_detail}", ActionType.error)

                # Update Job Progress
                update_job_progress(job_id, processed_count)

                # Step D: Interruptible delay between DMs (checks pause every 30s)
                if processed_count < len(leads):
                    delay = gaussian_delay(
                        settings.min_delay_between_dms_sec,
                        settings.max_delay_between_dms_sec,
                    )
                    log_activity_external(job_id, lead.id, "info", f"⏳ Esperando {delay/60:.1f} min (Gaussian Jitter)...", ActionType.profile_visited)
                    await interruptible_sleep(job_id, delay)

            except Exception as e:
                log_activity_external(job_id, lead.id, "error", f"💥 Error procesando @{lead.username}: {str(e)}", ActionType.error)
                continue

        # 4. Cleanup
        with Session(engine) as session:
            job = session.get(BatchJob, job_id)
            if job and job.status == JobStatus.running:
                job.status = JobStatus.completed
                job.finished_at = datetime.now(timezone.utc)
                log_activity(session, job_id, None, "success", f"🏁 Job #{job_id} completado con éxito.", ActionType.dm_sent)
                session.add(job)
                session.commit()

    except Exception as e:
        logger.error(f"Worker error: {e}")
        log_activity_external(job_id, None, "error", f"🆘 Error crítico: {str(e)}", ActionType.error)
    finally:
        # Close the page (not the full browser singleton) to release resources
        if page and not page.is_closed():
            try:
                await page.close()
            except Exception:
                pass


async def interruptible_sleep(
    job_id: Optional[int],
    total_sec: float,
    poll_interval: float = 30.0,
):
    elapsed = 0.0
    while elapsed < total_sec:
        if job_id is not None and not await check_job_status(job_id):
            return
        chunk = min(poll_interval, total_sec - elapsed)
        await asyncio.sleep(chunk)
        elapsed += chunk


# --- Helper Functions ---

def log_activity(session: Session, job_id: int, lead_id: Optional[int], level: str, message: str, action_type: ActionType):
    log = ActivityLog(job_id=job_id, lead_id=lead_id, level=level, message=message, action_type=action_type)
    session.add(log)
    session.commit()

def log_activity_external(job_id: int, lead_id: Optional[int], level: str, message: str, action_type: ActionType):
    with Session(engine) as session:
        log_activity(session, job_id, lead_id, level, message, action_type)

async def check_job_status(job_id: int) -> bool:
    with Session(engine) as session:
        job = session.get(BatchJob, job_id)
        return job.status == JobStatus.running if job else False

def update_lead_status(lead_id: int, status: LeadStatus):
    with Session(engine) as session:
        lead = session.get(Lead, lead_id)
        if lead:
            lead.status = status
            lead.updated_at = datetime.now(timezone.utc)
            session.add(lead)
            session.commit()

def update_job_progress(job_id: int, processed: int):
    with Session(engine) as session:
        job = session.get(BatchJob, job_id)
        if job:
            job.leads_processed = processed
            session.add(job)
            session.commit()
