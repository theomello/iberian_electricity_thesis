# Email to APA — historical reservoir storage data

Draft, 2026-08-19, updated the same day once real recipients were found.
Portuguese first, matching the convention set in `email-omie-followup.md`
for the OMIE correspondence. Context: `hydro-water-value-design.md`'s
2026-08-19 section — `snirh.apambiente.pt` returns 403 to every client
tried, including a full browser session, so the request is for the same
"Boletim de Armazenamento de Albufeiras" data confirmed to exist (two dead
ArcGIS Online snapshots from APA's own account, one covering September
2022, one covering December 2018 – September 2019) but never found as an
open, full-history source.

**Recipients: the regional water administrations (ARH), not a central
address.** APA's water-resources data is administered regionally, so each
office most likely only holds data for its own region's reservoirs — one
email to one office probably won't cover everything. Four of the five
cover our target basins (Algarve doesn't, and is skipped):

| region | email | our basins there |
|---|---|---|
| Norte | `arhn.geral@apambiente.pt` | Douro, Lima, Cávado, Tâmega |
| Centro | `arhc.geral@apambiente.pt` | Mondego |
| Tejo e Oeste | `arht.geral@apambiente.pt` | Tejo |
| Alentejo | `arhalt.geral@apambiente.pt` | Guadiana |

Each version below keeps the same structure as the general draft but
trims the basin list to what that office actually administers, and swaps
in a reservoir example from that region (still drawn from the real
December 2018 snapshot data already found — see the general note below —
so each office gets a concrete, regionally relevant proof that the data
exists, not just Alto Lindoso repeated four times):

| region | example reservoir | station code | Dec-2018 fill |
|---|---|---|---|
| Norte | Alto Lindoso (Lima) | 02H/01A | 24.7% |
| Centro | Aguieira (Mondego) | 11H/01A | 70.4% |
| Tejo e Oeste | Castelo de Bode (Tejo) | 16H/01A | 75.6% |
| Alentejo | Alqueva (Guadiana) | 24M/07A | 82.3% |

All four codes checked directly against the same December 2018 dataset
already found (`/tmp/webmap.json`, the embedded featureSet in APA's own
"Albufeiras do Boletim SNIRH" web map) — not guessed.

The general (non-regional) English reference version is kept below
unchanged, since the structure is identical across all five — only the
basin list and example change, as shown above.

---

## 2026-09-03 — APA replied, from the security officer

Their answer, in substance: SNIRH runs on 1990s technology, *"muito vulnerável
e sem atualizações possíveis"*, and **for that reason access from outside
Portugal is not permitted**. They offered to open an exception for a **fixed
IP** of ours.

That confirms the 403 diagnosis in
[`hydro-water-value-design.md`](hydro-water-value-design.md) — geo-block, not
bot-fingerprinting. See that note for why the bulk export is still the better
ask and the IP whitelist the fallback.

**Blocking unknown before replying: do we actually have a static IP?** Home
broadband is normally dynamic. Ask university IT for the institution's fixed
egress address, or a VPN with a stable exit. Do not answer the email until that
is confirmed — offering an address that rotates wastes their exception and
fails silently later.

**Do not route around the block with a Portuguese VPN.** They have explained it
is a security control on a system they cannot patch.

### Draft reply — Portuguese

**Assunto:** Re: Pedido de dados históricos de armazenamento de albufeiras (SNIRH)

Exmo. Senhor,

Muito obrigado pelo esclarecimento, e por explicar a razão da restrição — fica
perfeitamente compreendido, e não era de todo evidente a partir da resposta 403.

Antes de avançar com a exceção de IP, permita-me sugerir uma alternativa que
talvez seja mais simples para ambos e que dispensa qualquer acesso ao SNIRH:
**uma exportação única da série histórica**, em Excel ou CSV, do armazenamento
das albufeiras (em hm³ e/ou percentagem da capacidade total, com periodicidade
semanal ou mensal) para o período de 2018 a 2026.

Para o meu trabalho basta um ficheiro estático — não necessito de acesso
continuado nem de consultas em tempo real. Do vosso lado, evitaria abrir o
sistema a um endereço externo, o que, face à preocupação que descreve, me
parece preferível. Sei também que este tipo de extração já foi feito na APA:
existem duas publicações vossas no ArcGIS Online exatamente com este formato,
uma com o armazenamento de setembro de 2022 por bacia e outra com a situação
mensal de 61 albufeiras entre dezembro de 2018 e setembro de 2019, esta última
identificando cada albufeira pelo respetivo código de estação (por exemplo,
Alto Lindoso, 02H/01A).

Caso a exportação não seja viável, agradeço então a possibilidade da exceção de
IP e indico-lhe o endereço fixo assim que o confirmar junto dos serviços
informáticos da minha instituição. Nesse caso, agradecia que me confirmasse
apenas se é suficiente um único endereço IPv4.

Com os melhores cumprimentos,
[Nome]
[Instituição / orientador]

### English (for reference)

Thank you for the explanation, and for saying why the restriction exists — that
was not apparent from the 403 alone.

Before taking up the IP exception, may I suggest an alternative that is
probably simpler for both of us and needs no SNIRH access at all: **a one-off
export of the historical series**, in Excel or CSV, of reservoir storage (in
hm³ and/or percentage of total capacity, weekly or monthly) for 2018 to 2026.

A static file is all my work requires — I need neither continued access nor
real-time queries. On your side it would avoid opening the system to an
external address, which given the concern you describe seems preferable. I also
know this kind of extract has been done at APA before: there are two of your
own ArcGIS Online publications in exactly this format, one giving September 2022
storage by basin and another giving the monthly status of 61 reservoirs from
December 2018 to September 2019, the latter identifying each reservoir by its
station code (for example Alto Lindoso, 02H/01A).

If the export is not feasible, I would gratefully take up the IP exception and
will send the fixed address once my institution's IT services confirm it. In
that case, could you confirm whether a single IPv4 address is sufficient?

---

## Norte — arhn.geral@apambiente.pt

**Assunto:** Pedido de dados históricos de armazenamento de albufeiras (SNIRH) — bacias do Douro, Lima, Cávado e Tâmega

Exmos. Senhores,

Estou a realizar uma tese de mestrado sobre o mercado elétrico ibérico
(MIBEL), com particular atenção à hidroeletricidade de albufeira em Espanha
e Portugal. Para a parte portuguesa do trabalho, necessito de uma série
histórica do armazenamento nas principais albufeiras hidroelétricas das
bacias do **Douro, Lima, Cávado e Tâmega** — o mesmo tipo de dado que já
utilizo para Espanha, a partir do Boletín Hidrológico Semanal do MITECO.

Sei que este dado existe e é divulgado pela APA, através do Boletim de
Armazenamento de Albufeiras do SNIRH: encontrei duas publicações da APA no
ArcGIS Online que utilizam exatamente este formato — uma com o
armazenamento de setembro de 2022 por bacia, outra com a situação mensal
de 61 albufeiras entre dezembro de 2018 e setembro de 2019, esta última
identificando cada albufeira pelo seu código de estação — por exemplo, o
Alto Lindoso (bacia do Lima), código 02H/01A, com 24,7% de armazenamento
em dezembro de 2018. Não encontrei, no entanto, uma série completa e
atualizada disponível para download.

Tentei aceder diretamente a snirh.apambiente.pt para consultar os dados
sintetizados por albufeira, mas obtive sempre uma resposta de acesso
negado (erro 403), mesmo através de um browser convencional — pelo que
não sei se se trata de uma restrição de acesso geográfico ou de outra
limitação técnica.

Seria possível disponibilizar-me esta série histórica (armazenamento, em
hm³ e/ou percentagem da capacidade total, com periodicidade semanal ou
mensal) para as albufeiras das bacias do Douro, Lima, Cávado e Tâmega, no
período de 2018 a 2026? Qualquer formato (Excel, CSV, ou outro) serve
perfeitamente.

Agradeço desde já a atenção dispensada e fico ao dispor para qualquer
esclarecimento adicional.

Com os melhores cumprimentos,
[Nome]
[Instituição / orientador, se aplicável]

---

## Centro — arhc.geral@apambiente.pt

**Assunto:** Pedido de dados históricos de armazenamento de albufeiras (SNIRH) — bacia do Mondego

Exmos. Senhores,

Estou a realizar uma tese de mestrado sobre o mercado elétrico ibérico
(MIBEL), com particular atenção à hidroeletricidade de albufeira em Espanha
e Portugal. Para a parte portuguesa do trabalho, necessito de uma série
histórica do armazenamento nas principais albufeiras hidroelétricas da
**bacia do Mondego** — o mesmo tipo de dado que já utilizo para Espanha, a
partir do Boletín Hidrológico Semanal do MITECO.

Sei que este dado existe e é divulgado pela APA, através do Boletim de
Armazenamento de Albufeiras do SNIRH: encontrei duas publicações da APA no
ArcGIS Online que utilizam exatamente este formato — uma com o
armazenamento de setembro de 2022 por bacia, outra com a situação mensal
de 61 albufeiras entre dezembro de 2018 e setembro de 2019, esta última
identificando cada albufeira pelo seu código de estação — por exemplo, a
Aguieira (bacia do Mondego), código 11H/01A, com 70,4% de armazenamento em
dezembro de 2018. Não encontrei, no entanto, uma série completa e
atualizada disponível para download.

Tentei aceder diretamente a snirh.apambiente.pt para consultar os dados
sintetizados por albufeira, mas obtive sempre uma resposta de acesso
negado (erro 403), mesmo através de um browser convencional — pelo que
não sei se se trata de uma restrição de acesso geográfico ou de outra
limitação técnica.

Seria possível disponibilizar-me esta série histórica (armazenamento, em
hm³ e/ou percentagem da capacidade total, com periodicidade semanal ou
mensal) para as albufeiras da bacia do Mondego, no período de 2018 a 2026?
Qualquer formato (Excel, CSV, ou outro) serve perfeitamente.

Agradeço desde já a atenção dispensada e fico ao dispor para qualquer
esclarecimento adicional.

Com os melhores cumprimentos,
[Nome]
[Instituição / orientador, se aplicável]

---

## Tejo e Oeste — arht.geral@apambiente.pt

**Assunto:** Pedido de dados históricos de armazenamento de albufeiras (SNIRH) — bacia do Tejo

Exmos. Senhores,

Estou a realizar uma tese de mestrado sobre o mercado elétrico ibérico
(MIBEL), com particular atenção à hidroeletricidade de albufeira em Espanha
e Portugal. Para a parte portuguesa do trabalho, necessito de uma série
histórica do armazenamento nas principais albufeiras hidroelétricas da
**bacia do Tejo** — o mesmo tipo de dado que já utilizo para Espanha, a
partir do Boletín Hidrológico Semanal do MITECO.

Sei que este dado existe e é divulgado pela APA, através do Boletim de
Armazenamento de Albufeiras do SNIRH: encontrei duas publicações da APA no
ArcGIS Online que utilizam exatamente este formato — uma com o
armazenamento de setembro de 2022 por bacia, outra com a situação mensal
de 61 albufeiras entre dezembro de 2018 e setembro de 2019, esta última
identificando cada albufeira pelo seu código de estação — por exemplo, o
Castelo de Bode (bacia do Tejo), código 16H/01A, com 75,6% de
armazenamento em dezembro de 2018. Não encontrei, no entanto, uma série
completa e atualizada disponível para download.

Tentei aceder diretamente a snirh.apambiente.pt para consultar os dados
sintetizados por albufeira, mas obtive sempre uma resposta de acesso
negado (erro 403), mesmo através de um browser convencional — pelo que
não sei se se trata de uma restrição de acesso geográfico ou de outra
limitação técnica.

Seria possível disponibilizar-me esta série histórica (armazenamento, em
hm³ e/ou percentagem da capacidade total, com periodicidade semanal ou
mensal) para as albufeiras da bacia do Tejo, no período de 2018 a 2026?
Qualquer formato (Excel, CSV, ou outro) serve perfeitamente.

Agradeço desde já a atenção dispensada e fico ao dispor para qualquer
esclarecimento adicional.

Com os melhores cumprimentos,
[Nome]
[Instituição / orientador, se aplicável]

---

## Alentejo — arhalt.geral@apambiente.pt

**Assunto:** Pedido de dados históricos de armazenamento de albufeiras (SNIRH) — bacia do Guadiana

Exmos. Senhores,

Estou a realizar uma tese de mestrado sobre o mercado elétrico ibérico
(MIBEL), com particular atenção à hidroeletricidade de albufeira em Espanha
e Portugal. Para a parte portuguesa do trabalho, necessito de uma série
histórica do armazenamento nas principais albufeiras hidroelétricas da
**bacia do Guadiana** — o mesmo tipo de dado que já utilizo para Espanha, a
partir do Boletín Hidrológico Semanal do MITECO.

Sei que este dado existe e é divulgado pela APA, através do Boletim de
Armazenamento de Albufeiras do SNIRH: encontrei duas publicações da APA no
ArcGIS Online que utilizam exatamente este formato — uma com o
armazenamento de setembro de 2022 por bacia, outra com a situação mensal
de 61 albufeiras entre dezembro de 2018 e setembro de 2019, esta última
identificando cada albufeira pelo seu código de estação — por exemplo, o
Alqueva (bacia do Guadiana), código 24M/07A, com 82,3% de armazenamento em
dezembro de 2018. Não encontrei, no entanto, uma série completa e
atualizada disponível para download.

Tentei aceder diretamente a snirh.apambiente.pt para consultar os dados
sintetizados por albufeira, mas obtive sempre uma resposta de acesso
negado (erro 403), mesmo através de um browser convencional — pelo que
não sei se se trata de uma restrição de acesso geográfico ou de outra
limitação técnica.

Seria possível disponibilizar-me esta série histórica (armazenamento, em
hm³ e/ou percentagem da capacidade total, com periodicidade semanal ou
mensal) para as albufeiras da bacia do Guadiana, no período de 2018 a
2026? Qualquer formato (Excel, CSV, ou outro) serve perfeitamente.

Agradeço desde já a atenção dispensada e fico ao dispor para qualquer
esclarecimento adicional.

Com os melhores cumprimentos,
[Nome]
[Instituição / orientador, se aplicável]

---

## Portuguese

**Assunto:** Pedido de dados históricos de armazenamento de albufeiras (SNIRH)

Exmos. Senhores,

Estou a realizar uma tese de mestrado sobre o mercado elétrico ibérico
(MIBEL), com particular atenção à hidroeletricidade de albufeira em Espanha
e Portugal. Para a parte portuguesa do trabalho, necessito de uma série
histórica do armazenamento nas principais albufeiras hidroelétricas de
Portugal continental — o mesmo tipo de dado que já utilizo para Espanha, a
partir do Boletín Hidrológico Semanal do MITECO.

Sei que este dado existe e é divulgado pela APA, através do Boletim de
Armazenamento de Albufeiras do SNIRH: encontrei duas publicações da APA no
ArcGIS Online que utilizam exatamente este formato — uma com o
armazenamento de setembro de 2022 por bacia, outra com a situação mensal
de 61 albufeiras entre dezembro de 2018 e setembro de 2019, esta última
identificando cada albufeira pelo seu código de estação (por exemplo,
Alto Lindoço, código 02H/01A). Não encontrei, no entanto, uma série
completa e atualizada disponível para download.

Tentei aceder diretamente a snirh.apambiente.pt para consultar os dados
sintetizados por albufeira, mas obtive sempre uma resposta de acesso
negado (erro 403), mesmo através de um browser convencional — pelo que
não sei se se trata de uma restrição de acesso geográfico ou de outra
limitação técnica.

Seria possível disponibilizar-me esta série histórica (armazenamento, em
hm³ e/ou percentagem da capacidade total, com periodicidade semanal ou
mensal) para o período de 2018 a 2026? Interessam-me sobretudo as
albufeiras associadas às bacias do Douro, Lima, Cávado, Tâmega, Tejo,
Mondego e Guadiana, mas ficaria grato por qualquer conjunto mais alargado
que seja possível partilhar. Qualquer formato (Excel, CSV, ou outro) serve
perfeitamente.

Agradeço desde já a atenção dispensada e fico ao dispor para qualquer
esclarecimento adicional.

Com os melhores cumprimentos,
[Nome]
[Instituição / orientador, se aplicável]

---

## English (for reference)

**Subject:** Request for historical reservoir storage data (SNIRH)

Dear Sir or Madam,

I am writing a master's thesis on the Iberian electricity market (MIBEL),
with particular attention to reservoir-backed hydroelectric generation in
Spain and Portugal. For the Portuguese side of the work, I need a
historical time series of storage levels in Portugal's main hydroelectric
reservoirs — the same kind of data I already use for Spain, from MITECO's
Boletín Hidrológico Semanal.

I know this data exists and is published by APA through SNIRH's Boletim de
Armazenamento de Albufeiras: I found two APA publications on ArcGIS Online
using exactly this format — one giving September 2022 storage by basin,
the other giving the monthly status of 61 reservoirs from December 2018 to
September 2019, the latter identifying each reservoir by its station code
(for example, Alto Lindoso, code 02H/01A). I was not able to find a
complete, up-to-date series available for download, however.

I tried accessing snirh.apambiente.pt directly to look up the
per-reservoir synthesized data, but consistently received an access-denied
response (error 403), even through an ordinary browser — so I am not sure
whether this is a geographic access restriction or some other technical
limitation.

Would it be possible to share this historical series (storage, in hm³
and/or percentage of total capacity, weekly or monthly) for 2018 to 2026?
I am mainly interested in the reservoirs associated with the Douro, Lima,
Cávado, Tâmega, Tejo, Mondego and Guadiana basins, but would be grateful
for any broader set you are able to share. Any format (Excel, CSV, or
otherwise) works well.

Thank you in advance for your attention, and please let me know if any
clarification would help.

Kind regards,
[Name]
[Institution / supervisor, if applicable]
