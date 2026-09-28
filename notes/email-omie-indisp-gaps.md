# Email to OMIE — incomplete `indisp` monthly zips

Draft, 2026-09-28. **Not sent.** Spanish, matching the language of their replies
on ticket #12541. An English version and the full list of affected months follow.

## How to send

Send it to **Ayuda.InfoPublica@omie.es**, the public-information desk that
answered ticket #12541 (see [`omie-email-ready-to-send.txt`](omie-email-ready-to-send.txt)).
Mentioning the earlier ticket gives them context. If you would rather open a new
case, use the envelope icon at the bottom right of
https://www.portal-asistencia.omie.es/questions_sections, section
"00. Información pública de OMIE".

Paste the table from the appendix at the end of the email, or attach it. It is
what lets them find the fault without redoing our work.

**What is established and what is not.** The gaps are at source: re-downloading
on 2026-09-28 gave files identical to the 2026-08-21 copies, and OMIE serves no
daily `indisp` files. The nightly-append reading comes from the zips' own member
timestamps. That is strong evidence, but the email presents it as an
observation, since only OMIE knows its build process. Full detail is in the
`indisp` section of `CLAUDE.md`.

---

## Spanish

**Asunto:** Ficheros de indisponibilidades (`indisp`): ZIP mensuales incompletos
en 2023–2026

Estimados señores:

Les escribo de nuevo en relación con mi tesis de máster sobre el mercado diario
de MIBEL (consulta #12541, en la que me facilitaron los listados de unidades
ofertantes; les reitero mi agradecimiento).

Al procesar los ficheros públicos de indisponibilidades de unidades españolas
(`indisp`), he observado que **43 de los 100 ficheros ZIP mensuales** publicados
entre enero de 2018 y mayo de 2026 no contienen todos los días del mes. Casi
todos los casos se concentran a partir de febrero de 2023. Algunos ejemplos:

- `indisp_202401.zip` contiene únicamente del 1 al 20 de enero de 2024;
- `indisp_202403.zip` contiene únicamente el 1 de marzo de 2024;
- `indisp_202605.zip` contiene únicamente el 1 y el 2 de mayo de 2026.

Volví a descargarlos el 28/09/2026 y son idénticos a los que descargué en agosto,
por lo que no parece un problema de la descarga. Tampoco he encontrado en el
portal los ficheros diarios de los días que faltan.

Por las fechas internas de los ficheros contenidos en cada ZIP, parece que el
ZIP se completa cada noche con los ficheros del día anterior, y que en estos
meses deja de actualizarse a partir de un día determinado. En enero de 2024, por
ejemplo, la última incorporación es del 21/01/2024 a las 01:39. Adjunto la
relación completa de meses afectados, por si les resulta útil para localizar el
problema.

Estos ficheros son muy valiosos para mi trabajo porque recogen la **fecha de
declaración** de cada indisponibilidad, lo que permite estudiar con cuánta
antelación se comunica. Las declaraciones de menor antelación son precisamente
las que se pierden en los días que faltan: una indisponibilidad declarada y
finalizada dentro de esos días no aparece en los ficheros posteriores.

Les agradecería mucho que pudieran indicarme:

1. Si conservan los ficheros diarios de indisponibilidades de los días que
   faltan y, en ese caso, si sería posible regenerar los ZIP afectados o
   facilitármelos por otra vía.
2. Si no fuera posible recuperar todas las revisiones de cada día, me bastaría
   con la **última revisión publicada de cada día**, que es la que utilizo en el
   análisis.
3. Si existe otra fuente pública de OMIE con esta información para esas fechas.

Muchas gracias de antemano por su atención.

Un cordial saludo,
[Nombre]

---

## English (for reference)

**Subject:** Unavailability files (`indisp`): incomplete monthly zips, 2023–2026

Dear Sir or Madam,

I am writing again about my master's thesis on the MIBEL day-ahead market
(enquiry #12541, in which you kindly provided the offer-unit listings; thank you
again).

While processing the public unavailability files for Spanish units (`indisp`),
I found that **43 of the 100 monthly zip files** published between January 2018
and May 2026 do not contain every day of the month. Almost all the cases fall
from February 2023 onward. For example:

- `indisp_202401.zip` contains only 1–20 January 2024;
- `indisp_202403.zip` contains only 1 March 2024;
- `indisp_202605.zip` contains only 1–2 May 2026.

I downloaded them again on 28/09/2026 and they are identical to the copies from
August, so it does not appear to be a download problem. Nor could I find the
daily files for the missing days on the portal.

From the internal dates of the files inside each zip, the zip appears to be
extended each night with the previous day's files, and in these months it stops
being updated after a certain day. In January 2024, for example, the last
addition was made on 21/01/2024 at 01:39. I attach the full list of affected
months in case it helps locate the problem.

These files are very valuable to my work because they record the **declaration
date** of each unavailability, which shows how far in advance it was
communicated. The shortest-notice declarations are exactly the ones lost on the
missing days: an unavailability declared and ended within those days does not
appear in later files.

