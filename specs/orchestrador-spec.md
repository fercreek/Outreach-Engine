# Spec: Outreach Orchestrator
**Proyecto:** StudioLink Outreach System
**Versión:** 1.0 — Uso interno
**Objetivo:** Atraer dueños de academias, gimnasios y estudios hacia Studio Link de forma automatizada, con un agente de respuesta que convierte las conversaciones en trials.

---

## Visión general

El sistema no es una sola app — es una **capa de coordinación** que conecta tres módulos existentes y agrega un componente nuevo (el agente de respuesta).

```
                         ┌──────────────────────────────────┐
                         │         ORCHESTRATOR             │
                         │     (config + coordination)      │
                         └────────┬─────────┬───────────────┘
                                  │         │
              ┌───────────────────┘         └──────────────────┐
              ▼                                                 ▼
   ┌─────────────────────┐                        ┌────────────────────────┐
   │   Outreach Engine   │                        │     Response Agent     │
   │                     │                        │                        │
   │  Discovery          │  ──── reply detected ─▶│  Claude API            │
   │  Warming            │                        │  Knowledge base SL     │
   │  HITL approval      │◀─── send follow-up ─── │  Conversación DM       │
   │  DM send            │                        │  Califica al lead      │
   └─────────────────────┘                        └──────────┬─────────────┘
              │                                              │
              │ lead convertido                              │ lead caliente
              ▼                                              ▼
   ┌─────────────────────┐                        ┌────────────────────────┐
   │     MetriSync       │                        │  Notificación          │
   │                     │                        │  (WhatsApp a Fernando) │
   │  Genera contenido   │                        │  + Studio Link CRM     │
   │  para TikTok/IG     │                        │  (futuro webhook)      │
   │  de Studio Link     │                        └────────────────────────┘
   └─────────────────────┘
```

---

## Flujo completo de una prospección

```
1. DISCOVERY
   Outreach Engine scraping TikTok / Instagram
   → busca: dueños de academia, gym, estudio
   → guarda como Lead(status=discovered)

2. WARMING
   Visitar perfil, ver videos, dar like
   → Lead(status=warming)

3. APROBACIÓN (HITL)
   Fernando ve la cola de aprobación
   → revisa perfil + preview del mensaje
   → aprueba → Lead(status=dm_pending)
   → rechaza → Lead(status=excluded)

4. DM SEND
   Worker envía mensaje personalizado con spintax
   → Lead(status=dm_sent)
   → delay 15-20 min entre cada DM (Gaussian jitter)

5. DETECCIÓN DE RESPUESTA
   Monitor revisa bandeja de entrada cada N minutos
   → cuando detecta respuesta → emite evento reply_received
   → Lead(status=replied)

6. AGENTE DE RESPUESTA
   Claude API toma la conversación
   → contexto: quién es el lead, qué negocio tiene, qué respondió
   → knowledge base: qué hace Studio Link, precios, FAQs, cómo registrarse
   → responde como Fernando / equipo Studio Link
   → si el lead pide precio o dice "me interesa" → envía link de trial
   → Lead(status=converted) si acepta, (status=excluded) si no

7. NOTIFICACIÓN
   Cuando Lead(status=converted):
   → WhatsApp a Fernando con nombre, negocio, red social, resumen de conversación
   → (futuro) crea Customer en Studio Link CRM automáticamente
```

---

## Componentes

### A. Outreach Engine *(ya existe, parcialmente funcional)*

**Estado actual:**
- ✅ Worker con HITL (Fase 1 completada)
- ✅ Templates con spintax + personalización
- ✅ Gaussian jitter + keystroke dynamics
- ✅ Cola de aprobación (backend + UI)
- 🔴 Discovery: selectores TikTok obsoletos
- 🟡 Warming: básico funcional, selectores pueden fallar
- 🔴 Monitor de respuestas: 20% funcional, NO en uso

**Pendiente para que sea completo:**
- Reescribir `discovery.py` con selectores actuales de TikTok
- Reescribir `monitor.py` para detectar respuestas reales
- Adaptar ambos para Instagram

---

### B. Response Agent *(nuevo — el corazón del sistema)*

Es el componente que convierte una conversación fría en un cliente. Sin este, el sistema solo manda mensajes y espera que la persona tome la iniciativa.

**Tech stack:**
- Claude API (`claude-haiku-4-5` para respuestas rápidas, barato)
- Knowledge base: archivos markdown con info de Studio Link
- Historial de conversación: guardado en DB por `lead_id`
- Sistema de herramientas (tool use): `send_reply`, `mark_converted`, `escalate_to_human`

**Lógica del agente:**
```
system prompt:
  - Eres el equipo de Studio Link
  - Tu objetivo es entender el negocio del lead y mostrar cómo Studio Link lo ayuda
  - NO vendas de golpe — primero pregunta qué problema tienen
  - Si preguntan precio → explica planes y da el link de registro
  - Si muestran interés claro → da el link directo al trial gratuito
  - Si no responden en 48h → envía follow-up (solo una vez)
  - Si rechazan → marca excluded, no insistas

tools disponibles:
  - send_reply(lead_id, message): envía respuesta por DM
  - mark_converted(lead_id, notes): marca lead como convertido
  - mark_excluded(lead_id, reason): marca como excluido
  - escalate_to_human(lead_id, reason): manda WhatsApp a Fernando
  - get_lead_context(lead_id): info del negocio, niche, bio
```

**Knowledge base (archivos markdown):**
- `knowledge/studio-link-overview.md` — qué hace el producto
- `knowledge/plans-pricing.md` — planes, precios, diferencias
- `knowledge/faq.md` — objeciones comunes y cómo responderlas
- `knowledge/trial-signup.md` — cómo registrarse, qué incluye el trial

