# Email to REE requesting an ESIOS API token

Draft, 2026-08-21. **Address: `consultasios@ree.es`**

Spanish first, since that is a Spanish-language support desk and the OMIE
request in this repo was also sent in Spanish. An English version follows if you
prefer it.

## Why this is being asked for

The day-ahead/intraday premium design
([`rq-sequential-market-premium.md`](rq-sequential-market-premium.md)) has one
unresolved threat: if wind is systematically under-forecast at gate closure,
intraday supply is higher and its price lower, producing a premium with **no
firm conduct at all** — and that error is correlated with wind output itself, so
it mimics the arbitrage channel exactly. Separating them requires the day-ahead
wind forecast the market actually saw.

Checked and ruled out first, so the request is a last resort rather than a first
one: `demanda.ree.es` publishes no renewable forecast endpoint (four candidate
names all return 404); ESIOS indicator 541 returns HTTP 403 without a token, as
does `/archives`, so the token-free route that works for archives 82 and 83 does
not extend to indicators; ENTSO-E requires its own token.

**Indicator 541 is the one that matters.** Ask for general access rather than a
single indicator — 542 (solar forecast) and the demand-forecast indicators would
serve the same design, and there is no reason to make a second request later.

---

## Spanish version

**Para:** consultasios@ree.es
**Asunto:** Solicitud de token de acceso a la API de ESIOS — investigación académica

Estimado equipo de ESIOS:

Le escribo para solicitar un token personal de acceso a la API de ESIOS.

Soy estudiante de máster y estoy realizando mi tesis sobre el mercado eléctrico
ibérico (MIBEL) en el período 2018–2026. El trabajo analiza la relación entre el
mercado diario y los mercados intradiarios, utilizando datos públicos de OMIE
(curvas de oferta y casación a nivel de unidad) junto con datos de generación y
demanda de REE.

Para completar el análisis necesito acceder a las **previsiones publicadas por
REE**, en particular:

- **Indicador 541** — previsión de producción eólica
- **Indicador 542** — previsión de producción solar
- Los indicadores de **previsión de demanda** correspondientes

Estas series son necesarias para distinguir la parte anticipada de la no
anticipada de la producción renovable en el momento del cierre del mercado
diario. Sin ellas no es posible separar el error de previsión del comportamiento
de los agentes, que es precisamente el objeto del estudio.

El uso sería exclusivamente académico y sin ánimo de lucro, y por supuesto citaré
a Red Eléctrica de España y a ESIOS como fuente en la tesis y en cualquier
publicación derivada. El volumen de descarga sería moderado: series horarias para
el período indicado, obtenidas una sola vez.

Quedo a su disposición para cualquier información adicional que necesiten.

Muchas gracias por su tiempo y su ayuda.

Atentamente,

Theodor Mello
[institución]
theodormello@gmail.com

---

## English version

**To:** consultasios@ree.es
**Subject:** Request for an ESIOS API token — academic research

Dear ESIOS team,

I am writing to request a personal API token for ESIOS.

I am a master's student writing a thesis on the Iberian electricity market
(MIBEL) over 2018–2026. The work analyses the relationship between the day-ahead
and intraday markets, using OMIE's public unit-level bid and clearing data
alongside REE's generation and demand series.

To complete the analysis I need access to the **forecast series REE publishes**,
specifically:

- **Indicator 541** — wind generation forecast
- **Indicator 542** — solar generation forecast
- The corresponding **demand forecast** indicators

These are needed to separate the anticipated from the unanticipated component of
renewable output at day-ahead gate closure. Without them it is not possible to
distinguish forecast error from participants' behaviour, which is precisely what
the study is about.

The use is purely academic and non-commercial, and I will of course cite Red
Eléctrica de España and ESIOS as the source in the thesis and any resulting
publication. The download volume would be modest — hourly series for the period
above, retrieved once.

I am happy to provide any further information you need.

Thank you for your time and help.

Kind regards,

Theodor Mello
[institution]
theodormello@gmail.com

---

## When the token arrives

Create a gitignored `.env` at the repo root:

```
ESIOS_TOKEN=your_token_here
```

`scripts/lib/config.py` reads it. The token goes in the `x-api-key` header.
`fetch/fetch_esios_spain.py` is already written and has never been run.
