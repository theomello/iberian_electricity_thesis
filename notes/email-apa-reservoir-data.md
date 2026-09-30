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

**Blocking unknown before replying: do we actually have a static IP?**
*Resolved 2026-09-29, see the section below: LMU's eduVPN exits at
`194.95.236.6`, stable across a reconnect, but shared.* Home broadband is
normally dynamic. Ask university IT for the institution's fixed egress address,
or a VPN with a stable exit. Do not answer the email until that is confirmed —
offering an address that rotates wastes their exception and fails silently
later.

**Do not route around the block with a Portuguese VPN.** They have explained it
is a security control on a system they cannot patch.

### Draft reply — Portuguese (superseded 2026-09-29, see below)

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

## 2026-09-29 — a fixed address found; reply ready to send

**Sent 2026-09-30**, as a reply in the Mondego thread to Marco Orlando
(`marco.orlando@apambiente.pt`, APA's head of IT), cc `maria.saramago@apambiente.pt`,
`snirh@apambiente.pt` and the LMU address. It went from `theodormello@gmail.com`
(the connector's account), not from `T.Igel@campus.lmu.de` which sent the
original, so the body says so. Signed "Theodoro Mello, Ludwig-Maximilians-Universität",
as the original was; no supervisor line.

**The address.** Connected through LMU's eduVPN, this machine exits at
**`194.95.236.6`** (`eduvpn1.eduvpn.de`, AS680, DFN — the German research
network — Munich). It read the same on three checks and again after a disconnect
and reconnect. SNIRH (`snirh.apambiente.pt` → `web1.apambiente.pt`,
`193.136.235.19`) is IPv4-only, so one IPv4 address is all they need.
The VPN's IPv6 exit (`2001:638:d:d000:2::238`) plays no part.

**It is shared, and the reply says so.** It is the exit of DFN's eduVPN service,
not a personal or LMU address, so whitelisting it would admit other users of that
service. APA's security officer must be able to decide that knowingly. The reply
offers a dedicated address instead: a fixed IP from LRZ (LMU's computing centre),
or a paid dedicated IP from a VPN provider, located anywhere, since APA
whitelists the address and not the country. Switching eduVPN profiles does not
help: both profiles tried exit at the same IPv4 address.

**Still leads with the export**, for the reasons in
[`hydro-water-value-design.md`](hydro-water-value-design.md): a static file is
reproducible and cites cleanly, and it asks nothing of their security.

**What we need, and why:** each reservoir's **total and useful capacity** turns
the storage-hours floor (`rq-midday-hydro.md` §3.17) into a measurement, and
its **stored volume over time** is the Portuguese cascades' own state variable
for the water value, replacing the Spanish upstream-basin proxy (§3.16). The
list covers the EDP and Movhera cascades that §3.17 maps.

### Reply — Portuguese

**Assunto:** Re: Pedido de dados históricos de armazenamento de albufeiras (SNIRH)

Exmo. Senhor,

Muito obrigado pela resposta e por explicar a razão da restrição de acesso ao
SNIRH. Compreendo perfeitamente a preocupação de segurança.

Proponho duas vias, pela ordem que me parece mais simples para a APA:

1. **Uma exportação única**, em Excel ou CSV, que dispensa qualquer acesso ao
   sistema: para cada albufeira da lista abaixo, a capacidade total e a
   capacidade útil (hm³), e o volume armazenado (hm³ ou percentagem da
   capacidade), com periodicidade diária ou semanal, de janeiro de 2018 até à
   data. Um ficheiro estático é tudo o que o trabalho exige.

2. **A exceção de IP** que teve a amabilidade de oferecer. O endereço seria o
   **194.95.236.6** (apenas IPv4, uma vez que o SNIRH responde só em IPv4).
   Devo, no entanto, ser transparente: trata-se do endereço de saída do serviço
   eduVPN da rede académica alemã (DFN), através do qual me ligo a partir da
   minha universidade, a LMU München. É um endereço fixo, que confirmei em
   várias ligações, mas é partilhado por outros utilizadores desse serviço e não
   é exclusivamente meu. Se preferir um endereço de uso exclusivo, posso obter
   um endereço IPv4 fixo dedicado e enviar-lho de seguida.

Albufeiras de interesse, associadas aos aproveitamentos hidroelétricos:

- **Lima:** Alto Lindoso, Touvedo
- **Cávado, Rabagão e Homem:** Alto Rabagão, Paradela, Venda Nova, Vilarinho
  das Furnas, Salamonde, Caniçada
- **Douro:** Miranda, Picote, Bemposta, Baixo Sabor, Feiticeiro, Foz Tua,
  Pocinho, Valeira, Régua, Carrapatelo, Crestuma-Lever, Vilar (Tabuaço),
  Varosa, Torrão
- **Tejo e Zêzere:** Cabril, Bouçã, Castelo do Bode, Santa Luzia, Pracana,
  Fratel, Belver
- **Mondego:** Aguieira, Raiva, Caldeirão
- **Guadiana:** Alqueva, Pedrógão

Os dados serão usados apenas para fins académicos, na minha tese de mestrado,
com a APA e o SNIRH citados como fonte.

Com os melhores cumprimentos,
[Nome]
Ludwig-Maximilians-Universität München
[Orientador]

### Reply — English (for reference)

**Subject:** Re: Request for historical reservoir storage data (SNIRH)

Dear Sir,

Thank you for your reply, and for explaining the reason for restricting access
to SNIRH. I fully understand the security concern.

I would suggest two routes, in the order that seems simplest for APA:

1. **A one-off export** in Excel or CSV, needing no access to the system: for
   each reservoir listed below, the total and useful capacity (hm³) and the
   stored volume (hm³ or percentage of capacity), daily or weekly, from January
   2018 to date. A static file is all the work requires.

2. **The IP exception** you kindly offered. The address would be
   **194.95.236.6** (IPv4 only, since SNIRH answers only on IPv4). I should be
   transparent, though: it is the exit address of the eduVPN service of the
   German research network (DFN), through which I connect from my university,
   LMU Munich. It is fixed, which I confirmed across several connections, but
   it is shared by other users of that service and is not mine alone. If you
   would prefer an address used only by me, I can obtain a dedicated fixed IPv4
   address and send it to you straight away.

Reservoirs of interest, those of the hydroelectric schemes: [the list above].

The data will be used for academic purposes only, in my master's thesis, with
APA and SNIRH cited as the source.

Kind regards,
[Name]
Ludwig-Maximilians-Universität München
[Supervisor]

---

## 2026-09-30 — APA whitelisted the eduVPN address

Marco Orlando replied the same day (17:06 UTC, to the Gmail address, same cc
list): **194.95.236.6 is authorised**. He asks us to check whether access works,
and adds that if the site does not give the information, or makes it very
laborious to export, we should say so and **they will find a way to send it**.

So APA accepted the shared address knowingly, since the reply had said it was
DFN's eduVPN exit and not ours alone. They did not take up the export first,
but they offered it as the fallback.

**How to use it:**
- Access works only through LMU eduVPN. Check that the exit reads 194.95.236.6
  before any request. From home broadband (77.11.167.92 on 2026-09-30) SNIRH
  still returns 403, as it should.
- Keep requests few and sequential. The security officer called the system
  1990s technology that cannot be patched, and the exception was granted on
  trust.
- If per-reservoir export turns out to mean hundreds of page loads, take up
  the offer of a file. A file is reproducible and cites cleanly, which a fetcher
  that runs from only one network is not
  ([`hydro-water-value-design.md`](hydro-water-value-design.md), 2026-09-03).
- Once the data is in hand, reply to thank them and say whether the site was
  enough.

**Access confirmed the same evening.** Through eduVPN, SNIRH returned 200, and
the "dados de base" CSV export gives each reservoir gauge's weekly volume,
hourly level and daily inflow, turbined, pumped, spilled and outflow series.
That is more than the export we asked for. `scripts/fetch/fetch_snirh_reservoirs.py`
pulls 39 stations, one request each, 5 s apart.

### Thank-you reply — Portuguese

**Sent 2026-09-30**, in the same thread, to Marco Orlando, cc
`maria.saramago@apambiente.pt`, `snirh@apambiente.pt` and the LMU address, from
the Gmail address. Nothing further is owed; the correspondence is closed unless
a refresh needs the whitelist again.

**Assunto:** Re: Pedido de dados históricos de armazenamento de albufeiras (SNIRH) — bacia do Mondego

Exmo. Senhor Marco Orlando,

Muito obrigado pela rapidez. O acesso funciona: através do endereço autorizado
consegui descarregar, a partir dos dados de base do SNIRH, as séries de que
necessito para as albufeiras da lista, pelo que não será preciso enviarem-me
qualquer ficheiro. Fiz um número reduzido de pedidos, um por estação e
espaçados no tempo, tendo em conta a preocupação que referiu com o sistema.

A APA e o SNIRH serão citados como fonte na tese.

Com os melhores cumprimentos,
Theodoro Mello
Ludwig-Maximilians-Universität

### English (for reference)

Thank you for acting so quickly. Access works: through the authorised address I
was able to download, from SNIRH's base data, the series I need for the
reservoirs on the list, so there is no need to send me a file. I made only a
small number of requests, one per station and spaced out, given the concern you
mentioned about the system. APA and SNIRH will be cited as the source in the
thesis.

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
