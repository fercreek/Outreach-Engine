# 🚀 StudioLink Outreach Engine

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19+-61dafb?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Playwright](https://img.shields.io/badge/Playwright-1.48+-2ead33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev)

Sistema de prospección automatizada para atraer dueños de academias, gimnasios y estudios hacia **[Studio Link](https://studiolink.mx)**. Combina scraping con Playwright, envío de DMs con keystroke dynamics, y un agente de respuesta con Claude API.

> **Uso actual:** Fernando prospecta Studio Link internamente en TikTok.
> **Uso futuro (Fase 6):** servicio configurable para clientes — cada quien con su propia cuenta y knowledge base.

---

## Visión general — Orquestador

El sistema no es solo un bot de DMs. Es un pipeline completo de prospección con aprobación humana en cada paso crítico:

```
Discovery → Warming → Aprobación HITL → DM Send → Reply detected → Agent Response → Converted
```

Tres módulos coordinados por el orquestador:

```
┌─────────────────────┐     reply     ┌─────────────────────────┐
│   Outreach Engine   │ ──detected──▶ │     Response Agent      │
│                     │               │                         │
│  Discovery          │               │  Claude Haiku           │
│  Warming            │◀──send reply──│  Knowledge base SL      │
│  HITL approval      │               │  Historial conversación │
│  DM send            │               │  Tools: mark_converted, │
└─────────────────────┘               │  escalate_to_human...   │
           │                          └──────────┬──────────────┘
           │ lead convertido                     │ lead caliente
           ▼                                     ▼
┌─────────────────────┐          ┌────────────────────────────┐
│     MetriSync       │          │  Notificación WhatsApp     │
│  (contenido para    │          │  → Fernando                │
│   redes de SL)      │          │  → Studio Link CRM (futuro)│
└─────────────────────┘          └────────────────────────────┘
```

**Spec completo:** [`specs/orchestrador-spec.md`](specs/orchestrador-spec.md)

---

## Plan de implementación

### ✅ Fase 1 — Outreach Engine funcional *(completada)*

Objetivo: que el engine funcione manualmente para prospectar en TikTok.

- Fix de 6 bugs críticos en `worker.py` (personalize dict, LeadStatus, settings case, result dict, pausa interruptible, browser cleanup)
- Selectores resilientes en `outreach.py` — listas de fallback por elemento
- Cola de aprobación HITL: backend (`/leads/approval-queue`) + UI (`ApprovalQueue.jsx`)

---

### 🔴 Fase 2 — Discovery y monitor reales *(siguiente)*

Objetivo: poder encontrar leads sin hacerlo a mano y detectar respuestas automáticamente.

**Tareas:**
1. Reescribir `discovery.py` — scraping por hashtag en TikTok con selectores actuales
2. Reescribir `monitor.py` — polling del inbox cada 10 min, detecta respuestas, emite eventos
3. Endpoint `POST /discovery/run` con job en background
4. Calificación automática: leads con <500 seguidores → `excluded`; bio con keywords de niche → `qualified`
5. Prueba end-to-end: descubrir 10 leads → aprobar → DM → verificar detección de respuesta

**Guía técnica:** [`.cursor/rules/phase2-discovery.mdc`](.cursor/rules/phase2-discovery.mdc)

---

### ⬜ Fase 3 — Response Agent *(Claude API)*

Objetivo: cuando un prospecto responde, el agente toma la conversación y lo convierte.

**Tareas:**
1. Crear `services/agent.py` — Claude `haiku-4-5` con tool use
2. Knowledge base en `knowledge/` — 4 archivos markdown editables por Fernando:
   - `studio-link-overview.md`
   - `plans-pricing.md`
   - `faq.md`
   - `trial-signup.md`
3. Model `ConversationMessage` para historial por `lead_id`
4. Router `POST /agent/process-reply` — recibe evento del monitor, dispara agente en background
5. Tools del agente: `send_reply`, `mark_converted`, `mark_excluded`, `escalate_to_human`
6. UI `Conversations.jsx` — historial tipo WhatsApp + botón "tomar control"

**Guía técnica:** [`.cursor/rules/phase3-agent.mdc`](.cursor/rules/phase3-agent.mdc)

---

### ⬜ Fase 4 — Validación interna *(2 semanas)*

Objetivo: confirmar números reales antes de ofrecerlo como servicio.

**KPIs:**
- Tasa de respuesta a DMs: objetivo >10%
- Conversión respuesta → trial: objetivo >5%
- Leads descubiertos por hora de scraping
- Falsos positivos del agente (respuestas que Fernando tuvo que corregir)

**Configuración durante validación:**
- Solo TikTok, 45 DMs/día máximo
- Fernando revisa TODOS los mensajes del agente los primeros 3 días
- Log detallado de cada conversación para mejorar el system prompt

---

### ⬜ Fase 5 — Instagram

Objetivo: segundo canal de prospección con el mismo pipeline.

- Adaptar `discovery.py` y `outreach.py` para Instagram (selectores distintos, misma lógica)
- Campo `platform: tiktok | instagram` en `Lead` y `BatchJob`
- La cola de aprobación y el agente funcionan igual para ambos canales

---

### ⬜ Fase 6 — Multi-tenant *(para clientes)*

Objetivo: ofrecer el sistema configurado a clientes de Studio Link (Ale We Dance, Viviana Artec, etc.).

- Campo `tenant_id` en todas las tablas
- Knowledge base por tenant (cada quien describe su propio negocio)
- Panel de onboarding: "¿Qué hace tu negocio?" → Claude genera la knowledge base automáticamente
- Dashboard por tenant con sus propias métricas
- Configuración de límites por tenant

---

## Estado de módulos

| Módulo | Archivo | Estado |
|--------|---------|--------|
| Worker | `backend/app/services/worker.py` | ✅ Producción |
| Outreach | `backend/app/services/outreach.py` | ✅ Producción |
| Approval API | `backend/app/routers/leads.py` | ✅ Producción |
| Approval UI | `frontend/src/pages/ApprovalQueue.jsx` | ✅ Producción |
| Warming | `backend/app/services/warming.py` | 🟡 Básico funcional |
| Discovery | `backend/app/services/discovery.py` | 🔴 Reescribir (Fase 2) |
| Monitor | `backend/app/services/monitor.py` | 🔴 Reescribir (Fase 2) |
| Agent | `backend/app/services/agent.py` | ⬜ Fase 3 |
| Notifications | `backend/app/services/notifications.py` | ⬜ Fase 3 |
| Knowledge base | `backend/app/knowledge/` | ⬜ Fase 3 |
| Conversations UI | `frontend/src/pages/Conversations.jsx` | ⬜ Fase 3 |

---

## Tech Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11, FastAPI, SQLModel, SQLite |
| Automation | Playwright (Chromium, visible, no headless) |
| Frontend | React 19, Vite, React Router, CSS variables |
| Agent (Fase 3) | Claude API `claude-haiku-4-5` con tool use |
| Notificaciones (Fase 3) | Twilio WhatsApp API |

---

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
playwright install chromium

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API disponible en `http://localhost:8000` · Docs en `/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Panel de control en `http://localhost:5173`

---

## Protocolos de seguridad (irrompibles)

| Protocolo | Valor | Razón |
|-----------|-------|-------|
| Delay entre DMs | 15-20 min (Gaussian jitter) | Evitar ban de TikTok |
| Cap diario | 45 DMs | Límite seguro probado |
| Delay entre acciones | 45-90s | Simular comportamiento humano |
| Keystroke delay | 50-180ms por tecla | Anti-detección al escribir |
| Modo navegador | Visible (no headless) | Headless es detectado por TikTok |
| HITL | Obligatorio antes de cada DM | Nunca automatizar sin aprobación humana |

---

## Estructura del proyecto

```
outreach-engine/
├── CLAUDE.md                    ← contexto para Claude Code
├── specs/
│   └── orchestrador-spec.md     ← arquitectura completa y plan de fases
├── .cursor/rules/               ← reglas para Cursor
│   ├── project-overview.mdc
│   ├── backend-rules.mdc
│   ├── frontend-rules.mdc
│   ├── phase2-discovery.mdc
│   └── phase3-agent.mdc
├── backend/
│   └── app/
│       ├── models.py            ← Lead, BatchJob, ActivityLog, Blacklist
│       ├── config.py            ← límites de seguridad
│       ├── services/            ← lógica de automatización
│       ├── routers/             ← endpoints FastAPI
│       └── knowledge/           ← (Fase 3) markdown con info de Studio Link
└── frontend/
    └── src/
        ├── api/client.js        ← todas las llamadas al API
        └── pages/               ← Dashboard, LeadCenter, ApprovalQueue, Dispatch...
```

---

## Licencia

MIT — Fernando Contreras © 2026