---

### C. MetriSync *(ya existe, uso interno para ahora)*

Genera contenido para las cuentas de Studio Link en TikTok/Instagram. No está directamente conectado al flujo de prospección — su función es crear prueba social que hace que los prospectos digan "ya vi de esto".

**Conexión futura con el orquestador:**
- Cuando un lead es convertido → MetriSync puede sugerir qué tipo de contenido funciona mejor con ese nicho
- Por ahora: independiente, solo Fernando lo usa

---

### D. Notificaciones *(simple, implementar rápido)*

Cuando un lead llega a `converted`:
1. **WhatsApp a Fernando** vía Twilio o WhatsApp Business API
   - Formato: "✅ Nuevo lead: @username (Dance Studio, 1.2k seguidores) — dijo que quiere el plan Scale"
2. **Log en Activity Log** de Outreach Engine (ya existe el sistema)
3. **Futuro:** webhook POST a Studio Link CRM para crear el Customer automáticamente

---

## Plan de implementación

### Fase 1 — Outreach Engine funcional en TikTok ✅ *completado*
- Bugs del worker corregidos
- Selectores resilientes en outreach.py
- Cola de aprobación HITL

### Fase 2 — Discovery y monitor reales
**Objetivo:** poder encontrar leads sin hacerlo a mano y detectar respuestas

Tareas:
1. Reverse-engineer del DOM actual de TikTok para hashtag search
2. Reescribir `discovery.py` — flujo: búsqueda por hashtag → extraer perfiles → guardar leads
3. Reescribir `monitor.py` — flujo: revisar inbox cada 10 min → detectar mensajes nuevos → emitir evento
4. Prueba end-to-end: descubrir 10 leads → aprobar → enviar DM → verificar detección de respuesta

### Fase 3 — Response Agent (MVP)
**Objetivo:** que el sistema pueda sostener una conversación básica y convertir leads calientes

Tareas:
1. Crear `services/agent.py` — integración con Claude API + tool use
2. Escribir knowledge base inicial (4 archivos markdown)
3. Sistema de historial de conversación en DB (`ConversationMessage` model)
4. Endpoint `POST /agent/process-reply` que recibe un evento `reply_received` y dispara el agente
5. Herramienta `escalate_to_human` con notificación WhatsApp básica
6. Prueba manual: simular una conversación completa y verificar que el agente responde bien

### Fase 4 — Validación interna (2 semanas)
**Objetivo:** confirmar que el sistema funciona end-to-end antes de ofrecerlo

KPIs a medir:
- DMs enviados → tasa de respuesta (objetivo: >10%)
- Respuestas → tasa de conversión a trial (objetivo: >5%)
- Leads descubiertos por hora de scraping
- Falsos positivos del agente (respuestas que Fernando tuvo que corregir)

Configuración:
- 45 DMs/día máximo
- Solo TikTok primero
- Fernando revisa TODOS los mensajes del agente los primeros 3 días

### Fase 5 — Instagram como segundo canal
Replicar discovery + outreach para Instagram usando el mismo worker/agente. El único cambio real son los selectores de Playwright.

### Fase 6 — Multi-tenant (para clientes)
**Objetivo:** poder configurar el sistema para Ale (We Dance), Viviana (Artec), etc.

Cambios necesarios:
- Campo `tenant_id` en todas las tablas
- Knowledge base por tenant (cada quien tiene su propio producto)
- Dashboard por tenant
- Configuración de límites por tenant (no todos van a querer 45 DMs/día)
- Panel de onboarding: "¿Qué hace tu negocio?" → genera knowledge base automáticamente con Claude

---

## Estructura de archivos (target final)

```
outreach-engine/
├── backend/
│   └── app/
│       ├── services/
│       │   ├── worker.py         ✅ arreglado
│       │   ├── outreach.py       ✅ arreglado
│       │   ├── discovery.py      🔴 reescribir
│       │   ├── monitor.py        🔴 reescribir
│       │   ├── warming.py        🟡 revisar selectores
│       │   ├── agent.py          ⬜ nuevo
│       │   └── notifications.py  ⬜ nuevo
│       ├── knowledge/            ⬜ nuevo directorio
│       │   ├── studio-link-overview.md
│       │   ├── plans-pricing.md
│       │   ├── faq.md
│       │   └── trial-signup.md
│       └── routers/
│           ├── leads.py          ✅ approval queue añadida
│           ├── agent.py          ⬜ nuevo router
│           └── ...
└── frontend/
    └── src/
        └── pages/
            ├── ApprovalQueue.jsx  ✅ nuevo
            ├── Conversations.jsx  ⬜ nuevo (ver historial del agente)
            └── ...
```

---

## Decisiones de arquitectura

| Decisión | Elección | Razón |
|----------|----------|-------|
| Modelo del agente | `claude-haiku-4-5` | Rápido, barato, suficiente para DMs |
| Framework del agente | Tool use nativo de Claude | Sin LangChain, menos complejidad |
| Detección de respuestas | Playwright polling cada 10 min | No hay API oficial de TikTok DMs |
| Notificaciones | Twilio WhatsApp API | Fernando ya lo usa |
| Multi-tenant (futuro) | `tenant_id` en DB existente | No crear nueva app, extender la actual |
| Knowledge base | Markdown estático | Simple, editable sin código |

---

## Lo que NO construimos (por ahora)

- ❌ App móvil
- ❌ API pública para terceros
- ❌ Integración con CRM de terceros (HubSpot, etc.)
- ❌ Analytics avanzado de conversaciones
- ❌ A/B testing de mensajes automatizado
- ❌ Soporte para redes adicionales (Facebook, LinkedIn) — después de validar IG
