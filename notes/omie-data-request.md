# Data request to OMIE — unit-to-agent mapping

**Status: draft, not sent.** Send from your university address.

**Where.** Verify the current address on <https://www.omie.es/es/contacto>
before sending. Consider addressing Market Operations (*Operación del
Mercado*) rather than the general inbox.

**Design of the draft.** It opens with a single concrete example rather than
background, states the ask in one sentence, and offers a fallback question
that costs OMIE nothing to answer. It also lists the public sources already
checked, so the reply cannot simply point back at `pdbce`.

---

## English

> **Subject:** Academic data request — which market agent submits the offers of
> each offer unit
>
> Dear Sir or Madam,
>
> **The problem in one example.** In your published day-ahead offer curves
> (`curva_pbc_uof`) I can see that unit `EDPSVD1` offered energy on a given
> day, at what prices, and how much cleared. What I cannot determine from any
> public file is **which market agent submits those offers**. The same is true
> for most units that account for a large share of traded volume.
>
> **What I am asking for.** The correspondence between the offer unit code
> (`unidad de oferta`) and the market agent (`sujeto de mercado`) that submits
> its offers, ideally with the dates over which each association was valid, for
> generation units between 2018 and 2026.
>
> **Why it matters.** Measures of competition are defined at the level of the
> entity that decides the offer, not the individual unit. Assessing the demand
> facing one participant requires knowing which units that participant
> controls. Without this correspondence, only a single market-wide aggregate
> can be computed, and no statement can be made about any individual firm.
>
> **What I have already checked**, so as not to ask you for something already
> public:
>
> - `pdbce` contains a corporate group tag, but it is populated for about 2% of
>   units.
> - `cab` and `det` contain no agent field.
> - REE's ESIOS registries (archives 81, 82 and 83) publish the *sujeto de
>   mercado*, but only for units the system operator schedules. This excludes
>   the aggregated commercial units, which are precisely the ones carrying most
>   volume.
>
> **If the full correspondence is not something you can share**, any of the
> following would help, in descending order of usefulness:
>
> 1. The unit-to-agent correspondence for generation units, 2018–2026.
> 2. The same for a single representative year.
> 3. **Simply confirming whether the alphabetic prefix of the unit code is
>    assigned per agent.** A yes or no would let me group units belonging to the
>    same participant without your disclosing any agent identity at all.
>
> Point 3 alone would resolve most of the difficulty, and I would be grateful
> for an answer to it even if the first two are not possible.
>
> This is academic, non-commercial work for a master's thesis. I am happy to
> cite OMIE as the source, share the analysis before publication, and sign any
> confidentiality or acceptable-use undertaking you require. If this should be
> directed to another department, I would be grateful if you could tell me
> where.
>
> Thank you for your time.
>
> Yours faithfully,
> [Name] — [Programme, University] — [Email]

---

## Español

> **Asunto:** Solicitud académica — qué sujeto de mercado presenta las ofertas
> de cada unidad de oferta
>
> Estimados señores:
>
> **El problema, con un ejemplo concreto.** En las curvas de oferta del mercado
> diario que ustedes publican (`curva_pbc_uof`) puedo ver que la unidad
> `EDPSVD1` ofertó energía un día determinado, a qué precios y qué cantidad
> resultó casada. Lo que no puedo determinar con ningún fichero público es
> **qué sujeto de mercado presenta esas ofertas**. Lo mismo ocurre con la
> mayoría de las unidades que concentran una parte importante del volumen
> negociado.
>
> **Lo que solicito.** La correspondencia entre el código de unidad de oferta y
> el sujeto de mercado que presenta sus ofertas, preferiblemente con las fechas
> de validez de cada asociación, para unidades de generación entre 2018 y 2026.
>
> **Por qué es necesaria.** Las medidas de competencia se definen a nivel de la
> entidad que decide la oferta, y no de la unidad individual. Para evaluar la
> demanda a la que se enfrenta un participante concreto es imprescindible saber
> qué unidades controla. Sin esta correspondencia solo puede calcularse un
> agregado de mercado, y no cabe afirmar nada sobre ninguna empresa concreta.
>
> **Lo que ya he comprobado**, para no solicitarles algo que ya sea público:
>
> - `pdbce` incluye una etiqueta de grupo empresarial, pero está cumplimentada
>   para en torno al 2% de las unidades.
> - `cab` y `det` no contienen ningún campo de agente.
> - Los registros de ESIOS (REE, archivos 81, 82 y 83) publican el sujeto de
>   mercado, pero únicamente para las unidades que programa el operador del
>   sistema. Esto excluye las unidades comerciales agregadas, que son
>   precisamente las que concentran mayor volumen.
>
> **Si no fuera posible facilitar la correspondencia completa**, cualquiera de
> las siguientes opciones me sería de gran ayuda, por orden de utilidad:
>
> 1. La correspondencia unidad–sujeto de mercado para unidades de generación,
>    2018–2026.
> 2. La misma información para un único año representativo.
> 3. **Simplemente confirmar si el prefijo alfabético del código de unidad se
>    asigna por agente.** Un sí o un no me permitiría agrupar las unidades de un
>    mismo participante sin que ustedes revelen la identidad de ningún agente.
>
> El punto 3 por sí solo resolvería la mayor parte de la dificultad, y les
> agradecería una respuesta a esa pregunta aunque los dos primeros puntos no
> sean posibles.
>
> Se trata de un trabajo académico y sin fines comerciales, correspondiente a un
> trabajo de fin de máster. Puedo citar a OMIE como fuente, compartir el
> análisis antes de su publicación y firmar el compromiso de confidencialidad o
> de uso que consideren necesario. Si la solicitud debiera dirigirse a otro
> departamento, les agradecería que me indicaran dónde.
>
> Muchas gracias por su tiempo y atención.
>
> Atentamente,
> [Nombre] — [Programa, Universidad] — [Correo electrónico]

---

## Why it is built this way

- **Concrete example first.** `EDPSVD1` makes the gap unmistakable in two
  sentences. A recipient who works with these files daily will recognise it
  immediately.
- **Point 3 is the one to push.** It asks OMIE to confirm a structural fact,
  not to release data. It is cheap for them to answer, discloses nothing
  commercially sensitive, and would convert several hypotheses in
  [`unmapped-prefixes-to-confirm.md`](unmapped-prefixes-to-confirm.md) into
  derivations.
- **Listing what was checked** prevents a one-line reply pointing back at
  `pdbce` or ESIOS.
- Do not promise the data stays unpublished if you intend to publish aggregate
  results. The offer as written — share before publication, sign an
  undertaking — is the honest version.
