# Outreach Engine — Frontend

Panel de control para el sistema de prospección automatizada de Studio Link.

**Stack:** React 19 + Vite + React Router v6 · Sin Tailwind, CSS variables propias.

---

## Levantar

```bash
npm install
npm run dev
# http://localhost:5173
```

Requiere el backend corriendo en `http://localhost:8000`.

---

## Páginas

| Ruta | Página | Estado | Descripción |
|------|--------|--------|-------------|
| `/` | Dashboard | ✅ | Métricas generales: leads por estado, DMs de hoy |
| `/leads` | Lead Center | ✅ | CRUD de leads, filtros por nicho y estado |
| `/approval` | Approval Queue | ✅ | **HITL** — revisar leads y aprobar/rechazar antes del DM |
| `/templates` | Templates | ✅ | Gestión de plantillas con spintax |
| `/dispatch` | Dispatch Center | ✅ | Crear/iniciar/pausar jobs de envío |
| `/logs` | Activity Log | ✅ | Consola en tiempo real (SSE) |
| `/blacklist` | Blacklist | ✅ | Cuentas excluidas permanentemente |
| `/conversations` | Conversations | ⬜ Fase 3 | Historial del agente de respuesta por lead |

---

## Flujo de uso (orden correcto)

```
1. Templates      → crear plantilla con spintax para el DM inicial
2. Lead Center    → importar leads manualmente (o esperar Fase 2 discovery)
3. Approval Queue → revisar cada lead, ver preview del mensaje, aprobar ✅ o rechazar 🚫
4. Dispatch       → crear job → iniciar envío
5. Activity Log   → monitorear en tiempo real
6. Conversations  → (Fase 3) ver respuestas y seguimiento del agente
```

---

## Estructura

```
src/
├── api/
│   └── client.js          ← TODAS las llamadas al backend van aquí
├── components/
│   ├── Sidebar.jsx         ← navegación principal
│   ├── StatusBadge.jsx     ← badge de estado de lead/job
│   └── Toast.jsx           ← notificaciones (useToast hook)
└── pages/
    ├── Dashboard.jsx
    ├── LeadCenter.jsx
    ├── ApprovalQueue.jsx   ← HITL — central del flujo
    ├── Templates.jsx
    ├── Dispatch.jsx
    ├── ActivityLog.jsx
    ├── BlacklistPage.jsx
    └── Conversations.jsx   ← (Fase 3, pendiente)
```

---

## Añadir una nueva página

1. Crear `src/pages/NuevaPagina.jsx`
2. Añadir ruta en `App.jsx`
3. Añadir item en `Sidebar.jsx` → array `navItems`
4. Si hay nuevos endpoints: añadir funciones en `api/client.js`

## Sistema de diseño

CSS variables definidas en `src/index.css`. Las clases del sistema:

```
.card                  contenedor principal
.page-header           flex row título + acciones
.btn                   botón base neutro
.btn.btn-play          botón primario (azul)
.btn.btn-danger        botón destructivo (rojo)
.data-table            tabla con hover
```

No usar Tailwind ni librerías de UI externas — solo las clases del sistema.
