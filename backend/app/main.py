"""StudioLink Outreach Engine — FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_db_and_tables
from app.routers import leads, templates, blacklist, logs, jobs, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # ── Startup ──
    create_db_and_tables()
    _seed_default_templates()
    yield
    # ── Shutdown ──
    pass


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Automated TikTok cold outreach for StudioLink 🚀",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(dashboard.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(blacklist.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# ── Seed ─────────────────────────────────────────────────────

def _seed_default_templates():
    """Insert the default message templates on first run."""
    from sqlmodel import Session, select
    from app.database import engine
    from app.models import MessageTemplate, Niche

    with Session(engine) as session:
        existing = session.exec(select(MessageTemplate)).first()
        if existing:
            return  # Already seeded

        defaults = [
            MessageTemplate(
                name="Copy Maestro — Danza",
                niche=Niche.danza,
                template_text=(
                    "¡{Hola|Hey|Qué tal}! Como programador y bailarín 🕺 "
                    "{uso|utilizo} tecnología para automatizar el lado "
                    "{aburrido|tedioso|repetitivo} de {dar clases|administrar una academia}: "
                    "pagos, reservas, seguimiento de alumnos... "
                    "Tu perfil me {dio curiosidad|llamó la atención} por cómo lo "
                    "{llevan|manejan} ahorita... ¿Te gustaría automatizar tus procesos? "
                    "Aquí para {ayudar|echarte la mano} 🙂"
                ),
                spintax_enabled=True,
            ),
            MessageTemplate(
                name="Copy Maestro — Deportes",
                niche=Niche.futbol,
                template_text=(
                    "¡{Hola|Hey|Qué tal}! Soy programador y {también amo el deporte|me apasiona el deporte} ⚽ "
                    "{Creé|Desarrollé} una plataforma para automatizar "
                    "{cobros|pagos}, {inscripciones|reservas} y seguimiento de alumnos "
                    "en academias deportivas. Tu {academia|escuela} me {llamó la atención|pareció increíble}... "
                    "¿Te gustaría {platicar|saber más}? 🙂"
                ),
                spintax_enabled=True,
            ),
            MessageTemplate(
                name="Copy Maestro — General",
                niche=None,
                template_text=(
                    "¡{Hola|Hey|Qué tal}! Soy programador y {bailarín|deportista} 🕺 "
                    "{Automatizo|Simplifico} el lado {administrativo|operativo} de "
                    "{academias|escuelas|centros de entrenamiento}: "
                    "{pagos|cobros}, {reservas|inscripciones}, seguimiento de {alumnos|estudiantes}... "
                    "Vi tu perfil y me encantaría {platicar|saber} cómo {lo manejan|operan} hoy. "
                    "¿Te {interesa|gustaría saber más}? 🙂"
                ),
                spintax_enabled=True,
            ),
        ]

        for tpl in defaults:
            session.add(tpl)
        session.commit()
