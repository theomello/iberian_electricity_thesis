# Data request to OMIE — unit-to-agent mapping

**Status: draft, not sent.** Send from your university address; a student
address materially raises the response rate for academic requests.

**Where to send.** OMIE publishes a contact form at
<https://www.omie.es/es/contacto> and a general address of the form
`info@omie.es`. Verify the current address on the site before sending rather
than trusting this note — and consider addressing it to Market Operations
(*Operación del Mercado*) rather than the general inbox.

**What we are asking for, precisely.** The correspondence between the offer
unit code (`unidad de oferta`, the 7-character code in `curva_pbc_uof` and
`cab`) and the market agent (`sujeto de mercado`) that submits its offers,
including the validity dates of each association.

**Why it is not already public.** Every public route has been checked and is
recorded in `CLAUDE.md`: OMIE's `pdbce` carries a corporate tag for 2.4% of
units; `cab` and `det` carry no agent field; REE's ESIOS registries (archives
81/82/83) publish the agent but only for units the system operator dispatches,
which excludes the commercial aggregation vehicles that carry most volume.
Mention this in the email — it shows the request is a last resort, not a
first one, and it tells them exactly which gap to fill.

---

## English

> **Subject:** Academic data request — mapping of offer units to market agents
>
> Dear Sir or Madam,
>
> I am a master's student writing a thesis on competition in the Iberian
> day-ahead electricity market, using OMIE's published unit-level offer curves
> (`curva_pbc_uof`) together with the offer headers (`cab`) for the period
> 2018–2026. I am grateful for how much OMIE makes openly available; the
> rejected-offer data in particular makes analysis possible that most markets
> do not permit.
>
> I am writing to ask whether it is possible to obtain one piece of
> information that I have not been able to find in the public files: **the
> correspondence between each offer unit (`unidad de oferta`) and the market
> agent (`sujeto de mercado`) that submits its offers**, ideally with the
> dates over which each association was valid.
>
> This matters because measures of competition are defined at the level of the
> decision-maker rather than the individual unit: assessing the residual demand
> facing a given participant requires knowing which units that participant
> controls. Without the correspondence, only a market-wide aggregate can be
> computed.
>
> I have checked the public sources before writing. The `pdbce` files include a
> corporate tag for a small share of units; `cab` and `det` do not contain an
> agent field; and REE's ESIOS registries publish the *sujeto de mercado* only
> for units that the system operator schedules, which excludes the aggregated
> commercial units that account for a large share of traded volume.
>
> If a full correspondence is not something OMIE is able to share, I would be
> grateful for any of the following, in descending order of usefulness:
>
> 1. The unit-to-agent correspondence for generation units, 2018–2026.
> 2. The same for a single representative year.
> 3. Confirmation of whether the alphabetic prefix of the unit code is assigned
>    per agent, which would let me group units without identifying the agent.
>
> The work is academic and non-commercial. I am happy to cite OMIE as the
> source, to share the resulting analysis before publication, and to sign any
> confidentiality or acceptable-use undertaking you require. If the request
> should be directed to a different department, I would be grateful if you
> could tell me where to send it.
>
> Thank you for your time.
>
> Yours faithfully,
> [Name]
> [Programme, University]
> [Email]

---

## Español

> **Asunto:** Solicitud de datos con fines académicos — correspondencia entre
> unidades de oferta y sujetos de mercado
>
> Estimados señores:
>
> Soy estudiante de máster y estoy realizando mi trabajo de fin de máster sobre
> la competencia en el mercado diario ibérico de electricidad, utilizando las
> curvas de oferta por unidad publicadas por OMIE (`curva_pbc_uof`) junto con
> las cabeceras de las ofertas (`cab`) para el periodo 2018–2026. Agradezco el
> volumen de información que OMIE publica de forma abierta; en particular, la
> disponibilidad de las ofertas no casadas permite un análisis que la mayoría
> de los mercados no hace posible.
>
> Les escribo para consultar si sería posible obtener un dato que no he logrado
> encontrar en los ficheros públicos: **la correspondencia entre cada unidad de
> oferta y el sujeto de mercado que presenta sus ofertas**, preferiblemente con
> las fechas de validez de cada asociación.
>
> Esta correspondencia es relevante porque las medidas de competencia se
> definen a nivel del agente que decide la oferta, y no de la unidad
> individual: para evaluar la demanda residual a la que se enfrenta un
> participante es necesario saber qué unidades controla. Sin dicha
> correspondencia solo puede calcularse un agregado de mercado.
>
> He revisado previamente las fuentes públicas. Los ficheros `pdbce` incluyen
> una etiqueta de grupo empresarial para una pequeña parte de las unidades;
> `cab` y `det` no contienen un campo de agente; y los registros de ESIOS (REE)
> publican el sujeto de mercado únicamente para las unidades que programa el
> operador del sistema, lo que excluye las unidades comerciales agregadas que
> representan una parte importante del volumen negociado.
>
> Si no fuera posible facilitar la correspondencia completa, les agradecería
> cualquiera de las siguientes opciones, por orden de utilidad:
>
> 1. La correspondencia unidad–sujeto de mercado para unidades de generación,
>    2018–2026.
> 2. La misma información para un único año representativo.
> 3. La confirmación de si el prefijo alfabético del código de unidad se asigna
>    por agente, lo que me permitiría agrupar unidades sin identificar al
>    agente.
>
> Se trata de un trabajo académico y sin fines comerciales. Puedo citar a OMIE
> como fuente, compartir el análisis resultante antes de su publicación y
> firmar el compromiso de confidencialidad o de uso que consideren necesario.
> Si la solicitud debiera dirigirse a otro departamento, les agradecería que me
> indicaran dónde enviarla.
>
> Muchas gracias por su tiempo y atención.
>
> Atentamente,
> [Nombre]
> [Programa, Universidad]
> [Correo electrónico]

---

## Notes on the drafts

- **Option 3 is the cheap win.** If OMIE simply confirms that the code prefix
  is assigned per agent, the prefix clustering becomes a documented fact rather
  than an inference, and coverage jumps without their releasing anything
  commercially sensitive. Keep it in — it is the request most likely to be
  granted.
- The email states what has already been checked. That is deliberate: it
  prevents a reply that points back at `pdbce`.
- Do not claim the data will remain unpublished if you intend to publish
  aggregate results; the offer above (share before publication, sign an
  undertaking) is the honest version.
