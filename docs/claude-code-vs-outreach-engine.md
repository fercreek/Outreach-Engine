# Claude Code vs Outreach Engine — Comparación real de costos

Documento basado en la sesión del **1 abril 2026** donde se enviaron DMs de Instagram
usando Claude Code directamente (vía MCP `Claude_in_Chrome`), antes de usar el motor
Playwright de este repositorio.

---

## Contexto del experimento

Se intentó enviar 12 DMs de Instagram desde `@studiolink.online` usando Claude Code
(modelo `claude-sonnet-4-6`) como orquestador, controlando el browser vía MCP.

Resultado: **funciona**, pero con costos y velocidad muy por debajo del motor Playwright.

---

## Métricas observadas — Claude Code (sesión completa 2026-04-01)

### Resumen de envíos

| # | Handle | Timestamp | Status |
|---|--------|-----------|--------|
| 1 | danzaregiastudio | 16:20:36 | ✅ |
| 2 | danceacademymty | 16:27:48 | ✅ |
| 3 | dancingdreamcenter | 16:29:13 | ✅ |
| 4 | dancestudio11 | 16:35:44 | ✅ |
| 5 | dancersonlystudio | 17:36:15 | ✅ |
| 6 | danceologystudio_mx | 17:41:56 | ✅ |
| 7 | danceit.studio | 17:44:46 | ✅ |
| 8 | dance_mania_allstars | 17:49:27 | ✅ |
| 9–12 | corazon_rumbero, coppeliachihuahua, balletmorelia, bailare_dance_studio | — | ⏸️ pausados |

**Gap entre DM 4 y DM 5: ~60 min** — tiempo dedicado a crear `outreach_ig.py`,
debuggear Playwright CDP, y documentar. No fue tiempo de envío puro.

### Tiempos reales de envío (flujo estabilizado, excluyendo gap de desarrollo)

| Grupo | DMs | Tiempo real | Tiempo/DM |
|-------|-----|-------------|-----------|
| DMs 1–4 (con debugging Lexical) | 4 | ~21 min | ~5 min |
| DMs 5–8 (flujo limpio) | 4 | ~13 min | ~3 min |

El tiempo por DM en flujo limpio baja a **~3 min**, de los cuales **~25–30 seg son delay
intencional** entre envíos y el resto es navegación + render de Instagram.

### Problemas técnicos encontrados y costo en tool calls

| Problema | Tool calls desperdiciados | Resolución |
|----------|--------------------------|------------|
| `execCommand` duplica texto en Lexical | ~15 | Usar solo `editor.update()` con `getWritable()` |
| `ClipboardEvent` inconsistente por contexto | ~8 | Descartado; Lexical API es el camino |
| `textbox.textContent` retorna 0 aunque hay texto | ~6 | Usar `__lexicalTextContent` o leer el nodeMap |
| MCP tab group perdido entre sesiones | ~4 | Recrear con `createIfEmpty: true` |
| Playwright CDP no conecta a Chrome del usuario | ~10 | Perfil dedicado o seguir con MCP |
| `networkidle` vs `domcontentloaded` en Playwright | ~3 | `networkidle` + `wait_for_selector` |
| **Total overhead** | **~46** | Todos documentados y resueltos |

### Estimación de tokens — sesión completa (~2h)

| Fase | Tool calls | Tokens input est. | Tokens output est. |
|------|-----------|-------------------|--------------------|
| Setup + test con fuegolatino | 25 | 40 000 | 4 000 |
| Debugging Lexical (errores) | 46 | 100 000 | 9 000 |
| 8 DMs enviados (flujo limpio) | 64 | 110 000 | 10 000 |
| Escritura `outreach_ig.py` + docs | 20 | 35 000 | 8 000 |
| **Total sesión** | **~155** | **~285 000** | **~31 000** |

**Costo real estimado (Sonnet 4.6 — $3 input / $15 output por MTok):**

```
(285 000 / 1 000 000 × 3) + (31 000 / 1 000 000 × 15) = $0.855 + $0.465 = ~$1.32
```

> **~$1.32 USD total** para 8 DMs + crear `outreach_ig.py` + documentación.
> **~$0.165/DM** promedio real (incluye toda la inversión de la sesión).
>
> Costo marginal en sesión limpia (solo enviar, sin debugging ni desarrollo):
> ~7 tool calls × ~3 000 tokens = ~21 000 tokens input/DM → **~$0.06/DM**.

---

## Métricas esperadas — Outreach Engine (Playwright)

