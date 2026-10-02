# Email to REE requesting an ESIOS API token

Draft, 2026-08-21; purpose updated 2026-10-01 for the framework's instruments
(day-ahead forecasts as variation exogenous to the firms; spec §8 steps 5b–6).
**Address: `consultasios@ree.es`**

**Outcome: sent 2026-10-01, token received 2026-10-02** (in `.env`). REE's desk
replied that requests now go through the form at
https://www.esios.ree.es/es/token (since 2026-09-18); the token itself came by
automated email the same morning. It is personal, and REE asks that data already
downloaded is not requested again (`fetch_esios_spain.py` caches every month).
**Use 1777/1779/1775, not 541/542** as this draft asks: those two are
republished hourly up to delivery, while 1777 (wind), 1779 (solar) and 1775
(demand) are the forecasts published before 11:00 on D-1, from 2019.

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
ibérico (MIBEL) en el período 2018–2026. El trabajo analiza el comportamiento de
oferta de los agentes en el mercado diario, utilizando datos públicos de OMIE
(curvas de oferta y casación a nivel de unidad) junto con datos de generación y
demanda de REE.

Para completar el análisis necesito acceder a las **previsiones publicadas por
REE**, en particular:

- **Indicador 541** — previsión de producción eólica
- **Indicador 542** — previsión de producción solar
- Los indicadores de **previsión de demanda** correspondientes

Estas previsiones recogen la información disponible para los agentes al cierre
del mercado diario y no dependen de sus decisiones, por lo que son la fuente de
variación adecuada para analizar cómo responden sus ofertas. Las series
observadas de producción no sirven para ello, porque incluyen tanto el error de
previsión como las propias decisiones de oferta. Si fuera posible, agradecería
un acceso general a la API, ya que otros indicadores (por ejemplo, los programas
por unidad de programación) podrían ser útiles en fases posteriores.

El uso sería exclusivamente académico y sin ánimo de lucro, y por supuesto citaré
a Red Eléctrica de España y a ESIOS como fuente en la tesis y en cualquier
publicación derivada. El volumen de descarga sería moderado: series horarias para
el período indicado, obtenidas una sola vez.

Quedo a su disposición para cualquier información adicional que necesiten.

Muchas gracias por su tiempo y su ayuda.

Atentamente,

Theodor Mello
Ludwig-Maximilians-Universität München (LMU)
theodormello@gmail.com

---

## English version

**To:** consultasios@ree.es
**Subject:** Request for an ESIOS API token — academic research

Dear ESIOS team,

I am writing to request a personal API token for ESIOS.

I am a master's student writing a thesis on the Iberian electricity market
(MIBEL) over 2018–2026. The work analyses how market participants bid in the
day-ahead market, using OMIE's public unit-level bid and clearing data alongside
REE's generation and demand series.

To complete the analysis I need access to the **forecast series REE publishes**,
specifically:

- **Indicator 541** — wind generation forecast
- **Indicator 542** — solar generation forecast
- The corresponding **demand forecast** indicators

These forecasts capture the information available to participants at day-ahead
gate closure and do not depend on their decisions, so they are the right source
of variation for studying how offers respond. Realised output does not serve,
because it mixes forecast error with the bidding decisions themselves. If
possible, I would be grateful for general API access, since other indicators
(for example, the programmes by programming unit) may be useful later.

The use is purely academic and non-commercial, and I will of course cite Red
Eléctrica de España and ESIOS as the source in the thesis and any resulting
publication. The download volume would be modest — hourly series for the period
above, retrieved once.

I am happy to provide any further information you need.

Thank you for your time and help.

Kind regards,

Theodor Mello
Ludwig-Maximilians-Universität München (LMU)
theodormello@gmail.com

---

## When the token arrives

Create a gitignored `.env` at the repo root:

```
ESIOS_TOKEN=your_token_here
```

`scripts/lib/config.py` reads it. The token goes in the `x-api-key` header.
`fetch/fetch_esios_spain.py` is already written and has never been run.
