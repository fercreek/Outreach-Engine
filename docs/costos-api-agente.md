# Costos de API del agente (Anthropic vs Gemini)

Documento de referencia para estimar gasto mensual del Response Agent y comparar modelos. Los precios por token cambian; conviene revisar las fuentes oficiales al hacer presupuestos.

## Fuentes oficiales

- [Anthropic — Claude API pricing](https://docs.anthropic.com/en/about-claude/pricing)
- [Google — Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)

## Ejecución en Mac (u otro entorno local)

| Concepto | Notas |
|----------|--------|
| **API (Anthropic / Gemini)** | El costo es por **tokens**; es el mismo si el backend corre en tu Mac, en un VPS o en la nube. |
| **Electricidad / hardware** | Orden de magnitud bajo para uso típico (unas horas al día); irrelevante frente a la factura de API en volúmenes de docenas o cientos de conversaciones al mes. |
| **Twilio / WhatsApp** | Costo aparte si usas escalación o notificaciones por WhatsApp; no incluido en las tablas de solo modelo. |

## Configuración actual en código

- Modelo por defecto: `anthropic_model` en `backend/app/config.py` (p. ej. familia Haiku 3.5).
- El agente (`services/agent.py`) envía system + knowledge base + historial + tools; cada `process_reply` puede implicar **varias** llamadas al modelo (rondas de tool use).

## Precios de referencia (USD por millón de tokens, tier estándar)

Cifras orientativas según documentación; ver enlaces arriba para valores vigentes.

### Anthropic

| Modelo | Input ($/MTok) | Output ($/MTok) |
|--------|------------------|-----------------|
| Haiku 3.5 | 0,80 | 4,00 |
| Haiku 4.5 | 1,00 | 5,00 |
| Opus 4.6 | 5,00 | 25,00 |

### Gemini (tier Paid, ejemplos de la doc)

| Modelo | Input ($/MTok) | Output ($/MTok) |
|--------|----------------|-----------------|
| Gemini 3.1 Flash-Lite | 0,25 | 1,50 |
| Gemini 3 Flash | 0,50 | 3,00 |
| Gemini 3.1 Pro (prompts ≤200k) | 2,00 | 12,00 |

Gemini también ofrece **free tier** con límites; producción suele usar **Paid**.

## Supuestos para estimar un mes

Alineado al límite del producto (`max_dms_per_day` ≈ 45) y a un objetivo típico de **~10% de respuesta**:

- **~4–5 respuestas/día** → **~135 eventos/mes** donde corre el agente (monitor o `POST /agent/process-reply`).
- Por evento, orden de magnitud **conservador** para comparar modelos entre sí:
  - **~24.000 tokens de entrada** en total (system + KB + historial + resultados de tools en varias rondas),
  - **~3.000 tokens de salida** en total.

Fórmula por evento (USD):

```text
(24/1000 × precio_input) + (3/1000 × precio_output)
```

Si el uso real es distinto, el costo mensual escala **aproximadamente** con el número de eventos y con los tokens reales (medir en dashboard de proveedor o logs).

## Estimación mensual (~135 eventos, solo API)

| Opción | ~USD / evento | ~USD / mes |
|--------|----------------|------------|
| Gemini 3.1 Flash-Lite | ~0,011 | ~1,5 |
| Gemini 3 Flash | ~0,021 | ~2,8 |
| Haiku 3.5 | ~0,031 | ~4,2 |
| Haiku 4.5 | ~0,039 | ~5,3 |
| Gemini 3.1 Pro | ~0,084 | ~11 |
| Opus 4.6 | ~0,20 | ~26 |

## Comparación breve

| Criterio | Gemini Flash / Flash-Lite | Haiku | Opus |
|----------|---------------------------|-------|------|
| Costo suele ser | Más bajo en la tabla | Intermedio | Más alto |
| Integración hoy en el repo | Requiere otro SDK y adaptar tools | Nativa (`anthropic` + `anthropic_model`) | Misma API Anthropic; solo cambiar modelo |
| Uso típico | Alto volumen, presupuesto ajustado | Default razonable para agente de DM | Cuando el costo del error (tiempo, marca) justifica el precio |

## Mejor modelo vs costo-beneficio

- **Haiku** suele ser el equilibrio **costo / latencia / calidad** para conversaciones en español con tools.
- **Opus** multiplica el costo por token; conviene si reduces errores caros o conversaciones que de otro modo requerirían mucha intervención humana.
- **Gemini** puede bajar la factura respecto a Haiku, pero hay que sumar el coste de **implementar y mantener** un segundo proveedor si aún no está integrado.

## Próximo paso para cifras reales

Sustituir los supuestos (24k / 3k tokens y 135 eventos) por:

1. Número real de llamadas al modelo al mes.
2. Promedio de tokens de entrada y salida por llamada (panel del proveedor o instrumentación).

---

*Última revisión conceptual: marzo 2026. Actualizar precios desde las URLs oficiales antes de decisiones de compra.*