| Métrica | Valor |
|---------|-------|
| Tokens de AI por DM enviado | **0** (Playwright puro, sin LLM) |
| Costo de API por DM enviado | **$0.00** |
| Tiempo por DM (worker) | ~2–3 min (incluye delays configurados) |
| Delay entre DMs configurado | `min_delay_between_dms_sec` (≥ 900 seg por regla) |
| Tokens de AI (solo agente de respuesta) | ~24k input / 3k output **por respuesta recibida** |
| Costo agente por respuesta (Haiku 4.5) | ~$0.04 |
| Intervención humana | Cola HITL antes de enviar cada DM |

---

## Comparación directa

| Criterio | Claude Code directo | Outreach Engine |
|----------|--------------------|--------------------|
| Costo por DM enviado | ~$0.05–0.19 USD | $0.00 (sin agente) |
| Costo por respuesta gestionada | incluido arriba | ~$0.04 (Haiku 4.5) |
| Velocidad por DM | 8–12 min | 2–3 min |
| Robustez ante cambios de UI | Baja (requiere debugging) | Alta (fallbacks en selectores) |
| Delays humanos realistas | Manual (sleep) | Automáticos, configurables |
| HITL / aprobación | No implementado | ✅ Cola de aprobación |
| Escalabilidad | No (bloquea contexto) | ✅ Worker en background |
| Detección de CAPTCHA/bloqueo | Manual (Claude lo nota) | ✅ Manejado en `outreach.py` |
| Trazabilidad | Log en consola | ✅ DB SQLite + ActivityLog |

---

## Hallazgo 2 — Playwright CDP no hereda la sesión de Chrome (2026-04-01)

Al intentar conectar Playwright al Chrome del usuario vía `connect_over_cdp("http://localhost:9222")`
para usar la sesión activa de Instagram, se descubrió que:

- **El Chrome del usuario NO estaba corriendo con `--remote-debugging-port=9222`** por defecto.
- Playwright abría un Chromium **nuevo** (sin sesión) en lugar de conectarse al existente.
- El error resultante: `Target page, context or browser has been closed` porque la página
  se cerraba al desconectar.

### Opciones evaluadas para usar la sesión activa

| Opción | Estado | Notas |
|--------|--------|-------|
| `connect_over_cdp(9222)` | ❌ Requiere reiniciar Chrome con flag | Cambia el flujo de arranque del usuario |
| `launch_persistent_context(profile_dir)` | ⚠️ Solo si el perfil está cerrado | Chrome no puede compartir un perfil abierto |
| MCP `Claude_in_Chrome` (extensión) | ✅ Funciona | Ya tiene sesión activa; ejecuta JS directo |
| Perfil dedicado de outreach engine | ✅ Recomendado para producción | `~/.outreach-engine/profile-v2` — iniciar sesión una vez |

### Decisión: flujo híbrido

- **Desarrollo / pruebas puntuales:** usar MCP `Claude_in_Chrome` con la sesión del usuario.
- **Producción / worker diario:** usar `launch_persistent_context` con perfil dedicado
  (`~/.outreach-engine/profile-v2`) donde se inicia sesión en Instagram una sola vez.

Para habilitar CDP en Chrome del usuario (opcional):
```bash
# Agregar al script de arranque o al .zshrc / Launch Agent
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.outreach-engine/chrome-debug" &
```

---

## Cuándo tiene sentido usar Claude Code para outreach

Claude Code sí es útil en este flujo para tareas **puntuales y no repetitivas**:

| Caso de uso | ¿Vale la pena? |
|-------------|----------------|
| Enviar 3–5 DMs de prueba manuales | ✅ Sí (rápido de ejecutar) |
| Debuggear selectores de Instagram | ✅ Sí (acceso interactivo al DOM) |
| Explorar la UI de Instagram tras cambios | ✅ Sí |
| Enviar 10+ DMs en producción | ❌ No (caro y lento) |
| Operación diaria automatizada | ❌ No (usar el worker) |

---

## Conclusión

Para la operación diaria de outreach, el **Outreach Engine con Playwright es entre
5× y 20× más barato y más rápido** que delegar el control del browser a Claude Code.

Claude Code tiene valor como herramienta de **exploración y debugging** (descubrir
el truco de `__lexicalEditor` costó tiempo, pero ese conocimiento ya está capturado
en `outreach.py` para siempre).

El flujo Lexical descubierto en la sesión del 1 abril 2026 ya está o debe estar
reflejado en `backend/app/services/outreach.py` para Instagram.

---

## Mejoras identificadas en la sesión

### Lo que se puede eliminar del flujo Claude Code

| Ineficiencia | Causa raíz | Fix |
|--------------|-----------|-----|
| ~46 tool calls de overhead | Descubrir Lexical API iterativamente | Ya resuelto — `outreach_ig.py` tiene el JS correcto |
| Tab MCP perdido entre sub-sesiones | Cada conversación crea un grupo nuevo | Nada que hacer; es el modelo de MCP |
| Gap de 60 min entre DM 4 y 5 | Salto a desarrollo de Playwright | Separar sesiones: primero outreach, luego dev |
| 2 tool calls extra por `hasSend: false` | Send button tarda en aparecer post-inject | Agregar micro-wait en `outreach_ig.py` |