I would be very grateful if you could tell me:

1. Whether you keep the daily unavailability files for the missing days and, if
   so, whether the affected zips could be regenerated or provided another way.
2. If not every revision of each day can be recovered, the **last revision
   published each day** would be enough, since that is the one my analysis uses.
3. Whether any other public OMIE source holds this information for those dates.

Thank you in advance for your help.

Kind regards,
[Name]

---

## Appendix — affected months (to paste or attach)

Derived 2026-09-28 from the zips as downloaded. "Última escritura" is the latest
member timestamp inside the zip.

| mes | días publicados | días incluidos | última escritura en el zip |
|---|---|---|---|
| 09/2018 | 29 de 30 | 01/09–29/09 | 29/09/2018 21:44 |
| 05/2021 | 6 de 31 | 26/05–31/05 | 25/08/2021 12:42 |
| 07/2021 | 29 de 31 | 01/07–29/07 | 25/08/2021 13:04 |
| 02/2023 | 26 de 28 | 01/02–26/02 | 27/02/2023 01:38 |
| 03/2023 | 19 de 31 | 01/03–19/03 | 20/03/2023 01:38 |
| 04/2023 | 14 de 30 | 01/04–14/04 | 15/04/2023 00:39 |
| 05/2023 | 14 de 31 | 01/05–14/05 | 15/05/2023 00:40 |
| 06/2023 | 20 de 30 | 01/06–20/06 | 21/06/2023 00:40 |
| 07/2023 | 21 de 31 | 01/07–21/07 | 22/07/2023 00:39 |
| 08/2023 | 10 de 31 | 01/08–10/08 | 10/08/2023 23:39 |
| 09/2023 | 17 de 30 | 01/09–17/09 | 17/09/2023 23:40 |
| 10/2023 | 11 de 31 | 01/10–11/10 | 11/10/2023 23:37 |
| 11/2023 | 13 de 30 | 01/11–13/11 | 14/11/2023 00:37 |
| 12/2023 | 2 de 31 | 01/12–02/12 | 03/12/2023 00:37 |
| 01/2024 | 20 de 31 | 01/01–20/01 | 21/01/2024 01:39 |
| 02/2024 | 12 de 29 | 01/02–12/02 | 13/02/2024 01:48 |
| 03/2024 | 1 de 31 | 01/03 | 02/03/2024 01:37 |
| 04/2024 | 15 de 30 | 01/04–15/04 | 16/04/2024 00:37 |
| 05/2024 | 16 de 31 | 01/05–16/05 | 17/05/2024 00:37 |
| 06/2024 | 3 de 30 | 01/06–03/06 | 04/06/2024 00:38 |
| 07/2024 | 16 de 31 | 01/07–16/07 | 17/07/2024 00:38 |
| 08/2024 | 1 de 31 | 01/08 | 01/08/2024 23:37 |
| 09/2024 | 3 de 30 | 01/09–03/09 | 03/09/2024 23:36 |
| 10/2024 | 11 de 31 | 01/10–11/10 | 11/10/2024 23:37 |
| 11/2024 | 17 de 30 | 01/11–17/11 | 18/11/2024 00:36 |
| 12/2024 | 16 de 31 | 01/12–16/12 | 17/12/2024 00:37 |
| 01/2025 | 25 de 31 | 01/01–25/01 | 26/01/2025 01:38 |
| 02/2025 | 17 de 28 | 01/02–17/02 | 18/02/2025 01:38 |
| 03/2025 | 13 de 31 | 01/03–13/03 | 14/03/2025 01:40 |
| 04/2025 | 2 de 30 | 01/04–02/04 | 03/04/2025 01:03 |
| 05/2025 | 4 de 31 | 01/05–04/05 | 05/05/2025 01:02 |
| 06/2025 | 3 de 30 | 01/06–04/06 (con un día intermedio ausente) | 05/06/2025 01:08 |
| 07/2025 | 2 de 31 | 01/07–02/07 | 03/07/2025 01:11 |
| 08/2025 | 25 de 31 | 01/08–27/08 (con dos días intermedios ausentes) | 28/08/2025 00:13 |
| 09/2025 | 1 de 30 | 02/09 | 03/09/2025 00:34 |
| 10/2025 | 1 de 31 | 01/10 | 02/10/2025 00:10 |
| 11/2025 | 3 de 30 | 01/11–03/11 | 04/11/2025 01:18 |
| 12/2025 | 2 de 31 | 01/12–02/12 | 03/12/2025 01:13 |
| 01/2026 | 8 de 31 | 01/01–08/01 | 09/01/2026 02:15 |
| 02/2026 | 1 de 28 | 01/02 | 02/02/2026 02:13 |
| 03/2026 | 1 de 31 | 01/03 | 02/03/2026 02:09 |
| 04/2026 | 1 de 30 | 01/04 | 02/04/2026 01:19 |
| 05/2026 | 2 de 31 | 01/05–02/05 | 03/05/2026 01:16 |
