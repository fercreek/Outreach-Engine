# Outreach Engine — Claude Code Configuration

## Qué es este proyecto

Sistema de prospección automatizada para atraer dueños de academias, gimnasios y estudios hacia **Studio Link**. Combina scraping con Playwright, envío de DMs con keystroke dynamics, y un agente de respuesta con Claude API.

**Uso actual:** interno — Fernando prospecta Studio Link en TikTok/Instagram.
**Uso futuro:** servicio configurado para clientes (Ale We Dance, Viviana Artec, etc.)

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLModel, SQLite, Playwright (Chromium)
- **Frontend:** React 19, Vite, React Router, CSS variables (no Tailwind)
- **Agente (futuro):** Claude API con tool use, `claude-haiku-4-5`
- **Notificaciones (futuro):** Twilio WhatsApp API

## Spec maestro

`specs/orchestrador-spec.md` — lee este archivo antes de cualquier tarea.
Tiene: arquitectura completa, flujo de prospección, fases de implementación, estructura de archivos target.

**Costos del agente (API, Mac, Gemini vs Haiku vs Opus):** `docs/costos-api-agente.md`

## Estado actual por módulo

| Módulo | Archivo | Estado | Notas |
|--------|---------|--------|-------|
| Worker | `services/worker.py` | ✅ | Bugs corregidos, pausa interruptible |
| Outreach | `services/outreach.py` | ✅ | Selectores con fallbacks resilientes |
| Approval API | `routers/leads.py` | ✅ | `/approval-queue`, `/approve`, `/reject` |
| Approval UI | `frontend/pages/ApprovalQueue.jsx` | ✅ | HITL con preview de mensaje |
| Discovery | `services/discovery.py` | ✅ | Búsqueda `/search/user`, calificación, `POST /api/discovery/run` |
| Monitor | `services/monitor.py` | ✅ | Inbox + unread; opcional dispara agente si hay API key |
| Warming | `services/warming.py` | 🟡 | Básico funcional, verificar selectores |
| Agent | `services/agent.py` | ✅ | Claude + tools; `POST /api/agent/process-reply` |
| Notifications | `services/notifications.py` | ✅ | Escalación Twilio (opcional) + log; aviso convertido |
| Knowledge base | `app/knowledge/*.md` | ✅ | 4 archivos Studio Link |
| Conversations UI | `frontend/pages/Conversations.jsx` | ✅ | Historial + ejecutar agente manual |

## Fases de implementación

### Fase 1 ✅ — Outreach Engine funcional
- Fix bugs worker + outreach
- Cola de aprobación HITL

### Fase 2 ✅ — Discovery y monitor reales
1. `discovery.py` — búsqueda usuario por hashtag, perfiles, calificación
2. `monitor.py` — inbox, `poll_replies_forever`, opcional agente tras respuesta
3. `POST /api/discovery/run`
4. Prueba E2E pendiente en entorno real con TikTok

### Fase 3 ✅ — Response Agent (MVP)
1. `services/agent.py` — Anthropic Messages + tools
2. `app/knowledge/*.md` — 4 archivos
3. `ConversationMessage` en DB
4. `POST /api/agent/process-reply`, `GET /api/agent/conversations`, `GET .../messages`
5. `escalate_to_human` vía `notifications.py` (Twilio si hay env)
6. `Conversations.jsx` — historial + disparo manual del agente

### Fase 4 ⬜ — Validación interna (2 semanas)
KPIs: tasa de respuesta >10%, conversión a trial >5%

### Fase 5 ⬜ — Instagram
Replicar discovery + outreach para Instagram. Mismo worker/agente, diferentes selectores.

### Fase 6 ⬜ — Multi-tenant (para clientes)
- Campo `tenant_id` en tablas
- Knowledge base por tenant
- Panel de onboarding (genera knowledge base con Claude)

## Reglas críticas de desarrollo

1. **NUNCA** usar modo headless — `headless: False` siempre
2. **NUNCA** bajar el delay entre DMs por debajo de 900s (15 min)
3. **NUNCA** saltarse la aprobación HITL — todo lead pasa por la cola
4. **Selectores de Playwright** — siempre usar listas de fallbacks, nunca un solo selector
5. **send_dm** retorna `dict` con `{"success": bool, ...}` — verificar `result["success"]`, no hacer `if result:`
6. **personalize()** espera `dict` — siempre pasar `lead.model_dump()`, nunca el objeto Lead
7. **settings** usa snake_case — `settings.min_delay_between_dms_sec`, no `MIN_DELAY_...`
8. **LeadStatus válidos:** `discovered, qualified, warming, interacted, dm_pending, dm_sent, replied, converted, excluded` — no existe `interaction_failed`

## Variables de entorno (agente / escalación)

- `ANTHROPIC_API_KEY` — obligatoria para el agente
- `ANTHROPIC_MODEL` — opcional (default `claude-3-5-haiku-20241022`)
- `TRIAL_SIGNUP_URL` — opcional, inyectado en el contexto del agente
- `AGENT_AUTO_ON_REPLY` — default `true`; si `false`, el monitor no dispara el agente al detectar respuesta
- Twilio (opcional): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `ESCALATION_WHATSAPP_TO`

## Comandos comunes

```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pip install anthropic

# Frontend
cd frontend
npm run dev

# Ambos (si hay Makefile o script)
# Ver README.md
```

## Modelos de DB (SQLite)

- `Lead` — el prospecto. Campos clave: `username`, `business_name`, `niche`, `status`, `profile_url`
- `MessageTemplate` — plantilla con spintax. Campo: `content` (con `{opcion1|opcion2}`)
- `BatchJob` — trabajo de envío. Estados: `pending → running → paused/completed/cancelled`
- `ActivityLog` — historial de eventos por lead y job
- `Blacklist` — usernames excluidos permanentemente
- `ConversationMessage` — historial user/assistant por `lead_id` (agente)

## Conexión con Studio Link

El Outreach Engine es independiente de Studio Link (la app Rails). La conexión futura será:
- Webhook `POST /api/webhook/lead-converted` en Studio Link cuando un lead acepta
- Studio Link crea el Customer automáticamente
- Por ahora: notificación WhatsApp a Fernando es suficiente