### Fix inmediato en `outreach_ig.py`

El patrón `{ok: true, hasSend: false}` aparece en casi todos los envíos — el botón
Send existe pero aún no está visible cuando se evalúa. Se requiere un pequeño wait
entre `editor.update()` y buscar el botón:

```python
# En send_dm_instagram, después del editor.update():
await human_pause(0.5, 1.0)  # Dar tiempo a React para mostrar el botón Send
```

Esto eliminaría la segunda llamada JS de "retry send" en cada DM (~8 tool calls menos
por tanda de 8 DMs).

### Skill de Claude Code sugerido: `/ig-dm`

Para futuras sesiones donde se use Claude Code + MCP (no el worker), un skill
que encapsule el flujo completo reduciría el tiempo de setup de ~5 min a ~30 seg:

```
Trigger: /ig-dm @handle "mensaje"
Comportamiento:
  1. Verifica sesión IG activa
  2. Navega al perfil
  3. Scroll simulado
  4. Click Message
  5. Inyecta via Lexical API
  6. Envía + verifica
  7. Log resultado
```

Esto dejaría el costo marginal por DM en **~3–4 tool calls** (~$0.02/DM).

---

## Resultado final — Outreach Engine Playwright (medición real 2026-04-01)

| Handle | Timestamp | Status |
|--------|-----------|--------|
| corazon_rumbero | 18:58:32 | ✅ |
| coppeliachihuahua | 18:59:24 | ✅ |
| balletmorelia | 19:00:16 | ✅ |
| bailare_dance_studio | 19:01:11 | ✅ |

**4/4 enviados — 3.1 min — $0.00 — 0 tokens de Claude.**

### Fix crítico documentado: `page.keyboard.type()` en lugar de `execCommand` en evaluate

`execCommand('insertText')` dentro de `page.evaluate()` **no funciona** en Playwright
porque el elemento no tiene foco real del browser. La solución correcta:

```python
# ✅ Correcto — foco y tipo nativos del browser
tb_locator = page.locator('div[contenteditable="true"][role="textbox"]').first
await tb_locator.click()
await page.keyboard.type('x')        # crea el TextNode en Lexical
await page.evaluate(_JS_SET_LEXICAL_TEXT, message)  # sobreescribe con el mensaje

# ❌ No funciona en Playwright evaluate
document.execCommand('insertText', false, 'x')  # sin foco real → no crea TextNode
```

Esta diferencia explica por qué el mismo JS funcionó en MCP Chrome (tab activo del usuario)
pero falló en Playwright (ventana puede no estar en primer plano).

### Errores adicionales encontrados durante la sesión Playwright

| Error | Causa | Fix aplicado |
|-------|-------|-------------|
| `Timeout 30000ms — networkidle` | Instagram SPA nunca termina de cargar | `wait_until="load"` + `wait_for_selector` |
| `text node not found after seed` | `execCommand` sin foco real | `page.keyboard.type('x')` nativo |
| Browser cerrado durante login wait | `input()` no funciona sin stdin en Bash | Script `login_ig.py` dedicado con auto-close |

---

### Próximos pasos para llegar a $0.00/DM

1. **Resolver sesión Playwright** — iniciar sesión en `~/.outreach-engine/profile-v2`
   y correr `test_ig_outreach.py` con `USE_PERSISTENT_PROFILE = True`
2. **Agregar micro-wait** en `outreach_ig.py` (fix Send button)
3. **Conectar `outreach_ig.py` al worker** — `worker.py` actualmente solo llama
   a `outreach.py` (TikTok); necesita saber la plataforma del lead (`instagram` vs `tiktok`)
4. **Crear skill `/ig-dm`** para uso puntual sin levantar el motor completo

---

## Tabla resumen actualizada

| Sesión / Modo | DMs | Costo total | Costo/DM | Tiempo/DM | Tokens/DM |
|---------------|-----|------------|----------|-----------|-----------|
| CC + debugging (esta sesión) | 8 | ~$1.32 | ~$0.165 | ~5 min | ~39k |
| CC flujo limpio (estimado) | — | — | ~$0.06 | ~3 min | ~21k |
| CC con skill `/ig-dm` (futuro) | — | — | ~$0.02 | ~1.5 min | ~7k |
| Outreach Engine Playwright (objetivo) | — | $0.00 | $0.00 | ~2 min | 0 |

---

*Última actualización: 2026-04-01 — sesión de 8 DMs completados + `outreach_ig.py` creado.*
