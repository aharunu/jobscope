# Turkish job-source catalog (v3) — 2026-07-13

**v3 (2026-07-13)** — additive union of the three finalized TR discovery lanes onto the v2 base. v3 additions block: **158 distinct employers / 194 source lines**. Total catalog source lines: **1865** (1671 v2 base + 194 union additions). Per-source provenance: v2 base = 1671 lines (2026-06-16, preserved verbatim below); Claude lane = 101 incoming, Antigravity lane = 136 incoming, Codex lane = 32 incoming (269 total incoming → 194 distinct after collapsing 75 cross-lane name+domain collisions). Dedup identity = normalized(company name) + registered domain; distinct-domain alternates preserved. Union block, full provenance, and the liveness sample are in `## TR wave v3 additions — 2026-07-13` at the end of this file. The original v2 header and body follow unchanged.


1309 sources: the original 156 across 9 sectors (2026-06-16, 9-agent sweep) plus 2026-06-17 expansions — ~205 holding/conglomerate subsidiaries (section 1b), 175 banks/finance/fintech (section 2b), 121 tech-ecosystem (section 3b), ~206 e-commerce/retail/FMCG/logistics (section 4b), 222 manufacturing/industrial/energy (section 7b), 101 telecom/IT-services/consulting (section 5b), and 123 ATS-token long-tail (section 9b) companies — largely verified
(URLs, access posture, fetch method). Companion: `discovery-architecture.md` (the reusable
fetch/parse patterns and the company-to-career-page resolver).

## Access tiers
- **open** — public listings, fetchable without login (ideal; many expose a JSON/XML API).
- **login-to-apply** — browsing is public, applying needs an account (browse freely; apply supervised).
- **restricted** — the restriction applies to APPLYING only (ToS / bot-detection / announcement-driven: LinkedIn, Kariyer.net apply, İŞKUR, exam-based state banks) → apply via supervised session or paste-link. READING/searching these boards is public, permitted, and mandatory for discovery (see "Aggregator keyword sweep" in discovery-architecture.md) — except LinkedIn and İŞKUR, which stay fully hands-off.

## Most valuable machine-queryable API endpoints (use these first)
- **Lever**: `https://api.lever.co/v0/postings/<token>?mode=json` (HTML page often 403s bots; the API does not).
- **Greenhouse**: `https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true`
- **Ashby**: `POST https://api.ashbyhq.com/posting-api/job-board/<token>`
- **SmartRecruiters**: `https://api.smartrecruiters.com/v1/companies/<token>/postings`
- **Workday**: `POST https://<tenant>.<wdN>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs` body `{"appliedFacets":{},"limit":20,"offset":0,"searchText":"data analyst"}`
- **Recruitee**: `https://<company>.recruitee.com/api/offers/`
- **Personio**: `https://<company>.jobs.personio.com/xml`
- **SuccessFactors**: no clean public API → supervised browser; site pattern `career[2/5].successfactors.eu/careers?company=<tenant>`
- **Kariyer.net** firma-profil pages (`/firma-profil/<slug-id>`) list a company's live ads publicly; apply needs login.
- **Kariyer-only → Mode C**: entries whose only source is a kariyer.net firma-profil and that have no open ATS alternative are tagged `read-only ... Mode C human-apply` (checked 2026-06-21, JAC-52). Browse the public listing, apply by hand in a logged-in browser, and never automate kariyer.net apply.

---

## 1. Holdings & conglomerates
- **Koç — Koç Kariyerim** — `https://www.kockariyerim.com/` (and `/jobad/search/`, `/companies/<co>-is-ilanlari`) — open browse / login-to-apply — group portal aggregating 100+ Koç companies (Arçelik, Ford Otosan, Tofaş, Yapı Kredi, Otokar, Beko, Aygaz, KoçSistem, Koç University). Filter by `companyIds` + city İstanbul. **Best single Turkish entry point.** Verified.
- **Arçelik** — `https://www.arcelikglobal.com/en/company/human-resources/career/` → Koç SuccessFactors `career5.successfactors.eu/career?company=Koc` — open / login-to-apply — high-volume Data Science/BI/BA.
- **Sabancı — group gateway** — `https://www.sabanci.com/en/career/...` — open gateway (company dropdown; routes to subsidiary ATS). Enumerate subsidiaries, then fetch each.
- **SabancıDx** (Sabancı data/tech arm) — `https://www.sabancidx.com/en/about-us/career/` — open / login-to-apply — strong Data Science/BI/DA concentration.
- **Borusan — careers** — `https://careers.borusan.com/` — SuccessFactors, public search; login-to-apply.
- **Doğuş — group page** — `https://www.dogusgrubu.com.tr/tr/insan-kaynaklari/dogus-ta-is-firsatlari` + Kariyer.net `firma-profil/dogus-grubu-1463-5075` (live feed) — open browse.
- **Doğuş Teknoloji** — Kariyer.net `firma-profil/dogus-teknoloji-164050-226026` — open browse — dedicated Data Science/Analytics.
- **Eczacıbaşı — careers** — `https://careers.eczacibasi.com/search/` — SuccessFactors, public listings.
- **Zorlu — careers** — `https://www.zorlu.com.tr/en/careers` + Kariyer.net `firma-profil/zorlu-holding-3450-26923` — open browse (Vestel, Zorlu Enerji).
- **Anadolu Grubu — Anadolu Kariyerim** — `https://careers.anadolukariyerim.com/` (`?locale=tr_TR`) — SuccessFactors public search — 80+ companies (Anadolu Efes, CCI, Migros, McDonald's TR).
- **Yıldız Holding** — `https://www.yildizholding.com.tr/en/being-a-part-of-yildiz/career` → LinkedIn / Kariyer.net `firma-profil/yildiz-holding-4325-29208` — login-to-apply (Ülker, pladis, GODIVA).
- **Çalık — careers** — `https://careers.calik.com/viewalljobs/` — SuccessFactors public listings.
- **Tekfen Ventures** — `https://careers.tekfenventures.com/jobs` + `https://apply.workable.com/tekfen/` — open (venture-portfolio, mostly non-TR; filter Istanbul). Core Tekfen Holding roles: resolve via Kariyer.net search 'Tekfen'.
- **Enka İnşaat** — `https://www.enka.com/career/` + Kariyer.net `firma-profil/enka-insaat-ve-sanayii-a-s-5750-30633` (dated 2026 listings) — open browse — Project Manager heavy.

## 1b. Holding & conglomerate subsidiaries expansion — 2026-06-17 (batch JAC-32): ~205 verified companies
NEW distinct operating companies behind the Turkish holding groups (each subsidiary is its own employer, not a duplicate of its parent or sister companies). Istanbul-HQ first. Includes the finance/insurance/data-infrastructure companies that sit inside or alongside these groups. Companies sold to new owners were deliberately excluded. Many route through Koç Kariyerim / Anadolu Kariyerim / SuccessFactors / Peoplise / HRPeak / Kariyer.net firma-profil.

### Koç Holding group
- **Otokoç Otomotiv (Koç Holding)** — `https://www.kockariyerim.com/companies/otokoc-otomotiv-is-ilanlari` — login-to-apply — automotive retail / fleet rental (Avis, Budget, Zipcar), İstanbul; PM, finance/BI analyst; email: none found
- **Setur Servis Turistik (Koç Holding)** — `https://www.kockariyerim.com/companies/setur-is-ilanlari` — login-to-apply — tourism / travel agency & duty-free, İstanbul; PM, business analyst, supply-chain; email: none found
- **Setur Marinaları (Koç Holding)** — `https://www.kockariyerim.com/companies/setur-marinalari-is-ilanlari` — login-to-apply — marina operations, İstanbul/Muğla; ops/systems/energy-mgmt; email: none found
- **Divan Turizm İşletmeleri (Koç Holding)** — `https://www.kariyer.net/firma-profil/divan-turizm-isletmeleri-a-s-12833-231923` — login-to-apply — hospitality/hotels, İstanbul; PM, HR, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Zer / Koçzer (Koç Holding)** — `https://www.kariyer.net/firma-profil/zer-10317-344` — login-to-apply — procurement BPO & tech, İstanbul; process/supply-chain analyst, BI, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bilkom Bilişim Hizmetleri (Koç Holding)** — `https://www.kockariyerim.com/companies/bilkom-is-ilanlari` — login-to-apply — ICT distribution (Apple/Asus/DJI/PlayStation), Üsküdar/İstanbul; ops mgr, BI, PM; email: none found
- **Koç Finansman / Koçfinans (Koç Holding)** — `https://www.kockariyerim.com/companies/koc-finansman-is-ilanlari` — login-to-apply — consumer finance, İstanbul; data/finance analyst, PM, process; email: none found
- **Ram Dış Ticaret (Koç Holding)** — `https://www.kariyer.net/firma-profil/ram-dis-ticaret-1310-3392` — login-to-apply — foreign trade/export, İstanbul; trade/supply-chain/finance analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tanı Pazarlama ve İletişim Hizmetleri (Koç Holding)** — `https://www.kariyer.net/firma-profil/tani-pazarlama-ve-iletisim-hizmetleri-a-s-31611-23746` — login-to-apply — CRM/loyalty/advanced analytics (Chippin), İstanbul; data engineer, BI, business analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Yapı Kredi Yatırım (Koç Holding, via Yapı Kredi)** — `https://www.ykyatirim.com.tr` — login-to-apply — investment/brokerage, İstanbul; finance/data analyst, BI, PM; email: none found
- **Yapı Kredi Faktoring (Koç Holding, via Yapı Kredi)** — `https://www.kockariyerim.com/companies/yapi-kredi-is-ilanlari` — login-to-apply — factoring, İstanbul; business analyst, finance; email: none found
- **Yapı Kredi Finansal Kiralama / Leasing (Koç Holding, via Yapı Kredi)** — `https://www.ykleasing.com.tr/hakkimizda/insan-kaynaklari` — open — leasing, İstanbul; finance/process analyst, PM; email: none found
- **Yapı Kredi Portföy Yönetimi (Koç Holding, via Yapı Kredi)** — `https://www.yapikrediportfoy.com.tr/hakkimizda/insan-kaynaklari` — open — asset management, İstanbul; analyst, BI, finance; email: none found

### Sabancı Holding group
- **Teknosa (Sabancı Holding)** — `https://kariyer.sabanci.com/en/open-positions/teknosa` (Kariyer.net `firma-profil/teknosa-ic-ve-dis-tic-a-s-8183-33061`) — open — consumer-electronics retail, İstanbul; PM, data analyst, BI, supply-chain; email: none found
- **CarrefourSA (Sabancı + Carrefour)** — `https://kariyer.sabanci.com/en/open-positions/carrefoursa` — open — grocery retail (BIST: CRFSA), İstanbul; store ops, logistics, category mgmt, e-commerce; email: none found
- **Aksigorta (Sabancı + Ageas)** — `https://www.aksigorta.com.tr/hakkimizda/insan-kaynaklari/kariyer-firsatlari-ve-insan-kaynaklari-uygulamalari` — open — non-life insurance, İstanbul; data analyst, actuarial, BI, PM; email: none found
- **AgeSA Hayat ve Emeklilik (Sabancı + Ageas)** — `https://www.agesa.com.tr/tr/insan-kaynaklari/agesali-olmak/acik-pozisyonlar` — open — life insurance & pension (BIST: AGESA), Ataşehir/İstanbul; actuarial, BI, PM, finance; email: none found
- **Ak Yatırım Menkul Değerler (Akbank → Sabancı)** — `https://www.kariyer.net/firma-profil/ak-yatirim-menkul-degerler-a-s-3925-28808` — open — brokerage/capital markets, İstanbul; trading, research, custody; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Ak Portföy Yönetimi (Akbank → Sabancı)** — `https://kariyer.akbank.com/JobSearchMaster` — login-to-apply — asset management, Levent/İstanbul; fund mgmt, analysts; email: none found
- **Ak Finansal Kiralama / AKLease (Akbank → Sabancı)** — `https://www.kariyer.net/firma-profil/ak-finansal-kiralama-a-s-1660-7241` — open — leasing, İstanbul; credit/risk, sales, ops; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **AkÖde / Tosla (Akbank → Sabancı)** — `https://kariyer.akbank.com/JobSearchMaster` — login-to-apply — e-money/payments, İstanbul; fintech eng, product, ops; email: none found
- **Temsa İş Makinaları (Sabancı Holding)** — `https://www.kariyer.net/firma-profil/temsa-is-makinalari-imalat-pazarlama-ve-satis-a-s-1258-2821` — login-to-apply — construction-equipment distribution (Komatsu), İstanbul; service/PM, finance, supply-chain; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Anadolu Grubu group
- **Çelik Motor (AG Anadolu Grubu)** — `https://www.kariyer.net/firma-profil/celik-motor-1064-1667` — login-to-apply — automotive (Kia, Garenta rental, ikinciyeni.com), Ümraniye/İstanbul; PM, marketing, BI, finance analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Anadolu Motor / ANTOR (AG Anadolu Grubu)** — `https://www.anadolumotor.com/en/career/join-us` — open — engines/generators/marine & agri power, Gebze; PM, process, supply-chain; email: none found
- **Adel Kalemcilik (AG Anadolu Grubu / Faber-Castell)** — `https://www.adel.com.tr/insan-kaynaklari` — open — stationery, Çayırova/Kocaeli; finance, quality, PM, supply-chain; email: none found
- **Anadolu Etap (AEP Penkon Gıda) (AG Anadolu Grubu)** — `https://www.anadoluetap.com/kariyer` — open — fruit-juice concentrate/agri, İstanbul + Mersin/Denizli/Isparta; export sales, accounting, PM; email: none found
- **Anadolu Bilişim Hizmetleri / ABH (AG Anadolu Grubu)** — `https://careers.anadolukariyerim.com/` — open — IT/data-center/ERP/software arm, Maltepe/İstanbul; Data Analyst, BI, data roles; email: none found
- **AND Anadolu Gayrimenkul Yatırımları (AG Anadolu Grubu)** — `https://www.kariyer.net/firma-profil/and-anadolu-gayrimenkul-yatirimlari-a-s-1064-130815` — open — real estate, İstanbul; finance/project analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Anadolu Sağlık Merkezi (Anadolu Grubu / Anadolu Vakfı)** — `https://www.anadolusaglik.org/kariyer` — open — hospital (Johns Hopkins affiliation), Gebze/Kocaeli + Ataşehir/İstanbul; PM, finance, HR, data + clinical; email: none found

### Yaşar Holding group
- **Pınar Su ve İçecek (Yaşar Holding)** — `https://career.yasar.com.tr/` — login-to-apply — bottled water & beverages, İzmir; PM, supply-chain, finance, BI; email: none found
- **Yaşar Birleşik Pazarlama (Yaşar Holding)** — `https://career.yasar.com.tr/` — login-to-apply — distribution/marketing of Pınar products, İzmir; sales, supply-chain, BI, PM; email: none found
- **Çamlı Yem Besicilik (Yaşar Holding)** — `https://www.kariyer.net/firma-profil/camli-yem-besicilik-sanayii-ve-ticaret-a-s-1038-227672` — login-to-apply — animal feed/aquaculture, İzmir; PM, process, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Viking Kağıt ve Selüloz (Yaşar Holding)** — `https://www.kariyer.net/firma-profil/viking-kagit-ve-seluloz-a-s-2495-16421` — login-to-apply — tissue paper, İzmir; business-dev, sales, HSE, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Yaşar Bilgi İşlem (YABİM) (Yaşar Holding)** — `https://career.yasar.com.tr/` — login-to-apply — IT/SAP ERP services, İzmir; PM, BI, business/data analyst; email: none found
- **Altın Yunus Çeşme Resort (Yaşar Holding)** — `https://career.yasar.com.tr/` — login-to-apply — tourism/hospitality, Çeşme/İzmir; PM, finance, HR; email: none found

### Doğuş Holding group
- **Doğuş Otomotiv (Doğuş Holding)** — `https://kariyer.dogusotomotiv.com.tr/` (Kariyer.net `firma-profil/dogus-otomotiv-5094-29977`) — login-to-apply — VW/Audi/SEAT/CUPRA/Škoda/Porsche/Scania importer, Şekerpınar/Gebze; PM, BI/data, finance/supply-chain/process analyst; email: none found
- **Doğuş Oto Pazarlama (Doğuş Holding)** — `https://www.dogusoto.com.tr/ise-alim-ve-kariyer-firsatlari` — open — automotive retail/after-sales, İstanbul/Ankara; sales/finance/HR/process analyst; email: none found
- **Doğuş İnşaat ve Ticaret (Doğuş Holding)** — `https://www.kariyer.net/firma-profil/dogus-insaat-ve-ticaret-a-s-5200-30083` — open — infrastructure/construction, İstanbul + overseas; PM, planning/cost/process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Doğuş Gayrimenkul Yatırım (Doğuş Holding)** — `https://www.kariyer.net/firma-profil/dogus-grubu-1463-5075` — open — real-estate development/mgmt, İstanbul; finance/BI/project analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Doğuş GYO (DGGYO) (Doğuş Holding)** — `https://www.dogusgyo.com.tr/tr/insan-kaynaklari/basvuru.aspx` — open — listed REIT, İstanbul; finance/investment/data analyst; email: none found
- **Doğuş Yayın Grubu / NTV (Doğuş Holding)** — `https://ik.dogusyayingrubu.com/job/list` — open — media/broadcasting, İstanbul; data/digital/process analyst, project; email: none found
- **d.ream (Doğuş Yeme İçme) (Doğuş Holding)** — `https://www.kariyer.net/firma-profil/d-ream-37842-54144` — open — F&B/hospitality, İstanbul; HR-reporting, finance, ops; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Antur Turizm (Doğuş Holding)** — `https://www.dogusgrubu.com.tr/tr/insan-kaynaklari/dogus-ta-is-firsatlari` — open — corporate travel mgmt, İstanbul; ops/finance/data analyst; email: none found
- **D-Marin (Doğuş Marina) (Doğuş Holding)** — `https://www.d-marin.com/en/career/` — open — marina operator network, Muğla/İstanbul; project/finance/BI/ops analyst; email: none found
- **Volkswagen Doğuş Finansman (vdf) (Doğuş Holding — 49% JV)** — `https://www.kariyer.net/firma-profil/vdf-9476-247395` — open — auto financing/leasing JV, İstanbul; finance/credit/data/process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Zorlu Holding group
- **Vestel Beyaz Eşya (Zorlu Holding)** — `https://www.kariyer.net/firma-profil/vestel-sirketler-grubu-1115-1249` — open — white-goods (BIST: VESBE), Vestel City/Manisa; PM, supply-chain/process/data/BI analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Vestel Elektronik (Zorlu Holding)** — `https://www.vestelinternational.com/` — open — consumer electronics/TV (BIST: VESTL), Manisa & İstanbul; PM, data/BI/finance/supply-chain analyst; email: none found
- **Zorlu Gayrimenkul / Zorlu Yapı Yatırım (Zorlu Holding)** — `https://www.kariyer.net/firma-profil/zorlu-gayrimenkul-3450-237781` — open — real estate (Zorlu Center, Levent 199), İstanbul; project/finance/BI analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Zorlu Faktoring (Zorlu Holding)** — `https://www.zorlukariyer.com/is-ilanlari` — open — factoring/financial services, İstanbul; finance/credit/process analyst; email: none found
- **Zorlu PSM (Performans Sanatları Merkezi) (Zorlu Holding)** — `https://psm.zorlukariyer.com/is-ilanlari` — open — performing-arts venue mgmt, İstanbul; programming, finance, ops/data; email: hr@zorlupsm.com

### Yıldız Holding group
- **Yıldız Tech / Yıldız Holding Bilgi Sistemleri (Yıldız Holding)** — `https://www.yildiztech.com.tr/tr/kariyer` — open — group software/digital arm, Üsküdar/İstanbul; Data Analyst, BI, software/PM; email: none found
- **Polinas Plastik (Yıldız Holding)** — `https://www.polinas.com/tr/insan-kaynaklari/ik-uygulamalarimiz` — open — BOPP/BOPET flexible-packaging films, Manisa; PM, supply-chain/process/data analyst; email: info@polinas.com.tr
- **Besler Gıda ve Kimya (Yıldız Holding)** — `https://www.besler.com.tr/` — open — edible oils / frozen & canned (BIST: BESLR), İstanbul; finance/supply-chain/process/data analyst; email: none found
- **Önem Gıda (Yıldız Holding / Ülker)** — `https://www.kariyer.net/firma-profil/onem-gida-san-ve-tic-a-s-4325-233362` — open — cocoa/hazelnut/chocolate-paste & flour, Karaman; supply-chain/process/quality/data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Horizon Gıda (Yıldız Holding)** — `https://www.horizongida.com.tr/tr` — open — FMCG traditional-channel distribution (Ülker brands), İstanbul; supply-chain/sales/data/process analyst; email: none found

### Eczacıbaşı Holding group
- **Eczacıbaşı İlaç Pazarlama (EİP) (Eczacıbaşı Holding)** — `https://www.eczacibasiilac.com.tr/career` — login-to-apply — pharma marketing/sales & distribution, İstanbul; PM, finance/data/process/BI analyst; email: none found
- **Eczacıbaşı Girişim Pazarlama (Eczacıbaşı Holding)** — `https://eczacibasikariyer.com.tr/is-ilanlari` — login-to-apply — FMCG sales & distribution (Selpak, etc.), İstanbul; supply-chain/sales/data/process analyst; email: none found
- **Eczacıbaşı Bilişim (Eczacıbaşı Holding)** — `https://eczacibasibilisim.com.tr/kariyer/` — open — IT/digital-transformation services, İstanbul; Business Analyst, BI/data analyst, PM; email: none found
- **İpek Kağıt (Eczacıbaşı Holding)** — `https://eczacibasikariyer.com.tr/is-ilanlari` — login-to-apply — tissue paper (Selpak/Solo/Silen), Karamürsel/Kocaeli; PM, supply-chain/process/data/BI analyst; email: none found
- **VitrA Karo (Eczacıbaşı Holding)** — `https://eczacibasikariyer.com.tr/is-ilanlari` — login-to-apply — ceramic tile manufacturer, Bozüyük; production, engineering, finance/process; email: none found
- **Eczacıbaşı Sağlık Hizmetleri (Eczacıbaşı Holding)** — `https://www.kariyer.net/firma-profil/eczacibasi-saglik-hizmetleri-1026-232159` — login-to-apply — health services / OHS, Kavacık/İstanbul; ops/finance/data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Eczacıbaşı Yatırım Holding (ECZYT) (Eczacıbaşı Holding)** — `https://careers.eczacibasi.com/` — login-to-apply — listed investment holding, İstanbul; finance/investment/data analyst; email: none found
- **E-Kart Elektronik Kart Sistemleri (Eczacıbaşı + G&D JV)** — `https://www.ekart.com.tr/en/Career.aspx` — login-to-apply — smart-card/digital security, Gebze/Kocaeli; production, engineering, data; email: info@ekart.com.tr

### Borusan Holding group
- **Borusan Mannesmann Boru (BRSAN) (Borusan Holding)** — `https://careers.borusan.com/` — open — steel-pipe manufacturer, İstanbul/Gemlik; PM, supply-chain/process/data/BI analyst; email: none found
- **Borusan Makina ve Güç Sistemleri / Borusan Cat (Borusan Holding)** — `https://www.borusancat.com/tr/corporate/human-resources/career-process` — open — Caterpillar dealer (machinery/power), İstanbul; PM, finance/supply-chain/data/BI analyst; email: none found
- **Borusan Otomotiv (Borusan Holding)** — `https://www.kariyer.net/firma-profil/borusan-otomotiv-grubu-8526-65441` — open — BMW/MINI/Jaguar/Land Rover importer, İstanbul; data/BI/finance/process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Borusan Oto Servis (Borusan Holding)** — `https://www.borusanoto.com/hakkimizda/is-ilanlari` — open — automotive retail/after-sales, İstanbul/Ankara/İzmir; sales/finance/HR/data analyst; email: none found
- **Borçelik (Borusan Holding + ArcelorMittal JV)** — `https://www.borcelik.com/insan-ve-kariyer` — open — flat/galvanized steel, Gemlik/Bursa; PM, supply-chain/process/data analyst; email: none found
- **Supsan Motor Supapları (Borusan Holding)** — `https://careers.borusan.com/` — open — engine-valve/automotive components, Gebze; supply-chain/process/quality/data analyst; email: none found
- **Kerim Çelik (Borusan Holding)** — `https://kerimcelik.com/Tr/InsanveKariyer` — open — steel service center, Gemlik; supply-chain/process/data analyst; email: none found

### Doğan Holding group
- **Doğan Trend Otomotiv (Doğan Holding)** — `https://www.doganholding.com.tr/insan-kaynaklari/dogan-holding-de-kariyer/` — open — automotive importer & mobility (Suzuki, Chery), İstanbul; PM, data/BI/finance/process analyst; email: none found
- **Suzuki Motorlu Araçlar Pazarlama (Doğan Holding)** — `https://www.doganholding.com.tr/insan-kaynaklari/dogan-holding-de-kariyer/` — open — Suzuki distributor, İstanbul; sales/finance/data analyst; email: none found
- **Doğan Dış Ticaret ve Mümessillik (Doğan Holding)** — `https://www.ddt.com.tr/en/dogan-holding.html` — open — foreign trade / commodity & energy trading, İstanbul; trade/finance/supply-chain/data analyst; email: none found
- **Karel Elektronik (KAREL) (Doğan Holding)** — `https://www.karel.com.tr/` — open — telecom/electronics manufacturer, Ankara/İstanbul; PM, data/BI/process analyst; email: none found
- **Hepsiemlak (Doğan Holding)** — `https://www.hepsiemlak.com/` — open — real-estate listings platform, İstanbul; Data Analyst, BI, Business Analyst, product/project; email: none found
- **Hepiyi Sigorta (Doğan Holding)** — `https://www.doganholding.com.tr/insan-kaynaklari/dogan-holding-de-kariyer/` — open — insurance, İstanbul; actuarial/finance/data analyst; email: none found
- **Doruk Faktoring (Doğan Holding)** — `https://www.doganholding.com.tr/insan-kaynaklari/dogan-holding-de-kariyer/` — open — factoring, İstanbul; finance/credit/data analyst; email: none found

### Çalık Holding group
- **Aktif Yatırım Bankası / Aktif Bank (Çalık Holding)** — `https://www.aktifbank.com.tr/hakkimizda/yetenek-ve-gelisim` — login-to-apply — investment banking, İstanbul; finance/data/BI/business analyst, risk; email: none found
- **GAP İnşaat (Çalık Holding)** — `https://gapinsaat.com/tr/insan-kaynaklari.html` — open — construction/EPC, İstanbul + intl; PM, cost/finance analyst, planning; email: none found
- **Lidya Madencilik (Çalık Holding)** — `https://lidyamadencilik.com/kariyer/` — open — mining, İstanbul HQ + sites; data/finance/process analyst, PM; email: ik@lidyamadencilik.com
- **E-Kent (Aktif Bank ecosystem, Çalık Holding)** — `https://www.aktifbank.com.tr/en/about-us/affiliated-corporations` — restricted — urban smart-transit fare/ticketing, İstanbul; PM/data/BI/process; email: none found
- **UPT Ödeme Hizmetleri (Aktif Bank ecosystem, Çalık Holding)** — `https://www.aktifbank.com.tr/en/about-us/affiliated-corporations` — restricted — money-transfer/payments fintech, İstanbul; product/data/finance/process analyst; email: none found
- **N Kolay Ödeme (Aktif Bank ecosystem, Çalık Holding)** — `https://www.aktifbank.com.tr/en/about-us/affiliated-corporations` — restricted — bill-payment/e-money network, İstanbul; BI/data/ops/process; email: none found
- **Sigortayeri (Aktif Bank ecosystem, Çalık Holding)** — `https://www.aktifbank.com.tr/en/corporate-banking/insurance-services/sigortayeri` — restricted — insurance brokerage, İstanbul; finance/data/BI/ops analyst; email: none found
- **Aktif Portföy Yönetimi (Aktif Bank ecosystem, Çalık Holding)** — `https://www.aktifbank.com.tr/en/about-us/affiliated-corporations` — restricted — asset/fund management, İstanbul; investment/finance/data analyst; email: none found

### Enka group
- **ENKA Pazarlama (Enka)** — `https://www.kariyer.net/firma-profil/enka-pazarlama-ihracat-ithalat-a-s-5566-30449` — login-to-apply — heavy-machinery distribution (Hitachi/XCMG), İstanbul; supply-chain/business/data analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Çimtaş (Çimtaş Çelik/Boru/Gemi) (Enka)** — `https://www.kariyer.net/firma-profil/cimtas-1234-2557` — open — steel fabrication/pipe/modules, Gemlik/Bursa; project/process/quality analyst, planning, PM; email: cimtas_gemlik@cimtas.com (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **ENKA Power / Enka Enerji (Enka)** — `https://www.kariyer.net/firma-profil/enka-power-156069-80798` — login-to-apply — power generation, İstanbul/Gebze/Adapazarı/İzmir; finance/data/process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kasktaş (Enka)** — `https://www.kariyer.net/firma-profil/kasktas-a-s-5760-30643` — login-to-apply — geotechnical/foundation engineering, İstanbul; project/planning analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **ENKA Teknik (Enka)** — `https://enka.hrpeak.com/jobs` — login-to-apply — O&M/facility & plant services, İstanbul; process/finance analyst, PM; email: none found
- **ENKA Okulları (Enka)** — `https://www.enka.k12.tr/istanbul/tr/insan-kaynaklari/` — open — education, İstanbul/Adapazarı/İzmir; admin, finance, HR; email: hr@enka.k12.tr

### Tekfen Holding group
- **Tekfen İnşaat ve Tesisat (Tekfen Holding)** — `https://www.kariyer.net/firma-profil/tekfen-insaat-ve-tesisat-a-s-54192-175164` — login-to-apply — EPC construction, İstanbul; PM, project controls, civil/mechanical eng; email: business@tekfen.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tekfen Mühendislik / Engineering (Tekfen Holding)** — `https://www.tekfenmuhendislik.com/careers/` — login-to-apply — engineering/EPC design, Kağıthane/İstanbul; project/process/data analyst, PM; email: muhendislik.ik@tekfen.com.tr

### OYAK group
- **Oyak Renault (OYAK 49%)** — `http://www.oyak-renault.com.tr/RenaultBasvuru/` — login-to-apply — automotive manufacturing, Bursa; process/supply-chain/data analyst, PM, finance; email: none found
- **OYAK Yatırım Menkul Değerler (OYAK)** — `https://www.kariyer.net/firma-profil/oyak-yatirim-menkul-degerler-a-s-33182-25474` — login-to-apply — brokerage/investment, Levent/İstanbul; finance/data/BI analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **OYAK Portföy Yönetimi (OYAK)** — `https://www.oyak.com.tr/oyak-sirketleri/kariyer` — login-to-apply — asset management, İstanbul; finance/data analyst; email: none found
- **OYAK Pazarlama (OYAK)** — `https://www.oyak.com.tr/oyak-sirketleri/kariyer` — login-to-apply — retail/marketing/tourism, Ankara/İstanbul; business/supply-chain analyst; email: none found
- **OYAK Denizcilik ve Liman İşletmeleri / OYAK Maritime (OYAK)** — `https://www.oyakliman.com/` — login-to-apply — port/maritime, İstanbul/İskenderun; strategic-planning/business-dev/supply-chain analyst, PM; email: none found
- **Almatis (OYAK)** — `https://www.almatis.com/en/careers` — open — alumina/specialty chemicals, global + Turkey ops; process/supply-chain/data analyst, PM; email: none found
- **Ataer Holding (OYAK)** — `https://www.oyak.com.tr/oyak-sirketleri/kariyer` — login-to-apply — steel-investment holding (Erdemir parent), Ankara; finance/BI/business analyst; email: none found

### Çukurova Holding group
- **Çukurova İnşaat Makinaları / Çimsataş (Çukurova)** — `https://www.kariyer.net/firma-profil/cukurova-insaat-makinalari-san-ve-tic-a-s-2136-12474` — login-to-apply — steel casting/forging, Mersin; process/quality/production analyst, PM; email: cimsatas@cimsatas.com (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Çukurova Makina İmalat (Çukurova)** — `https://www.kariyer.net/firma-profil/cukurova-makina-imalat-ve-ticaret-a-s-19341-10254` — login-to-apply — construction machinery, Mersin/Adana; process/supply-chain analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Akkök Holding group
- **AKTEK Bilgi İletişim (Akkök)** — `https://www.aktekbilisim.com/en/kariyer/` — open — IT/SAP/data analytics/BI, İstanbul; data engineer, BI specialist, business/RPA analyst; email: none found
- **Akiş GYO (Akkök)** — `https://www.akisgyo.com/acik-pozisyonlar` — open — real estate (Akasya/Akbatı malls), İstanbul; finance/BI/business analyst, PM; email: none found
- **Akcoat (Akkök, via Akkim)** — `https://www.kariyer.net/firma-profil/akcoat-235354-269860` — login-to-apply — advanced chemical coatings, Hendek/Sakarya; process/supply-chain/finance analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **DowAksa (Akkök/Aksa + Dow JV)** — `https://www.kariyer.net/firma-profil/dowaksa-ileri-kompozit-malzemeler-31109-23426` — login-to-apply — carbon-fiber composites, Yalova/İstanbul; process/supply-chain/data analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Ak-Pa Tekstil İhracat Pazarlama (Akkök)** — `https://www.akpa.com.tr/en/corporate/akkok-group` — open — textile trading/marketing, İstanbul; trade/supply-chain/business analyst; email: none found
- **Akmerkez GYO (Akkök-affiliated)** — `https://www.akmgyo.com/insan-kaynaklari` — login-to-apply — shopping-mall REIT, İstanbul; finance/business analyst; email: none found

### IC Holding (IC İçtaş) group
- **IC İçtaş İnşaat (IC Holding)** — `https://live.peoplise.com/icholding/career` (Kariyer.net `firma-profil/ic-ictas-insaat-a-s-3815-233412`) — open — construction/infrastructure (airports, bridges, highways), İstanbul/Ankara; PM, planning/cost eng, business-dev, finance analyst; email: none found
- **IC İçtaş Enerji (IC Holding)** — `https://live.peoplise.com/icholding/career` — open — power generation/distribution, İstanbul; BI/data analyst, finance, process eng; email: none found
- **İçtaş Nükleer (IC Holding)** — `https://ictasnukleer.com.tr/en/career/` — open — nuclear/industrial-facilities construction (Akkuyu), Mersin/İstanbul; project/planning, supply-chain, doc-control; email: none found
- **IC Hotels (IC Holding)** — `https://live.peoplise.com/icholding/career` — open — tourism/hospitality, Antalya; finance, revenue/BI analyst, HR; email: none found

### Limak Holding group
- **Limak İnşaat (Limak Holding)** — `https://www.limak.com.tr/kariyer/kariyer-firsatlari` — open — construction/infrastructure (airports, ports, highways), Ankara/İstanbul; PM, planning/cost/business analyst, supply-chain; email: none found
- **Limkon Gıda (Limak Holding)** — `https://www.limak.com.tr/kariyer` — open — fruit-juice concentrate/tomato paste, Adana; supply-chain/process/quality analyst, finance; email: none found
- **LimakPort İskenderun (Limak Holding)** — `https://www.limakports.com.tr/tr/is-basvurulari` — open — container/port terminal, İskenderun/Hatay; ops, supply-chain/data analyst, finance; email: none found
- **Limak Hotels / Limak Tourism (Limak Holding)** — `https://kariyer.limakhotels.com/general-application` — login-to-apply — tourism/hospitality, Antalya/Bodrum/İstanbul; revenue/BI analyst, finance, HR; email: none found
- **Hamitabat Elektrik (HEAŞ) (Limak Holding)** — `https://www.hamitabatelektrik.com/kariyer-firsatlari` — open — natural-gas power generation, Kırklareli; process eng, finance/data analyst; email: none found

### Cengiz Holding group
- **Cengiz İnşaat (Cengiz Holding)** — `https://www.cengizholding.com.tr/kariyer` — open — heavy construction/infrastructure, İstanbul; PM, planning/cost eng, business analyst, supply-chain; email: none found
- **Cengiz Enerji (Cengiz Holding)** — `https://www.cengizholding.com.tr/kariyer` — open — power generation/distribution & gas, İstanbul; BI/data/finance analyst, process eng; email: none found
- **CK Enerji / CK Boğaziçi-Akdeniz (Cengiz Holding)** — `https://www.cengizholding.com.tr/kariyer` — open — electricity distribution/retail, İstanbul/Akdeniz; data analyst, finance, process; email: none found
- **İGA Havalimanı İşletmesi / İstanbul Airport (Kalyon 55% + Cengiz 45%)** — `https://www.igairport.aero/en/career/` — login-to-apply — airport operations, İstanbul; data/BI, business, process, finance analyst, PM; email: none found

### Kibar Holding group
- **Kibar Dış Ticaret (Kibar Holding)** — `https://www.youthall.com/en/kibarholding/` — open — foreign trade/distribution, İstanbul; supply-chain/trade/finance analyst, BI; email: none found
- **Assan Panel (Kibar Holding)** — `https://www.assanpanel.com/en/corporate/career/we-at-kibar-future` — open — building materials (sandwich panels), Tuzla/İstanbul; process/supply-chain analyst, finance, project; email: none found
- **Hyundai Assan Otomotiv (Kibar Holding + Hyundai JV)** — `https://www.youthall.com/en/kibarholding/` — restricted — automotive manufacturing, İzmit/Kocaeli; process/supply-chain/quality analyst, finance; email: none found
- **İspak Esnek Ambalaj (Kibar Holding)** — `https://www.kibar.com/en` — open — flexible packaging, İzmit; process/supply-chain analyst, finance; email: none found
- **Assan Lojistik (Kibar Holding)** — `https://www.assanlojistik.com.tr/en/corporate/kibar-holding` — open — logistics, İstanbul/Kocaeli; supply-chain/data analyst, ops, finance; email: none found
- **Assan Bilişim (Kibar Holding)** — `https://www.kibar.com/en` — open — group IT services, İstanbul; BI/data analyst, business analyst, PM; email: none found

### Eren Holding group
- **Modern Karton (Eren Holding)** — `https://www.erenholding.com.tr/sayfa/kariyer-29` — open — paper/board (largest TR corrugated-board paper), Çorlu/Tekirdağ; process/supply-chain analyst, finance, project; email: none found
- **Eren Enerji (Eren Holding)** — `https://www.erenholding.com.tr/sayfa/kariyer-29` — open — power generation (ZETES coal plants), Zonguldak/İstanbul; process eng, BI/data/finance analyst; email: none found
- **Modern Ambalaj (Eren Holding)** — `https://www.modern-ambalaj.com.tr/sayfa/kariyer-12` — open — packaging/corrugated converting, Çorlu/Manisa/Gebze; process/supply-chain/quality analyst, finance; email: none found

### Yıldırım Group (Yıldırım Holding)
- **Yilport Holding (Yıldırım Holding)** — `https://www.yilport.com/en/career/detail/Job-Applications/236/296/0` — open — port/container-terminal operations, İstanbul; ops, supply-chain/data/BI analyst, finance, PM; email: hr@yilport.com
- **Yılmaden Holding (Yıldırım Holding)** — `https://yildirimcareers.com/` — open — metals & mining (chrome, ferroalloys), İstanbul; process/supply-chain/finance analyst, project; email: none found
- **Eti Krom / Yılmaden (Yıldırım Holding)** — `https://www.etikrom.com/` — open — chromite mining & ferrochrome, Elazığ/İstanbul; process/quality/supply-chain analyst, finance; email: none found
- **Yilyak (Yıldırım Holding)** — `https://yildirimcareers.com/` — open — coal/coke import-trading, İstanbul; supply-chain/trade/data analyst, finance; email: none found
- **Yilfert Holding (Yıldırım Holding)** — `https://yildirimcareers.com/` — open — fertilizers/chemicals, İstanbul; process/supply-chain/finance analyst; email: none found
- **Yilmar Shipping (Yıldırım Holding)** — `https://yildirimcareers.com/` — open — shipping mgmt/chartering/brokering, İstanbul; ops, finance/data analyst; email: none found

### Sanko Holding group
- **Sanko Enerji (Sanko Holding)** — `https://sankoenerji.com.tr/` — open — renewable energy generation, Gaziantep; BI/data/finance analyst, process eng; email: none found
- **Sanko Pazarlama (Sanko Holding)** — `https://www.sankopazarlama.com/` — open — textile marketing (yarn/fabric/denim), Gaziantep/İstanbul; supply-chain/trade/finance/data analyst; email: none found
- **Süper Film Ambalaj (Sanko Holding)** — `https://sanko.com.tr/en/career-at-sanko-holding/` — open — flexible-packaging films (BOPP), Gaziantep/Adana; process/supply-chain/quality analyst, finance; email: none found
- **Enko Enerji (Sanko Holding)** — `https://sanko.com.tr/en/career-at-sanko-holding/` — open — energy production, Gaziantep; process/finance/data analyst; email: none found

### Kale Group
- **Kale Kilit (Kale Group)** — `https://www.kalekilit.com.tr/en/corporate/human-resources/hr-processes` — open — locks/security hardware, İstanbul/Gebze; process/supply-chain/production/HR analyst, PM; email: none found
- **Kalekim (Kale Group)** — `https://www.kariyer.net/firma-profil/kalekim-kimyevi-maddeler-san-ve-tic-a-s-39873-122939` — open — construction chemicals (BIST-listed), İstanbul/Çanakkale; BI/finance/process analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kale Pratt & Whitney (Kale Group JV)** — `https://www.kalepw.com/en/kale-group` — restricted — aerospace engine components, İstanbul; project/process/supply-chain analyst; email: none found

### Fiba Holding group
- **Fibabanka (Fiba Holding)** — `https://www.fibabanka.com.tr/hakkimizda/insan-kaynaklari/fibabankada-kariyer` — login-to-apply — banking, İstanbul; data analyst, BI, business/finance analyst; email: none found
- **Fiba Faktoring (Fiba Holding)** — `https://www.fibafaktoring.com.tr/insan-kaynaklari/is-olanaklari` — open — factoring/finance, İstanbul; financial/business analyst; email: none found
- **Gelecek Varlık Yönetimi (Fiba Holding)** — `https://www.gelecekvarlik.com.tr/` — restricted — asset/debt-portfolio management, İstanbul; data/finance/business analyst; email: none found
- **Fiba Commercial Properties (Fiba Holding)** — `https://fibacp.com.tr/` — restricted — commercial real estate (malls/offices), İstanbul; finance/BI/project analyst; email: none found
- **Fiba Retail / BB Mağazacılık (Fiba Holding)** — `https://www.fibaretail.com.tr/en/about-us/history-of-fiba-retail` — restricted — M&S/GAP/lululemon TR licensee, İstanbul; retail/supply-chain/data analyst; email: none found
- **HDI Fiba Emeklilik ve Hayat (Fiba + HDI/Talanx JV)** — `https://www.kariyer.net/firma-profil/hdi-fiba-emeklilik-ve-hayat-anonim-sirketi-152621-77949` — open — pension/life; actuarial, data, marketing, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Boyner Group
- **Boyner Büyük Mağazacılık (Boyner Group)** — `https://www.kariyer.net/firma-profil/boyner-buyuk-magazacilik-1155-1689` — open — department-store retail flagship, İstanbul; data analyst, BI, business/merch/supply-chain analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Hopi (Boyner Group)** — `https://www.boynergrup.com/kariyer` — restricted — loyalty/data & digital-payments platform, İstanbul; data analyst (strong fit), BI, product/business analyst; email: none found
- **BR Mağazacılık (Boyner Group)** — `https://www.boynergrup.com/en/career` — restricted — specialty retail formats, İstanbul; retail/supply-chain/data analyst; email: none found

### TAB Gıda / TFI (Ata Holding) group
- **Ata Holding (HQ)** — `https://www.ataholding.com.tr/kariyer` — open — diversified holding (QSR/food, logistics, energy, finance), Beşiktaş/İstanbul; corporate/finance, A-Talent program; email: none found
- **TAB Gıda (Ata Holding / TFI)** — `https://www.tabgida.com.tr/kariyer/tab-gidada-calismak` — open — QSR master-franchisee (Burger King, Popeyes, Sbarro, Arby's, Subway), İstanbul; finance/BI/supply-chain/process; email: none found
- **Fasdat Gıda Dağıtım (Ata Holding / TFI)** — `https://www.fasdat.com.tr/kariyer` — open — cold-chain/3PL logistics, Beşiktaş/İstanbul; supply-chain/logistics/data/process analyst; email: none found
- **Atakey Patates (ATAKP) (Ata Holding / TFI)** — `https://www.atakey.com.tr/insan-kaynaklari/` — open — frozen-potato processing, Afyonkarahisar; supply-chain/process/data analyst, PM; email: none found
- **Ekmek Unlu Gıda (Ata Holding / TFI)** — `https://www.tabfoods.com/en/companies/ekmek-unlu-gida` — open — industrial bakery, Gebze/Kocaeli; production/quality/supply-chain; email: none found
- **Ekur Et Entegre (Ata Holding / TFI)** — `https://www.ataholding.com.tr/kariyer/kariyer-basvurusu` — open — red-meat supply (Amasya Et), Suluova/Amasya; food-eng/supply/finance; email: none found

### Ciner Group
- **Eti Soda (Ciner Group)** — `https://www.etisoda.com/kariyer/` — open — natural soda-ash mining/production, Beypazarı/Ankara; process/supply-chain/finance/data analyst, PM; email: none found
- **Park Cam (Ciner Group)** — `https://parkcam.com.tr/kariyer/` — open — glass packaging, Bozüyük/Bilecik; process/supply-chain/quality/data analyst, PM; email: none found
- **Silopi Elektrik Üretim (Ciner Group)** — `https://www.cinergroup.com.tr/en` — restricted — coal-fired power generation, Şırnak/Silopi; process/finance analyst, PM; email: none found

### Demirören Holding group
- **Demirören Medya / Demirören Gazetecilik (Demirören Holding)** — `https://www.kariyer.net/firma-profil/demiroren-medya-grubu-29952-42769` — open — media (Hürriyet, Milliyet, Posta, Kanal D, CNN Türk, DHA), İstanbul; data/BI/business/finance analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Esas Holding group
- **Esas Gayrimenkul / Esas Properties (Esas Holding)** — `https://www.esasgayrimenkul.com.tr/insanvekultur` — open — commercial real estate ("Burda" malls), İstanbul; finance/BI/project/business analyst; email: none found
- **Esas Holding (HQ)** — `https://www.kariyer.net/firma-profil/esas-holding-a-s-110956-107440` — open — investment holding / private equity, İstanbul; investment/finance/data/business analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Global Yatırım Holding group
- **Global Ports Holding (Global Yatırım Holding)** — `https://www.globalportsholding.com/careers/` — open — world's largest cruise-port operator (LSE-listed; İstanbul HQ); finance/data/business analyst, PM; email: careers@globalportsholding.com
- **Straton Maden (Global Yatırım Holding)** — `https://www.kariyer.net/firma-profil/straton-maden-yatirimlari-ve-isletmeciligi-a-s-48774-226010` — open — feldspar mining, Yatağan/Muğla; process/supply-chain/finance analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Akfen Holding group
- **Akfen İnşaat (Akfen Holding)** — `https://www.akfen.com.tr/insan-kaynaklari/genel-basvuru/` — open — construction/infrastructure (PPP, airports, ports), Ankara/İstanbul; PM, planning/cost-control, BI/finance analyst; email: none found
- **Akfen Yenilenebilir Enerji (Akfen Holding)** — `https://www.kariyer.net/firma-profil/akfen-yenilenebilir-enerji-a-s-27717-208845` — open — renewable energy (HES/RES/GES), İstanbul; data/process/finance analyst, asset-mgmt; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Akfen GYO / Akfen Gayrimenkul (Akfen Holding)** — `https://www.akfen.com.tr/insan-kaynaklari/genel-basvuru/` — open — hotel REIT (Novotel/ibis), İstanbul; BI, finance, business analyst; email: none found
- **Akfen Çevre ve Su (Akfen Holding)** — `https://www.akfen.com.tr/insan-kaynaklari/genel-basvuru/` — open — water/wastewater concessions, İstanbul; process/finance analyst, PM; email: none found

### Rönesans Holding group
- **Rönesans İnşaat / Rönesans Construction (Rönesans Holding)** — `https://careers.ronesans.com/` — open — construction/contracting, Ankara/İstanbul; PM, planning, cost, BI/business analyst; email: none found
- **Rönesans Endüstri Tesisleri / RES (Rönesans Holding)** — `https://www.kariyer.net/firma-profil/ronesans-endustri-6626-232419` — open — industrial plants/EPC, Maltepe/İstanbul; PM, supply-chain/procurement analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Rönesans Gayrimenkul Yatırım / RGY (Rönesans Holding)** — `https://www.kariyer.net/firma-profil/ronesans-gayrimenkul-yatirim-6626-46439` — open — commercial real estate (Optimum/Piazza malls), İstanbul; BI, finance, leasing/business analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Rönesans Sağlık Yatırım / RSY (Rönesans Holding)** — `https://careers.ronesans.com/` — open — healthcare PPP hospital investments/ops, İstanbul; finance, BI, business analyst, PM; email: none found

### Nurol Holding group
- **Nurol İnşaat ve Ticaret (Nurol Holding)** — `https://www.nurol.com.tr/en/job-applicaiton` — open — construction/contracting, Ankara; PM, planning, cost, finance analyst; email: none found
- **Nurol GYO (Nurol Holding)** — `https://www.kariyer.net/firma-profil/nurol-holding-5245-30128` — open — real-estate REIT, Ankara/İstanbul; BI, finance, business analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Nurol Yatırım Bankası / NurolBank (Nurol Holding)** — `https://www.kariyer.net/firma-profil/nurol-yatirim-bankasi-as-67827-142300` — open — investment/corporate banking & treasury, İstanbul; data/BI/risk/finance analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Nurol Enerji (Nurol Holding)** — `https://www.nurolenerji.com.tr/en/human-resources/` — open — energy generation/marketing & solar, Ankara; process/finance analyst; email: info@nurolenerji.com.tr

### STFA Group
- **STFA İnşaat (STFA Group)** — `https://www.stfa.com/en/careers/` — open — construction/contracting, İstanbul; PM, planning, cost analyst; email: none found
- **STFA Deniz İnşaatı (STFA Group)** — `https://www.stfa.com/en/careers/` — open — marine/maritime construction (ports, dredging), İstanbul; PM, supply-chain analyst, planning; email: none found
- **Enerya Enerji (STFA Group)** — `https://www.enerya.com.tr/tr/kurumsal/insan-kaynaklari/eneryada-kariyer` — open — natural-gas distribution (10 cities) & electricity trade, İstanbul; data/BI/process/finance analyst; email: none found

### Gülermak group
- **Gülermak Ağır Sanayi İnşaat (Gülermak)** — `https://www.kariyer.net/firma-profil/gulermak-agir-sanayi-insaat-ve-taahhut-a-s-26285-17890` — open — metro/tunnel/rail heavy-civil contractor, Ankara; PM, planning, geotechnical, cost/BI analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Kolin Holding group
- **Kolin İnşaat (Kolin / Koloğlu Holding)** — `https://www.kariyer.net/firma-profil/kolin-insaat-turizm-sanayi-ve-ticaret-a-s-23707-15055` — open — infrastructure/transport construction, Ankara; PM, planning, cost, BI/finance analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kolin Enerji Yatırımları (Kolin / Koloğlu Holding)** — `https://tr.linkedin.com/company/kolin-enerji-yatirimlari` — login-to-apply — power generation, gas distribution, LNG, Ankara; process/finance/data analyst; email: none found

### Kalyon Holding group
- **Kalyon İnşaat (Kalyon Holding)** — `https://www.kariyer.net/firma-profil/kalyon-insaat-sanayi-ve-ticaret-a-s-14452-222656` — open — construction & aviation contractor, İstanbul; PM, planning, cost, BI/process analyst; email: holdinginsankaynaklari@kalyonholding.com (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kalyon Holding (HQ)** — `https://kalyonholding.com/Career` — open — holding HQ, İstanbul; data/BI/finance/HR analyst; email: holdinginsankaynaklari@kalyonholding.com

### Gama Holding group
- **GAMA Güç Sistemleri / Power Systems (Gama Holding)** — `https://www.kariyer.net/firma-profil/gama-guc-sistemleri-a-s-7363-80606` — open — power-plant EPC engineering & contracting, Ankara; PM, planning, procurement/supply-chain analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **GAMA Endüstri Tesisleri (Gama Holding)** — `https://www.kariyer.net/firma-profil/gama-endustri-tesisleri-imalat-ve-montaj-a-s-7363-32241` — open — industrial-plant manufacturing/erection, Ankara; procurement/proposal eng, supply-chain/BI analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Gama Enerji (Gama Holding)** — `https://enerji.gama.com.tr/en/career/career-at-gama/general-application/` — open — energy generation/distribution investments, Ankara; process/finance/data analyst; email: none found

### Türkerler Holding group
- **Türkerler İnşaat Turizm Madencilik Enerji (Türkerler Holding)** — `https://www.kariyer.net/firma-profil/turkerler-insaat-turizm-madencilik-tic-ve-san-as-4721-29604` — open — construction + renewables + mining (PPP hospitals, YEKA wind), Ankara; PM, planning, BI/finance/process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Polat Holding group
- **Polat Holding (HQ)** — `https://www.kariyer.net/firma-profil/polat-holding-164403-89659` — open — real estate/energy/aviation/industry holding, İstanbul; data/BI/finance/HR analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Polat Gayrimenkul (Polat Holding)** — `https://www.polat.com/polatta-hayat` — open — real-estate development (Piyalepaşa İstanbul), İstanbul; BI, finance, leasing/business analyst; email: none found

### Hayat Holding group
- **Kastamonu Entegre (KENT) (Hayat Holding)** — `https://www.kastamonuentegre.com/en/human` — open — wood-based panels/MDF/laminate (BIST-listed), Gebze/Kocaeli + Kastamonu; PM, BI, supply-chain, process, finance analyst; email: kariyer@keas.com.tr

### Doğanlar Holding group
- **Doğtaş Kelebek Mobilya (DGNMO) (Doğanlar Mobilya Grubu)** — `https://www.kariyer.net/firma-profil/dogtas-kelebek-mobilya-4687-232051` — open — furniture (legal entity behind Doğtaş+Kelebek brands; BIST-listed), Biga/Çanakkale; PM, retail-ops, BI, supply-chain analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Biotrend Enerji (BIOEN) (Doğanlar Holding)** — `https://www.doganlarholding.com.tr/markalarimiz` — restricted — waste-to-energy (BIST-listed); process/data/finance analyst; email: none found

### Erciyes Anadolu Holding group
- **Boyteks Tekstil (Erciyes Anadolu Holding)** — `https://www.boyteks.com/tr/insan-kaynaklari/ise-alim/acik-pozisyonlar` — open — technical/mattress-ticking textiles, Kayseri; process/supply-chain/BI analyst; email: none found
- **Boyçelik (Erciyes Anadolu Holding)** — `http://www.boycelik.com.tr/insan-kaynaklari` — open — iron & steel/metal goods, Kayseri; production/process/supply-chain analyst; email: none found
- **Form Sünger (Erciyes Anadolu Holding)** — `https://kariyer.erciyes.com` — login-to-apply — polyurethane foam/chemicals, Kayseri; process/supply-chain analyst; email: none found
- **Gümüşsuyu Halı (Erciyes Anadolu Holding)** — `https://kariyer.erciyes.com` — login-to-apply — carpet/textiles, Kayseri/İstanbul; BI/supply-chain analyst; email: none found

### Aydınlı Group
- **Aydınlı Hazır Giyim (Aydınlı Group)** — `https://aydinli.com.tr/tr/kurumsal/hakkimizda` — restricted — apparel mfg (U.S. Polo Assn., Pierre Cardin, Cacharel licenses), Silivri/İstanbul; PM, retail/merch, supply-chain, BI analyst; email: none found

### NG Holding (Güral / NG Group)
- **Kütahya Porselen (KUTPO) (NG Group / Güral)** — `https://kutahyaporselen.com.tr/tr/insan-kaynaklari` — open — porcelain tableware manufacturer (BIST-listed), Kütahya; PM, process/supply-chain/BI analyst; email: none found
- **NG Hotels (NG Group)** — `https://www.nghotels.com.tr/tr/` — restricted — hotel/resort operations (NG Afyon/Sapanca/Phaselis Bay), Afyon/Sapanca/Antalya; revenue/finance/ops analyst; email: none found

### MNG Holding group
- **MNG Havayolları / MNG Airlines (MNG Holding)** — `https://www.kariyer.net/firma-profil/mng-hava-yollari-ve-tasimacilik-a-s-4864-29747` — open — air cargo & charter, İstanbul Airport; PM, ops/supply-chain/data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **MNG Turizm (MNG Holding)** — `https://www.kariyer.net/firma-profil/mng-turizm-7162-218337` — open — travel agency/tour operator, İstanbul; PM, BI/finance/process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Net Holding group
- **Net Turizm (Net Holding)** — `https://www.kariyer.net/firma-profil/net-turizm-tic-ve-san-a-s-merit-lefkosa-otel-14015-50961` — open — tourism/hotel operating company, İstanbul + TRNC; PM, finance/BI/ops analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Merit International Hotels & Resorts (Net Holding)** — `https://www.kariyer.net/firma-profil/merit-international-hotels-resorts-14015-232196` — open — casino-hotel chain (TRNC, Croatia); revenue/finance/HR/ops analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### İhlas Holding group
- **İhlas Ev Aletleri (IHEVA) (İhlas Holding)** — `https://tr.linkedin.com/company/ihlas-ev-aletleri` — open — home/small appliances manufacturer (BIST-listed), İstanbul; PM, process/supply-chain/BI analyst; email: none found
- **İhlas Pazarlama (İhlas Holding)** — `https://ihlaspazarlama.com.tr/tr/kurumsal/insan-kaynaklari` — open — nationwide retail/distribution (~850 points), İstanbul; PM, sales-ops/supply-chain/data analyst; email: none found
- **İhlas Gazetecilik / Türkiye Gazetesi (IHGZT) (İhlas Holding)** — `https://www.ihlas.com.tr/ihlas-journalism-co` — open — newspaper/media, Bahçelievler/İstanbul; finance/process/HR analyst; email: none found

### Albayrak Group
- **Tümosan Motor ve Traktör (TMSN) (Albayrak Group)** — `https://www.kariyer.net/firma-profil/tumosan-motor-ve-traktor-san-a-s-4429-6731` — open — diesel engines & tractors (BIST-listed), Konya + Zeytinburnu/İstanbul; PM, process/supply-chain/data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Albayrak Turizm Seyahat (Albayrak Group)** — `https://www.albayrak.com.tr/kariyer/` — open — transport/tourism, İstanbul; PM, ops/finance analyst; email: ik@albayrak.com.tr
- **Varaka Kağıt (Albayrak Group)** — `https://www.albayrak.com.tr/is-ilanlari/` — restricted — recycled-paper manufacturing, Balıkesir; process/supply-chain analyst; email: ik@albayrak.com.tr
- **Albayrak İnşaat (Albayrak Group)** — `https://www.albayrak.com.tr/is-ilanlari/` — open — construction, İstanbul; PM, finance/process analyst; email: ik@albayrak.com.tr
- **Yeni Şafak / Albayrak Medya (Albayrak Group)** — `https://www.albayrak.com.tr/is-ilanlari/` — open — newspaper & media (incl. TVNET), İstanbul; finance/process/HR analyst; email: ik@albayrak.com.tr

### Tosyalı Holding group
- **Tosyalı Toyo Çelik (Tosyalı + Toyo Kohan JV)** — `https://www.kariyer.net/firma-profil/tosyali-toyo-celik-anonim-sirketi-68636-220210` — open — flat steel, Osmaniye; production/quality/finance/supply-chain analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tosçelik Granül (Tosyalı Holding)** — `https://kariyer.tosyaliholding.com.tr/` — open — steel granule/abrasive, Osmaniye; production/process/supply-chain analyst; email: none found
- **Tosyalı Elektrik Enerjisi (Tosyalı Holding)** — `https://kariyer.tosyaliholding.com.tr/` — open — wholesale electricity trading; energy-trading/finance analyst; email: none found
- **Tosyalı Filmaşin ve İnşaat Demiri (Tosyalı Holding)** — `https://kariyer.tosyaliholding.com.tr/` — open — wire rod & rebar, Osmaniye; production/planning/finance; email: none found
- **Tosyalı Denizcilik ve Liman İşletmeciliği (Tosyalı Holding)** — `https://kariyer.tosyaliholding.com.tr/` — open — maritime & port ops/logistics; supply-chain/logistics/PM; email: none found

### Sancak Group
- **Sancak Ecza Deposu (Sancak Group)** — `https://tr.linkedin.com/company/sancak-ecza-deposu` — login-to-apply — pharma/cosmetic cold-chain distribution, İstanbul; supply-chain/logistics/finance/data analyst; email: none found
- **Sancak Enerji Hizmetleri (Sancak Group)** — `https://www.sancakenerji.com/` — restricted — renewable energy (wind/solar), İstanbul/Konya; PM/energy-analyst/finance; email: none found

### Bereket / Aydem group
- **Aydem Yenilenebilir Enerji (AYDEM) (Bereket Enerji)** — `https://www.aydemenerji.com.tr/bilgi/45/kariyer-firsatlari/` — open — renewable power generation (BIST-listed); PM/BI/finance/process analyst; email: none found
- **Aydem Elektrik Perakende (Bereket Enerji)** — `https://www.aydemperakende.com.tr/en/career` — open — electricity retail (Aydın-Denizli-Muğla); business-analyst/BI/finance; email: none found
- **Gediz Elektrik Perakende (Bereket Enerji)** — `https://www.gedizperakende.com.tr/en/career` — open — electricity retail (İzmir-Manisa); analyst/finance/process; email: none found
- **ADM Elektrik Dağıtım (Bereket Enerji)** — `https://www.aydemenerji.com.tr/bilgi/45/kariyer-firsatlari/` — open — electricity distribution (Aydın-Denizli-Muğla); PM/data analyst/process; email: none found

### Gözde Girişim (Yıldız Holding PE)
- **Gözde Girişim Sermayesi Yatırım Ortaklığı (GOZDE) (Yıldız Holding)** — `https://www.kariyer.net/firma-profil/gozde-girisim-sermayesi-yatirim-ortakligi-a-s-4325-233361` — login-to-apply — private equity/VC, İstanbul; investment-analyst/finance/BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Acıbadem Sağlık Grubu
- **Acıbadem Sağlık Hizmetleri (Acıbadem Sağlık Grubu)** — `https://kariyer.acibadem.com.tr/` — open — hospital group (29 hospitals), İstanbul; PM/BI/finance/HR/process analyst + clinical; email: none found
- **Acıbadem Labmed (Acıbadem Sağlık Grubu)** — `https://www.kariyer.net/firma-profil/acibadem-saglik-grubu-3713-28596` — open — central medical labs; lab + data/quality/supply-chain analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Acıbadem Mobil Sağlık (Acıbadem Sağlık Grubu)** — `https://acibademmobil.com.tr/` — open — home/mobile health & emergency, İstanbul; ops/PM/process; email: none found
- **Acıbadem Mehmet Ali Aydınlar Üniversitesi (Acıbadem Sağlık Grubu)** — `https://www.kariyer.net/firma-profil/acibadem-mehmet-ali-aydinlar-universitesi-3713-332167` — open — private health-sciences university, İstanbul; academic + admin/finance/HR/data; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Altınbaş Holding group
- **Altınbaş Üniversitesi (Altınbaş Holding)** — `https://www.kariyer.net/firma-profil/altinbas-holding-3406-26439` — open — private university, İstanbul; academic + admin/finance/HR/data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Creditwest Faktoring (Altınbaş Holding)** — `http://www.altinbasholding.com/tr/iletisim/grup-sirketleri/` — restricted — factoring/finance, İstanbul; finance/credit-analyst/BI; email: none found

### Eroğlu Holding group
- **Eroğlu Giyim (Eroğlu Holding)** — `https://www.eroglugroup.com.tr/tr/career` — open — apparel/denim manufacturing (supplies Colin's/Loft + global brands), İstanbul/Aksaray; supply-chain/purchasing/PM/process/finance analyst; email: none found
- **Eroğlu Gayrimenkul (Eroğlu Holding)** — `https://www.kariyer.net/firma-profil/eroglu-gayrimenkul-4674-46582` — open — real estate/mall development (Erasta, Skyland), İstanbul; PM/finance/leasing analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Yıldızlar Yatırım Holding group
- **Yıldız Entegre Ağaç (Yıldızlar Yatırım Holding)** — `https://www.yildizentegre.com/tr/kariyer` — open — forest products / MDF & particleboard, Kocaeli; PM/BI/supply-chain/process/finance analyst; email: none found

### Kazancı Holding group
- **Aksa Jeneratör / Aksa Power Generation (Kazancı Holding)** — `https://www.kariyer.net/firma-profil/aksa-jenerator-5315-257921` — open — power-generator mfg/export, Çatalca/İstanbul; PM/supply-chain/process/data/finance analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Aksa Doğalgaz Dağıtım (Kazancı Holding)** — `https://www.aksadogalgaz.com.tr/Kurumsal/Kariyer/Is-Basvuru-Formu` — open — natural-gas distribution (largest in TR); PM/billing-analyst/process/finance; email: none found

### İş Bankası group
- **İş Yatırım Menkul Değerler (İş Bankası group)** — `https://www.isyatirim.com.tr/en-us/who-we-are/human-resources/pages/default.aspx` — open — brokerage/investment banking, Levent/İstanbul; finance/quant, trader, BI, business/data analyst; email: ik@isyatirim.com.tr
- **İş Portföy Yönetimi (İş Bankası group)** — `https://www.isportfoy.com.tr/insan-kaynaklari` — open — asset/portfolio management, İstanbul; portfolio mgr, quant, fund/data analyst; email: kariyer@isportfoy.com.tr
- **İş Faktoring (İş Bankası group)** — `https://www.kariyer.net/firma-profil/is-faktoring-2230-13508` — open — factoring/finance, İstanbul; credit/risk analyst, business analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **İş Finansal Kiralama / İş Leasing (İş Bankası group)** — `https://www.isleasing.com.tr/insan-kaynaklari/ise-alim-ve-kariyer/` — open — financial leasing, İstanbul; finance, credit/risk, business analyst; email: none found
- **İş GYO (İş Bankası group)** — `https://www.kariyer.net/firma-profil/is-gayrimenkul-yatirim-ortakligi-a-s-186738-201634` — open — REIT, Levent/İstanbul; project/finance/PM, business analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Softtech (İş Bankası group)** — `https://softtech.com.tr/en/category/career/` — open — IT/fintech software, İstanbul; software, data analyst, BI, data science, AI, cybersecurity; email: none found
- **İşNet (İş Bankası group)** — `https://www.kariyer.net/firma-profil/is-net-4543-29426` — open — telecom/data-center/cloud/cybersecurity, Tuzla/İstanbul & Ankara; network/data eng, BI, business analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **TSKB (Türkiye Sınai Kalkınma Bankası) (İş Bankası group)** — `http://www.tskb.com.tr/tr/tskb-de-kariyer/tskb-de-is-firsatlari/acik-pozisyonlar` — open — development/investment bank, Fındıklı/İstanbul; finance/quant, credit/project finance, data/BI, ESG analyst; email: none found
- **TSKB Gayrimenkul Değerleme (İş Bankası group)** — `https://www.tskbgd.com.tr/kariyer/genel-basvuru/` — open — real-estate appraisal, İstanbul + regional; appraisal expert, analyst; email: none found
- **Yatırım Finansman Menkul Değerler (İş Bankası group, via TSKB)** — `https://www.yf.com.tr/hakkimizda/bizi-taniyin` — open — brokerage/capital markets, Levent/İstanbul; trader, advisory, finance/quant, analyst; email: none found
- **Maxis Girişim Sermayesi Portföy Yönetimi (İş Bankası group)** — `https://www.kariyer.net/firma-profil/maxis-girisim-sermayesi-portfoy-yonetimi-anonim-si-371903-429458` — open — VC fund management, Levent/İstanbul; investment/finance analyst, fund/PM, business analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Milli Reasürans (İş Bankası group)** — `http://www.millire.com/Kariyer.html` — open — reinsurance, Levent/İstanbul; actuarial, underwriting, finance/quant, data analyst, risk; email: none found
- **Anadolu Sigorta (İş Bankası / Milli Reasürans group)** — `https://www.kariyer.net/firma-profil/anadolu-sigorta-18168-8964` — open — insurance (dedicated "Veri Analizi ve Yönetim Raporlaması" unit), Kavacık/İstanbul; Data Analyst, BI, actuarial, underwriting analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Anadolu Hayat Emeklilik (İş Bankası group)** — `https://cv.anadoluhayat.com.tr/` — login-to-apply — pension/life, İstanbul; actuarial, data, software; email: none found

### Insurers (various groups / independent)
- **Türkiye Sigorta (Türkiye Varlık Fonu, state)** — `https://turkiyesigortakariyer.hrpeak.com/jobs` — open — insurance, Levent/İstanbul; İş Analisti, Data Analyst, actuarial; email: none found
- **Türkiye Hayat ve Emeklilik (Türkiye Varlık Fonu, state)** — `https://turkiyesigortakariyer.hrpeak.com/jobs` — open — pension/life, İstanbul; actuarial, data, BI; email: none found
- **Mapfre Sigorta Türkiye** — `https://www.mapfre.com.tr/sigorta-tr/biz-kimiz/insan-kaynaklari/mapfrede-kariyer/acik-pozisyonlarimiz/` — open — insurance, İstanbul; Data Analyst, BI, underwriting analyst; email: none found
- **Allianz Türkiye / Allianz Sigorta** — `https://www.allianz.com.tr/tr_TR/bize-katilin/allianzda-kariyer.html` — open — insurance, Ataşehir/İstanbul; Data Analyst, BI, Business Analyst, actuarial; email: none found
- **HDI Sigorta (HDI/Talanx)** — `https://www.hdisigorta.com.tr/hdi-kariyer` — open — insurance, İstanbul; Data Analyst, BI, underwriting analyst; email: none found
- **Sompo Sigorta Türkiye** — `https://www.somposigorta.com.tr/en/human-resources` — open — insurance, Beykoz/İstanbul; marketing analytics, underwriting, Business Analyst, actuarial; email: none found
- **Türk Nippon Sigorta (Harel group)** — `https://www.turknippon.com/tr/insan-kaynaklari` — open — insurance, İstanbul; Hasar Destek Analisti, risk mgmt, underwriting; email: none found
- **Groupama Sigorta Türkiye** — `https://www.kariyer.net/firma-profil/groupama-sigorta-ve-groupama-hayat-a-s-4098-233841` — open — insurance/pension, Maslak/İstanbul; Data Analyst, BI, SAP/system, accounting analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Zurich Sigorta Türkiye** — `https://zurichsigorta.com.tr/zurich-sigorta/kariyer` — open — insurance, İstanbul; Veri Analisti, compliance, underwriting analyst; email: none found
- **Generali Sigorta Türkiye** — `https://www.generali.com.tr/insan-kaynaklari` — open — insurance, İstanbul; System Analyst, Data Analyst, Business Analyst, claims; email: none found
- **Ray Sigorta (Vienna Insurance Group)** — `https://www.raysigorta.com.tr/hakkimizda/ray-sigortada-kariyer` — open — insurance, Tarabya/İstanbul; Data Analyst, BI, Business Analyst, actuarial; email: none found
- **Doğa Sigorta (independent)** — `https://www.dogasigorta.com/dogada-kariyer` — open — insurance, Maslak/İstanbul; İş Analisti, Data Analyst, underwriting; email: none found
- **Neova Katılım Sigorta (Kuveyt Türk group)** — `https://www.neova.com.tr/hakkimizda/insan-kaynaklari` — open — participation insurance, İstanbul; Data Analyst, BI, underwriting; email: none found
- **Quick Sigorta (Maher Holding)** — `https://kurumsal.quicksigorta.com/kariyer.html` — open — insurance, Ataşehir/İstanbul; İş Zekası Uzmanı (BI), Data Analyst, underwriting; email: none found
- **Ankara Sigorta (independent)** — `https://www.ankarasigorta.com.tr/hakkimizda/insan-kaynaklari` — open — insurance, Ankara/İstanbul; technical/underwriting, data, BI; email: none found
- **Unico Sigorta (independent)** — `https://www.unicosigorta.com.tr/insan-kaynaklari` — open — insurance, İstanbul; Project Manager, finance analyst, underwriting, data; email: none found
- **Vakıf Yatırım Menkul Değerler (VakıfBank group)** — `https://www.vakifyatirim.com.tr/insan-kaynaklari` — open — brokerage & research, Levent/İstanbul; research analyst, business analyst, data; email: vkyisealim@vakifyatirim.com.tr
- **Vakıf Faktoring (VakıfBank group)** — `https://www.kariyer.net/firma-profil/vakif-faktoring-a-s-138827-62577` — open — factoring/financing, İstanbul; finance, risk, analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Financial-market & data infrastructure
- **Borsa İstanbul (BIST)** — `https://kariyer.borsaistanbul.com/#/home` — open — stock exchange, İstanbul; Data Analyst, BI, business analyst, quant, risk analyst, IT; email: none found
- **Takasbank (İstanbul Takas ve Saklama Bankası)** — `https://www.kariyer.net/firma-profil/istanbul-takas-ve-saklama-bankasi-a-s-13146-188029` — open — central clearing/CCP/settlement, İstanbul; risk analyst, IT, ops, data; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **MKK (Merkezi Kayıt Kuruluşu)** — `https://www.kariyer.net/firma-profil/merkezi-kayit-kurulusu-a-s-3038-211239` — open — central securities depository, İstanbul; software, data, analyst; email: kariyer@mkk.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **BKM (Bankalararası Kart Merkezi)** — `https://www.kariyer.net/firma-profil/bankalararasi-kart-merkezi-a-s-37959-121764` — open — card payments/interbank switching, Etiler/İstanbul; DevOps, system, product, data; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **KKB (Kredi Kayıt Bürosu / Findeks)** — `https://www.kkb.com.tr/insan-kaynaklari` — open — credit data & analytics/fintech, Ataşehir/İstanbul; Data Analyst, BI, risk/business analyst, data science; email: hr@kkb.com.tr
- **SBM (Sigorta Bilgi ve Gözetim Merkezi)** — `https://www.kariyer.net/firma-profil/sigorta-bilgi-ve-gozetim-merkezi-9377-34255` — open — insurance data center, Kadıköy/İstanbul; DB specialist, data/business analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Bilkent Holding group
- **Tepe İnşaat Sanayi (Bilkent Holding)** — `https://www.kariyer.net/firma-profil/tepe-insaat-sanayi-a-s-7324-233419` — open — construction, Ankara; project/finance/contracts analyst, civil eng, HSE; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tepe Servis ve Yönetim (Bilkent Holding)** — `https://www.tepeservis.com.tr/kariyer` — open — facility management, nationwide/Ankara; ops/process/HR/supply-chain analyst, PM; email: none found
- **Bilintur (Bilkent Holding)** — `https://www.kariyer.net/firma-profil/bilintur-bilkent-turizm-insaat-yatirim-ve-tic-a-s-7324-32202` — open — tourism/hospitality & catering (Bilkent Hotel), Ankara; HR, finance, sales analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Meteksan Sistem ve Bilgisayar Teknolojileri (Bilkent Holding)** — `https://www.kariyer.net/firma-profil/meteksan-bilisim-grubu-1123-1337` — open — IT/data systems, Ankara + İstanbul/İzmir; Data Analyst, BI, Business Analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tepe Emlak Yatırım (Bilkent Holding)** — `https://www.kariyer.net/firma-profil/tepe-emlak-yatirim-insaat-ve-ticaret-a-s-7324-233418` — open — real estate/shopping-center & asset mgmt, Ankara; leasing, finance, project analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Çolakoğlu / Ferko / Kıraça groups
- **Çolakoğlu Dış Ticaret (Çolakoğlu Grubu)** — `https://www.colakoglu.com.tr/kariyer/kariyer-olanaklari` — open — steel/metals foreign trade & export, Beykoz/İstanbul; foreign-trade, finance, supply-chain analyst; email: none found
- **Ferko İnşaat Turizm (Ferko Holding)** — `https://www.kariyer.net/firma-profil/ferko-insaat-turizm-san-ve-tic-a-s-52970-38553` — open — real estate/construction/tourism, İstanbul; budget & finance specialist, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Hexagon Studio (Kıraça Holding)** — `https://www.hexagonstudio.com.tr/en/career/career-opportunities/` — open — design & engineering (automotive/marine/rail/defense), Gebze/Kocaeli; R&D/design eng, PM, process; email: ik@hexagonstudio.com.tr
- **Karland Otomotiv (Kıraça Holding)** — `https://jobs.kiracakariyer.com/` — login-to-apply — automotive aftermarket/spare parts, Sancaktepe/İstanbul; sales/regional sales, supply-chain; email: none found

### Tarım Kredi group
- **Tarım Kredi Teknoloji (Tarım Kredi group)** — `https://www.tkteknoloji.com.tr/tr/kariyer` — open — IT/digital arm, Ankara; software, data, BI, analyst; email: none found

## 2. Banks, finance & fintech
- **İş Bankası** — `https://ik.isbank.com.tr/is-ilanlari-listesi` — login-to-apply, JS-rendered (supervised session). Data/BI/Data Science units.
- **Garanti BBVA** — public listing `https://kariyer.garantibbva.com.tr/public/Announcement.aspx` — login-to-apply (EN talent page 403s bots).
- **Garanti BBVA Teknoloji** — `https://www.garantibbvateknoloji.com.tr/bizde-kariyer` + Kariyer.net `firma-profil/garanti-bbva-teknoloji-1198-2162` — open — Data Eng/DS/BI/BA concentrate here.
- **Akbank** — `https://kariyer.akbank.com/jobsearchMaster` — login-to-apply, JS-rendered (supervised); detail `JobSearchDetail/Index?id=<guid>`.
- **Yapı Kredi** (Koç) — `https://www.kockariyerim.com/companies/yapi-kredi-is-ilanlari` — login-to-apply; tech via Yapı Kredi Teknoloji `ykteknoloji.com.tr/en/career`.
- **QNB** (ex-Finansbank) — `https://www.qnb.com.tr/insan-kaynaklari/ailemize-katilin/is-ilanlari-ve-basvuru` + `https://qnbkariyer.com/` — login-to-apply.
- **Ziraat Bankası** — `https://www.ziraatbank.com.tr/.../acik-pozisyonlar` — restricted (exam-based / Kariyer Kapısı `kariyerkapisi.cbiko.gov.tr`).
- **Ziraat Teknoloji** — `https://ziraatteknoloji.hrpeak.com/jobs` — HRPeak ATS, 403s bots (supervised) — Data Eng/BI/DS.
- **VakıfBank** — `https://www.vakifbank.com.tr/.../insan-kaynaklari/kariyer` — login-to-apply.
- **Halkbank** — `https://kariyer.halkbank.com.tr/` (apply `basvuru.halkbank.com.tr`) — login-to-apply, partly exam-based.
- **DenizBank** — `https://kariyer.denizbank.com/` (apply `basvuru.denizbank.com`, Humanist) — login-to-apply.
- **TEB** — `https://www.tebkariyer.com/tr` + Kariyer.net `firma-profil/teb-...-1126-1370` — login-to-apply.
- **ING Türkiye** — Workday `https://ing.wd3.myworkdayjobs.com/tr-TR/ICSGBLCOR` (CXS JSON `.../wday/cxs/ing/ICSGBLCOR/jobs`) + Kariyer.net `firma-profil/ing-bank-a-s-19589-10526` — open — confirmed live Data Analyst req.
- **Papara** — `https://jobs.lever.co/papara` (API `api.lever.co/v0/postings/papara?mode=json`) — open — fintech, ideal for scraping.
- **iyzico** — `https://jobs.lever.co/iyzico` (Lever API) — open — payments fintech.
- **Param / ParamTech** — `https://hr.param.com.tr/tr/pozisyonlar` → Zoho Recruit `param.zohorecruit.com/jobs/PARAM-Kariyer` — open.

## 2b. Banks, finance & fintech expansion — 2026-06-17 (batch JAC-33): 175 verified companies
NEW finance-sector companies (no overlap with section 2, the 1b finance subsidiaries, or the 3b fintech). Istanbul-first (Turkey's finance hub). State-owned banks recruit via exam / Kariyer Kapısı (marked `restricted`). Crypto entries carry regulatory flags where status is uncertain. Most domestic finance firms route through own ATS or Kariyer.net firma-profil (which 403s bots but is a real apply channel).

### Participation (Islamic) banks
- **Kuveyt Türk Katılım Bankası** — `https://www.katilbize.com/` — open — participation bank, İstanbul; PM, Data Analyst, BI, Business Analyst, credit/risk analyst, finance/quant; email: none found
- **Albaraka Türk Katılım Bankası** — `https://www.albaraka.com.tr/en/about-us/human-values/open-positions` (Kariyer.net `firma-profil/albaraka-turk-katilim-bankasi-a-s-2569-17235`) — login-to-apply — participation bank, İstanbul; Business Analyst, credit/risk analyst, finance/quant, HR analytics, auditor; email: none found
- **Türkiye Finans Katılım Bankası** — `https://kariyer.turkiyefinans.com.tr/` — login-to-apply — participation bank, İstanbul; PM, Data Analyst, BI, Business Analyst, credit/risk analyst, finance/quant; email: none found
- **Vakıf Katılım Bankası** — `https://vakifkatilim.bizdekariyer.com/` — restricted (state-owned) — participation bank, İstanbul; Business Analyst, credit/risk analyst, finance/quant, IT; email: none found
- **Ziraat Katılım Bankası** — `https://kariyer.ziraatkatilim.com.tr/jobs` — restricted (state-owned) — participation bank, İstanbul/Ankara; credit/risk analyst, finance/quant, Business Analyst, IT, ops; email: none found
- **Türkiye Emlak Katılım Bankası** — `https://www.emlakkatilim.com.tr/tr/insan-kaynaklari` — restricted (state-owned) — participation bank, İstanbul; MIS/BI, Data Analyst, Business Analyst, credit/risk analyst, fintech; email: none found
- **Hayat Finans Katılım Bankası** — `https://hayatfinans.com.tr/en/about-us/careers` — login-to-apply — digital participation bank (Hayat Holding), İstanbul; Data Analyst, BI, PM, Business Analyst, finance/quant, software; email: none found
- **Dünya Katılım Bankası** — `https://www.kariyer.net/firma-profil/dunya-katilim-bankasi-anonim-sirketi-364808-421514` — login-to-apply — participation bank (operating since Dec 2023), Ümraniye/İstanbul; Business Analyst, credit/risk analyst, finance/quant; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Development, investment & other commercial banks
- **İller Bankası (İlbank)** — `https://www.ilbank.gov.tr/sayfa/insan-kaynaklari-politikamiz` — restricted (state-owned, KPSS/exam) — development/infrastructure bank, Ankara; civil/infra eng, finance/credit analyst, IT/data, PM, Business Analyst; email: bilgiedinme@ilbank.gov.tr
- **Türk Eximbank** — `https://www.eximbank.gov.tr/tr/hakkimizda/insan-kaynaklari` (Kariyer.net `firma-profil/turkiye-ihracat-kredi-bankasi-a-s-41906-124310`) — restricted (state-owned, exam) — export-credit & trade finance, İstanbul/Ankara; credit/risk analyst, finance/quant, economist, BI/Data Analyst, Business Analyst, PM; email: info@eximbank.gov.tr
- **Türkiye Kalkınma ve Yatırım Bankası** — `https://kalkinma.com.tr/hakkimizda/insan-kaynaklari/is-ilanlari-ve-basvurular` — login-to-apply — development/investment bank, İstanbul/Ankara; investment banking, credit/risk analyst, treasury, BI, Business Analyst, PM; email: none found
- **GSD Yatırım Bankası (GSD Bank)** — `https://www.gsdbank.com.tr/insan-kaynaklari` — open (email apply) — investment/corporate bank (GSD Holding), Maltepe/İstanbul; corporate/commercial credit analyst, treasury, finance, Business Analyst; email: ik@gsdholding.com.tr
- **PASHA Yatırım Bankası (Pasha Bank Türkiye)** — `https://www.pashabank.com.tr/tr/insan-kaynaklari/` — login-to-apply — corporate & investment bank, Kağıthane/İstanbul; corporate banking, credit/risk analyst, treasury, BI/Data Analyst, Business Analyst; email: none found
- **Diler Yatırım Bankası** — `https://www.dilerbank.com.tr/TR/insan-kaynaklari/acik-pozisyonlar` — open — investment bank (Diler Holding), İstanbul; treasury, IT systems analyst, credit/risk analyst, finance; email: none found
- **Standard Chartered Türkiye** — `https://www.sc.com/tr-en/careers/` — login-to-apply — corporate/wholesale banking, İstanbul; credit/risk analyst, Business Analyst, finance/quant, PM; email: none found
- **Bank of China (Turkey)** — `https://www.kariyer.net/firma-profil/bank-of-china-turkey` — login-to-apply — corporate banking & trade finance, İstanbul; ops specialist, credit/risk analyst, Business Analyst; email: career@bankofchina.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Burgan Bank Türkiye** — `https://www.kariyer.net/firma-profil/burgan-bank-turkiye-17959-8735` — login-to-apply — corporate & private banking, İstanbul; branch ops, audit, portfolio manager, digital/BI, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Odeabank** — `https://www.odeabank.com.tr/en/about-odeabank/human-resources` (Kariyer.net `firma-profil/odea-bank-a-s-35622-28158`) — login-to-apply — retail/commercial bank, Şişli/İstanbul; portfolio manager, branch ops, MT program, data analyst; email: none found
- **ICBC Turkey Bank** — `https://www.icbc.com.tr/tr/kariyer/` (Kariyer.net `firma-profil/icbc-turkey-2000-10978`) — login-to-apply — corporate/commercial/SME bank, Maslak/İstanbul; digital-banking Business Analyst, fintech innovation, credit/risk analyst, BI/data analyst; email: none found
- **HSBC Türkiye** — `https://www.hsbc.com.tr/en/about-hsbc/human-resources/recruitment` — login-to-apply — wealth & corporate banking, İstanbul; ops, digital-banking specialist, Business Analyst, data analyst, credit/risk, PM; email: none found
- **Citibank Türkiye (Citi)** — `https://jobs.citi.com/location/istanbul-turkey-jobs/287/298795-745042/3` — login-to-apply — corporate/commercial banking, treasury, trade finance, İstanbul; corporate-banking analyst, credit/risk analyst, finance/quant, Business Analyst; email: none found
- **JPMorgan Türkiye** — `https://careers.jpmorganchase.com/pages/international/turkey` — login-to-apply — corporate & investment banking, payments, İstanbul; banking analyst, payments product, quant/finance, data analyst; email: none found
- **Deutsche Bank Türkiye** — `https://careers.db.com/professionals/search-roles/` — login-to-apply — corporate banking & capital markets, Şişli/İstanbul; markets/sales-trading analyst, finance/quant, risk analyst; email: none found
- **Şekerbank** — `https://kariyer.sekerbank.com.tr/` — login-to-apply — commercial bank (agri/SME focus), İstanbul; credit/risk analyst, Business Analyst, BI/data analyst, head-office finance; email: none found
- **Anadolubank** — `https://ikportal.anadolubank.com.tr/anadolubankta-kariyer/ise-alim-ve-basvuru` — login-to-apply — commercial bank (HABAŞ group), İstanbul; corporate/commercial banking, credit/risk analyst, treasury/quant, BI/data analyst, PM; email: none found
- **Alternatif Bank (ABank)** — `https://www.alternatifbank.com.tr/en/about-us/human-resources/kariyer-yonetimi` — login-to-apply — commercial/corporate bank (Commercial Bank of Qatar), İstanbul; MT program, corporate banking, credit/risk analyst, Business Analyst, treasury; email: none found
- **Turkland Bank (T-Bank)** — `https://www.tbank.com.tr/insan-kaynaklari/detay/Ilanlarimiz-Basvuru/31/18/0` — login-to-apply — niche commercial/corporate bank (acquired by Papara 2024, entity intact), İstanbul; corporate/commercial banking, credit/risk analyst, FI officer, Business Analyst; email: none found

### Payment & e-money institutions
- **Paycell (Turkcell Ödeme ve Elektronik Para)** — `https://www.kariyer.net/firma-profil/turkcell-ve-grup-sirketleri-2931-21215` — login-to-apply — e-money institution, İstanbul; PM, backend, data/BI, risk/compliance, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **TODEO (TT Ödeme Hizmetleri, Türk Telekom)** — `https://www.turktelekomkariyer.com.tr/` — open — payment institution, İstanbul/Ankara; finance, technology, product, risk/compliance; email: none found
- **ininal** — `https://www.kariyer.net/firma-profil/ininal-73428-146566` — login-to-apply — e-money institution, İstanbul; product, ops, BI/data, compliance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Moka United** — `https://www.kariyer.net/firma-profil/moka-united-odeme-hizmetleri-ve-elektronik-para-ku-86769-156759` — login-to-apply — e-money/payment institution (İş Bankası + United Payment; absorbed Birleşik Ödeme 2025), Esentepe/İstanbul; product, Data Analyst, Business Analyst, risk/compliance, finance, sales; email: info@mokaunited.com (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Paratika (Payten / ASEE-Asseco)** — `https://tr.asseco.com/hakkimizda/asseco-da-kariyer/` — open — payment institution, Maslak/İstanbul; product, Business Analyst, data/BI, finance, risk/compliance, sales; email: none found
- **Elekse** — `https://www.elekse.com/kariyer` — open — e-money/payment institution, Kağıthane/İstanbul; software, customer relations, sales portfolio; email: none found
- **Paymes (PayTabs group)** — `https://www.kariyer.net/firma-profil/paymes-172904-185519` — login-to-apply — payment institution / e-commerce fintech, İstanbul; customer ops, product, Business Analyst, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Edenred Türkiye** — `https://www.kariyer.net/firma-profil/edenred-kurumsal-cozumler-a-s-1696-7637` — login-to-apply — payment institution / prepaid meal-card (Ticket Restaurant), Sarıyer/İstanbul; PM, sales, BI/Data, finance, risk/compliance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Pluxee Türkiye (ex-Sodexo Avantaj)** — `https://www.kariyer.net/firma-profil/pluxee-turkiye-10163-38415` — login-to-apply — payment institution / employee-benefits cards, İstanbul; PM, Data, BI, finance, compliance, product; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Metropolcard (Metropol Ödeme)** — `https://www.kariyer.net/firma-profil/metropolcard-242075-277405` — login-to-apply — payment institution / prepaid cards, Üsküdar/İstanbul; Business Analyst, ops, finance, sales; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **PayCore (ex-Cardtek)** — `https://www.paycore.com/hakkimizda/kariyer` — open — payment-tech & switching software, Sarıyer (İTÜ Teknokent)/İstanbul; product, BI/Data, Business Analyst, risk/compliance, finance, engineering; email: none found
- **Vepara** — `https://www.vepara.com.tr` — open — e-money institution (licensed 2022), İstanbul; PM, product, Business Analyst, risk/compliance, finance; email: none found
- **Lidio (ex-Mobilexpress)** — `https://tr.linkedin.com/company/lidio` — open — payment institution / virtual POS, İstanbul; product, BI/Data, Business Analyst, finance, engineering; email: none found
- **Moneypay (Migros / Anadolu Group)** — `https://moneypay.com.tr/` — open — payment institution / e-money, İstanbul; PM, Data Analyst, BI, Business Analyst, product, risk/compliance, finance; email: none found

### Crypto exchanges
- **BTCTurk** — `https://www.kariyer.net/firma-profil/btcturk-159244-181853` — login-to-apply — crypto exchange (SPK/MASAK-registered, ~850+ staff), Akmerkez/İstanbul; PM, Data Analyst, BI, Business Analyst, product, risk/compliance, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bitexen** — `https://jobs.bitexen.com/` — open — crypto exchange, Sarıyer (İTÜ ARI Teknokent)/İstanbul; PM, Data Analyst, BI, Business Analyst, product, risk/compliance, finance; email: none found
- **SAFEbit (formerly Bitci)** — `https://www.kariyer.net/firma-profil/safebit-kripto-varlik-alim-satim-platformu-anonim-250361-287336` — open — crypto exchange (rebranded from Bitci in 2025), İstanbul; PM, Data Analyst, BI, Business Analyst, product, risk/compliance, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **ICRYPEX** — `https://www.kariyer.net/firma-profil/icrypex-kripto-varlik-alim-satim-platformu-a-s-182673-195662` — login-to-apply — crypto exchange, Maslak/İstanbul; PM, Data Analyst, BI, Business Analyst, risk/compliance, finance; email: none found (FLAG: reported MASAK investigation / asset freeze in 2025 — operating status uncertain) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bitay** — `https://www.kariyer.net/firma-profil/bitay-200322-227112` — login-to-apply — crypto exchange / blockchain tech, Şişli (YTÜ Teknopark)/İstanbul; PM, Data Analyst, BI, Business Analyst, blockchain dev, risk/compliance; email: none found (FLAG: SPK/MASAK registration not confirmed) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Binance TR** — `https://www.binance.com/tr/careers` — open — crypto exchange (local entity, reduced TR footprint after 2024–25 regulation), İstanbul; PM, Data Analyst, BI, Business Analyst, product, risk/compliance, finance; email: none found

### Brokerages
- **Garanti BBVA Yatırım Menkul Kıymetler** — `https://kariyer.garantibbva.com.tr/garantibbva-kuruluslari/garanti-bbva-yatirim` — open — brokerage/investment banking, Zincirlikuyu/İstanbul; research/finance analyst, M&A/corporate finance, capital markets, trader, BI/Data Analyst; email: none found
- **QNB Finansinvest (QNB Invest)** — `https://www.qnbinvest.com.tr/insan-kaynaklari` — open — brokerage/investment, İstanbul; research analyst, corporate finance, investment advisory, trader; email: insankaynaklari@qnbinvest.com.tr
- **Ünlü & Co (Ünlü Menkul Değerler)** — `https://unluco.hrpanda.co/` — login-to-apply — brokerage/corporate finance/asset mgmt, İstanbul; MT program, research/finance analyst, M&A, investment advisory, PM; email: none found
- **Gedik Yatırım Menkul Değerler** — `https://www.kariyer.net/firma-profil/gedik-yatirim-menkul-degerler-a-s-77180-46090` — open — brokerage, Kadıköy/İstanbul; research analyst, finance, trader, BI/Data Analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Şeker Yatırım Menkul Değerler** — `https://www.sekeryatirim.com.tr/Kurumsal/InsanKaynaklari` — open — brokerage (Şekerbank group), İstanbul; research analyst, finance, trader; email: none found
- **Tacirler Yatırım Menkul Değerler** — `https://tacirler.com.tr/insan-kaynaklari` — open (email apply) — brokerage, Etiler/Akmerkez/İstanbul; research/finance analyst, software, investment consultant, trader; email: insan_kaynaklari@tacirler.com.tr
- **Info Yatırım Menkul Değerler** — `https://infoyatirim.com/hakkimizda/insan-kaynaklari` — open — brokerage (Hedef Group), İstanbul; research analyst, fund ops, finance, BI; email: none found
- **Marbaş Menkul Değerler** — `https://marbas.com.tr/kurumsal/kariyer/` — open (email apply) — brokerage, Beylikdüzü/İstanbul; customer rep, finance, trader, analyst; email: ik@marbasmenkul.com.tr
- **A1 Capital Yatırım Menkul Değerler** — `https://www.kariyer.net/firma-profil/a1-capital-yatirim-menkul-degerler-as-52937-171869` — open — brokerage/portfolio mgmt, Maslak/İstanbul + regional; investment specialist, research/finance analyst, trader; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **PhillipCapital Menkul Değerler (Türkiye)** — `https://www.phillipcapital.com.tr/bize-katilin` — open (form) — brokerage/portfolio mgmt, İstanbul + regional; research analyst, finance, trader; email: none found
- **Integral Yatırım Menkul Değerler** — `https://www.kariyer.net/firma-profil/integral-yatirim-menkul-degerler-a-s-1712-67356` — open — brokerage (Ulukartal Holding), Maslak/İstanbul; research analyst, accounting, fund ops, BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Ahlatcı Yatırım Menkul Değerler** — `https://www.ahlatciyatirim.com.tr/hakkimizda/insan-kaynaklari` — open (email apply) — brokerage/portfolio mgmt, Maslak/İstanbul + Çorum; investment advisory, research analyst, trader; email: ik@ahlatciyatirim.com.tr
- **Ziraat Yatırım Menkul Değerler** — `https://www.kariyer.net/firma-profil/ziraat-yatirim-menkul-degerler-a-s-17236-7941` — open — brokerage (Ziraat group), İstanbul + branches; research/finance analyst, trader, fund/asset mgmt, BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Halk Yatırım Menkul Değerler** — `https://www.halkyatirim.com.tr/insan-kaynaklari` — open — brokerage (Halkbank group), İstanbul + branches; research/finance analyst, trader, BI; email: none found
- **Deniz Yatırım Menkul Kıymetler** — `https://kariyer.denizbank.com/` — open — brokerage (DenizBank group), İstanbul; research/finance analyst, auditor, trader, intern programs; email: none found
- **TEB Yatırım** — `https://www.tebyatirim.com.tr/hakkimizda/insan-kaynaklari` — open — brokerage (TEB/BNP Paribas group), İstanbul; research/finance analyst, trader, BI; email: none found
- **Burgan Yatırım Menkul Değerler** — `https://www.burganyatirim.com.tr/hakkimizda/burgan-yatirimda-kariyer` — open — brokerage/corporate finance/asset mgmt (Burgan Group), İstanbul; research/finance analyst, M&A, trader; email: none found
- **Strateji Menkul Değerler** — `https://www.kariyer.net/firma-profil/strateji-menkul-degerler-a-s-14004-4387` — open — brokerage, İstanbul; research analyst, IT, ops, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Meksa Yatırım Menkul Değerler** — `https://www.kariyer.net/firma-profil/meksa-yatirim-menkul-degerler-a-s-91848-160773` — open (email apply) — brokerage (+ Meksa Portföy), İstanbul + branches; research/finance analyst, trader; email: ik@meksa.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Osmanlı Yatırım Menkul Değerler** — `https://www.osmanlimenkul.com.tr/finansal-planlama/neden-osmanli-yatirim/insan-kaynaklari` — open — brokerage, Maslak/İstanbul; research/finance analyst, trader, investment specialist; email: none found
- **Galata Menkul Değerler** — `https://www.kariyer.net/firma-profil/galata-menkul-degerler-a-s-25712-17260` — open — brokerage, İstanbul; finance analyst, trader, ops; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Anadolu Yatırım Menkul Kıymetler** — `https://anadoluyatirim.com.tr/insan-kaynaklari` — open — brokerage (Anadolubank group), İstanbul; research/finance analyst, trader, BI; email: none found
- **ICBC Turkey Yatırım Menkul Değerler** — `https://www.icbcyatirim.com.tr/tr/hakkimizda/detay/Insan-Kaynaklari/9/8/0` — open — brokerage/investment banking (ICBC group), İstanbul + branches; research/finance analyst, M&A, trader; email: none found
- **Alnus Yatırım Menkul Değerler** — `https://www.alnusyatirim.com/kariyer` — open (email apply) — brokerage, İstanbul; research/finance analyst, trader; email: ik@alnusyatirim.com
- **Trive Yatırım Menkul Değerler (ex-GCM Yatırım)** — `https://www.kariyer.net/firma-profil/trive-yatirim-menkul-degerler-anonim-sirketi-46471-37971` — open — brokerage (forex/CFD + equities), Maslak/İstanbul; research analyst, trader, BI/Data Analyst, fintech; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **ALB Yatırım Menkul Değerler (rebranding to Pusula Yatırım)** — `https://www.kariyer.net/firma-profil/alb-yatirim-menkul-degerler-anonim-sirketi-36836-35804` — open — brokerage, Fulya/İstanbul; research/finance analyst, trader; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Dinamik Yatırım Menkul Değerler** — `https://www.kariyer.net/firma-profil/dinamik-menkul-degerler-anonim-sirketi-26787-18442` — open — brokerage, Akmerkez/İstanbul; finance analyst, trader, ops; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bizim Menkul Değerler (BMD)** — `https://www.bmd.com.tr/hakkimizda/insan-kaynaklari` — open — brokerage (participation-finance focus), Kadıköy/İstanbul; research/finance analyst, HR, trader; email: none found

### Portfolio & asset management
- **Garanti BBVA Portföy Yönetimi** — `https://kariyer.garantibbva.com.tr/garantibbva-kuruluslari/garanti-bbva-portfoy` — open — portfolio mgmt (Türkiye's first PM company), Beşiktaş/İstanbul; PM, quant, research/finance analyst, fund ops; email: none found
- **QNB Portföy Yönetimi** — `https://www.qnbinvest.com.tr/insan-kaynaklari` — open — portfolio mgmt (QNB group), İstanbul; PM, quant, research analyst, fund ops; email: insankaynaklari@qnbinvest.com.tr
- **Ünlü Portföy** — `https://unluco.hrpanda.co/` — login-to-apply — portfolio mgmt, İstanbul; PM, quant, research/finance analyst, risk; email: none found
- **Ziraat Portföy Yönetimi** — `https://www.ziraatportfoy.com.tr/` — restricted — portfolio mgmt (Ziraat group), İstanbul; PM, research/finance analyst, fund ops; email: none found

### Factoring
- **Garanti BBVA Faktoring** — `https://www.garantibbvafactoring.com/tr/ik/bize-katilin/is-olanaklari` — login-to-apply — factoring, İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found
- **QNB Faktoring** — `https://www.qnbfaktoring.com.tr/bizi-taniyin/insan-kaynaklari/insan-kaynaklari-anlayisimiz` — login-to-apply — factoring, İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found
- **Deniz Faktoring** — `https://www.denizfactoring.com.tr/insan-kaynaklari` — login-to-apply — factoring (DenizBank group), Şişli/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found
- **TEB Faktoring** — `https://www.tebfaktoring.com.tr/hakkimizda/insan-kaynaklari` — login-to-apply — factoring (TEB/BNP Paribas), İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found
- **Şeker Faktoring** — `https://www.sekerfactoring.com/home/IcerikSayfalari/insan-kaynaklari` — open (email apply) — factoring, Şişli/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, collections; email: sekerfact@sekerfactoring.com
- **Halk Faktoring** — `https://www.halkfaktoring.com.tr/tr/kurumsal/insan-kaynaklari/ise-alim-sureci.html` — open — factoring (Halkbank group), Maslak/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, collections; email: info@halkfaktoring.com.tr
- **Lider Faktoring** — `https://www.kariyer.net/firma-profil/lider-faktoring-a-s-8976-33854` — login-to-apply — factoring (BIST-listed), Şişli/İstanbul (21 branches); credit/risk analyst, finance, collections, Business Analyst/Data, BI, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Çağdaş Faktoring** — `https://www.kariyer.net/firma-profil/cagdas-faktoring-a-s-11782-227075` — login-to-apply — factoring, Şişli/İstanbul + Ankara/İzmir/Bursa/Gaziantep/Konya; credit/risk analyst, finance, collections, Business Analyst/Data, BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Destek Finans Faktoring** — `https://destekfaktoring.com.tr/en/human-resource` — restricted — factoring (BIST: DSTKF), Şişli/İstanbul; credit/risk analyst, finance, collections, Business Analyst/Data, BI; email: none found
- **Ekspo Faktoring** — `https://www.ekspofaktoring.com/tr/insan-kaynaklari/detay/insan-kaynaklari/7/71/0` — open (form) — factoring, Maslak/İstanbul; credit/risk analyst, finance, Business Analyst, collections; email: none found
- **Kapital Faktoring** — `https://www.kapitalfaktoring.com.tr/InsanKaynaklari` — open — factoring, Maslak/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, collections; email: ik@kapitalfaktoring.com.tr
- **Tam Faktoring (Tam Finans)** — `https://www.tamfinans.com.tr/is-ilanlari/` — open / login-to-apply — factoring, Şişli/İstanbul (49 branches); credit/risk analyst, finance, Business Analyst, Data Analyst, BI, collections, branch staff; email: none found
- **Optima Faktoring** — `https://www.kariyer.net/firma-profil/optima-faktoring-a-s-14842-314699` — login-to-apply — factoring, Maslak/İstanbul; credit/risk analyst, finance, Business Analyst, collections; email: info@optimafaktoring.com (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Sümer Faktoring** — `https://sumerfaktoring.com/insan-kaynaklari/` — open (email apply) — factoring, Şişli/İstanbul; credit/risk analyst, finance, Business Analyst, collections; email: ik@sumerfaktoring.com.tr
- **Eko Faktoring** — `https://www.kariyer.net/firma-profil/eko-faktoring-a-s-9478-34356` — login-to-apply — factoring, Maslak/İstanbul + Ankara/Bursa/İzmir/Konya; credit/risk analyst, finance, Business Analyst, collections; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Atılım Faktoring** — `http://www.atilimfaktoring.com.tr/tr/kurumsal/insan-kaynaklari` — open (form) — factoring, İstanbul; credit/risk analyst, finance, branch ops, collections; email: none found
- **Acar Faktoring** — `https://www.acarfactoring.com.tr/insan-kaynaklari` — open — factoring, Şişli/İstanbul + Ankara; credit/risk analyst, finance, ops, collections; email: none found
- **Mert Finans Faktoring** — `https://www.mertfinans.com/kurumsal/kariyer.html` — open (email apply) — factoring, Bağcılar/İstanbul; ops, credit/risk, finance, collections; email: kariyer@mertfinans.com.tr
- **Ulusal Faktoring** — `https://www.ulusalfaktoring.com/insan-kaynaklari/` — open (form) — factoring, Maslak/İstanbul (48 branches); credit/risk analyst, finance, accounting, ops, collections; email: none found

### Leasing (finansal kiralama)
- **Garanti BBVA Finansal Kiralama (Garanti Leasing)** — `https://www.garantibbvaleasing.com.tr/insan-kaynaklari` — open — leasing, İstanbul + 13 branches; credit/risk analyst, finance, Business Analyst, Data/BI Analyst, PM, collections; email: none found
- **QNB Finans Finansal Kiralama (QNB Leasing)** — `https://www.qnbleasing.com.tr/kurumsal/insan-kaynaklari/ik-politikamiz/` — open — leasing, İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found
- **Deniz Finansal Kiralama (DenizLeasing)** — `https://www.denizleasing.com/denizleasing-kariyer` — login-to-apply — leasing/fleet (DenizBank group), İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found
- **Halk Finansal Kiralama (Halk Leasing)** — `https://www.halkleasing.com.tr/tr/hakkimizda/insan-kaynaklari.html` — open (email apply) — leasing (Halkbank group), Mecidiyeköy/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, collections; email: ik@halkleasing.com.tr
- **Şeker Finansal Kiralama (Şeker Leasing)** — `https://www.sekerleasing.com.tr/hakkimizda/insan-kaynaklari` — open (form) — leasing, İstanbul + Ankara/İzmir/Gaziantep; credit/risk analyst, finance, Business Analyst, Data Analyst, collections; email: none found
- **Ziraat Finansal Kiralama (Ziraat Leasing)** — `https://www.kariyer.net/firma-profil/ziraat-finansal-kiralama-a-s-18695-9543` — login-to-apply — leasing (Ziraat group), İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, collections; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **BNP Paribas Finansal Kiralama (TEB Leasing)** — `https://leasingsolutions.bnpparibas.com.tr/en/careers/` — open — leasing (TEB/BNP Paribas), İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found
- **Burgan Leasing (Burgan Finansal Kiralama)** — `https://www.burganleasing.com.tr/` — open — leasing (Burgan Group), Maslak/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, collections; email: info@burganleasing.com.tr
- **ALJ Finans (Abdul Latif Jameel)** — `https://www.aljfinans.com.tr/hakkimizda/insan-kaynaklari` — open — auto/vehicle finance, İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: happypeople@aljfinans.com
- **Mercedes-Benz Finansman Türk** — `https://careers.mercedesbenzturk.com.tr/` — open — vehicle finance + leasing, İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found
- **Koç Fiat Kredi Finansman (Fiat Finans)** — `https://www.kocfiatkredi.com.tr/` — restricted — auto consumer finance, Şişli/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, collections; email: info@kocfiatkredi.com.tr
- **ORFİN Finansman** — `https://www.orfin.com.tr/kariyer/` — open — auto/vehicle finance (Renault/Dacia, OYAK + Renault JV), İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, PM, collections; email: none found

### Consumer finance & financing
- **TEB Finansman (TEB Cetelem)** — `https://www.tebkariyer.com/tr` — open / login-to-apply — consumer finance (auto/POS), Ümraniye/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, collections, PM; email: insankaynaklari@tebcetelem.com.tr
- **Doruk Finansman (ex-DD Mortgage)** — `https://www.kariyer.net/firma-profil/doruk-finansman-a-s-30558-214400` — login-to-apply — consumer/housing finance (Deutsche Bank + Doğan JV), Beşiktaş/İstanbul; credit/risk analyst, internal audit, finance, Business Analyst, collections, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Hemenal Finansman (QNB Finansbank consumer-finance arm)** — `https://hemenalfinans.com.tr` — open / login-to-apply — consumer finance (POS retail financing), 4. Levent/İstanbul; credit/risk analyst, finance, Business Analyst, Data Analyst, BI, collections, PM; email: none found

### Asset & debt management (varlık yönetim)
- **Hayat Varlık Yönetim (Turkasset)** — `https://www.kariyer.net/firma-profil/hayat-varlik-yonetim-a-s` — login-to-apply — debt/NPL asset mgmt (~500+ staff, 7 cities), İstanbul; collections, credit/risk analyst, customer rep, finance, BI/Data Analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Birikim Varlık Yönetim** — `https://www.birikimvarlik.com.tr/` — open / login-to-apply — debt/NPL asset mgmt (Altınhas Holding), İstanbul; collections, lawyer, credit/risk, finance, Business Analyst/Data; email: insankaynaklari@birikimvarlik.com.tr
- **Doğru Varlık Yönetim** — `https://www.dogruvarlik.com/` — open / login-to-apply — debt/NPL asset mgmt, İstanbul; collections, credit/risk analyst, finance, Business Analyst/Data; email: info@dogruvarlik.com
- **Güven Varlık Yönetim** — `https://www.kariyer.net/firma-profil/guven-varlik-yonetim-a-s-21905-230379` — login-to-apply — debt/NPL asset mgmt (Fiba Holding), İstanbul; collections, credit/risk analyst, finance, Business Analyst/Data; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **İstanbul Varlık Yönetim** — `https://www.istanbulvarlik.com/kariyer/` — open — debt/NPL asset mgmt, Maslak/İstanbul; collections, credit/risk, finance, Business Analyst/Data/BI, PM; email: insan.kultur@istanbulvarlik.com
- **Mega Varlık Yönetim** — `https://www.megavarlik.com.tr/` — open / login-to-apply — debt/NPL asset mgmt, Üsküdar/İstanbul; collections, credit/risk, finance, Business Analyst/Data; email: basvuru-ozgecmis@megavarlik.com.tr
- **Sümer Varlık Yönetim** — `https://www.sumervarlik.com.tr/acik-pozisyonlarimiz` — open — debt/NPL asset mgmt, İstanbul; collections, credit/risk, finance, Business Analyst/Data, new-grad program; email: kariyer@sumervarlik.com.tr
- **Denge Varlık Yönetim** — `https://dengevarlik.com.tr/ik.html` — open — debt/NPL asset mgmt, İstanbul; collections, risk management, finance, Business Analyst/Data; email: info@dengevarlik.com.tr
- **Boğaziçi Varlık Yönetim** — `https://bogazicivarlik.com.tr/` — open — debt/NPL asset mgmt, İstanbul; collections, credit/risk, finance, Business Analyst/Data; email: info@bogazicivarlik.com.tr
- **Efes Varlık Yönetim** — `https://www.efesvarlik.com.tr/` — open / login-to-apply — debt/NPL asset mgmt (İş Bankası subsidiary), Ataşehir/İstanbul; collections, finance/reporting, credit/risk, IT support, Business Analyst/Data; email: none found
- **Arsan Varlık Yönetim** — `https://www.arsanvarlik.com.tr/` — open / login-to-apply — debt/NPL asset mgmt, İstanbul; collections, finance/admin, credit/risk, Business Analyst/Data; email: none found

### Insurers & pension
- **AXA Türkiye (AXA Sigorta + AXA Hayat ve Emeklilik)** — `https://www.axasigorta.com.tr/axa-da-kariyer` (Peoplise `https://live.peoplise.com/axasigorta/career`) — open — non-life + life & pension, İstanbul; actuarial, underwriting analyst, Data Analyst, BI, Business Analyst, PM, risk, finance; email: none found
- **Katılım Emeklilik ve Hayat** — `https://www.kariyer.net/firma-profil/katilim-emeklilik-ve-hayat-a-s-51948-38434` — open — life & pension, participation/takaful (Kuveyt Türk + Albaraka JV), İstanbul; actuarial, BES ops, finance, BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Türkiye Katılım Sigorta** — `https://www.kariyer.net/firma-profil/turkiye-katilim-sigorta-306706-352858` — open — non-life participation insurance (Türkiye Wealth Fund), Ümraniye/İstanbul; underwriting analyst, actuarial, risk, finance, Data Analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bereket Sigorta + Bereket Emeklilik ve Hayat** — `https://www.kariyer.net/firma-profil/bereket-emeklilik-17823-73876` — open — non-life + life & pension, participation (Tarım Kredi group), İstanbul; actuarial, underwriting analyst, agri-insurance, finance, BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bupa Acıbadem Sigorta** — `https://www.bupaacibadem.com.tr/acibademsigortadakariyer` — open — health insurance specialist, Ataşehir/İstanbul; health claims/underwriting analyst, actuarial, Data Analyst, BI, PM; email: none found
- **QNB Sigorta (ex-Cigna Finans Emeklilik ve Hayat)** — `https://www.qnbsigorta.com.tr/` (Kariyer.net `firma-profil/cigna-saglik-hayat-ve-emeklilik-a-s-29940-270517`) — open — life & pension + health (QNB subsidiary), İstanbul; actuarial, BES ops, Data Analyst, BI, Business Analyst, finance; email: none found
- **BNP Paribas Cardif Türkiye (Cardif Hayat + Cardif Emeklilik)** — `https://www.kariyer.net/firma-profil/bnp-paribas-cardif-16231-6836` — open — life & credit-protection insurance + pension, İstanbul; actuarial, risk, Business Analyst, Data Analyst, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **MetLife Emeklilik ve Hayat (Türkiye)** — `https://www.metlife.com.tr/hakkimizda/kariyer/` — open — life & pension, İstanbul; actuarial, fund ops, Data Analyst, BI, finance, CRM; email: none found
- **NN Hayat ve Emeklilik (Türkiye)** — `https://www.nnhayatemeklilik.com.tr/hakkimizda/insan-kaynaklari/ise-alim` — open — life & pension (transitioning into Zurich group), İstanbul; actuarial, BES ops, Data Analyst, finance; email: none found
- **Garanti BBVA Emeklilik ve Hayat** — `https://www.garantibbvaemeklilik.com.tr/is-firsatlari-ve-basvurular` — open — life & pension (bancassurance), İstanbul; actuarial, BES ops, Data Analyst, BI, Business Analyst, finance, risk; email: none found
- **Ziraat Sigorta + Ziraat Hayat ve Emeklilik** — `https://www.kariyer.net/firma-profil/ziraat-hayat-ve-emeklilik-34647-225749` — open — non-life + life & pension (Ziraat group), İstanbul; actuarial, underwriting analyst, BES ops, Data Analyst, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Vakıf Emeklilik ve Hayat** — `https://www.kariyer.net/firma-profil/vakif-emeklilik-a-s-18465-9291` — open — life & pension (VakıfBank subsidiary), İstanbul; actuarial, BES ops, Data Analyst, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Demir Sağlık ve Hayat Sigorta** — `https://www.demirsaglik.com.tr/hakkimizda/kariyer` — open — health & life insurance, Şişli/İstanbul; health claims, underwriting analyst, actuarial, finance; email: none found
- **Magdeburger Sigorta** — `https://www.magdeburger.com.tr/magdeburgerde-kariyer` — open — non-life insurance, İstanbul; actuarial, health/claims analyst, underwriting analyst, finance; email: none found
- **Orient Sigorta** — `https://www.orientsigorta.com.tr/insan-kaynaklari-politikasi` — open — non-life insurance, İstanbul; risk engineer, underwriting analyst, claims, finance; email: none found
- **Ethica Sigorta** — `https://www.kariyer.net/firma-profil/ethica-sigorta-anonim-sirketi-182758-196073` — open — non-life insurance, Ataşehir/İstanbul; underwriting analyst, technical/claims, Data Analyst, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Türk P&I Sigorta** — `https://www.turkpandi.com/tr/hr` — open — marine P&I insurance, Ümraniye/İstanbul; marine underwriting analyst, claims, risk, finance; email: none found
- **Corpus Sigorta** — `https://corpussigorta.com.tr/tr/kurumsal/insan-kaynaklari` — open — non-life insurance, İstanbul; underwriting analyst, claims, finance, BI; email: none found
- **Şeker Sigorta** — `https://www.kariyer.net/firma-profil/seker-sigorta-a-s-4739-207447` — open — non-life insurance, Levent-Şişli/İstanbul; accounting/finance, claims, legal/recourse, underwriting analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **GIG Sigorta (ex-Gulf Sigorta)** — `https://www.gig.com.tr/kariyer` — open — non-life insurance (Gulf Insurance Group), İstanbul + Ankara; underwriting analyst, actuarial, claims, finance, Data Analyst; email: gighr@gig.com.tr

### Reinsurance & credit insurance
- **Türk Reasürans** — `https://turkreasurans.com.tr/tr/kariyer/acik-pozisyonlar/tum-ilanlar/genel-basvuru/` — open — reinsurance (state reinsurer), Çekmeköy/İstanbul + Ankara; actuarial, treaty/fac underwriting analyst, risk/MASAK, fund ops, finance; email: none found
- **Türk Katılım Reasürans** — `https://www.turkkatilimreasurans.com.tr/` — open — reinsurance, participation/retakaful, Çekmeköy/İstanbul + Ankara; actuarial, underwriting analyst, risk, finance; email: none found
- **Coface Türkiye (Coface Sigorta)** — `https://www.coface.com.tr/hakkimizda/kariyer` — open — credit insurance, İstanbul; credit/risk analyst, underwriting analyst, economist, Data Analyst, finance; email: none found
- **Atradius Türkiye** — `https://www.kariyer.net/firma-profil/atradius-credit-insurance-n-v-turkiye-13339-3655` — open — credit & surety insurance, İstanbul; credit/risk analyst, underwriting analyst, collections, finance; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Allianz Trade Türkiye (ex-Euler Hermes)** — `https://www.eulerhermes.com/tr_TR/about-us/kariyer.html` — open — credit insurance & surety, Şişli/İstanbul; credit/risk analyst, underwriting analyst, economist, Data Analyst, finance; email: none found

### Insurtech & insurance software
- **SFS (Sigorta Bilgi Sistemleri)** — `https://sfs.com.tr/sfs-kariyer/` — open — insurtech / insurance software & analytics, Sarıyer (İTÜ ARI Teknokent)/İstanbul; software, Data Analyst, BI, Business Analyst, PM, QA; email: none found

### Banking-tech & financial-software vendors
- **Fineksus** — `https://fineksus.talentics.app/` (Talentics ATS) — open — payments/SWIFT/ISO 20022/AML-regtech vendor, İstanbul (İTÜ Ayazağa Teknokent); software, QA, AI/ML, solution advisor, PM; email: none found
- **Cybersoft (C/S Enformasyon)** — `https://cs.com.tr/kariyer.html` — open — core-banking vendor (Lidya / V@Wfinans), Ankara (Bilkent Cyberpark) HQ + İstanbul; Java/.NET software, AI/ML, Business Analyst; email: none found
- **Architecht** — `https://architecht.com/en/corporate/career/` — open — banking-tech vendor (Kuveyt Türk subsidiary, BOA core platform), Pendik Teknopark/İstanbul; software architect, DevOps, data/analytics, product; email: none found
- **Provus (Mastercard Payment Transaction Services Turkey)** — `https://www.kariyer.net/firma-profil/mpts-2121-12309` — open — card issuing/acquiring processing vendor (Mastercard-owned), Ayazağa/İstanbul; software, payments ops, Business Analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Logo Yazılım** — `https://live.peoplise.com/logo/career` (Peoplise ATS) — open — ERP/SaaS + e-invoicing/fintech vendor, Gebze/Kozyatağı/İstanbul + Ankara/İzmir; software, product, BI/data, PM; email: none found
- **Paraşüt** — `https://parasut.recruitee.com/` (Recruitee `parasut`) — open — SME accounting / e-invoicing / collections fintech-SaaS (DST Technology), İstanbul; software, product, data, sales; email: none found
- **Kuika** — `https://www.kuika.com` — open (email apply) — AI low-code platform (fintech app build), R&D İstanbul; software, product, low-code engineering; email: jobs@kuika.com
- **OBSS** — `https://obss.tech/en/career-development/` — open — banking-tech IT-services vendor (~600 staff), İstanbul; software, Business Analyst (banking/finance), DevOps, QA, PM; email: none found
- **Obase** — `https://obase.com/obase/kariyer/?lang=tr` — open — BI / data-warehouse / analytics vendor (BIST: OBASE), İstanbul; BI, Data Analyst, ERP consultant, software; email: ik@obase.com
- **KOBIL** — `https://www.kobil.com/career/` — open — mobile security / digital identity / SuperApp for mobile banking, İstanbul presence (HQ Germany); mobile/C++ software, security engineering, product; email: none found
- **Bileşim (Bileşim Finansal Teknolojiler ve Ödeme Sistemleri)** — `https://www.kariyer.net/firma-profil/bilesim-alternatif-dagitim-kanallari-37949-121755` — open — ATM mgmt / merchant acquiring / card personalization (Ziraat/Halk/Vakıf-owned), Bahçekapı/İstanbul; software, payments ops, financial reporting, Business Analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **VakıfBank Bilgi Teknolojileri (IT arm)** — `https://kariyer.vakifbank.com.tr` — login-to-apply — in-house bank IT, İstanbul; Java/.NET dev, DBA, sysadmin, network, software test; email: btkariyer@vakifbank.com.tr
- **AlbarakaTech Global** — `https://www.kariyer.net/firma-profil/albaraka-teknoloji-bilisim-sistemleri-ve-pazarlama-295850-340359` — open — banking-tech vendor (Albaraka Türk IT subsidiary), İstanbul; software, data, product, new-grad program; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Worldline Türkiye (ex-Ingenico Türkiye)** — `https://www.kariyer.net/firma-profil/worldline-odeme-sistem-cozumleri-a-s-17581-8321` — open — POS/EFT terminals & payments vendor, İstanbul; software, payments engineering, support, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **SAS Türkiye** — `https://www.sas.com/tr_tr/careers.html` — open — analytics/AI/risk & fraud software for banks, Şişli/İstanbul & Ankara; analytics consultant, data scientist, presales; email: sastr@sas.com
- **FICO Türkiye** — `https://www.fico.com/en/careers` (Workday `https://fico.wd1.myworkdayjobs.com/External`) — open — credit scoring / decisioning / fraud analytics, İstanbul; analytics, data science, credit-risk consulting, presales; email: none found
- **Experian Türkiye** — `https://jobs.experian.com/` — open — credit-bureau-tech (risk, decisioning, analytics), İstanbul; data scientist, analytics consultant (IFRS9/Basel/collections), risk; email: none found

### Lending, neobank, wealthtech & crowdfunding
- **Midas (Midas Menkul Değerler)** — `https://jobs.lever.co/getmidas` (also Recruitee `midas`) — open — wealthtech / investing app (SPK-licensed; BIST/US/crypto), İstanbul; software, product, data, risk/compliance, settlement ops; email: none found
- **InvestAZ (InvestAZ Yatırım Menkul Değerler)** — `https://kariyer.investaz.com.tr/` — open — wealthtech / brokerage (forex/CFD/futures/shares), İstanbul; investment specialist, software, dealer, wealth management; email: none found
- **Piapiri** — `https://www.linkedin.com/showcase/piapiri/` — restricted — wealthtech / investing app (ÜNLÜ & Co spin-off), İstanbul; software, product, data, research; email: none found
- **Morpara** — `https://www.linkedin.com/company/morpara` — restricted — neobank / e-money (CBRT-licensed), İstanbul; software, product, payments ops, compliance; email: none found
- **Pratik İşlem (piepara)** — `https://piepara.com/` (Kariyer.net `firma-profil/pratik-islem-odeme-ve-elektronik-para-a-s-123231-116172`) — open — e-money / payments fintech (TCMB-licensed; virtual POS/wallet), Ümraniye/İstanbul; software, payments ops, sales; email: none found
- **Fongogo** — `https://www.fongogo.com/Hr` — open — reward-based crowdfunding (+ equity arm Fongogo Ventures), İstanbul; community rep, marketing, content, software; email: info@fongogo.com
- **Fonbulucu (Global Kitle Fonlama Platformu)** — `https://invest.fonbulucu.com/` — restricted — SPK-licensed equity crowdfunding, İstanbul; software, analyst, investor relations, marketing; email: none found
- **Birevim (Birevim Tasarruf Finansman)** — `https://www.kariyer.net/firma-profil/birevim-tasarruf-finansman` — open — tasarruf finansman (interest-free home/auto financing, BDDK-licensed), İstanbul + nationwide; savings-finance specialist, portfolio sales, software, Business Analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Katılımevim (Katılımevim Tasarruf Finansman)** — `https://www.kariyer.net/firma-profil/katilimevim-tasarruf-finansman-a-s-209792-240850` — open — tasarruf finansman (BDDK-licensed; 77 branches), Ümraniye/İstanbul + nationwide; software, Business Analyst, sales, HR; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Eminevim (Emin Evim Tasarruf Finansman)** — `https://www.eminevim.com/insan-kaynaklari` — open — tasarruf finansman (sector leader, BDDK-licensed; 140+ branches), İstanbul + nationwide; sales rep, software, business/process, HR; email: none found

## 3. Tech unicorns, gaming & software scaleups
- **Trendyol** — `https://jobs.lever.co/trendyol` (API `api.lever.co/v0/postings/trendyol?mode=json`; HTML 403s bots) — open — Data Analyst/BI/Analytics Eng/Product.
- **Getir** — `https://getir.careers-page.com/` — open — confirmed Senior Data Analyst Istanbul (SQL, Redshift/Athena, Tableau/Power BI/Looker).
- **Hepsiburada** — `https://kurumsal.hepsiburada.com/en/careers` + Kariyer.net + LinkedIn (company 150890) — open browse (corporate page 403s bots) — Data Analyst/Sr DA/Sr DS Istanbul confirmed.
- **Insider (Insider One)** — `https://jobs.lever.co/insiderone` (API `.../postings/insiderone`) — open — BI/Data. (CAUTION: `greenhouse.io/insider` = Business Insider, different company.)
- **Dream Games** — `https://jobs.lever.co/dreamgames` (API) + `https://www.dreamgames.com/open-positions` — open — Data Scientist Istanbul.
- **Peak** — `https://peak.com/open-positions` (dept 'Big Data & Data Science') — open. (CAUTION: greenhouse 'pdbackend' = Peak Design, different company.)
- **Yemeksepeti / Delivery Hero** — `https://jobs.smartrecruiters.com/DeliveryHero` (API `api.smartrecruiters.com/v1/companies/DeliveryHero/postings`) — open — Data Analyst Istanbul confirmed.
- **Gram Games** (Zynga/Take-Two) — `https://job-boards.greenhouse.io/gramgamescareers` (API `boards-api.greenhouse.io/v1/boards/gramgamescareers/jobs?content=true`) — open — Data Analyst Istanbul.
- **Spyke Games** — `https://jobs.lever.co/spyke-games` (API) — open — Data Analyst/PM.
- **Picus Security** — `https://jobs.lever.co/picus` (API) — open — Deal/Revenue Ops Analyst → BA/DA.
- **Vivense** — `https://www.vivense.com/kariyer.html` + Kariyer.net `firma-profil/vivense-...-48678-128729` — open.
- **Modanisa** — `https://modanisa.applytojob.com/apply` (JazzHR) — open.
- **Sahibinden** — `https://kariyer.sahibinden.com/` (403s bots; supervised) + Kariyer.net `firma-profil/sahibinden-com-18667-9512` — open browse. (NOT `sahibinden.com/en/jobs`, which is classifieds.)

## 3b. Tech-ecosystem expansion — 2026-06-17 (batch JAC-34): 121 verified companies
NEW companies (no overlap with the 156 base entries above), Istanbul-first, fit for the Project Manager / Data Analyst / BI / Business Analyst cluster. The research spanned the tech ecosystem and adjacent sectors (this batch also seeds the fintech, e-commerce and IT-services batches). ATS tokens are recorded only where the board/API returned live data; "email: none found" means no public address was confirmed (the company is still reachable via its careers page).

### Gaming studios
- **Rollic Games** — `https://rollicgames.com/jobs` — open — Istanbul hypercasual publisher (Zynga/Take-Two); product/growth/eng roles; email: none found
- **Zynga Istanbul** — `https://job-boards.greenhouse.io/zyngacareers` (API `boards-api.greenhouse.io/v1/boards/zyngacareers/jobs?content=true`) — open — Istanbul office (Gram Games/Rollic umbrella); game eng/QA/product; email: none found
- **Masomo** — `https://www.linkedin.com/company/masomo/jobs` — login-to-apply — İzmir/Istanbul/London social mobile games (Online Head Ball); design/eng/analytics; email: none found
- **Ace Games** — `https://apply.workable.com/ace-games/` (Workable token `ace-games`) — open — Istanbul; verified live Business Analyst (CEO Office), Data Analyst (SQL/BigQuery/Looker); email: none found
- **Bigger Games** — `https://jobs.ashbyhq.com/biggergames` (API `POST api.ashbyhq.com/posting-api/job-board/biggergames`) — open — Istanbul; verified live Data Scientist + eng; email: none found
- **Good Job Games** — `https://job-boards.greenhouse.io/goodjobgames` (API `boards-api.greenhouse.io/v1/boards/goodjobgames/jobs?content=true`) — open — Istanbul (Azur Games, 2025); verified live Data & Monetization Analyst, Growth Manager; email: none found
- **Grand Games** — `https://jobs.lever.co/grand` (API `api.lever.co/v0/postings/grand?mode=json`) — open — Istanbul; verified live Product Manager, Product Specialist + eng; email: none found
- **Panteon Games** — `https://www.panteon.games/en/job-application-form/` — open — Ankara (ODTÜ Teknokent) mobile studio; game dev/design/test; email: none found
- **Vertigo Games** — `https://vertigogames.co/open-positions/` — open — Istanbul midcore multiplayer; verified Data Engineer, Product Manager, perf marketing; email: jobs@vertigogames.co
- **Unico Studio** — `https://unicostudio.co/careers` — open — Istanbul/Ankara/Palo Alto casual (Brain Test); verified Product Manager, UA Manager; email: none found
- **Gamegos** — `https://www.gamegos.com/jobs` — open — Istanbul social/mobile (Manor Cafe, Cafeland); verified Game Analyst + game dev; email: jobs@gamegos.com
- **MagicLab Game Technologies** — `https://maglab.com.tr/jobs/` — open — Ankara HQ + Istanbul casual/hybrid-casual; Growth Manager, game dev; email: none found
- **Matchingham Games** — `https://matchingham.gs/career` — open — Istanbul presence (global publisher); product/tech roles; email: none found
- **Pine Games** — `https://www.pinegames.com/careers` — open — Istanbul puzzle studio (ex-Peak/ex-Dream leadership); email: none found
- **Zuuks Games** — `https://www.zuuks.com/job-list-1` — open — Istanbul casual mobile studio (~73 staff); backend/eng; email: none found
- **TaleWorlds Entertainment** — `https://www.taleworlds.com/en/Career` — open — Ankara PC/console (Mount & Blade); programmers, 3D artists; email: jobs@taleworlds.com
- **Joygame Publishing** — `https://tr.linkedin.com/company/joygame` — login-to-apply — Istanbul PC/mobile publisher (120+ staff); apply via Netmarble EMEA HR; email: none found
- **Netmarble EMEA Interactive Services** — `https://www.netmarbleemea.com/career/` — open — Istanbul (QA/loc/marketing for Netmarble titles); email: none found
- **Voodoo Istanbul** — `https://jobs.ashbyhq.com/voodoo` (API `POST api.ashbyhq.com/posting-api/job-board/voodoo`) — open — Istanbul Match-3 dev studio; verified Istanbul role Publishing Manager – Türkiye; email: none found
- **Fabrika Games** — `https://www.fabrikgames.com/careers` — open — Istanbul hypercasual (Voodoo-invested); game design; email: jobs@fabrikgames.com

### Fintech & payments
- **Macellan** — `https://jobs.macellan.net/` (API `macellan.recruitee.com/api/offers/`) — open — Istanbul fintech SuperApp / digital wallets & payments; Recruitee token `macellan`; email: none found
- **Sipay** — `https://app.gethirex.com/o/sipay/` (Hirex board; no public JSON API) — open — e-money & payments; Strategy & Growth, Ops, Compliance roles; email: none found
- **Paribu** — `https://app.gethirex.com/o/paribu/` (Hirex board) — open — crypto exchange; also `kariyer.paribu.com/tr`; email: none found
- **HangiKredi** — `https://www.hangikredi.com/hakkimizda/kariyer` — open — credit/loan comparison; verified Lead Data Engineer, Data Engineer, Product Manager (apply via LinkedIn); email: none found
- **Tarfin** — `https://tarfin.com/kariyer` — open — agri-fintech / embedded lending; verified Data Scientist, Customer Segmentation Associate; email: none found
- **BiLira** — `https://www.bilira.co/en/open-positions` — open — TRYB stablecoin / crypto; recurring careers page; email: talent@bilira.co
- **Craftgate** — `https://craftgate.io/en/careers` — login-to-apply (email) — payment orchestration (ex-iyzico founders); PM/data/business analyst plausible; email: talent@craftgate.io
- **Apsiyon** — `https://kariyer.apsiyon.com/acik-pozisyonlar` — open — property-management SaaS with finance/collections; own EasyHR portal; email: none found
- **Figopara** — `https://figopara.com/en/career` (HRPanda `figopara.hrpanda.co`) — open — supply-chain finance / invoice-to-cash fintech; email: hr@figopara.com
- **Norma** — `https://norma.co` (careers via site / LinkedIn `normafinans`) — open — neobank for freelancers & micro-SMEs; email: none found
- **Ödeal** — `https://odeal.com/odealda-kariyer/` — open — payment institution / SoftPOS; funnels to Kariyer.net + LinkedIn; email: none found
- **Ozan SuperApp (Ozan Elektronik Para)** — `https://www.ozan.com/tr/kariyer` — open — e-money / digital wallet super-app; email: none found
- **Hesapkurdu** — `https://www.hesapkurdu.com/kariyer` — open — personal-finance / insurance & loan aggregator; historically posts Business Analyst roles; email: none found
- **DGPays** — `https://www.dgpays.com/` (jobs via LinkedIn `dgpays`) — restricted — payment software (gateway/POS/card) for 50+ banks; email: none found
- **Pavo (Pavo Finansal Teknoloji)** — `https://www.pavo-group.com/career` — open — Android POS / new-gen payment systems (Aktif Bank group); email: none found
- **Colendi** — `https://www.colendi.com/career` — open — fintech infra / credit scoring / digital bank; verified Product Manager + eng; email: info@colendi.com
- **Multinet Up** — `https://multinet.com.tr/kariyer-firsatlarimiz` — open (routes to Kariyer.net/LinkedIn) — meal/expense-card fintech; PM, BI, data/business analysts; email: none found
- **Token Financial Technologies** — `https://www.tokeninc.com/tokenli-olmak/` — open (Koç Kariyerim) — Koç Holding POS/payment company; PM, data analyst, BI; email: none found

### E-commerce, marketplace, logistics & mobility
- **Çiçeksepeti** — `https://jobs.lever.co/ciceksepeti` (API `api.lever.co/v0/postings/ciceksepeti?mode=json`) — open — floral/gifting marketplace (+ LolaFlora); verified Data & Business Analyst, Marketplace Analyst; email: none found
- **BiTaksi** — `https://career.bitaksi.com/` (BambooHR `bitaksi.bamboohr.com/careers/`) — open — ride-hailing; verified Data Engineer, FP&A Specialist, Product Manager; email: none found
- **Navlungo** — `https://navlungo.talentics.app/` (Talentics board, token `navlungo`) — open — digital freight-forwarding logistics-tech (Istanbul); email: none found
- **Solvoyo** — `https://careers.solvoyo.com/` (Teamtailor-hosted) — open — supply-chain planning/analytics SaaS (Istanbul ITU R&D + Boston); strong data/analytics/BI fit; email: talentsuccessteam@solvoyo.com
- **İstegelsin** — `https://www.linkedin.com/company/istegelsin/jobs/` — login-to-apply — Yıldız Holding online supermarket; verified CRM Data Analyst (Growth); email: none found
- **OPLOG** — `https://www.linkedin.com/company/oplogturkey/jobs/` — login-to-apply — robotics e-commerce fulfillment/3PL tech; email: hr@oplog.io
- **Cimri** — `https://www.kariyer.net/firma-profil/cimri-bilgi-teknolojileri-ve-sistemleri-a-s-221299-253438` — login-to-apply — price-comparison platform; verified Web Analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Akakçe** — `https://www.kariyer.net/firma-profil/akakce-16532-7167` — login-to-apply — price-comparison (Beenos-backed, ~20M monthly visitors); email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **ePttAVM (PttEM A.Ş.)** — `https://www.kariyer.net/firma-profil/pttem-teknoloji-ve-elektronik-hizmetler-a-s-197748-186773` — login-to-apply — PTT's marketplace; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Decathlon Türkiye** — `https://job-boards.eu.greenhouse.io/decathlontechnologyen` (Greenhouse token `decathlontechnologyen`; TR roles also `tr.linkedin.com/company/decathlonturkey/jobs`) — open/login-to-apply — verified Data Analyst, Web Analyst (Istanbul); email: none found
- **CarrefourSA** — `https://kurumsal.carrefoursa.com/tr/insan-kaynaklari/acik-pozisyonlar` — login-to-apply — grocery retailer + e-commerce (Tıkla Gel Al); email: none found
- **Koçtaş** — `https://www.koctas.com.tr/kurumsal/is-ilanlari` — login-to-apply — home-improvement retailer + e-commerce; email: none found
- **MediaMarkt Türkiye** — `https://careers.mediamarktsaturn.com/MediaMarktTR/?locale=tr_TR` — login-to-apply — consumer-electronics retailer + e-commerce; email: none found
- **Tıkla Gelsin** — `https://tr.linkedin.com/company/tikla-gelsin/jobs` — login-to-apply — TAB Gıda food-delivery + e-commerce; Core Talent grad program (eng/math/stats); email: none found
- **Volt Lines** — `https://www.voltlines.com/careers/?lang=en` (GoHire token `volt-lines-zvk8vmts`) — open — B2B smart corporate-shuttle mobility; sales/CS/ops/product; email: none found
- **Scotty** — `https://scotty.com.tr/kariyer` — open — motorcycle ride-hailing mobility app (Istanbul); email: none found

### SaaS, B2B software, AI & data
- **Jotform** — `https://www.jotform.com/jobs/` — open — Ankara/Istanbul form-builder SaaS; confirmed hiring Data Analyst (Ankara); email: none found
- **Codeway (Codeway Studios)** — `https://jobs.lever.co/codeway` (API `api.lever.co/v0/postings/codeway?mode=json`) — open — Istanbul consumer/generative-AI app studio; PM, Growth, AI roles; email: none found
- **Tarla.io** — `https://tr.indeed.com/cmp/Tarla.io/jobs` — open — Ankara (Bilkent Cyberpark) agritech SaaS; email: info@tarla.io
- **Segmentify** — `https://career.segmentify.com/` — open — Istanbul-founded e-commerce personalization AI; PM, product/data analyst, data engineer; email: none found
- **Pisano** — `https://www.pisano.com/en/careers` — open — Istanbul (İTÜ ARI Teknokent) CX/feedback SaaS; PM, Data Analyst, data engineer; email: info@pisano.com
- **Related Digital (Euromessage/Visilabs)** — `https://www.relateddigital.com/en/careers/` — login-to-apply (via LinkedIn) — Istanbul marketing-automation/CDP (Doğuş Group); PM/BI/data-analyst; email: none found
- **Commencis** — `https://jobs.lever.co/commencis` (API `api.lever.co/v0/postings/commencis?mode=json`) — open — Istanbul digital-product/engineering consultancy; Product/Program Manager + analyst/data roles; email: none found
- **Intertech** — `https://career.intertech.com.tr/` — login-to-apply — Istanbul (Kurtköy Teknopark) financial software (DenizBank/İş Bankası group); BI/business-analyst/data-engineer; email: none found
- **Sestek** — `https://www.sestek.com/careers` — open — Istanbul/Ankara conversational-AI/speech-tech (Unifonic-owned); Product Owner, business analyst, data engineer, BI; email: info@sestek.com
- **Mobven** — `https://mobven.com/careers/` — login-to-apply — Istanbul mobile-tech (Payten/Asseco); PM/data plausible; email: hr@mobven.com
- **VeriPark** — `https://veripark.wd103.myworkdayjobs.com/veripark` (Workday tenant `wd103`, site `veripark`) — open — fintech/banking CRM software; Business Analyst, IT/Project Manager; email: none found
- **ICterra** — `https://www.icterra.com/company/career/` — open (email) — Ankara (ODTÜ Teknokent) software & defence engineering; email: hr.tr@icterra.com
- **Etiya** — `https://etiya.peoplebox.biz/portal/open-positions/` (PeopleBox ATS) — open — Istanbul telco BSS/CRM software (~1,500 staff); PM, business analyst; email: none found
- **Cybersoft** — `https://www.cybersoft.com.tr/kariyer.html` — open (via Kariyer.net) — Ankara enterprise software; business analyst, data; email: none found
- **Cyberwise** — `https://tr.linkedin.com/company/cyberwisetr/jobs` — login-to-apply — Istanbul/Ankara/Izmir cybersecurity MSSP; project management, business/data analyst; email: none found
- **VBT Yazılım** — `https://www.vbt.com.tr/en/page/career` — open (email/CV) — Istanbul software/data house; actively hires Business Analyst (İş Analisti); email: cv@vbt.com.tr
- **İnomera** — `https://inomera.com/en/career/` — open — Istanbul e-commerce/mobile-engagement/telco software; product/data; email: none found
- **V-Count** — `https://v-count.com/careers/` — login-to-apply (via LinkedIn) — Ankara/ODTÜ visitor-analytics / people-counting; product, data/analytics; email: none found
- **Teknasyon** — `https://teknasyon.com/en/career/` — open — Istanbul mobile app studio/SaaS (~400 staff); data analytics, product management; email: ik@teknasyon.com
- **App Samurai (incl. Storyly)** — `https://careers.smartrecruiters.com/AppSamurai` (API `api.smartrecruiters.com/v1/companies/AppSamurai/postings`; also `jobs.lever.co/appsamurai`) — open — Istanbul mobile-growth ad-tech + Storyly in-app stories SaaS; product, growth, data; email: none found
- **Enuygun (Wingie Enuygun Group)** — `https://www.enuygun.com/kariyer/` — open — Istanbul travel OTA; strong fit Data Scientist/Data Analyst/PM/data engineer; email: none found
- **HotelRunner** — `https://hotelrunner.com/en/careers/` (Breezy `hotelrunner.breezy.hr`) — open — Istanbul hospitality SaaS; PM/BI/data/analytics + eng; email: none found
- **Akinon** — `https://akinon.com/en/careers/` — open — Istanbul unified/headless commerce platform; PM/data engineer/analytics; email: none found
- **B2Metric** — `https://b2metric.com/company/careers` — open — Istanbul AI/ML data-analytics platform; Data Engineer, PM, product/data analyst, BI; email: none found
- **HubX** — `https://hubx.co/jobs` — open — Istanbul/Izmir mobile app studio + publisher; PM, marketing, data; email: none found
- **Nesine (Nesine.com)** — `https://www.nesine.com/hakkimizda/kariyer` — restricted (own page + Kariyer.net) — Istanbul iGaming (~700 staff); data/analytics/BI/PM + eng; email: none found
- **OpenZeka** — `https://openzeka.com/kariyer/` — open — Ankara/Bilkent autonomous-driving / NVIDIA embedded; software/AI-ML; email: info@openzeka.com
- **Vispera** — `https://www.careers-page.com/vispera-5` (Manatal board, token `vispera-5`) — open — Istanbul retail shelf computer-vision; PM, data engineer, analytics engineer, BI, business analyst; email: info@vispera.co

### Cybersecurity
- **SOCRadar** — `https://socradar.breezy.hr/` (API `socradar.breezy.hr/json`, BreezyHR token `socradar`) — open — Istanbul-founded (2019) Extended Threat Intelligence SaaS; rotates product/data/CTI analyst roles; email: none found
- **PRODAFT** — `https://www.prodaft.com/career` — restricted — threat-intel (Switzerland/Netherlands/Turkey; Turkish eng team); Threat Intelligence Analyst; email: none found
- **Brandefense** — `https://brandefense.io/careers/` — login-to-apply — Ankara DRPS/EASM/CTI; CTI Analyst, Threat Researcher; email: none found
- **Roksit / DNSSense** — `https://www.dnssense.com/` — restricted — Istanbul (Teknopark) DNS-layer security; network/security + interns; email: none found
- **Barikat Siber Güvenlik** — `https://www.barikat.com.tr/en/corporate/human-resources` — login-to-apply — Istanbul/Ankara (300+ staff); PM, Business Analyst, Data Analyst plausible; email: hr@barikat.com.tr
- **Black Kite (formerly NormShield)** — `https://blackkite.com/careers/` — login-to-apply — Turkish-founded, HQ Boston, technical team in Turkey; engineering + data/analytics; email: none found
- **CRYPTTECH (CryptoSIM)** — `https://www.crypttech.com/` — restricted — Istanbul (2006) SIEM/SOAR; Data Analyst/BI plausible given SIEM focus; email: none found
- **Berqnet / Timus Cyber Security** — `https://www.timusnetworks.com/` — login-to-apply — Gebze/Kocaeli domestic R&D (SASE/firewall); PM/data plausible; email: none found
- **Logsign** — `https://www.logsign.com/join-the-team/` — open (apply-by-email) — Turkish-founded SIEM/SOAR/TDIR (R&D in Turkey, US HQ); Data Analyst/BI plausible; email: none found

### Devtools & cloud
- **Kloia** — `https://www.kloia.com/jobs` — open — Istanbul DevOps/cloud consultancy; Delivery Manager (PM-like), SRE, Platform/Observability eng; email: none found
- **OpsGenie (now Atlassian)** — `https://www.atlassian.com/company/careers/all-jobs` — login-to-apply — Turkish-founded (Ankara 2012), Atlassian-acquired; PM/Data/Analytics by location; email: none found
- **Resmo (now JumpCloud)** — `https://jobs.lever.co/jumpcloud` (API `api.lever.co/v0/postings/jumpcloud?mode=json`) — open — Turkish-founded (ex-OpsGenie team), JumpCloud-acquired 2024; email: none found

### Martech & adtech
- **Adphorus (Sojern)** — `https://www.sojern.com/careers` — restricted — Istanbul-founded 2015, Sojern-acquired; Istanbul team remains; email: none found
- **Admost** — `https://www.admost.com/` — restricted — Istanbul (2015) ad mediation (~14 staff); email: amr@admost.com

### Healthtech
- **Albert Health** — `https://jobs.techstars.com/companies/albert-health` (Techstars/Getro board) — open — Istanbul voice-AI chronic-disease platform; verified live Senior Data Analyst (SQL/Python/Power BI); email: info@albert.health
- **Doktortakvimi (Docplanner Group)** — `https://jobs.smartrecruiters.com/Docplanner` (API `api.smartrecruiters.com/v1/companies/Docplanner/postings`) — open — Istanbul-HQ'd; hires Data Analyst, Data Engineer, Product Analyst, BI; email: none found
- **Wellbees** — `https://wellbees.co/en/follow-the-bee#join-colony` — open (form) — Istanbul corporate-wellbeing B2B/AI; Product Analyst, Data Analyst, BI, PM; email: info@wellbees.co
- **Enbiosis** — careers via contact form / LinkedIn (no standalone ATS) — restricted — gut-microbiome AI/biotech (Kayseri/Istanbul R&D); Data Analyst/Engineer plausible; email: none found
- **Heltia** — jobs via `opportunities.northzone.com/companies/heltia` + LinkedIn — restricted — Istanbul (2022) mental-health app; Product/Data Analyst, PM; email: none found

### IT services & system integrators
- **Innova (İnnova Bilişim Çözümleri)** — `https://www.innova.com.tr/is-ilanlari` — open — IT integrator (Türk Telekom group); İş Analizi Uzmanı, Proje Yönetimi Kıdemli Uzmanı, Teknik Analist; email: none found
- **Detaysoft** — `https://detaysoft.com/tr-TR/kariyer-olanaklari-pg-118` — open — largest 100% Turkish-owned SAP Platinum partner; SAP consultant roles; email: none found
- **Experteam** — `https://www.experteam.com.tr/experteam-kariyer` — open — Oracle Platinum partner (Istanbul); email: none found
- **NTT DATA Business Solutions Türkiye** — `https://nttdata-solutions.com/us/careers-at-ntt-data/` — open — SAP/digital-transformation arm (~2,200 staff TR); SAP BW/EPM/PaPM consultant; email: none found
- **Asseco SEE Turkey (ASEE)** — `https://asee.io/career-center/` — open — banking/payments software group; Senior Project Manager, Java dev, QA (Istanbul); email: none found
- **Sentim Bilişim** — `http://www.sentim.com.tr/en/` — restricted — system integrator (healthcare/security/infra); Product Manager, Network Specialist (email apply); email: none found
- **Mantis Yazılım** — `https://mantis.com.tr/en/career/` — open — search/data-mining & analytics R&D house (Ankara, ODTÜ Teknokent); Software Engineer, internships; email: info@mantis.com.tr
- **Kartaca** — `https://kartaca.com/en/` — restricted — Google Cloud Data Analytics specialization partner (Istanbul); email: none found

### Enterprise & gov software vendors
- **Architecht** — `https://www.kuveytturk.com.tr/en/about-us/human-resources/careers-at-kuveyt-turk` — restricted — Kuveyt Türk tech subsidiary (BOA core banking, advanced analytics/AI); email: none found
- **KoçDigital** — `https://kocdigital.com/corporate/career` — restricted — Koç Holding Data/AI/IIoT & analytics company; email: none found
- **Obase** — `https://obase.com/en/corporate/careers` — restricted — retail BI/analytics & data-warehousing vendor (BIST: OBASE); email: ik@obase.com
- **Akgün Yazılım** — `https://www.akgun.com.tr/tr/kariyer/acik-pozisyonlar` — open — health-informatics vendor (Ankara); software + health-data roles (SQL/R/Matlab/data-mining); email: none found
- **MİA Teknoloji** — `https://www.miateknoloji.com/en/corporate/career/` — open — security/authentication/smart-transport software (Ankara, BIST: MIATK); email: none found
- **Kron (Krontech)** — `https://krontech.com/` — restricted — cybersecurity/telecom software (PAM/IAM, BIST-listed); apply via LinkedIn; email: none found

### Defense & telco tech
- **STM (Savunma Teknolojileri Mühendislik)** — `https://isealim.stm.com.tr/` — login-to-apply — defense software/cyber/data integrator; StarTeaM program; email: none found
- **MilSOFT Yazılım** — `https://www.milsoft.com.tr/index.php/career/` (portal `milsoft.hrpeak.com`) — login-to-apply — defense software (first CMMI L5 in TR, Ankara ODTÜ); email: none found
- **TUSAŞ / Turkish Aerospace (TAI)** — `https://kariyer.tusas.com/acik-pozisyonlarimiz` (apply `basvuru.tai.com.tr/en_US/jobs`) — login-to-apply — aerospace; software/engineering, SKY talent program; email: none found
- **Baykar Teknoloji** — `https://kariyer.baykartech.com/tr/open-positions/` — login-to-apply — UAV/defense (Esenyurt); AI-software, backend, SRE; email: ik@baykartech.com
- **P.I. Works** — `https://piworks.net/about/jobopportunities` (BambooHR `piworks.bamboohr.com/jobs/`) — open — AI mobile-network optimization (Istanbul); Software & Big Data Engineer, Telecom Data Solutions Delivery Engineer; email: none found
- **Argela** — `https://www.argela.com.tr/en/career` — restricted — Türk Telekom 5G/telecom-software R&D subsidiary; software + MIS/IT roles; email: none found

## 4. E-commerce, retail & FMCG
- **Migros** — `https://www.migroskurumsal.com/kariyer/simdi-basvurun/ilanlar` — open browse (Lokasyon/Departman filters); apply needs SMS verify.
- **BİM** — `https://www.bim.com.tr/.../hizli-basvuru.aspx` (talent-pool form only) → Kariyer.net `firma-profil/bim-...-1888-9746` for real roles.
- **A101** — `https://www.a101.com.tr/insan-kaynaklari` + İŞKUR ('YENİ MAĞAZACILIK A.Ş.') + Kariyer.net — open.
- **ŞOK** — `https://kurumsal.sokmarket.com.tr/insan-kaynaklari/sokta-kariyer` + Kariyer.net `firma-profil/sok-marketler-4325-233357` — open.
- **LC Waikiki** — restricted (QR/`hr@lcwaikiki.com`) → Kariyer.net / LinkedIn for queryable roles.
- **Boyner Grup** — `https://www.boynergrup.com/kariyer` → Kariyer.net `firma-profil/boyner-grup-1102-1108` / LinkedIn / SecretCV — open via boards.
- **DeFacto** — → Kariyer.net `firma-profil/defacto-...-6553-31434` — open via board.
- **Arçelik** — Koç SuccessFactors `career5.successfactors.eu/career?company=Koc` — open browse.
- **Vestel** — `https://www.vestelkariyer.com/is-ilanlari` (`/ilan/<id>`) + Kariyer.net `firma-profil/vestel-...-1115-1249` — login-to-apply.
- **Ülker / pladis** — Workday `https://pladis.wd3.myworkdayjobs.com/tr-TR/pladis_Careers` + Kariyer.net `firma-profil/pladis-4325-233359` — open browse.
- **Eti** — → Kariyer.net `firma-profil/eti-gida-...-2539-16905` / LinkedIn — open via board (HQ Eskişehir; HQ roles also Istanbul).
- **Coca-Cola İçecek (CCI)** — `https://careerscci.com/?locale=tr_TR` — SuccessFactors public; category `/go/Dijital-Teknoloji/5308501/`.
- **Unilever Türkiye** — `https://careers.unilever.com/location/istanbul-turkey-jobs/34155/298795-745042/3` (Workday backend) — open.
- **P&G Türkiye** — `https://www.pgcareers.com/location/istanbul-turkey-jobs/936/298795-745042/3` (Phenom) — open, JS (rendered/API).

## 4b. E-commerce, retail, FMCG & logistics expansion — 2026-06-17 (batch JAC-35): ~206 verified companies
NEW companies (no overlap with the base entries above), Istanbul-first then nationwide-HQ employers, fit for the Project Manager / Data Analyst / BI / Business Analyst cluster (plus category/merchandising/demand-planner/CRM analyst roles common in retail & FMCG). Most Turkish-domestic retailers route through Kariyer.net `firma-profil` pages (stable slug+id, login-to-apply); clean machine-queryable ATS tokens are mostly the multinational FMCG arms (Workday/SuccessFactors) and Metro (SmartRecruiters `METROMAKRO`). "email: none found" = no public address confirmed.

### Online marketplaces & D2C e-commerce
- **n11** — `https://www.kariyer.net/firma-profil/n11-com-40089-37810` — login-to-apply — open marketplace, İTÜ Teknokent Maslak/İstanbul; e-commerce/data/product roles; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Pazarama** — `https://www.techcareer.net/sirketler/pazarama` — login-to-apply — Turkish marketplace, İstanbul; category/operations roles; email: none found
- **Dolap (Trendyol-owned 2nd-hand)** — `https://jobs.lever.co/trendyol?department=Dolap` (API `https://api.lever.co/v0/postings/trendyol?mode=json`, filter dept Dolap) — open — 2nd-hand marketplace; live Dolap CRM Analyst + Data Analyst, Maslak/İstanbul; email: none found
- **Gardrops** — `https://www.kariyer.net/firma-profil/gardrops-89986-43425` — login-to-apply — 2nd-hand clothing marketplace, Üsküdar/İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Letgo (OLX/Dubizzle Group)** — `https://www.kariyer.net/firma-profil/letgo-mobil-internet-servisleri-ve-ticaret-anonim-` — login-to-apply — 2nd-hand classifieds + oto+, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Idefix (Turkuvaz)** — `https://www.idefix.com/kurumsal/kariyer` — open — books/media e-com; data-analytics & supply-chain roles; email: none found
- **D&R (Turkuvaz)** — `https://www.kariyer.net/firma-profil/d-r-6427-209909` — login-to-apply — books/entertainment retail + e-com; data-analytics roles; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kitapyurdu** — `https://www.kariyer.net/firma-profil/kitapyurdu-yayincilik-ve-iletisim-a-s-30960-228423` — login-to-apply — books e-commerce; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Evidea** — `https://www.kariyer.net/firma-profil/evidea-33189-25481` — login-to-apply — home-decor e-com, Bostancı/İstanbul; actively posts Kategori Uzmanı; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Sigortam.net** — `https://www.sigortam.net/is-basvurusu` — open/login-to-apply — digital insurance marketplace, Ümraniye/İstanbul; CRM/data roles; email: none found
- **Encazip** — `https://www.kariyer.net/firma-profil/encazip-com-86892-46083` — login-to-apply — energy price-comparison platform; data/analytics roles; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Fashion, apparel, footwear & jewelry retail
- **Mavi** — `https://www.mavikariyer.com` (Kariyer.net `firma-profil/mavi-jeans-19390-10308`) — open — RTW/retail + HQ, İstanbul; email: none found
- **Koton** — `https://kariyer.koton.com.tr/` (Kariyer.net `firma-profil/koton-2116-12254`) — login-to-apply — fast-fashion HQ İstanbul; hires merchandising/buyer/analytics/PM; email: none found
- **Beymen / Beymen Group** — `https://hr.beymen.com/beymende-kariyer` (Kariyer.net `firma-profil/beymen-group-16386-282757`) — login-to-apply — luxury retail + e-com, Sarıyer/İstanbul; merchandising/category; email: none found
- **Vakko** — `https://www.kariyer.net/firma-profil/vakko-3060-22633` — login-to-apply — textile/RTW, Üsküdar/İstanbul; email: insankaynaklari@vakko.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **İpekyol** — `https://kariyerim.ipekyol.com.tr/` (Kariyer.net `firma-profil/ipekyol-group-11021-1110`) — login-to-apply — RTW womenswear, İstanbul (shared portal w/ Twist & Machka); email: none found
- **Yargıcı** — `https://www.yargici.com/kariyer` (Kariyer.net `firma-profil/yargici-konfeksiyon-a-s-6976-31855`) — restricted — RTW, İstanbul; email: none found
- **AdL (Adil Işık Group)** — `https://www.adl.com.tr/tr/kariyer` — open — womenswear, Türkiye-wide; email: kariyer@adilisik.com.tr
- **Kiğılı** — `https://www.kariyer.net/firma-profil/kigili-giyim-ticaret-a-s-24118-223317` — login-to-apply — menswear, HQ Kocaeli, 62 provinces; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Damat / Tween / D'S Damat (Orka Holding)** — `https://www.damattween.com/insan-kaynaklari` — login-to-apply — menswear, İstanbul; email: ikgroup@damat.com.tr
- **Sarar** — `https://kurumsal.sarar.com/ik/` — login-to-apply — men's/womenswear, HQ Eskişehir; email: none found
- **Ramsey (Gürmen Group)** — `https://www.ramsey.com.tr/insan-kaynaklari` — login-to-apply — menswear, İstanbul/Bursa/Konya; email: none found
- **Hotiç** — `https://www.hotic.com.tr/insan-kaynaklari` — login-to-apply — footwear/leather/accessories; email: none found
- **Derimod** — `https://www.derimod.com.tr/insan-kaynaklari` — login-to-apply — footwear/leather/apparel, İstanbul; email: ik@derimod.com.tr
- **FLO Mağazacılık (Ziylan Group)** — `https://kurumsal.flo.com.tr/kariyer` — login-to-apply — footwear retailer (~800 stores), İstanbul; email: none found
- **Greyder** — `https://www.greyder.com.tr/insan-kaynaklari` — login-to-apply — footwear, İstanbul; email: none found
- **Desa (Desa Deri)** — `https://www.desa.com.tr/insan-kaynaklari/` — open (CV by email) — leather goods/fashion, İstanbul; email: insankaynaklari@desa.com.tr
- **Süvari** — `https://www.kariyer.net/firma-profil/suvari-13888-484718` — login-to-apply — menswear (Adana-origin); email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Atasay** — `https://www.atasay.com/insan-kaynaklari` — login-to-apply — jewelry, İstanbul; email: none found
- **Altınbaş** — `https://www.altinbas.com/insan-kaynaklari/acik-pozisyonlar` — open — jewelry, retail + HQ, İstanbul; email: ik@altinbas.com
- **Pierre Cardin / U.S. Polo Assn (Aydınlı Grup)** — `https://www.aydinli.com.tr/TR/insan-kaynaklari/kariyer-imkanlari` (Kariyer.net `firma-profil/aydinli-grup-8371-33249`) — login-to-apply — licensee apparel, İstanbul; posts HQ analytics/buyer roles; email: none found
- **Colin's (Eroğlu Holding)** — `https://www.erogluholding.com/bizi-taniyin/insan-kaynaklari/` — restricted (CV by email) — apparel + HQ, İstanbul; email: erogluholdinginsankaynaklari@erogluholding.com
- **Lufian** — `https://www.kariyer.net/firma-profil/lufian-pazarlama-hizmetleri-a-s-158329-120331` — login-to-apply — menswear (İzmir-origin); email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Avva (Dido Group)** — `https://www.kariyer.net/firma-profil/avva-magazacilik-a-s-40238-47534` — login-to-apply — menswear, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Mudo (Concept + home)** — `https://hr.mudo.com.tr/` (Kariyer.net `firma-profil/mudo-3042-225758`) — open — apparel + home retail (~120 stores), İstanbul; posts allocation/category & sales analyst; email: none found
- **Roman** — `https://www.kariyer.net/firma-profil/roman-a-s-9520-34398` — login-to-apply — women's RTW, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Setre** — `https://www.kariyer.net/firma-profil/setre-bayan-giyim-20444-11467` — login-to-apply — womenswear, Sarıyer/İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Oxxo** — `https://www.oxxo.com.tr/tr/k/oxxo-da-kariyer` — open — apparel retail; email: none found
- **Suwen** — `https://suwencompany.com/bizimle-calismak-ister-misin/` — open — lingerie/homewear, İstanbul; email: ik@suwen.com.tr
- **Tudors** — `https://www.tudors.com/insan-kaynaklari` — open — menswear (180+ stores); email: none found
- **B&G Store** — `https://www.kariyer.net/firma-profil/bgstore-magazacilik-a-s-13629-3974` — login-to-apply — children's apparel (100+ stores), İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Brandroom (Demsa Group)** — `https://demsagroup.com/ik/` (Kariyer.net `firma-profil/demsa-group-1311-3403`) — login-to-apply — multi-brand luxury retail, İstanbul; email: ik@demsagroup.com
- **Altınyıldız Classics / AC&Co (Boyner Group)** — `https://www.kariyer.net/firma-profil/altinyildiz-classics-35309-27813` — login-to-apply — menswear/formalwear (200+ stores), HQ roles via Boyner Group; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **LTB / Little Big (Çak Tekstil)** — `https://www.kariyer.net/firma-profil/ltb-1585-6416` — login-to-apply — denim/apparel; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Gizia** — `https://www.kariyer.net/firma-profil/gizia-moda-tekstil-san-ve-dis-tic-ltd-sti-17516-8249` — login-to-apply — accessible-luxury womenswear, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Loft (Eroğlu Holding)** — `https://www.kariyer.net/firma-profil/loft-4674-46575` — login-to-apply — apparel; posts HQ business-dev roles; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Dagi** — `https://www.kariyer.net/firma-profil/dagi-giyim-sanayi-veticaret-a-s-27402-224798` — login-to-apply — underwear/homewear/beachwear, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Hatemoğlu** — `https://www.kariyer.net/firma-profil/hatemoglu-213274-244567` — login-to-apply — menswear, İstanbul; actively posts e-commerce/category-manager roles; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Jakamen** — `https://www.kariyer.net/firma-profil/jakamen-tekstil-urunleri-giyim-san-ve-tic-ltd-s-148117-188287` — login-to-apply — menswear (208 retail points), İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Cross Jeans (Şık Makas)** — `https://www.kariyer.net/firma-profil/sik-makas-cross-jeans-3115-23238` — login-to-apply — denim/apparel, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Skechers Türkiye (Olka Spor)** — `https://www.kariyer.net/firma-profil/skechers-turkiye-olka-spor-malzemeleri-tic-a-s-117891-51321` — login-to-apply — footwear (74 stores), İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Inditex Türkiye (Zara/Pull&Bear/Bershka/Stradivarius/Massimo Dutti/Oysho)** — `https://www.kariyer.net/firma-profil/inditex-1952-10450` — login-to-apply — multi-brand fashion, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **H&M Türkiye** — `https://career.hm.com/tr-tr/` — open — fast-fashion; hires HQ buying/merchandising; email: none found
- **Mango Türkiye (Mango TR Tekstil)** — `https://www.kariyer.net/firma-profil/mango-tr-tekstil-tic-ltd-sti-18905-9774` — login-to-apply — fashion retail, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Lacoste Türkiye (Eren Perakende)** — `https://erenperakende.com/sayfa/kariyer-372` — open — Lacoste stores + HQ; NextGen grad program; email: none found

### Supermarket, grocery & discount chains
- **Onur Market** — `https://kurumsal.onurmarket.com/kariyer/acik-pozisyonlar` — open — Özen Grup chain (~160 stores), Küçükçekmece/İstanbul; email: info@onurmarket.com
- **Hakmar Express** — `https://ik.hakmarexpress.com.tr/` — open — discount chain, İstanbul; email: none found
- **Happy Center** — `https://www.happycenter.com.tr/kurumsal/insan-kaynaklari/` — open — İstanbul grocery chain; email: bilgi@happy.com.tr
- **Tarım Kredi Kooperatif Market** — `https://www.tkholding.com.tr/tr/is-ilanlari` — login-to-apply — Tarım Kredi Holding, Ataşehir/İstanbul; email: info@tkholding.com.tr
- **Mopaş** — `https://mopas.com.tr/ik-politikasi` — open — Mopaş Marketçilik (~131 stores), İstanbul; email: none found
- **Seç Market** — `https://www.kariyer.net/firma-profil/sec-market-208002-238934` — login-to-apply — Üsküdar/İstanbul, franchising model; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Snowy (Ulu Kardeşler)** — `https://www.kariyer.net/firma-profil/snowy-market-ulu-kardesler-144750-77507` — login-to-apply — Kağıthane/İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bizim Toptan (Yıldız Holding)** — `https://ibf.bizimtoptan.com.tr/` — open — cash & carry, Altunizade/İstanbul, BIST-listed; live İş Analisti listing; email: none found
- **Metro Türkiye** — `https://kariyer.metro-tr.com/jobs` (SmartRecruiters; API `https://api.smartrecruiters.com/v1/companies/METROMAKRO/postings?country=tr`) — login-to-apply — cash & carry (~36 stores), Güneşli/İstanbul; Category Executive; email: none found
- **Pehlivanoğlu** — `https://www.mpehlivanoglu.com/kariyer/` — open — İzmir/Torbalı chain (~47 stores); email: info@mpehlivanoglu.com
- **Groseri** — `https://www.kariyer.net/firma-profil/groseri-gida-ve-ihtiyac-maddeleri-tic-ve-san-ltd-s-15855-6422` — login-to-apply — ~30 stores Adana/Mersin; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Altunbilekler** — `https://www.altunbilekler.com/yeni-insan-kaynaklari` — open — Ankara chain (80+ stores); actively hiring category/demand-planner/BI/CRM; email: none found
- **Çağrı Market** — `https://cagri.com/kariyer` — open — İstanbul/Kocaeli grocery + online (~68 stores), Sancaktepe; email: none found
- **Yunus Marketler Zinciri** — `https://www.yunusmarket.com.tr/ik/insan-kaynaklari` — open — Ankara chain (~100 branches); explicitly lists project manager; email: none found

### Electronics, appliance & DIY/home-improvement retail
- **Vatan Bilgisayar** — `https://www.vatanbilgisayar.com/kariyernet-acik-pozisyonlar/` (Kariyer.net `firma-profil/vatan-bilgisayar-san-tic-a-s-8643-33521`) — login-to-apply — electronics/IT retail + e-com, Şişli/İstanbul; HQ PM/Data/BI/category/supply-chain; email: none found
- **Evkur** — `https://www.kariyer.net/firma-profil/evkur-29309-21214` — login-to-apply — home-appliance/electronics/furniture retail (~82 stores), Küçükçekmece/İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Beğendik** — `https://www.kariyer.net/firma-profil/begendik-magaza-isletmeleri-tic-ve-san-a-s-23663-15007` — login-to-apply — department-store chain (Ankara/Konya/Kayseri/Nevşehir/Kırşehir); email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bauhaus Türkiye** — `https://www.bauhaus.com.tr/is-imkanlari` — open — DIY/home-improvement, Ataşehir/İstanbul; email: none found
- **Praktiker Türkiye (Uygulama Yapı Marketleri)** — `https://www.praktiker.com.tr/` — login-to-apply — DIY chain (İstanbul/Ankara/İzmir/Gaziantep); email: none found
- **Tekzen** — `https://kurumsal.tekzen.com.tr/kariyer` — open — DIY/home-improvement (~133 stores); email: ik@tekzen.com.tr

### Furniture, home furnishing & houseware
- **İstikbal (Erciyes Anadolu Holding)** — `https://erciyesanadolu.com/cv-form` (Kariyer.net `firma-profil/istikbal-mobilya-sanayi-ve-ticaret-a-s-10096-38068`) — open — furniture, HQ Kayseri; email: none found
- **Bellona** — `https://www.kariyer.net/firma-profil/bellona-mobilya-san-ve-tic-a-s-10096-224490` — open — furniture, HQ Kayseri; category/merchandising/demand-planner/BI/CRM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Mondi / Mondi Home** — `https://erciyesanadolu.com/cv-form` (Kariyer.net `firma-profil/mondi-mobilya-sanayi-ve-ticaret-anonim-sirketi-10096-38071`) — open — furniture, HQ Kayseri; email: none found
- **Doğtaş (Doğanlar Mobilya Grubu)** — `https://www.doganlarholding.com.tr/acikpozisyonlar` — open — furniture, İstanbul/İzmir; PM/BI/Business Analyst/demand-planner; email: none found
- **Kelebek Mobilya (Doğanlar Mobilya Grubu)** — `https://www.doganlarholding.com.tr/acikpozisyonlar` — open — furniture; merchandising/BI/CRM/PM; email: none found
- **Çilek Mobilya** — `https://cilekworld.com/pages/careers` — open — children's/youth furniture (71 countries); Data/category/supply-chain/CRM; email: none found
- **Yataş Grup (Enza Home, Yataş Bedding)** — `https://www.kariyer.net/firma-profil/yatas-1994-10912` — open — furniture/bedding, Kartal/İstanbul, BIST-listed; strong BI/Data/demand-planner/CRM/PM fit; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Alfemo Mobilya** — `https://alfemo.com/tr/career` — open — furniture, Torbalı/İzmir; email: none found
- **Modalife (Liderler Pazarlama)** — `https://www.kariyer.net/firma-profil/modalife-33465-25785` — open — furniture (140+ branches), Ankara; email: info@modalife.com (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Weltew Home (Newjoy)** — `https://www.kariyer.net/firma-profil/weltew-home-weltew-yatak-newjoy-9580-34458` — open — furniture (~220 stores), İnegöl/Bursa; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **IKEA Türkiye (MAPA / Maya Holding)** — `https://www.ikea.com.tr/tr/about-us/career` — open — master-franchisee, İstanbul; Data/BI/supply-chain/demand-planner/CRM/PM/category; email: none found
- **Karaca (Karaca Home)** — `https://kurumsal.karaca.com/insan-ve-kultur` — open — kitchenware/homeware group (~3,500 staff, 11 brands), İstanbul; category/merchandising/demand-planner/BI/PM; email: none found
- **Paşabahçe Mağazaları (Şişecam)** — `https://careers.sisecam.com/go/Pasabahce-Stores/4500801/` (SAP SuccessFactors) — login-to-apply — glassware/home retail (~45 stores), İstanbul; email: none found
- **English Home (Aydın Tekstil)** — `https://www.kariyer.net/firma-profil/english-home-19751-10705` — open — home textiles (~425 stores), Üsküdar/İstanbul; category/merchandising/planning; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Madame Coco** — `https://jobs.madamecocotech.com/p/careers` — open — home textiles/homeware (~850 stores), Şişli/İstanbul; data/BI/demand-planner/CRM/category; email: none found
- **Linens (Zorlu Tekstil)** — `http://ztkariyer.com/` — open — home textiles retail, İstanbul/Bursa; email: none found
- **Tepe Home (Bilkent Holding)** — `https://www.bilkentholding.com.tr/tr/acik-pozisyonlar` — open — furniture & home accessories, Ankara; project-specialist/category roles; email: none found
- **Özdilek Holding (retail)** — `https://www.kariyer.net/firma-profil/ozdilek-holding-1241-2634` — open — department stores + hypermarkets + home textiles (~8,000 staff), Bursa; BI/data/supply-chain/demand-planner/category/PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### FMCG — dairy, poultry, meat & cheese
- **Pınar Süt (Yaşar Holding)** — `https://career.yasar.com.tr/go/pinar-sut-tr/9367455/` (SAP SuccessFactors) — open/login-to-apply — HQ İzmir; demand/supply planner, BI/category analyst, PM; email: none found
- **Pınar Et (Yaşar Holding)** — `https://career.yasar.com.tr/go/pinar-et-tr/9367755/` (SAP SuccessFactors) — open/login-to-apply — Kemalpaşa/İzmir; sales analyst; email: none found
- **Sütaş** — `https://www.sutas.com.tr/kariyer-firsatlari` — open/login-to-apply — İstanbul center + plants; supply-chain/planning/analyst; email: none found
- **Banvit (BRF)** — `https://www.banvit.com/banvite-sor/acik-pozisyon` — open — Bandırma/Balıkesir; planner/BI/analyst; email: none found
- **Yörsan (Matlı Group)** — `https://www.kariyer.net/firma-profil/yorsan-sut-ve-sut-urunleri-sanayi-ve-ticaret-a-s-3991-342208` — login-to-apply — Susurluk/Balıkesir; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **İçim / Ak Gıda (Lactalis Türkiye)** — `https://www.akgida.com.tr/en/career-management/` — open — Pamukova/Sakarya; quality/sales/logistics analyst; email: none found
- **Namet** — `https://www.namet.com.tr/kariyer` — open — Çayırova/Kocaeli; ERP/quality/accounting; email: none found
- **Şenpiliç** — `https://www.senpilic.com.tr/ik-anlayisi/` — open/login-to-apply — Sakarya; HR/production/planning; email: none found
- **Beypiliç** — `https://www.beypilic.com.tr/ik` — open — Bolu; email: none found
- **Erpiliç** — `https://erpilic.com.tr/kariyer` — open — Bolu; systems-analyst roles posted; email: none found
- **Keskinoğlu** — `https://www.keskinoglu.com.tr/sayfa-detay/kariyer-olanaklari` — open/login-to-apply — Akhisar/Manisa; IT/software; email: none found
- **Bahçıvan (peynir)** — `https://bahcivanpeynir.com/insan-kaynaklari/` — open/login-to-apply — İstanbul/Tekirdağ; quality/sales; email: none found
- **Ekici (peynir)** — `https://www.kariyer.net/firma-profil/ekici-peynir-9127-40994` — login-to-apply — Antalya OSB; production/planning/sales; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Aytaç Gıda (Yıldız Holding)** — `https://www.kariyer.net/firma-profil/aytac-gida-yatirim-san-ve-tic-a-s-5400-30283` — open/login-to-apply — Çankırı; supply-chain/category; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### FMCG — snacks, confectionery, pasta, edible oil & canned
- **Şölen Çikolata** — `https://www.kariyer.net/firma-profil/solen-cikolata-4705-225759` — login-to-apply — Gaziantep + Silivri; MT + internships; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Torku (Konya Şeker / Anadolu Birlik Holding)** — `https://kariyer.abholding.com.tr/` — open — Konya; demand-planning, food/agri; email: none found
- **Tat Gıda / Tat Konserve (Koç)** — `https://www.kockariyerim.com/companies/tat-gida.html` (SAP SuccessFactors `career5.successfactors.eu/career?company=Koc`) — login-to-apply — Çekmeköy/İstanbul + Bursa; finance/procurement/BI/category; email: none found
- **Tukaş** — `https://www.kariyer.net/firma-profil/tukas-gida-sanayi-ve-ticaret-anonim-sirketi-25402-225019` — login-to-apply — Turgutlu/Manisa; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Filiz / Barilla Türkiye** — `https://www.kariyer.net/firma-profil/barilla-1347-3799` (global `https://jobs.barillagroup.com/`) — login-to-apply — Bolu plant; supply-chain/demand planner, category/BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Nuh'un Ankara Makarnası** — `https://www.nuh.com.tr/kurumsal/insan-kaynaklari-formu` — open — Ankara; email: none found
- **Oba Makarna** — `https://www.obamakarna.com.tr/oba-kariyer.html` — login-to-apply — Gaziantep + Sakarya; recent Marka Takip Uzmanı (analyst-adjacent); email: none found
- **Komili / Ana Gıda (Bunge)** — `https://jobs.bunge.com/` (SAP SuccessFactors) — login-to-apply — Bunge TR office Maltepe/İstanbul; demand-planning/BI/supply-chain; email: none found
- **Yudum (Savola Gıda)** — `https://www.kariyer.net/firma-profil/yudum-gida-sanayi-ve-ticaret-a-s-20342-11355` — login-to-apply — İstanbul; CRM/category/supply-chain; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Orkide (Küçükbay Yağ ve Deterjan)** — `https://www.orkide.com.tr/6-kurumsal/251-insan-kaynaklari/` — open — Bornova/İzmir; planning/finance/audit; email: info@orkide.com.tr
- **Marsan Gıda (Yıldız Holding)** — `https://www.kariyer.net/firma-profil/marsan-gida-sanayi-ve-ticaret-a-s-1016-172` — login-to-apply — İstanbul; supply-chain/BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kerevitaş / SuperFresh (Yıldız Holding)** — `https://www.kariyer.net/firma-profil/yildiz-holding-4325-29208` — login-to-apply — frozen unit (Bursa & Afyon plants); supply-chain/demand planner, BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Penguen Gıda** — `https://www.kariyer.net/firma-profil/penguen-gida-san-a-s-4953-29836` — login-to-apply — Nilüfer/Bursa; quality/data analyst; email: insankaynaklari@penguen.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Dardanel** — `https://www.kariyer.net/firma-profil/dardanel-1184-2008` — login-to-apply — Çanakkale plant + İstanbul HQ; supply-chain/BI; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tamek** — `https://www.tamek.com.tr/kurumsal/kariyer` — login-to-apply — İstanbul; supply-chain/data analyst; email: ik@tamekgrup.com.tr
- **Göknur Gıda** — `https://www.kariyer.net/firma-profil/goknur-gida_son` — login-to-apply — Ankara HQ + plants; quality/demand planner; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Dr. Oetker Türkiye** — `https://jobs.oetker.com/Oetker/?locale=tr_TR` (SAP SuccessFactors) — open/login-to-apply — Torbalı/İzmir; data/BI/category/demand planner; email: ik@droetker.com.tr

### FMCG — tea, coffee, water, soft-drinks & juice
- **Anadolu Efes** — `https://careers.anadolukariyerim.com/AnadoluEfes/search/` — open/login-to-apply — Ümraniye/İstanbul; "Project Future" MT; PM/BI/analyst/supply-chain; email: none found
- **Doğuş Çay** — `https://www.kariyer.net/firma-profil/dogus-cay-3387-26230` — login-to-apply — İstanbul; sales/eng/HR/accounting; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Lipton Türkiye (Lipton Teas & Infusions)** — `https://www.liptonteas.com/careers/job-search/` — open/login-to-apply — Sakarya site; planning/logistics; email: none found
- **Uludağ İçecek (Erbak Uludağ)** — `https://kariyer.uludagicecek.com.tr/` — login-to-apply — Bursa; production/sales/quality; email: hr@uludagicecek.com.tr
- **Aroma** — `https://www.kariyer.net/firma-profil/aroma-a-s-6818-31697` — login-to-apply — Gürsu/Bursa; production + commercial; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Dimes** — `https://www.kariyer.net/firma-profil/dimes-gida-san-ve-tic-a-s-4882-29765` — login-to-apply — İstanbul/İzmir/Tokat/Aydın; commercial/analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Sırma (Sırma Grup İçecek)** — `https://www.kariyer.net/firma-profil/sirma-grup-icecek-san-ve-tic-a-s-8208-33086` — login-to-apply — İstanbul/Ankara/Bursa/Antalya; sales/logistics; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Hayat Su / Hayat Kimya (Hayat Holding)** — `https://www.hayat.com/tr/kariyer/` — login-to-apply — İstanbul; "H Generation" MT; data/BI analyst, demand planner, CRM; email: none found
- **Erikli (Nestlé Waters Türkiye)** — `https://www.nestle.com.tr/jobs/search-jobs` (SAP SuccessFactors) — open/login-to-apply — Bursa plant + İstanbul offices; email: none found

### FMCG — cosmetics, personal-care & home-care
- **Eczacıbaşı Tüketim / Sanipak (Selpak, Selin, Uni Baby)** — `https://www.eczacibasituketim.com/` — login-to-apply — İstanbul HQ + Gebze plants; category analyst, demand/supply planner, BI, CRM; email: none found
- **Eyüp Sabri Tuncer** — `https://www.eyupsabrituncer.com/en/insan-kaynaklari-` — open/login-to-apply — İstanbul HQ + Ankara plant; category specialist/procurement/QA; email: none found
- **Evyap (Duru, Arko, Fax)** — `https://www.evyap.com.tr/en/` — open/login-to-apply — İstanbul; brand mgr, demand planner, BI/analyst; email: none found
- **Kopaş Kozmetik (Dalin)** — `https://www.kopas.com/index.php/kariyer/` — open/login-to-apply — Sarıyer/İstanbul; marketing/R&D/export; email: none found
- **Hunca Kozmetik** — `https://hunca.com/kariyer/` — open/login-to-apply — Şişli/İstanbul + Çerkezköy plant; email: none found
- **Flormar (Kosan Kozmetik)** — `https://www.kariyer.net/firma-profil/flormar-kosan-kozmetik-san-ve-tic-a-s-5378-30261` — login-to-apply — cosmetics D2C, Çerkezköy/İstanbul; marketing/product dev/sales; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Golden Rose (Erkul Kozmetik)** — `https://www.goldenrose.com.tr/tr/iletisim/insan-kaynaklari.asp` — open/login-to-apply — İstanbul; marketing/product dev/logistics/QC; email: none found
- **Note Cosmetics (ACT Group)** — `https://www.kariyer.net/firma-profil/note-cosmetique-35807-28361` — open/login-to-apply — Şişli/İstanbul; marketing; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Farmasi (Farmasi Kozmetik)** — `https://www.kariyer.net/firma-profil/farmasi-kozmetik-15522-6057` — open/login-to-apply — Çekmeköy/İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bioxcin / Biota Laboratuvarları** — `https://biotalab.com/acik-pozisyonlar` — open/login-to-apply — İstanbul; R&D/production; email: none found
- **Sevil Parfümeri** — `https://www.kariyer.net/firma-profil/sevil-parfumeri-2278-14036` — login-to-apply — beauty/perfume retail + e-com, Etiler/İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Gratis (Sedes Holding)** — `https://kariyer.gratis.com/` — open/login-to-apply — cosmetics retail + e-com, 81 provinces; HQ & supply-chain roles; email: none found
- **Watsons Türkiye** — `https://www.watsons.com.tr/isealimsureci` — login-to-apply — beauty/personal-care retail + e-com, İstanbul HQ; email: none found
- **Rossmann Türkiye** — `https://kariyer.rossmann.com.tr/` — open — drugstore retail + e-com, İstanbul; email: none found

### FMCG — multinational Türkiye arms (global ATS, Istanbul roles)
- **Reckitt Türkiye** — `https://careers.reckitt.com/` (SuccessFactors `career2.successfactors.eu`, tenant `reckittb01`) — open/login-to-apply — İstanbul; supply/marketing analyst; email: none found
- **Henkel Türkiye** — `https://www.henkel.com/careers/find-your-job-apply` (SAP SuccessFactors) — open/login-to-apply — Ataşehir/İstanbul + plants; KAM/marketing/R&D; email: recruitment-hr@henkel.com
- **Colgate-Palmolive Türkiye** — `https://jobs.colgate.com/` (Workday) — open/login-to-apply — İstanbul + Gebze plant; analytics/supply-chain/finance; email: none found
- **Nestlé Türkiye** — `https://www.nestle.com.tr/jobs/search-jobs` (SAP SuccessFactors, tenant `nestleHRprdBX`) — open/login-to-apply — Maslak/İstanbul; finance/IT/supply-chain; NestLéaders MT; email: none found
- **Danone Türkiye** — `https://careers.danone.com/en-global/home.html?countries=Turkey` — open/login-to-apply — İstanbul HQ + Bursa plant; Product Analyst, digital/trade marketing; email: none found
- **Mars Türkiye** — `https://careers.mars.com/global/en` (Workday tenant `mars`) — open/login-to-apply — İstanbul; data analysis/marketing/grad programs; email: none found
- **PepsiCo Türkiye** — `https://www.pepsicojobs.com/main/europe/turkey` — open/login-to-apply — Suadiye/İstanbul; Consumer/Shopper Insights Mgr, pricing/IT; email: none found
- **Mondelez Türkiye** — `https://www.mondelezinternational.com/careers/` (Workday tenant `mdlz`) — open/login-to-apply — Bağlar/İstanbul; Analyst Customer Collaboration, CP&A, insights; email: none found
- **L'Oréal Türkiye** — `https://careers.loreal.com/en_US/content/Turkey` (Avature) — open/login-to-apply — Ümraniye/İstanbul; marketing MT, finance/talent; email: none found
- **Beiersdorf Türkiye (Nivea)** — `https://www.beiersdorf.com/career/locations/turkiye` — open/login-to-apply — Vadistanbul/Sarıyer; email: none found
- **Kenvue Türkiye (Johnson's, Listerine, Neutrogena)** — `https://jobs.kenvue.com/` (Workday tenant `kenvue.wd5`) — open/login-to-apply — İstanbul; Supply Chain Project Manager; email: none found
- **Kimberly-Clark Türkiye** — `https://careers.kimberly-clark.com/en/turkey` (Workday tenant `kimberlyclark`) — open/login-to-apply — İstanbul office + manufacturing; email: none found

### Logistics, cargo, courier, 3PL & last-mile
- **Yurtiçi Kargo** — `https://www.yurticikargo.com/tr/kariyer/acik-pozisyonlar` — open — sector-leading cargo, HQ İstanbul, 81 provinces; email: none found
- **Sürat Kargo** — `https://www.suratkargo.com.tr/Basvurular/IsBasvuruFormu` — login-to-apply — cargo/courier; Operasyon Uzmanı roles, Turkey-wide; email: none found
- **Sendeo (= Kolay Gelsin, Koç/Aygaz)** — `https://sendeo.com.tr/life-and-career` (Koç Kariyerim; Kariyer.net `firma-profil/sendeo-dagitim-hizmetleri-anonim-sirketi-260580-299433`) — login-to-apply — last-mile cargo, 81 provinces, Ümraniye/İstanbul; email: none found
- **HepsiJET (Hepsiburada)** — `https://www.kariyer.net/firma-profil/hepsijet-65911-243648` — open — last-mile arm; logistics ops + branch roles, İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Trendyol Express** — `https://careers.trendyol.com/trendyol-express` (Lever `https://jobs.lever.co/trendyol`) — open — e-commerce delivery network, İstanbul; data-driven roles; email: none found
- **UPS Türkiye** — `https://global.jobs-ups.com/tr-turkey` — open — global ATS; sales/customer-solutions roles; email: none found
- **FedEx Türkiye (= TNT)** — `https://careers.fedex.com/` — open — global FedEx ATS; İstanbul intern/courier/warehouse; email: none found
- **Ekol Lojistik** — `https://www.ekol.com/en/corporate/human-resources/career-at-ekol/` — open — integrated 3PL/contract logistics, İstanbul HQ; talent/leadership programs; email: none found
- **Borusan Lojistik** — `https://careers.borusan.com/` — open — integrated 3PL, Kağıthane/İstanbul; Süreç Geliştirme/Yönetim Sistemleri Uzmanı (PM-adjacent); email: none found
- **Omsan Lojistik (OYAK)** — `https://www.omsan.com/en/human-resources/career-management-and-development/career-opportunities/` — open — 3PL/transport, multimodal; email: none found
- **Reysaş Lojistik** — `https://reysas.com/acik-pozisyonlar` — open — warehousing/3PL (BIST-listed); Lojistik & İş Geliştirme Müdürü, İstanbul Anatolian side; email: ik@reysas.com
- **Netlog Lojistik** — `https://www.netloglogistics.com/en/kariyer` — open — large 3PL (warehousing/cold chain/distribution); ops manager roles; email: none found
- **Mars Logistics** — `https://www.marslogistics.com/tr/marsli-olmak` — login-to-apply — freight forwarding/logistics group, Güneşli/İstanbul; email: ik@marslogistics.com
- **Horoz Lojistik** — `https://www.kariyer.net/firma-profil/horoz-lojistik-kargo-hizmetleri-ve-tic-a-s-3614-225197` — open — domestic 3PL/distribution, Bağcılar/İstanbul; e-commerce warehouse + ops; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Arkas Lojistik** — `https://arkaslojistik.com.tr/en/career` (group ATS `https://careers.arkas.com/`, SAP SuccessFactors) — login-to-apply — Arkas Holding multimodal logistics; Arkas Academy; email: none found
- **Barsan Global Logistics** — `https://www.barsan.com/company/careers` — open — integrated logistics/freight forwarding, Şişli/İstanbul; management-trainee program; email: none found
- **CEVA Logistics Türkiye (absorbed Gefco)** — `https://www.cevalogistics.com/en/careers/` — open — CMA CGM group 3PL/freight forwarding/contract logistics, İstanbul; email: none found
- **DB Schenker Arkas Türkiye** — `https://www.dbschenker.com/tr-tr/kariyer/acik-pozisyonlar` — open — air/ocean/land/contract logistics, Kağıthane/İstanbul; email: none found
- **Kuehne+Nagel Türkiye** — `https://jobs.kuehne-nagel.com/` — open — freight forwarding/integrated logistics; Digital & Tech, marine-logistics roles İstanbul; email: none found
- **DSV Türkiye** — `https://www.dsv.com/en/careers/job-openings/tr` — open — global transport/logistics; İstanbul (Kavacık) sales/finance/key-account; email: info@tr.dsv.com
- **Geodis Türkiye** — `https://workatgeodis.com/jobs` — open — Supply Chain Optimization/Contract Logistics, Ataşehir/İstanbul; email: none found
- **Yusen Logistics Türkiye** — `https://www.yusen-logistics.com/en/europe/turkey/careers/tr` (iCIMS) — open — NYK-group freight forwarding/contract logistics; email: none found
- **Bolloré Logistics Türkiye (Horoz Bolloré)** — `https://jobs.bollore.com/en` — open — freight forwarding, İstanbul; email: none found
- **ID Logistics Türkiye** — `https://career.id-logistics.com/homepage.aspx?LCID=2057` — open — contract logistics/warehousing; email: none found
- **Logwin Türkiye** — `https://www.logwin-logistics.com/people/entry/career-entry` — open — air+ocean & contract logistics; email: none found
- **Çelebi Hava Servisi** — `https://www.celebiaviation.com/career/open-positions` — open — ground handling (30 airports); management-trainee track; email: none found
- **TGS (Turkish Ground Services)** — `https://aday.tgs.aero/` — login-to-apply — THY+Havaş JV ground handling; email: none found
- **Havaş (TAV Group)** — `https://www.tav.jobs/` — open — ground handling; email: none found
- **PTS Worldwide Express** — `https://www.kariyer.net/firma-profil/pts-worldwide-express-5994-30875` — open — int'l express courier, Güneşli/İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Vigo** — `https://www.kariyer.net/firma-profil/vigo-teknoloji-ve-lojistik-anonim-sirketi-216604-248204` — open — tech-driven courier/last-mile q-delivery, Kadıköy/İstanbul; ops/PM/demand-planning; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Mobility (logistics-adjacent)
- **Martı Teknoloji** — `https://www.marti.tech/en/ilanlar/` — open — e-scooter/ride-hailing (Nasdaq-listed), Maslak/İstanbul; logistics + tech roles; email: none found
- **BinBin** — `https://www.kariyer.net/firma-profil/bin-ulasim-ve-akilli-sehir-teknolojileri-a-s-209326-240350` — open — e-scooter micromobility, Ümraniye/İstanbul; field-ops; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Retail-tech & e-commerce-enabler SaaS
- **ikas** — `https://www.kariyer.net/firma-profil/ikas-teknoloji-a-s-37079-87179` — open — e-commerce SaaS (Ankara + İstanbul + Stuttgart); PM/data/BI/category-analyst; email: cv@ikas.com (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **IdeaSoft** — `https://www.ideasoft.com.tr/sayfa/ideasoft-kariyer/` — open — e-commerce SaaS, Üsküdar/İstanbul; product/data roles; email: none found
- **Ticimax** — `https://www.ticimax.com/insan-kaynaklari/` — open — e-commerce SaaS, İstanbul; BI/analyst plausible; email: none found
- **T-Soft** — `https://www.tsoft.com.tr/Eticaret/e-ticaret-kariyer.php` — open — e-commerce SaaS, Şişli/İstanbul; support/dev/PM roles; email: none found
- **Shopier** — `https://shopier.talentics.app/` (Talentics ATS) — open — payments/e-commerce SaaS, İstanbul; PM/data/analyst plausible; email: none found
- **Prisync** — `https://www.prisync.com` — open — competitor-price-tracking / dynamic-pricing analytics SaaS, Şişli/İstanbul; strong data/BI/pricing-analyst fit; email: none found
- **D·engage (Dengage)** — `https://dengage.zohorecruit.com/jobs/Careers` (Zoho Recruit) — open — omni-channel marketing-automation / CDP SaaS, Beşiktaş/İstanbul; CRM/data/PM; email: none found
- **SmartMessage** — `https://www.kariyer.net/firma-profil/smartmessage-16595-7236` — open — omni-channel marketing/CX SaaS, Ümraniye/İstanbul; Software PM, CRM/campaign/data; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Faprika** — `https://www.faprika.com/kariyer` — login-to-apply — e-commerce infrastructure + marketplace-integration SaaS; .NET dev + e-commerce roles; email: none found
- **BirFatura** — `https://www.kariyer.net/firma-profil/birfatura-yazilim-teknolojileri-a-s-203612-234022` — open — e-invoice + marketplace-integration SaaS; ops/integration/data; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Entegra Bilişim** — `https://www.entegrabilisim.com/` — open — marketplace-integration SaaS (Trendyol/HB/N11/Amazon); integration/ops/analyst; email: none found
- **Sentos** — `https://www.kariyer.net/firma-profil/sentos-yazilim-teknolojileri-ticaret-limited-sirke-214351-245809` — open — pre-accounting + marketplace-integration SaaS, Ataşehir/İstanbul; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Paraşüt (Mikrogrup)** — `https://www.parasut.com/kariyer` — open — SaaS pre-accounting/financial-management for SMEs, Maslak/İstanbul; product/data/PM; email: none found

### Q-commerce & food-delivery
- **Fuudy** — `https://fuudy.co/` — restricted (no public listings) — gourmet food-delivery, İstanbul; ops/PM plausible; email: info@fuudy.co
- **Paket Mutfak** — `https://www.linkedin.com/company/paketmutfak/jobs/` — login-to-apply — cloud-kitchen network + kitchen-management software, İstanbul; ops/PM/supply; email: none found

## 5. Telco, defense-tech & IT services
- **Turkcell** — `https://kariyerim.turkcell.com.tr/kariyer-firsatlari` + Kariyer.net `firma-profil/turkcell-1107-1163` — open.
- **Vodafone Türkiye** — `https://jobs.vodafone.com/careers?domain=vodafone.com&location=Turkey` (Workday) — open.
- **Türk Telekom** — `https://www.turktelekomkariyer.com.tr/` → listing `basvuru.turktelekomkariyer.com.tr/ilan/site.aspx` — login-to-apply (TC ID).
- **ASELSAN** — `https://www.aselsan.com/en/kariyer` + `https://kariyerportal.aselsannet.com.tr/` — login-to-apply (TC ID; TR nationals).
- **HAVELSAN** — `https://kariyer.havelsan.com.tr/` (KOVAN ATS) + LinkedIn — login-to-apply.
- **Logo Yazılım** — `https://live.peoplise.com/logo/career` (Peoplise) + Kariyer.net `firma-profil/logo-yazilim-...-3066-22699` — open.
- **Netaş** — `https://kariyer.netas.com.tr/content/CAREERS/?locale=en_US` — open.
- **KoçSistem** — `https://www.kocsistem.com.tr/en/corporate/career` → Koç Kariyerim — open browse.
- **OBSS** — LinkedIn `tr.linkedin.com/company/obss/jobs` (primary) + Kariyer.net `firma-profil/obss-...-16418-7041` — login / open board.
- **TurkNet** — `https://kariyer.turk.net/` (Talentics; dept 'Data Analysis & Data Science'; `/jobs/<uuid>`) — open — strong DA/DS match.

## 5b. Telecom, IT services & consulting expansion — 2026-06-17 (batch JAC-37): 101 verified companies
NEW telecom operators, ISPs, data centers, IT integrators/VARs/distributors, ERP & software houses, strategy-consulting and executive-search firms, and BPO/call-centers — each a distinct employer, not a duplicate of any parent or sister company. Istanbul-first. Companies already present in sections 5, 6, 3b or 2b were skipped; where a careers subdomain blocks direct fetches, a Kariyer.net firma-profil URL is cited instead.

### Telecom operators, MVNOs & ISPs
- **Netgsm** — `https://www.kariyer.net/firma-profil/netgsm-iletisim-ve-bilgi-teknolojileri-a-s-46899-51361` — login-to-apply — MVNO & ISP (virtual mobile, fixed-line, internet), Ankara; Project Manager, Data Analyst, Business Analyst, ops; email: info@netgsm.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Türksat (Türksat Uydu Haberleşme Kablo TV ve İşletme A.Ş.)** — `https://kariyer.turksat.com.tr/jobs` — open — satellite operator, cable & ISP, e-government IT, Ankara; PM, Data Analyst, BI, Business Analyst; email: info@turksat.com.tr (general)
- **Millenicom** — `https://www.kariyer.net/firma-profil/millenicom-telekominikasyon-hizmetleri-a-s-8010-32888` — login-to-apply — alternative fiber ISP / telecom operator (SOCAR Türkiye), İstanbul; Data Analyst, PM, Business Analyst, ops; email: info@milleni.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **DorukNet (Doruk İletişim)** — `https://doruk.net.tr/kariyer` — open — corporate ISP, data center, cloud & hosting, İstanbul (also İzmir, Antalya); PM, Business Analyst, Data Analyst, ops; email: info@doruk.net
- **Netspeed İnternet** — `https://www.kariyer.net/firma-profil/netspeed-internet-anonim-sirketi-213346-244646` — login-to-apply — independent fiber ISP, İstanbul; Business Analyst, ops, CRM/analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Verimor Telekom** — `https://www.verimor.com.tr/insan-kaynaklari/` — open — cloud communications / CPaaS (cloud PBX, SMS/OTP, voice), İstanbul (Kağıthane); PM, Business Analyst, ops; email: ik@verimor.com.tr
- **DE-CIX Istanbul** — `https://www.de-cix.net/en/about-de-cix/careers` — open — internet exchange (IX/peering), İstanbul; Network Engineer, PM, Business Analyst, ops; email: none found
- **GTT (Türkiye/Istanbul)** — `https://gtt.wd3.myworkdayjobs.com/external` (CXS `https://gtt.wd3.myworkdayjobs.com/wday/cxs/gtt/external/jobs`) — open — global Tier 1 IP network & managed connectivity, İstanbul; PM, network/sales engineering, ops; email: none found

### Data centers, hosting & cloud infra
- **Radore** — `https://www.kariyer.net/firma-profil/radore-veri-merkezi-a-s-49555-38456` — login-to-apply — data center & hosting, İstanbul; PM, BI/Data Analyst, system/ops engineers, sales; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Natro** — `https://www.natro.com/ik` — open — domain & web hosting (team.blue group), İstanbul; PM, Business Analyst, ops/customer operations; email: none found
- **Vargonen** — `https://www.kariyer.net/firma-profil/vargonen-teknoloji-a-s-11581-1724` — login-to-apply — managed cloud & web hosting / data center, İzmir; PM, ops, technical support; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bulutistan** — `https://www.kariyer.net/firma-profil/bulutistan-206473-237266` — login-to-apply — cloud computing (managed SAP/cloud, data centers), İstanbul (Üsküdar); PM, Business Analyst, BI/Data Analyst, system/ops; email: info@bulutistan.com (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Medianova** — `https://www.kariyer.net/firma-profil/medianova-internet-hizmetleri-ve-tic-a-s-25005-16482` — login-to-apply — CDN & cloud security, İstanbul; PM, BI/Data Analyst, system/ops; email: info@medianova.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Veridyen** — `https://www.veridyen.com/hakkimizda/iletisim/` — restricted — web hosting, domain, cloud & server services, İzmir (Konak); technical support, ops, sales; email: info@veridyen.com
- **İdeal Hosting** — `https://www.kariyer.net/firma-profil/ideal-hosting-sunucu-internet-hizmetleri-tic-ltd-70241-41067` — login-to-apply — hosting & data center (İstanbul & Bursa facilities), İstanbul (Bağcılar); PM, BI/Data Analyst, system/ops; email: info@idealhosting.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Güzel Hosting** — `https://www.guzel.net.tr/kariyer.php` — open — web hosting & domains, İstanbul (Ataşehir); PM, Business Analyst, support/ops; email: none found
- **Turhost** — `https://www.turhost.com/hakkimizda/insan-kaynaklari/` — open — hosting & domains (team.blue group), İzmit (Kocaeli); PM, BI/Data Analyst, ops/support; email: none found
- **İsim Tescil Bilişim A.Ş. (isimtescil)** — `https://www.kariyer.net/firma-profil/isim-tescil-bilisim-a-s-3926-220104` — login-to-apply — domain & hosting, İstanbul; Business Analyst, PM, Data Analyst, customer ops; email: info@isimtescil.net (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **GlassHouse** — `https://www.glasshouse.com.tr/en/career` — open — managed cloud & IT infrastructure / hybrid cloud / data center, İstanbul (also Ankara, İzmir); PM, Business Analyst, Cloud Solution Architect, monitoring/ops; email: hr@glasshouse.com.tr
- **Comnet Datacenter İstanbul** — `https://www.kariyer.net/firma-profil/comnet-datacenter-istanbul-143168-253453` — login-to-apply — Tier III data center / IP transit / colocation & ISP, İstanbul (Bahçelievler); PM, ops, analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kuzey Veri Merkezi** — `https://www.kariyer.net/firma-profil/kuzey-veri-merkezi-381563-440267` — login-to-apply — Tier III colocation / cloud / dedicated data center, İstanbul (Çekmeköy); PM, ops, analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Teknotel Telekomünikasyon** — `https://www.kariyer.net/firma-profil/teknotel-telekomunikasyon-a-s-4634-29517` — login-to-apply — carrier-neutral data center / internet / cloud (Telehouse Istanbul), İstanbul; PM, Business Analyst, ops; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Veriteknik Veri Merkezi** — `https://www.kariyer.net/firma-profil/veriteknik-veri-merkezi-64829-42317` — login-to-apply — data center / managed servers / PCI-DSS infrastructure, İstanbul; Business Analyst, ops, infrastructure analyst; email: iletisim@veriteknik.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Equinix Türkiye (Istanbul)** — `https://careers.equinix.com/jobs/search?location=Istanbul` — open — colocation / data center & internet exchange (IL2 & IL4 facilities), İstanbul; PM, Business/Data Analyst, data center ops, critical facilities engineer; email: none found

### IT integrators & VARs
- **Gantek Teknoloji** — `https://gantek.com/tr/gantek-te-calismak` — open — system integrator (infrastructure, Red Hat, datacenter), İstanbul; PM, system & presales engineers; email: job@gantek.com
- **Data Market (Data Market Bilgi Hizmetleri)** — `https://www.kariyer.net/firma-profil/data-market-bilgi-hizmetleri-ltd-sti-14021-4406` — login-to-apply — system integrator & VAR (Microsoft LAR, Cisco, Dell EMC, HPE), İstanbul; PM, presales, BI & infrastructure; email: info@datamarket.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **TURCom Teknoloji** — `https://api.smartrecruiters.com/v1/companies/turcom/postings` (also Kariyer.net `firma-profil/turcom-iletisim-sistemleri-sanayi-ve-ticaret-a-s-28100-78298`) — open — IT system integrator & managed services, İstanbul; PM, presales, network & system; email: insan_kaynaklari@turcom.com.tr (was kariyer-only; resolved via SmartRecruiters 2026-06-21)
- **Turkuaz Bilgisayar** — `https://www.kariyer.net/firma-profil/turkuaz-bilgisayar-yazilim-donanim-network-14036-4422` — login-to-apply — system integrator (software, consulting, project, corporate sales, technical support), İstanbul; PM, presales; email: info@turkuaz.net (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Atos Türkiye (Atos Bilişim ve Danışmanlık)** — `https://www.kariyer.net/firma-profil/atos-bilisim-ve-danismanlik-a-s-17957-220338` (global `https://jobs.atos.net/`) — login-to-apply — system integrator & managed services (Big Data, consulting, security), İstanbul; PM, Data/Business Analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **DXC Technology / Luxoft Türkiye** — `https://career.luxoft.com/locations/turkiye` — open — global IT services & systems integration, İstanbul; PM, Business Analyst, data; email: none found
- **Hitachi Vantara Türkiye** — `https://careers.hitachi.com/search/jobs/in/istanbul` (CXS `https://hitachi.wd1.myworkdayjobs.com/wday/cxs/hitachi/hitachi/jobs`) — open — data infrastructure & analytics integrator/VAR, İstanbul; Data/BI, PM, presales; email: none found
- **Komtaş Bilgi Yönetimi** — `https://www.kariyer.net/firma-profil/komtas-35654-28193` — login-to-apply — data & analytics consultancy/integrator (BI, big data, DWH), İstanbul; Data Analyst, BI, Data Management Consultant, PM; email: info@komtas.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bilge Adam Technologies** — `https://www.kariyer.net/firma-profil/bilge-adam-teknoloji-1899-9867` — login-to-apply — IT services (software, Big Data & Analytics, cloud, consulting), İstanbul & Ankara; Business Analyst, PM, data; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Innovera** — `https://www.innovera.com.tr/` — open — cybersecurity & IT-continuity consulting/integrator, İstanbul & Ankara; security consultants/analysts, PM; email: info@innovera.com.tr (general)
- **Boğaziçi Yazılım** — `https://www.kariyer.net/firma-profil/bogazici-yazilim-a-s-10414-450` — login-to-apply — Siemens PLM software VAR/integrator, İstanbul (Ataşehir); presales, PM, application consultants; email: bogazici@bogaziciyazilim.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### IT distributors
- **Index Grup** — `https://www.indexgrup.com/insan-kaynaklari` — open — leading IT/telecom/CE distribution group (Index, Datagate, Despec, Netex, Teklos), İstanbul; Data Analyst, BI, Product & Project Manager; email: kvkk@indexgrup.com.tr (general)
- **Penta Teknoloji** — `https://www.penta.com.tr/kariyer/kariyer-firsatlari` — open — value-added technology distributor (Yıldız Holding), İstanbul; Product/Project Manager, Data Analyst, BI; email: info@penta.com.tr (general)
- **Arena Bilgisayar** — `https://www.arena.com.tr/hakkimizda/kariyer` — open — technology distributor (HP, Huawei, Dell, Microsoft; Redington group), İstanbul (Göktürk); Data Analyst, BI, Product & Project Manager; email: musteri.hizmetleri@arena.com.tr (general)
- **Despec (Index Grup)** — `https://www.despec.com.tr/insan-kaynaklari` — open — IT consumables & accessories distributor, İstanbul (Kağıthane); Product/Data Analyst, PM; email: info@despec.com.tr (general)
- **Ingram Micro Türkiye (formerly Armada Bilgisayar)** — `https://careers.ingrammicro.com/en/locations/emea/turkey/` (CXS `https://ingrammicro.wd5.myworkdayjobs.com/wday/cxs/ingrammicro/IngramMicro/jobs`) — open — global value-added IT distributor (Cisco, Dell, Fortinet, Lenovo, VMware), İstanbul; Product/Project Manager, presales, BI; email: insankaynaklari.tr@ingrammicro.com
- **ASBIS Türkiye** — `https://career.asbis.com/` — open — multinational IT-products distributor (EMEA), İstanbul; Product/Data Analyst, PM; email: none found
- **EMPA Elektronik** — `https://empa.com/kariyer/` — open — technology/semiconductor distributor with IoT/IT division, İstanbul; Product/Project Manager, presales; email: none found

### ERP / SAP / software houses
- **Uyumsoft** — `https://www.kariyer.net/firma-profil/uyumsoft-bilgi-sistemleri-ve-teknolojileri-tic-a-2668-224788` — login-to-apply — ERP/e-transformation vendor, İstanbul/Ankara/İzmir/Bursa/Tokat; PM, Process Analyst (Süreç Analisti), Product Manager, ERP consultant; email: iletisim@uyumsoft.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Mikro Yazılım** — `https://www.mikro.com.tr/hakkimizda/mikro-yazilimda-kariyer/` — open — accounting/ERP software vendor (SMB), İstanbul; Financial Analyst, support/dev, BI; email: none found
- **Nebim (Nebim V3)** — `https://www.nebim.com.tr/en/career-at-nebim` — open — retail ERP vendor, İstanbul; ERP consultant, Business Analyst, Product Manager, PM; email: nebim@nebim.com.tr (general)
- **Workcube** — `https://www.workcube.com/tr/kariyer` — open — web-based ERP/CRM/HR vendor, İstanbul; Strategic Consultant, PM, module/ERP consultant; email: none found
- **IFS Türkiye** — `https://www.kariyer.net/firma-profil/ifs-turkiye-3622-28505` — login-to-apply — global ERP/EAM/FSM vendor (TR office), İstanbul; ERP Consultant, Senior ERP Consultant, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Sentez Yazılım** — `https://www.kariyer.net/firma-profil/sentez-yazilim-firma-profili-2319-86207` — login-to-apply — ERP vendor (retail/textile/foreign-trade), İstanbul; ERP/dev consultant, analyst; email: info@sentez.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **CANIAS ERP / IAS (Industrial Application Software)** — `https://www.canias40.com/tr/career` — open — ERP product vendor (canias4.0), İstanbul & İzmir; ERP Consultant, Senior ERP Consultant (Production), dev; email: info@canias.com (general)
- **DİA Yazılım** — `https://www.kariyer.net/firma-profil/dia-a-s-24214-38959` — login-to-apply — cloud ERP vendor, Ankara/İstanbul/Antalya; ERP support/dev, sales support; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Akınsoft** — `https://www.kariyer.net/firma-profil/akinsoft-akin-yazilim-bilgisayar-ltd-sti-25149-16640` — login-to-apply — business software vendor, Konya; Project Representative, C#/ASP.NET dev, QA, planning; email: ikaynaklari@akinsoft.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Link Bilgisayar** — `https://www.kariyer.net/firma-profil/link-bilgisayar-sistemleri-yaz-ve-don-san-ve-tic-31332-23439` — login-to-apply — e-transformation/ERP vendor (BIST-listed), İstanbul & Ankara; Front-End dev, data/BI, PM; email: info@link.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Vega Yazılım (Vegagrup)** — `https://www.kariyer.net/firma-profil/vegagrup-yazilim-ve-bilisim-teknolojileri-ticaret-5303-30186` — login-to-apply — ERP vendor (Arctos ERP, retail/restaurant), Ankara; software dev, support, analyst; email: info@vegayazilim.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **ETA Bilgisayar** — `http://www.eta.com.tr/insan_kaynaklari.asp` — restricted (email-only) — commercial accounting/ERP software vendor, İstanbul; accounting-program specialist, C++ dev, support; email: eta@eta.com.tr
- **Zirve Yazılım** — `https://www.kariyer.net/firma-profil/zirve-bilgi-teknolojileri-sanayi-ticaret-anonim-st-1941-248067` — login-to-apply — accounting software vendor (Mikro group); accounting/dev/support; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Smartiks** — `https://www.kariyer.net/firma-profil/smartiks-yazilim-a-s-13078-3368` — login-to-apply — business-software & Microsoft/data house, İstanbul (Kadıköy); data, BI, business analyst, consultant; email: ik@smartiks.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Set Yazılım** — `https://www.kariyer.net/firma-profil/set-yazilim-2863-20469` — login-to-apply — financial ERP/banking software house, İstanbul (Ataşehir); İş Analisti (Business Analyst), software expert; email: info@setsoftware.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Universal Yazılım** — `https://www.kariyer.net/firma-profil/universal-yazilim-a-s-30620-22656` — login-to-apply — sector-specific software/ERP vendor (R&D center), İstanbul; PM, support, consulting; email: info@uni-yaz.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Egebimtes** — `https://egebimtes.com.tr/d/Tr/egebimtes-te-kariyer-131.html` — restricted (email-only) — digital-transformation/ERP implementation house, İzmir; ERP consultant, PM; email: ik@egebimtes.com.tr
- **Inveon** — `https://www.kariyer.net/firma-profil/inveon-bilgi-teknolojileri-10872-948` — login-to-apply — e-commerce software/integration house, İstanbul; data analytics, product mgmt, system integration, PM; email: info@inveon.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **CoreSys** — `https://www.coresys.com.tr/kariyer/` — open — CANIAS ERP solution partner, İzmir/Bursa/İstanbul/Antalya; ERP Consultant; email: info@coresys.com.tr
- **ABAS Türkiye** — `https://www.kariyer.net/firma-profil/abas-turkiye-27148-18839` — login-to-apply — abas ERP implementation partner, İstanbul; ERP Application Consultant, ERP Technical Consultant; email: abas@abas.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **TeamPro Danışmanlık** — `https://www.kariyer.net/firma-profil/teampro-danismanlik-ve-bilisim-hizmetleri-239724-274559` — login-to-apply — SAP partner (S/4HANA), İstanbul (Kadıköy); SAP Project Manager, SAP SD/logistics consultant; email: ik@teampro.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **HumanEra** — `https://www.kariyer.net/firma-profil/humanera-40655-37510` — login-to-apply — IT/SAP recruitment & consulting house, İstanbul; SAP consultant, analyst; email: info@humanera.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **QSoft (Qsoft Bilişim ve Teknoloji)** — `https://www.kariyer.net/firma-profil/qsoft-bilisim-ve-teknoloji-a-s-394442-455067` — login-to-apply — enterprise software house, İstanbul (Başakşehir); software dev, analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Datasel Bilgi Sistemleri** — `https://www.kariyer.net/firma-profil/datasel-bilgi-sistemleri-a-s-2710-18786` — login-to-apply — business software/ERP house; software expert, architecture/dev; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Likom Yazılım** — `https://www.kariyer.net/firma-profil/likom-yazilim-3911-42089` — login-to-apply — Gusto ERP vendor (mid/large enterprise); ERP dev/consultant/support; email: info@likom.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Elsis Elektronik Sistemler** — `https://www.kariyer.net/firma-profil/elsis-elektronik-sistemler-san-a-s-31734-23881` — login-to-apply — defense/electronics software & systems house, Ankara (Çankaya); ERP/IT, PM, dev; email: insankaynaklari@elsis.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Management & strategy consulting
- **Boston Consulting Group (BCG)** — `https://careers.bcg.com/global/en/locations/turkey` — open — strategy/operations/transformation consulting, İstanbul (Kanyon, Levent); Associate, Consultant, IT Consultant, Data roles; email: none found
- **Bain & Company** — `https://www.bain.com/offices/istanbul/` — login-to-apply — strategy & PE/commercial due-diligence consulting, İstanbul (Akmerkez, Etiler); Associate Consultant, Consultant, Analyst; email: none found
- **Kearney** — `https://www.tr.kearney.com/careers` — open — management/strategy & operations consulting, İstanbul (Nidakule, Levent); Analyst, Consultant, Business Analyst; email: none found
- **Oliver Wyman** — `https://www.oliverwyman.com/careers.html` (CXS `https://mmc.wd1.myworkdayjobs.com/wday/cxs/mmc/MMC/jobs`, shared Marsh McLennan board) — login-to-apply — strategy, operations, risk & org-transformation consulting, İstanbul (Maya Akar Center, Esentepe); Consultant, Analyst; email: recruiting@oliverwyman.com
- **Arthur D. Little** — `https://www.adlittle.com/tr-en/about-us/locations/istanbul` — login-to-apply — strategy, digital & operational-transformation consulting, İstanbul (İş Kuleleri, Levent); Consultant, Business Analyst; email: none found
- **Simon-Kucher** — `https://www.simon-kucher.com/en/careers` — open — strategy, pricing & growth/commercial consulting, İstanbul (Özdilek River Plaza, Şişli); Consultant, Analyst; email: recruitment.turkey@simon-kucher.com
- **Strategy& (PwC)** — `https://www.strategyand.pwc.com/tr/en/kariyer.html` — login-to-apply — strategy consulting (PwC strategy arm, distinct careers page), İstanbul; Consultant, Analyst; email: none found
- **OC&C Strategy Consultants** — `https://careers.occstrategy.com/vacancies/vacancy-search-results.aspx` — open — boutique strategy consulting (İstanbul office via Teknort), İstanbul (Maslak); Associate Consultant – Strategy/Analytics; email: none found
- **Egon Zehnder** — `https://www.egonzehnder.com/office/istanbul` — restricted — executive search & leadership advisory/consulting, İstanbul (Akaretler, Beşiktaş); Consultant, Associate; email: eziistanbul@egonzehnder.com
- **Korn Ferry** — `https://www.kornferry.com/about-us/global-offices/istanbul` — login-to-apply — org strategy, leadership & talent consulting + exec search, İstanbul; Consultant, Associate, Analyst; email: none found
- **Heidrick & Struggles** — `https://www.heidrick.com/en/careers` — login-to-apply — executive search & leadership/organization consulting, İstanbul (Park Maya); Engagement Leader, Senior Associate; email: none found
- **Spencer Stuart** — `https://www.spencerstuart.com/locations/istanbul` — restricted — executive search & leadership/strategic-transformation advisory, İstanbul; Consultant, Associate; email: none found
- **Russell Reynolds Associates** — `https://www.russellreynolds.com/en/locations/turkey/istanbul` — restricted — leadership advisory & executive search, İstanbul; Consultant, Associate; email: none found
- **Stanton Chase** — `https://www.stantonchase.com/office/executive-search-firm-in-istanbul-turkey` — restricted — executive search & leadership consulting, İstanbul; Consultant, Researcher; email: istanbul@stantonchase.com
- **Odgers** — `https://www.odgers.com/en-us/about-us/locations/europe/turkey/` — restricted — executive search, assessment & human-capital consulting, İstanbul; Consultant, Researcher; email: contact@odgers.com.tr (general)
- **Mercer Türkiye** — `https://www.mercer.com/tr-tr/careers/mercer-careers/` (CXS `https://mmc.wd1.myworkdayjobs.com/wday/cxs/mmc/MMC/jobs`, shared Marsh McLennan board) — open — human-capital / org & rewards consulting (Marsh McLennan), İstanbul; Consultant, Analyst; email: none found
- **WTW (Willis Towers Watson) Türkiye** — `https://careers.wtwco.com/` — open — HR, rewards, risk & actuarial advisory/consulting, İstanbul (Astoria, Şişli); Analyst, Consultant, Actuary; email: none found
- **Aon Türkiye** — `https://jobs.aon.com/jobs` — open — risk, retirement & human-capital advisory/consulting, İstanbul; Associate Director, Analyst, Intern; email: none found
- **ARGE Danışmanlık (ARGE Consulting)** — `https://arge.com/en/` — restricted — local Turkish management/strategy & governance consulting, İstanbul; Consultant, Analyst; email: info@arge.com (general)

### BPO & call centers
- **AssisTT** — `https://www.assisttkariyerim.com/` — open — BPO/contact-center (Türk Telekom subsidiary), İstanbul HQ + 27 sites nationwide; WFM/Quality/Reporting analysts, team leads, ops & project managers; email: kurumsaliletisim@assistt.com.tr (general)
- **Teleperformance Türkiye** — `https://myjobteleperformance.com/` — open — global CX/BPO outsourcer, İstanbul + 7 cities; PM, BI/Data Analyst, WFM/Quality analysts, ops leads; email: none found
- **Concentrix Türkiye (incl. former Webhelp)** — `https://jobs.concentrix.com/turkey/tr/is-ara/` — open — global CX/BPO, İstanbul (Kağıthane) + 6 cities; PM, Business/Data Analyst, WFM/Quality/Reporting, team leads; email: none found
- **Konecta Türkiye (formerly Comdata; incl. Callus)** — `https://www.konecta-group.com/tr/careers` — open — global customer-management BPO, İstanbul (Ümraniye) + multiple cities; ops managers, WFM/Quality/Reporting analysts, team leads; email: iletisim@konecta.com (general)
- **Foundever Türkiye** — `https://jobs.foundever.com/go/Jobs-in-T%C3%BCrkiye/9268600/` — open — global CX/BPO (multilingual hubs), İstanbul (Beşiktaş); customer-ops, team leads, WFM/Quality analysts; email: none found
- **Mplus Türkiye (formerly CMC)** — `https://www.kariyer.net/firma-profil/m-plus-2093-12001` — login-to-apply — independent BPO/CX & consulting, İstanbul (Kağıthane) + 6 sites; Data/BI analysts, ops & project managers, WFM/Quality, team leads; email: info@mplusgroup.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tempo Çağrı Merkezi (Tempo BPO)** — `https://www.kariyer.net/firma-profil/tempo-cagri-merkezi-ve-is-surecleri-dis-kaynak-hiz-22416-224473` — login-to-apply — BPO/CX outsourcer, İstanbul + 4 cities; ops/team-lead, reporting & quality analysts; email: info@tempobpo.com (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Atos Müşteri Hizmetleri** — `https://www.kariyer.net/firma-profil/atos-musteri-customer-services-206801-237636` — login-to-apply — BPO contact-center (finance-focused, multilingual), İstanbul + Ordu + Düzce; ops, WFM/Quality/Reporting analysts, team leads; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **VANAD Engage Turkey** — `https://www.kariyer.net/firma-profil/vanad-engage-turkey-musteri-hizmetleri-anonim-sirk-371657-429182` — login-to-apply — CX/customer-service outsourcer (Dutch-market focus), İstanbul (Maltepe); team leads, quality/reporting analysts; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **ETB Support Solutions** — `https://etb-group.com/en/career/` — open — Dutch/Benelux-market contact-center BPO, İstanbul (Maltepe & Bahçelievler) + multiple cities; ops, team leads, quality analysts; email: s.yilmaz@etb-group.com
- **Callpex Çağrı Merkezi** — `https://www.kariyer.net/firma-profil/callpex-cagri-merkezi-ve-musteri-hizmetleri-a-s-25591-17127` — login-to-apply — contact-center outsourcer, İstanbul + other sites; operations manager, team leads, reporting/quality; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Procat** — `https://www.kariyer.net/firma-profil/procat-18824-9685` — login-to-apply — turnkey contact-center/BPO (setup, reporting & quality), İstanbul/İzmir/Ankara/Antalya; team leads, reporting/quality analysts, ops; email: info@procat.com.tr (general) (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Pusula Call Center** — `https://www.kariyer.net/firma-profil/pusula-call-center-13036-3322` — login-to-apply — contact-center outsourcer (public & private sector, multilingual), İstanbul + 3 locations; team leads, quality/reporting analysts, ops; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Çözüm İletişim ve Müşteri Hizmetleri** — `https://www.kariyer.net/firma-profil/cozum-iletisim-ve-musteri-hizmetleri-42017-37585` — login-to-apply — call-center/customer-services outsourcer, İstanbul/Ankara; customer-ops, team leads, reporting/quality; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

## 6. Consulting, Big 4 & multinationals
- **PwC Türkiye** — Workday `https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers` and `/Global_Campus_Careers` — open (CXS JSON).
- **Deloitte** — `https://apply.deloitte.com/en_US/careers/SearchJobs` (filter Turkey/Istanbul) — open.
- **EY** — `https://careers.ey.com/ey/search/?q=&locationsearch=Istanbul` (SuccessFactors) — open — Junior Data Analyst, Consulting New Grad confirmed.
- **KPMG Türkiye** — `https://kpmg.com/tr/en/home/careers.html` + Kariyer.net — open.
- **Accenture Turkey** — Workday `https://accenture.wd103.myworkdayjobs.com/AccentureCareers` — open (Data & AI).
- **McKinsey** — `https://www.mckinsey.com/careers/search-jobs` (office=Istanbul) — open — Business Analyst, Data Scientist confirmed.
- **Microsoft** — `https://careers.microsoft.com/v2/global/en/locations/istanbul.html` (SPA/API) — open — Business Program Manager.
- **IBM** — `https://www.ibm.com/careers/search` (filter Turkey) + `https://www.ibm.com/tr-tr/employment/` — open.
- **SAP** — `https://jobs.sap.com/search/?q=&locationsearch=Istanbul` (SuccessFactors, site 34700) — open — BI/consultant roles.
- **Amazon** — `https://www.amazon.jobs/en/locations/istanbul-turkey` (search.json `?loc_query=Istanbul` / `normalized_country_code=TUR`) — open.

## 7. Airlines, logistics, energy & industrial
- **Turkish Airlines** — `https://careers.turkishairlines.com/en-US/vacant-positions` (apply `apply.turkishairlines.com`) — open browse.
- **Turkish Technology** (THY IT/data arm) — `https://careers.turkishtechnology.com/` (`/data-analyst.html`) — open — best THY entity for Data/BI/DS (poll; sometimes empty).
- **Pegasus** — `https://flypgs.peoplebox.biz/web/open-positions?...` (PeopleBox; intermittently empty) + LinkedIn `company/pegasus-airlines/jobs` — open / login.
- **MNG Kargo → DHL eCommerce Türkiye** — Kariyer.net `firma-profil/dhl-ecommerce-turkiye-5754-30637` + DHL global `https://careers.dhl.com/eu/tr/agp/jobs-in-istanbul-turkey` — open.
- **Aras Kargo** — Kariyer.net `firma-profil/aras-kargo-3079-40011` (no own board; `kariyer@araskargo.com.tr`) — open via board.
- **Tüpraş** — `https://kariyer.tupras.com.tr/` + Kariyer.net `firma-profil/tupras-12834-3100` — open.
- **Aygaz** (Koç) — `https://kurumsal.aygaz.com.tr/kurumsal/acik-pozisyonlar` → Koç Kariyerim — open.
- **Ford Otosan** (Koç) — Koç Kariyerim `companies/ford-otosan-is-ilanlari` + `https://fordotosan.onenewone.com/` — open.
- **Tofaş** (Koç/Stellantis) — Koç Kariyerim + Kariyer.net `firma-profil/tofas-1006-66` — open.

## 7b. Manufacturing, industrial & energy expansion — 2026-06-17 (batch JAC-36): 222 verified companies
NEW companies (no overlap with the base entries or sections 3b/4b above), Istanbul-HQ and Marmara/Aegean/Anatolian industrial zones, fit for the Project Manager / Data Analyst / BI / Business Analyst cluster (plus production/demand/supply-chain planner, process/quality analyst, ERP-SAP analyst, financial analyst). Many large industrials route through SuccessFactors/Workday tenants or Kariyer.net firma-profil pages. State energy/mining/defense entities recruit via exam / Kariyer Kapısı and are marked `restricted`; defense manufacturers are realistic only for Turkish-national applicants.

### Automotive OEMs & suppliers
- **Toyota Otomotiv Sanayi Türkiye** — `https://www.toyotatr.com/acik-pozisyonlar` (Kariyer.net `firma-profil/toyota-otomotiv-sanayi-turkiye-a-s-1048-66594`) — open — Sakarya/Adapazarı plant; production/supply-chain/demand planner, process/quality, PM/BI; email: none found
- **BMC Otomotiv** — `https://www.bmc.com.tr/kurumsal/insan-kaynaklari` — open — İzmir + Sakarya; commercial & defense vehicles; procurement/supply-chain, process/quality, PM, financial analyst; email: ik@bmc.com.tr
- **Karsan** — `https://www.karsan.com/en-us/corporate/careers` (Kariyer.net `firma-profil/karsan-otomotiv-san-ve-tic-a-s-3534-27847`) — login-to-apply — Akçalar/Bursa; bus/commercial-vehicle & autonomous-EV; PM, BI/data, supply-chain/production planning, ERP-SAP, financial analyst; email: none found
- **Temsa** — `https://live.peoplise.com/temsa/career` (Peoplise) — login-to-apply — Adana + İstanbul; bus/coach/light-truck; production/process eng, quality, supply-chain, PM, BI/analyst; email: none found
- **Anadolu Isuzu** — `https://anadoluisuzu.com.tr/hakkimizda/ik-politikasi` (Anadolu Kariyerim + Kariyer.net `firma-profil/anadolu-isuzu-otomotiv-sanayi-ve-tic-a-s-1064-3854`) — login-to-apply — Şekerpınar/Kocaeli; trucks/buses; BI/data, supply-chain, process/quality, PM, financial analyst; email: none found
- **Türk Traktör (Koç)** — `https://www.kockariyerim.com/companies/turk-traktör-is-ilanları` — login-to-apply — Ankara (Sincan) & Sakarya; PM, BI/data, supply-chain/production planning, process/quality, ERP-SAP, financial analyst; email: none found
- **Hema Endüstri (Hattat Holding)** — `https://www.kariyer.net/firma-profil/hema-endustri-a-s-3114-23227` — login-to-apply — Çerkezköy/Tekirdağ; tractors + hydraulic components; production/process planning, quality, supply-chain, ERP-SAP, financial/PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Erkunt Traktör** — `https://www.kariyer.net/firma-profil/erkunt-traktor-sanayii-a-s-4764-37409` — login-to-apply — Sincan OSB/Ankara; tractors; production planning, process/quality, supply-chain, PM, ERP-SAP, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Hidromek** — `https://www.hidromek.com/tr-tr/insan-kaynaklari/` — login-to-apply — Sincan/Ankara; construction machinery/excavators; PM, BI/data, supply-chain/production planning, process/quality, ERP-SAP, financial analyst; email: ik@hidromek.com.tr
- **Bozankaya** — `https://www.bozankaya.com.tr/` (Kariyer.net `firma-profil/bozankaya-rayli-sistemler-anonim-sirketi-6137-209890`) — login-to-apply — Sincan/Ankara; electric buses/trolleybuses/rail; PM, BI/data, supply-chain/production planning, process/quality, ERP-SAP, financial analyst; email: none found
- **Tırsan Treyler / Kässbohrer** — `https://kaessbohrer.com/en/vacancies-527-pg` (Kariyer.net `firma-profil/tirsan-sirketler-grubu-2354-14871`) — open — Adapazarı/Sakarya; trailers; supply-chain/production planning, process/quality, PM, BI/data, ERP-SAP, financial analyst; email: none found
- **Bosch Türkiye** — `https://jobs.bosch.com/en/` (filter Turkey) — login-to-apply — Bursa + İstanbul; PM, demand/production planner, SAP/ERP analyst, BI/data, financial analyst; email: none found
- **Valeo Türkiye** — `https://www.valeo.com/en/turkiye/` (Kariyer.net `firma-profil/valeo-otomotiv-sanayi-ve-ticaret-as-1301-3293`) — login-to-apply — R&D center, Bursa/İstanbul; supply-chain, quality, process, planning, BI/analyst; email: none found
- **Marelli Mako (Mako Elektrik)** — `https://www.kariyer.net/firma-profil/marelli-mako-turkey-elektrik-sanayi-ve-ticaret-a-s-6376-31257` — login-to-apply — automotive lighting/electronics; process/quality analyst, supply-chain, ERP analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Farplas** — `https://www.farplas.com/people/job-openings/` — open — injection-molded interior parts, Gebze/Kocaeli; supply-chain, purchasing, quality/process analyst; email: none found
- **Coşkunöz Holding** — `https://careers.coskunoz.com.tr/` (SAP SuccessFactors) — login-to-apply — Bursa; production planning & logistics, procurement, finance, lean & digital; production/demand planner, BI, financial/process analyst, PM; email: none found
- **Martur Fompak International** — `https://careers.marturfompak.com/` — login-to-apply — seats/interiors, Bursa; demand/inventory planner, supply-chain, data/BI, quality analyst; email: none found
- **Teklas Kauçuk** — `https://www.kariyer.net/firma-profil/teklas-kaucuk-1608-6669` — login-to-apply — rubber parts, Gebze/Kocaeli + Bartın; supply-chain, ERP/IT analyst, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Standard Profil** — `https://www.standardprofil.com/tr/kariyer/sp-de-is-hayati` (Kariyer.net `firma-profil/standard-profil-otomotiv-sanayi-ve-ticaret-a-s-3792-225024`) — login-to-apply — sealing systems; Düzce & Manisa, İstanbul HQ; PM, planner, BI/reporting, financial/process analyst; email: none found
- **Maxion İnci Jant (Maxion Wheels Turkey)** — `https://www.maxionwheelsturkey.com/en/career/career-opportunities` — login-to-apply — steel/alloy wheels, Manisa + İzmir; production/demand planner, quality/process analyst, SAP analyst, financial analyst; email: none found
- **Cevher Jant** — `https://www.kariyer.net/firma-profil/cevher-jant-sanayi-a-s-164621-89470` — login-to-apply — light-alloy wheels, İzmir; quality/process analyst, planning, supply-chain; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Ditaş Doğan** — `https://www.ditas.com.tr/insan-kaynaklari-ditas-ta-is-firsatlari` (Kariyer.net `firma-profil/ditas-dogan-yedek-parca-imalat-ve-teknik-a-s-55105-45093`) — restricted — steering/suspension parts, Niğde; quality/process, production planner, financial analyst; email: kariyer@ditas.com.tr
- **Norm Holding / Norm Fasteners** — `https://normfasteners.com/kariyer/acik-pozisyonlar/` (Peoplise `live.peoplise.com/normholding/career`) — login-to-apply — fasteners, İzmir & Salihli; production/demand planner, ERP-SAP analyst, BI/data analyst, process/quality analyst, PM; email: info@normfasteners.com
- **Ege Endüstri** — `https://egeendustri.net/en/career` (Kariyer.net `firma-profil/ege-endustri-ve-ticaret-a-s-18293-230544`) — login-to-apply — commercial-vehicle axles/suspension, İzmir; BIST-listed; supply-chain/production planner, quality/process analyst, financial analyst, PM; email: info@egeendustri.net
- **MAHLE Türkiye** — `https://careers.mahle.com/?optionsFacetsDD_country=TR&locale=en_US` — login-to-apply — engine components/filtration; İzmir HQ + Gebze; SAP/ERP analyst, demand/supply planner, BI/data analyst, PM; email: recruiting.turkey@mahle.com
- **Schaeffler Türkiye** — `https://www.schaeffler.com.tr/en/careers/job-search/jobs-overview/index.jsp` (global `jobs.schaeffler.com`) — login-to-apply — bearings/precision components; business analyst, Six Sigma/process analyst, BI/data analyst, PM, supply-chain planner; email: none found
- **ZF Türkiye** — `https://jobs.zf.com/?locale=tr_TR` — login-to-apply — driveline/chassis; İstanbul, İzmir, Gebze; quality/process analyst, production planner, PM, BI/data analyst; email: none found
- **Marelli Türkiye (ex-Magneti Marelli)** — `https://jobs.marelli.com/` — login-to-apply — lighting/electronics/powertrain; İstanbul; PM, business/data analyst, supply-chain planner; email: none found
- **Maysan Mando** — `https://maysanmando.com/insan-kaynaklari/` (Kariyer.net `firma-profil/maysan-mando-3868-28751`) — login-to-apply — shock absorbers/suspension, Bursa; ERP/IT-SAP analyst, business analyst, demand/production planner, PM, financial analyst; email: none found
- **Federal-Mogul / Tenneco Türkiye** — `https://jobs.tenneco.com/` — login-to-apply — pistons/powertrain; İzmit, Sapanca, Arslanbey; production/supply planner, quality analyst, SAP/ERP analyst, financial analyst, PM; email: none found
- **Componenta Döktaş** — `https://www.kariyer.net/firma-profil/doktas-dokumculuk-tic-ve-san-a-s-4121-29004` — login-to-apply — iron casting/machining, Bursa & Manisa; production/demand planner, quality/process analyst, supply-chain analyst, PM, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Çukurova Ziraat** — `https://cukurovaziraat.com.tr/kariyer/` (Kariyer.net `firma-profil/cukurova-ziraat-end-ve-tic-a-s-6167-31048`) — login-to-apply — construction/material-handling machinery; Kartal/İstanbul + Adana/İzmir/Ankara; supply-chain/production planner, business/data analyst, PM, financial analyst; email: none found

### Chemicals & petrochemicals
- **Petkim / SOCAR Türkiye** — `https://careers.socar.com.tr/` — login-to-apply — petrochemicals, İzmir/Aliağa + İstanbul HQ; process/production planner, quality analyst, ERP-SAP, BI/data, supply-chain, PM; email: none found
- **Aksa Akrilik (Akkök)** — `https://www.aksa.com/insan-kaynaklari/aksada-kariyer/kariyer-firsatlari` — open — acrylic fiber, Yalova; production/process engineer, planning, procurement, quality, financial analyst; email: none found
- **SASA Polyester** — `https://www.sasa.com.tr/kariyer` — open — polyester/PTA, Adana; production/process, planning, quality, SAP, financial analyst; email: none found
- **Bagfaş (Bandırma Gübre)** — `https://www.bagfas.com.tr/IsFirsatlari.aspx` — open — fertilizer/chemicals, Bandırma/Balıkesir; procurement, planning, maintenance/process, sales engineer; email: ik@bagfas.com.tr
- **Gübretaş** — `https://www.gubretas.com.tr/tr/kariyer` — open — fertilizer, İstanbul HQ + Yarımca/İskenderun; supply-chain, demand/production planner, financial/BI analyst; email: none found
- **Toros Tarım (Tekfen)** — `https://www.toros.com.tr/tr/toros-kurumsal/kariyer/kariyer-olanaklari` — open — fertilizer/agri, İstanbul HQ + Ceyhan/Samsun/Mersin; PM, data/BI, supply-chain, financial analyst; email: none found
- **İGSAŞ (Yıldızlar Holding)** — `https://www.kariyer.net/firma-profil/istanbul-gubre-sanayi-a-s-igsas-11704-49333` — open — fertilizer, Körfez/Kocaeli; production planner, process/quality, marketing analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Soda Sanayii (Şişecam, Mersin)** — `https://careers.sisecam.com/` (`sisecamkariyerim.com/tr`) — login-to-apply — soda ash & chromium chemicals, Mersin; process/quality analyst, production planner, SAP, BI; email: none found
- **Akkim Kimya (Akkök)** — `https://www.kariyer.net/firma-profil/akkim-kimya-san-ve-tic-a-s-1592-6493` — open — specialty chemicals, Yalova + Aydın; process/production, planning, procurement, R&D regulatory, quality; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **DYO Boya (Yaşar Holding)** — `https://kariyer.yasar.com.tr/` — open — paints/coatings, İzmir + Dilovası; production/process, R&D, planning, sales/marketing analyst; email: none found
- **Polisan Holding** — `https://www.kariyer.net/firma-profil/polisan-holding-a-s-5654-30537` — open — chemicals/paint/port, Dilovası/Kocaeli + İstanbul HQ; BIST-listed; production planner, process/quality, financial/BI analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Polisan Kansai Boya (Marshall)** — `https://www.kariyer.net/firma-profil/polisan-kansai-boya-sanayi-ve-ticaret-anonim-sirke-240526-275522` — open — decorative/industrial paint, Dilovası/Kocaeli; sales analyst, production, HR, planning; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Betek Boya (Filli Boya, DAW)** — `https://www.kariyer.net/firma-profil/betek-boya-ve-kimya-san-a-s-4094-225412` — open — paints/construction chemicals, Gebze + Balıkesir; production, R&D, HR, sales/marketing analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kansai Altan Boya** — `https://www.kariyer.net/firma-profil/kansai-altan-boya-sanayi-ve-tic-a-s-1535-42477` — open — paints/coatings & polymer, İzmir; procurement, production planner, process/quality, ERP/IT; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Organik Kimya** — `https://www.kariyer.net/firma-profil/organik-kimya-1579-6350` — open — polymer emulsions/adhesives, İstanbul; production/process planner, R&D, demand/supply planning; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kordsa (Sabancı)** — `https://kordsa.com/career` — login-to-apply — industrial reinforcement/composites, İzmit/Kocaeli + global; PM, supply-chain, process/quality, BI/data, financial analyst; email: none found
- **Alkim (Alkim Alkali Kimya)** — `https://www.kariyer.net/firma-profil/alkim-alkali-kimya-a-s-18409-9229` — open — inorganic chemicals, BIST-listed, İstanbul HQ + İzmir; process/quality, production planner, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Hektaş (OYAK)** — `https://hektas.com.tr/insan-kaynaklari/kariyer` — open — crop-protection/agrochemicals & seeds, Gebze/Kocaeli; PM, supply-chain/demand planner, process/quality, BI/data, financial analyst; email: none found
- **BASF Türkiye** — `https://basf.jobs/?locale=tr_TR` — login-to-apply — chemicals, İstanbul HQ + Gebze/Çerkezköy; supply-chain, procurement/logistics, sales/marketing, finance, HR analyst; email: none found
- **Dow Türkiye** — `https://corporate.dow.com/en-us/careers/jobs.html` — login-to-apply — chemicals/materials, İstanbul + Gebze/Kocaeli; supply-chain, process, commercial/BI, finance analyst; email: none found
- **Bayer Türkiye** — `https://www.bayer.com.tr/tr/kariyer` (global `talent.bayer.com/careers`) — login-to-apply — pharma + crop science, İstanbul HQ; supply-chain, demand planner, data/BI, finance, PM; email: none found

### Cement & construction materials
- **Akçansa (Sabancı/Heidelberg)** — `https://www.sabanci.com/en/career` — login-to-apply — cement, İstanbul + Çanakkale/Ladik; PM, production/process planner, quality, BI/data, financial analyst; email: none found
- **Çimsa (Sabancı)** — `https://cimsakariyerim.com/en/home/` — login-to-apply — cement & building materials, Mersin HQ + Eskişehir/Afyon; production/process planner, quality, supply-chain, ERP-SAP, financial analyst; email: none found
- **OYAK Çimento** — `https://kariyer.oyakcimento.com/` — login-to-apply — cement group, multi-city; PM, production planner, process/quality, BI/data, SAP, financial analyst; email: none found
- **Ünye Çimento (OYAK)** — `https://www.kariyer.net/firma-profil/unye-cimento-sanayii-ve-ticaret-a-s-4479-233402` — open — cement, Ünye/Ordu; BIST (UNYEC); production planner, process/quality, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Limak Çimento** — `https://www.limakcimento.com/kariyer` — open — cement (11 plants), Ankara HQ + Şanlıurfa/Gaziantep; PM, production planner, process/quality, supply-chain, financial/BI analyst; email: none found
- **Nuh Çimento** — `https://www.nuhcimento.com.tr/` — open — cement & clinker, Körfez/Kocaeli; BIST-listed; production planner, process/quality, maintenance, financial analyst; email: none found
- **Aşkale Çimento** — `https://www.askalecimento.com.tr/kariyer` — open — cement (Erzurum + Gümüşhane/Van/Samsun); production planner, process/quality, financial analyst; email: none found
- **Bursa Çimento** — `https://www.bursacimento.com.tr/insan-kaynaklari` — open — cement, Kestel/Bursa; BIST-listed; production planner, process/quality, financial analyst; email: none found
- **Göltaş Çimento** — `https://www.kariyer.net/firma-profil/goltas-goller-bolgesi-cimento-san-ve-tic-a-s-3958-28841` — open — cement, Isparta; BIST-listed; production/planning, process/quality, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Konya Çimento** — `https://www.kariyer.net/firma-profil/konya-cimento-3949-28832` — open — cement, Konya; production planner, process/quality, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Çimko Çimento (Sanko)** — `https://www.kariyer.net/firma-profil/cimko-cimento-ve-beton-sanayi-ticaret-anonim-sirke-30729-233329` — open — cement & concrete, Gaziantep/Adıyaman; production planner, process/quality, supply-chain, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Votorantim Çimento Türkiye** — `https://www.votorantimcimentos.com.tr/kariyer/` — open — cement/concrete/aggregates, Ankara HQ + Sivas/Yozgat; PM, production/demand planner, process/quality, finance/BI analyst; email: none found
- **Batıçim (Batı Anadolu Çimento)** — `https://www.batianadolu.com/insan-kaynaklari/kariyer` — open — cement & ready-mix, İzmir; BIST-listed; production planner, process/quality, maintenance, financial analyst; email: none found
- **Batısöke Çimento** — `https://www.batisoke.com.tr/` (HR via `batianadolu.com`) — open — cement, Söke/Aydın; BIST-listed; production planner, process/quality, financial analyst; email: none found
- **Kütahya Seramik (NG Holding)** — `https://www.kariyer.net/firma-profil/ng-kutahya-seramik-porselen-turizm-a-s-2061-225002` — open — ceramic tiles & porcelain, Kütahya; production planner, process/quality, ERP-SAP, BI/data, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **VitrA / Eczacıbaşı Yapı (EYAP)** — `https://eczacibasikariyer.com.tr/is-ilanlari` — login-to-apply — ceramic sanitaryware & tiles (VitrA, Artema), Bilecik + İstanbul HQ; PM, supply-chain/demand planner, process/quality, BI/data, SAP, financial analyst; email: none found
- **Kaleseramik (Kale Grubu)** — `https://www.kariyer.net/firma-profil/kaleseramik-canakkale-kalebodur-seramik-san-a-s-13432-185885` — open — ceramic tiles & sanitaryware, Çanakkale + İstanbul HQ; PM, production/process planner, quality, BI/data, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Ege Seramik** — `https://www.egeseramik.com/kurumsal/is-basvuru-formu` — open — ceramic tiles, İzmir; BIST-listed; procurement, production planner, process/quality; email: none found
- **Seranit** — `https://www.kariyer.net/firma-profil/seranit-granit-seramik-2573-42374` — open — technical porcelain tiles, Eskişehir + İstanbul HQ; production planner, process/quality, sales analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Yurtbay Seramik** — `https://www.yurtbayseramik.com/en/career` — open — ceramic tiles, Zonguldak; production planner, process/quality, IT/ERP, HR, BI; email: none found
- **İzocam** — `https://www.izocam.com.tr/tr/izocamda-kariyer` — open — insulation, Gebze/Tarsus/Eskişehir + İstanbul HQ; production planner, process/quality, supply-chain, financial analyst; email: none found
- **Knauf Türkiye** — `https://career.knauf.com/jobs?country=Türkiye` — login-to-apply — gypsum boards & insulation, Ankara HQ + İzmit/Çorlu/Bilecik; PM, production planner, process/quality, supply-chain, people analyst; email: info.tr@knaufinsulation.com
- **AKG Gazbeton** — `https://www.kariyer.net/firma-profil/akg-yalitim-ve-insaat-malzemeleri-sanayi-ve-tic-15478-6008` — open — aerated concrete & Çimstone, İzmir + Kırıkkale/Çorlu; production planner, process/quality, procurement, R&D lab; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Iron, steel & metals
- **Ereğli Demir Çelik (Erdemir, OYAK)** — `https://www.erdemir.com.tr/kariyer/kariyer-olanaklari` (Kariyer.net `firma-profil/eregli-demir-celik-fab-t-a-s-4685-29568`) — open — largest flat-steel producer, Ereğli/Zonguldak; planning specialist, supply-chain/production planner, process/quality analyst, business-development engineer, financial analyst; email: none found
- **İsdemir (OYAK)** — `https://www.isdemir.com.tr/kariyer/kariyer-olanaklari` (Kariyer.net `firma-profil/isdemir-4685-46159`) — open — integrated long-products mill, İskenderun/Hatay; production/demand planner, quality/process analyst, ERP-SAP analyst; email: none found
- **Kardemir** — `https://www.kardemir.com/basvurular` (Kariyer.net `firma-profil/kardemir-karabuk-demir-celik-34950-27419`) — open — integrated mill, Karabük; production planner, process/quality analyst, BI/data analyst; email: none found
- **Çolakoğlu Metalurji** — `https://www.colakoglu.com.tr/kariyer/kariyer-olanaklari` (Kariyer.net `firma-profil/colakoglu-metalurji-a-s-12863-225206`) — open — flat/long steel, Gebze-Dilovası/Kocaeli; supply-chain/demand planner, process analyst, financial analyst; email: none found
- **İçdaş Çelik** — `https://www.icdas.com.tr/pages/5766/687/f/tr-TR/is_Basvurusu.aspx` (Kariyer.net `firma-profil/icdas-celik-enerji-tersane-ve-ulasim-san-a-s-1883-9691`) — open — integrated steel/energy/port, Çanakkale & İstanbul; PM, process/quality analyst, financial/internal-audit analyst, ERP analyst; email: none found
- **Tosyalı Holding / Tosçelik** — `https://career2.successfactors.eu/career?company=tosyalihol` (SuccessFactors token `tosyalihol`) — login-to-apply — global steel group, İskenderun/Osmaniye; PM, supply-chain/production planner, ERP-SAP analyst, BI/data analyst, financial analyst; email: none found
- **Habaş** — `https://www.habas.com.tr/tr/kariyer` (Kariyer.net `firma-profil/habas-sinai-ve-tibbi-gazlar-istihsal-endustri-a-s-65018-140202`) — open — steel + industrial/medical gas, Aliağa/İzmir; industrial engineer, process/quality analyst, planner; email: none found
- **Diler Demir Çelik** — `https://www.kariyer.net/firma-profil/diler-demir-celik-endustri-ve-tic-a-s-8833-98855` — open — long products, Dilovası/Kocaeli; process/quality analyst, lab/production; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Kroman Çelik** — `https://www.kariyer.net/firma-profil/kroman-celik-sanayii-a-s-22545-201116` — open — structural/long & automotive steel, Darıca/Kocaeli; sales/supply-chain analyst, quality analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Ekinciler Demir Çelik** — `https://www.kariyer.net/firma-profil/ekinciler-demircelik-15575-6115` — open — long steel, İskenderun/Hatay; export/sales analyst, mechanical/production; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Çemtaş Çelik Makina** — `https://www.kariyer.net/firma-profil/cemtas-celik-makina-sanayi-ve-ticaret-a-s-6179-31060` — open — special long steel, Bursa OSB; BIST-listed; process/quality analyst, production planner, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Asil Çelik** — `https://www.kariyer.net/firma-profil/asil-celik-sanayi-ve-ticaret-anonim-sirketi-8921-33799` — open — special steel, Orhangazi/Bursa; procurement/supply-chain analyst, quality analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Sarkuysan** — `https://www.sarkuysan.com.tr/kariyer/` — open — largest copper producer, Gebze/Darıca; production/supply-chain planner, process/quality analyst, financial analyst; email: none found
- **Assan Alüminyum (Kibar Holding)** — `https://www.assanaluminyum.com/en/kariyer/assan-aluminyum-da-kariyer` (Kariyer.net `firma-profil/assan-aluminyum-1227-45657`) — open — flat-rolled aluminum, Dilovası/Kocaeli & Tuzla; supply-chain/demand planner, BI/data analyst, ERP-SAP analyst, PM; email: none found
- **Asaş Alüminyum** — `https://www.kariyer.net/firma-profil/asas-2245-70844` — open — aluminum extrusion/flat/PVC, Akyazı/Sakarya; ERP-SAP analyst, supply-chain planner, PM, data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Eti Bakır / Eti Alüminyum (Cengiz Holding)** — `https://www.etibakir.com.tr/en/kariyer` — open — copper & aluminum/mining; production/process analyst, supply-chain planner, financial analyst; email: kariyer@etigubre.com
- **MMK Metalurji** — `https://mmkturkey.com.tr/kariyer` (Kariyer.net `firma-profil/mmk-metalurji-sanayi-ticaret-ve-liman-isletmecilig-19935-10907`) — open — flat steel, Dörtyol/Hatay & Gebze/Kocaeli; production/supply-chain planner, process/quality analyst, ERP analyst; email: none found
- **Yıldız Demir Çelik (Yıldızlar Yatırım)** — `https://www.kariyer.net/firma-profil/yildiz-demir-celik-sanayi-a-s-11704-48949` — open — flat steel, Kocaeli; ERP analyst, procurement/supply-chain analyst, data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Noksel Çelik Boru** — `https://www.noksel.com/career` — open — steel pipe, İskenderun & Hendek/Sakarya, HQ Ankara; production/quality engineer-analyst, financial analyst; email: none found

### Glass & packaging
- **Şişecam (group portal — Trakya Cam, Anadolu Cam)** — `https://careers.sisecam.com/?locale=tr_TR` (Kariyer.net `firma-profil/sisecam-3653-28536`) — open — ~24,000 staff; glass/packaging arms under one portal; multiple sites; PM, BI/data analyst, business analyst, supply-chain/demand planner, ERP-SAP analyst, financial analyst; email: none found
- **Sarten Ambalaj** — `https://www.sarten.com.tr/en/hr/our-human-resources-policy/` (Kariyer.net `firma-profil/sarten-ambalaj-san-ve-tic-a-s-19054-9938`) — open — metal + plastic packaging, multi-plant; production planner, process/quality analyst, sales/financial analyst; email: none found
- **Korozo (Korozo Group)** — `https://www.korozogroup.com/about/careers/` (Kariyer.net `firma-profil/korozo-ambalaj-san-ve-tic-a-s-2706-18742`) — open — flexible packaging, İstanbul HQ; financial/credit analyst, procurement/supply-chain analyst, PM, data analyst; email: none found
- **Bak Ambalaj (Bakioğlu Holding)** — `https://www.bakambalaj.com.tr/kariyer-olanaklari.aspx` (Kariyer.net `firma-profil/bak-ambalaj-san-ve-tic-a-s-3246-424552`) — open — flexible packaging, İzmir; BIST-listed; maintenance/quality analyst, production planner; email: basvuru@bakambalaj.com.tr
- **Polibak (Bakioğlu Holding)** — `https://www.polibak.com.tr/genel-basvuru.aspx` (Kariyer.net `firma-profil/polibak-plastik-san-ve-tic-a-s-3246-431101`) — open — BOPP/CPP film, İzmir; production planner, quality analyst; email: basvuru@polibak.com.tr
- **Elif Plastik Ambalaj (Huhtamaki)** — `https://www.kariyer.net/firma-profil/elif-plastik-ambalaj-san-ve-tic-a-s-2698-225731` — open — flexible packaging, Esenyurt/İstanbul; accounting/financial analyst, technical/production, supply-chain analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Duran Doğan Basım ve Ambalaj** — `https://www.kariyer.net/firma-profil/duran-dogan-basim-ve-ambalaj-san-a-s-2997-21940` — open — folding-carton packaging, İstanbul; financial/tax analyst, export/sales analyst, production planner; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Sun Chemical Türkiye (DIC Group)** — `https://www.kariyer.net/firma-profil/sun-chemical-matbaa-murekkepleri-san-tic-a-s-7378-32256` — open — printing inks/pigments, İzmir; process/quality analyst, supply-chain analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tetra Pak Türkiye** — `https://jobs.tetrapak.com/` — login-to-apply — carton packaging multinational, İstanbul; PM, supply-chain/demand planner, BI/data analyst, process analyst; email: none found
- **Sealed Air Türkiye** — `https://jobs.sealedair.com/` — login-to-apply — protective/food packaging multinational; supply-chain analyst, PM, process analyst; email: none found
- **Crown Bevcan Türkiye (Crown Holdings)** — `https://crownholdings.wd501.myworkdayjobs.com/CrownHoldings` (Workday) — login-to-apply — aluminum beverage-can maker, İzmit/Kocaeli; production planner, process/quality analyst, supply-chain analyst; email: none found

### Tires & rubber
- **Brisa (Bridgestone–Sabancı)** — `https://www.kariyer.net/firma-profil/brisa-bridgestone-sabanci-lastik-sanayi-ve-ticaret-1013-225407` — open — tire-industry leader, İzmit/Kocaeli & Aksaray, R&D İzmit; PM, BI/data analyst, supply-chain/demand planner, process/quality analyst, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Goodyear Lastikleri Türk** — `https://jobs.goodyear.com/` (Kariyer.net `firma-profil/goodyear-lastikleri-turk-a-s-1015-230229`) — login-to-apply — tire manufacturer, Adapazarı & İzmit; process/quality engineer-analyst, HR/PM, supply-chain analyst; email: none found
- **Petlas Lastik (Starmaxx)** — `https://ikportal.petlas.com.tr/` (Kariyer.net `firma-profil/petlas-6064-230819`) — open — tire manufacturer, Kırşehir; financial/accounting analyst, production planner, process/quality analyst, IT/data; email: none found
- **Pirelli Otomobil Lastikleri (Türk Pirelli)** — `https://www.kariyer.net/firma-profil/pirelli-otomobil-lastikleri-a-s-158020-225035` — open — tire manufacturer, İzmit/Kocaeli plant, HQ İstanbul; financial analyst, process/quality analyst, sales analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Özka Lastik (Kanık Group)** — `https://www.kariyer.net/firma-profil/kanik-sirketler-grubu-ozka-lastik-ve-kaucuk-san-11173-217005` — open — agricultural/industrial tire maker, Başiskele/Kocaeli; production manager/planner, process/quality analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Energy, utilities & generation
- **Enerjisa Enerji** — `https://www.enerjisa.com.tr/tr/enerjisa-hakkinda/kariyer/enerjisada-kariyer` — open — Sabancı/E.ON distribution & retail, HQ İstanbul; ENTER & ROTA grad programs; PM, data analyst, BI, financial analyst, ERP-SAP; email: none found
- **Enerjisa Üretim** — `https://www.enerjisauretim.com.tr/en/people-and-culture/our-impact-changes-the-career-journey/job-postings/` (Peoplise) — login-to-apply — largest private power generator, HQ İstanbul; PM, financial/data analyst, production planner; email: none found
- **Zorlu Enerji** — `https://www.zorluenerji.com.tr/zorlu-enerjide-hayat/kariyer-firsatlari` — open — integrated generation/distribution/EV-charging, HQ İstanbul; commercial-operations/data/financial analyst; email: none found
- **Akenerji (Akkök/ČEZ)** — `https://akkok.com.tr/en/kariyer/` (Kariyer.net `firma-profil/akenerji-elektrik-uretim-a-s-1559-233275`) — open — generation JV, HQ İstanbul; financial/process analyst; email: none found
- **Aksa Enerji (Kazancı Holding)** — `https://www.aksaenerji.com.tr/tr/insan-kaynaklari/` — open — BIST-listed IPP, HQ İstanbul; EnerjiMAXa grad program; business/process analyst; email: none found
- **Limak Enerji** — `https://www.limak.com.tr/kariyer/kariyer-firsatlari` — open — Limak energy arm (generation + distribution), HQ Ankara; PM, financial/BI analyst, supply-chain; email: none found
- **Çalık Enerji** — `https://www.calikenerji.com/kariyer` — open — Çalık EPC + power, HQ İstanbul; PM, process/quality analyst, ERP analyst; email: none found
- **Naturelgaz** — `https://naturelgaz.com/en/career/` — open — Global Yatırım Holding, BIST-listed CNG/LNG, HQ İstanbul; demand/supply-chain & logistics planner, data analyst; email: none found
- **Entek Elektrik (Koç)** — `https://www.kockariyerim.com/companies/entek.html` — login-to-apply — Koç power generation, HQ İstanbul; PM, financial/data analyst; email: none found
- **Bereket Enerji** — `https://www.bereketenerji.com.tr/` — open — multi-source generation group, HQ Denizli; ERP-SAP/business/financial analyst; email: none found
- **SOCAR Türkiye** — `https://careers.socar.com.tr/viewalljobs/` — login-to-apply — SOCAR Turkey arm (Petkim, STAR Refinery, TANAP), HQ İstanbul/İzmir; PM, data/financial/process analyst; email: none found
- **EPİAŞ (EXIST – energy exchange)** — `https://www.epias.com.tr/epias-kurumsal/kariyer/` — restricted — operates electricity/gas markets, HQ İstanbul; BI/data/financial/business analyst; email: none found
- **BOTAŞ** — `https://www.botas.gov.tr/Sayfa/personel-alimi/124` — restricted — national gas pipeline/transmission, HQ Ankara; engineer/specialist; email: none found
- **EÜAŞ** — `https://www.euas.gov.tr/kariyer-ve-staj` — restricted — national electricity generation, HQ Ankara; technician/engineer cadres; email: none found
- **TEİAŞ** — `https://www.teias.gov.tr/` — restricted — national electricity transmission, HQ Ankara; technician/engineer cadres; email: none found
- **İGDAŞ** — `https://kariyer.ibb.istanbul/` — restricted — İBB Istanbul gas distribution; ERP-SAP analyst; email: none found
- **BEDAŞ (Boğaziçi EDAŞ)** — `https://www.bedas.com.tr/kariyer-ve-yasam` — open — Istanbul-European distribution DISCO; process/data analyst; email: none found
- **SEDAŞ (Sakarya EDAŞ)** — `https://www.sedas.com` — open — distribution DISCO (Sakarya/Kocaeli/Bolu/Düzce); process/data analyst; email: none found
- **Başkent EDAŞ** — `https://www.baskentedas.com.tr/sayfa/is-ve-staj-olanaklari` — open — Ankara-region distribution DISCO (Enerjisa); data/process analyst; email: none found

### Renewables — solar & wind
- **Kalyon Enerji / Kalyon PV** — `https://www.kalyonenerji.com/en/career` (`kalyonpv.com/insan-kaynaklari`) — open — integrated solar gigafactory, Sincan/Ankara; PM, production/quality/process analyst, supply-chain planner; email: none found
- **Smart Güneş (Smart Solar Technologies)** — `https://www.kariyer.net/firma-profil/smart-gunes-enerjisi-a-s-149768-119103` — open — BIST-listed solar IPP/EPC/module maker, Gebze/Kocaeli, HQ İstanbul; PM, production/quality analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **CW Enerji** — `https://www.cwenerji.com` (Kariyer.net `firma-profil 81426-169349`) — open — BIST-listed solar-panel maker/EPC, HQ Antalya; PM, production/quality analyst; email: none found
- **HT Solar Enerji** — `https://htsolar.com.tr/kariyer/` — open — solar-module maker, Tuzla/İstanbul; process/data analyst; email: none found
- **Tekno Ray Solar** — `https://www.teknoraysolar.com.tr/insan-kaynaklari/` — open — solar-EPC; PM/project engineer; email: none found
- **Margün Enerji** — `https://www.margunenerji.com.tr/` — open — solar developer/EPC/O&M; PM, project/process; email: none found
- **Galata Wind Enerji** — `https://galatawindenerji.com/insan-kaynaklari/` — open — Doğan Holding, BIST-listed wind+solar; financial/BI/data analyst; email: none found
- **Fina Enerji (Fiba Yenilenebilir)** — `https://www.kariyer.net/firma-profil/fina-enerji-21811-231976` — open — Fiba renewables, HQ İstanbul; BI/data/business analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Polat Enerji** — `https://www.polat.com/polatta-hayat` — open — Polat Holding wind leader; energy-trading/data/financial analyst; email: none found
- **Borusan EnBW Enerji** — `https://www.borusanenbw.com.tr/kariyer` — login-to-apply — Borusan + EnBW renewables JV, HQ İstanbul; business/financial/process analyst, supply-chain; email: none found

### Oil, gas & lubricants
- **Petrol Ofisi (POAŞ)** — `https://www.petrolofisi.com.tr/en/human-resources/career-at-petrol-ofisi` — open — largest fuel/lubricant distributor, HQ İstanbul; PM, process/data/financial analyst, ERP-SAP; email: none found
- **Opet (Koç/Öztürk)** — `https://www.opet.com.tr/kariyer-imkanlari` — open — fuel distributor, HQ İstanbul; PM, data/financial analyst, supply-chain; email: none found
- **Shell & Turcas** — `https://www.shell.com.tr/kariyer.html` — open — fuel JV, HQ İstanbul; PM, data/financial/process analyst; email: none found
- **Aytemiz** — `https://www.kariyer.net/firma-profil/aytemiz-akaryakit-dagitim-a-s-24449-208831` — open — fuel distributor, HQ İstanbul; process/operational-excellence/data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **TotalEnergies Türkiye** — `https://tr.totalenergies.com/tuketici/turkiyede-total/kariyer/basvuru-portali` — login-to-apply — lubricants marketing, HQ İstanbul; data/financial/process analyst; email: none found
- **Lukoil Türkiye** — `https://www.lukoil.com.tr/56/sayfalar/lukoilde-kariyer` — open — lubricants plant İzmir + fuel retail, HQ İstanbul; demand/supply-chain planner, financial/trading analyst; email: none found
- **Belgin Madeni Yağlar** — `https://www.kariyer.net/firma-profil/belgin-madeni-yaglar-tic-ve-san-a-s-5006-29889` — open — lubricants maker, Gebze/Kocaeli; data/BI/financial analyst, production/demand planner; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Alpet (Altınbaş)** — `http://www.altinbasholding.com/tr/insan-kaynaklari/is-firsatlari/` — open — fuel distributor, HQ İstanbul; supply-chain planner, data analyst; email: none found
- **İpragaz** — `https://www.ipragaz.com.tr/kurumsal/kariyer/is-staj-olanaklari` — open — SHV-owned LPG distributor, HQ İstanbul; pricing/financial/data/BI analyst; email: none found
- **Milangaz (Demirören LPG)** — `https://milangaz.com.tr/kurumsal/kariyer/` — open — Demirören LPG distributor, HQ İstanbul; supply-chain/financial analyst; email: none found

### Mining & metals
- **Eti Maden** — `https://www.etimaden.gov.tr/ise-alim-duyurulari` — restricted — world's largest boron producer, HQ Ankara; worker/engineer cadres; email: none found
- **Koza Altın İşletmeleri** — `https://www.kozaaltin.com.tr/kurumsal/is-basvurulari/` — open — gold miner, HQ Ankara; process/data analyst; email: none found
- **Tüprag (Eldorado Gold Türkiye)** — `https://kariyer.tuprag.com.tr/is-ilanlari/` — open — Eldorado Gold subsidiary (Uşak/İzmir); PM, process/data analyst; email: none found
- **TKİ (Türkiye Kömür İşletmeleri)** — `https://www.tki.gov.tr/e-hizmetlerimiz` — restricted — national coal mining, HQ Ankara; mining-engineer/technical cadres; email: none found
- **Çayeli Bakır İşletmeleri** — `https://www.cayelibakir.com/tr/Kariyer/Cayeli-Bakirda-Kariyer` — open — First Quantum copper/zinc, Çayeli/Rize; process/reliability/data analyst; email: none found
- **Demir Export (Koç)** — `https://www.kockariyerim.com/companies/demir-export-is-ilanlar` — login-to-apply — Koç mining, HQ Ankara; PM, process/data/financial analyst, supply-chain; email: none found
- **Esan (Eczacıbaşı Endüstriyel Hammaddeler)** — `https://eczacibasikariyer.com.tr/` (Kariyer.net `firma-profil/esan-1026-232174`) — login-to-apply — industrial-minerals miner, HQ İstanbul (12 sites); production/quality/process analyst, supply-chain; email: none found
- **Park Elektrik / Kazan Soda (Ciner Group)** — `https://www.kazansoda.com/kariyer/` — open — Ciner mining/soda-ash (Beypazarı/Ankara); process/production/quality analyst; email: none found
- **Kümaş Manyezit** — `https://kumasref.com/tr/insan-kaynaklari/kariyer` — open — refractory/magnesite producer, Kütahya; production/process/quality analyst, supply-chain/procurement analyst; email: none found
- **Nurol Teknoloji (Madencilik)** — `https://www.kariyer.net/firma-profil/nurol-teknoloji-sanayi-ve-madencilik-ticaret-a-s-5245-226777` — open — Nurol tech/mining, Gölbaşı/Ankara; production/supply-chain planner, process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Textiles & home-textile manufacturing
- **Yünsa (Sabancı)** — `https://www.yunsa.com/is-basvurulari` — open — worsted wool fabric, Çerkezköy/Tekirdağ; production/quality planner, supply-chain, process/quality analyst; email: none found
- **Bossa (Adana, denim)** — `https://www.kariyer.net/firma-profil/bossa-ticaret-ve-sanayi-isletmeleri-t-a-s-8349-33227` — login-to-apply — integrated denim/textile, Adana; production planner, industrial-engineering/process analyst, ERP analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Menderes Tekstil** — `https://www.kariyer.net/firma-profil/menderes-tekstil-sanayi-ve-tic-a-s-12976-207876` — login-to-apply — integrated home textiles, Denizli; production/demand planner, BI/data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Zorluteks / Zorlu Tekstil (TAÇ, Valeron)** — `https://www.zorlutekstil.com.tr/Career/CareerOpportunities` — open — home textiles, Lüleburgaz; PM, supply-chain/demand planner, ERP-SAP analyst, financial analyst; email: none found
- **Korteks (Zorlu)** — `https://www.korteks.com.tr/tr/kariyer/kariyer-yonetimi` — open — polyester yarn, Bursa; production planner, process/quality analyst; email: none found
- **Söktaş** — `https://www.soktas.com.tr/culture-careers/` — open — cotton shirting fabric, Söke/Aydın; production/quality planner, BI analyst; email: none found
- **Sun Tekstil** — `https://www.kariyer.net/firma-profil/sun-tekstil-1452-223728` — login-to-apply — apparel, Torbalı/İzmir; BIST-listed; production planner, data/BI analyst, process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Yeşim Tekstil** — `https://www.yesim.com/yesimde-kariyer` — open — integrated apparel + home textiles, Bursa; supply-chain/demand planner, ERP analyst, PM; email: none found
- **Çalık Denim** — `https://www.calikdenim.com/tr/kariyer` — open — premium denim, Malatya; production/process planner, quality analyst; email: none found
- **Kipaş Mensucat (Kipaş Holding)** — `https://www.kipas.com.tr/kariyer` — open — yarn/fabric/denim, Kahramanmaraş; production planner, BI/data analyst, ERP analyst; email: ik@kipas.com.tr
- **Sanko Tekstil** — `https://www.sankotextile.com/en/company/careers/` — open — yarn/denim/towel, Gaziantep; production planner, process/quality analyst; email: none found
- **Kıvanç Tekstil** — `https://kivanctekstil.com.tr/tr/kariyer` — open — yarn/fabric, Adana; production/quality planner, supply-chain analyst; email: info@kivanctekstil.com.tr
- **İskur Holding / İskur Tekstil** — `https://www.kariyer.net/firma-profil/iskur-holding-78831-42118` — login-to-apply — integrated textile, Kahramanmaraş; production planner, process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Karsu Tekstil** — `https://www.kariyer.net/firma-profil/karsu-tekstil-sanayi-ve-ticaret-a-s-14798-5260` — login-to-apply — integrated cotton, Kayseri; production/quality planner; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)

### Machinery & industrial equipment (incl. HVAC/heating)
- **Ermaksan** — `https://www.ermaksan.com.tr/tr-TR/kariyer` — open — fiber laser / press brakes / sheet-metal machines, Bursa; PM, process/quality analyst, ERP analyst; email: insankaynaklari@ermaksan.com.tr
- **Durmazlar Makina (Durma)** — `https://www.kariyer.net/firma-profil/durmazlar-makina-san-ve-tic-a-s-3801-28684` — login-to-apply — machine tools/press, Bursa; PM, production planner, process analyst, ERP-SAP analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Dener Makina** — `https://dener.com/en/career/` — open — press brakes / fiber laser / shears, Kayseri; production planner, process/method engineer-analyst; email: none found
- **Baykal Makine** — `https://www.kariyer.net/firma-profil/baykal-makine-san-ve-tic-a-s-5757-30640` — login-to-apply — sheet-metal machinery, Bursa; production planner, process analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Tezmaksan** — `https://www.tezmaksan.com.tr/kariyer.php` — open — CNC machine tools + software, İstanbul; sales/BI analyst, PM; email: none found
- **Mikropor** — `https://www.mikropor.com/tr/kariyer/acik-pozisyonlar/` — open — industrial filtration, Ankara; production/process analyst, PM, supply-chain; email: mikropor@mikropor.com
- **Standart Pompa (Masgrup)** — `https://www.kariyer.net/firma-profil/standart-pompa-5646-30529` — login-to-apply — pumps, Ümraniye/İstanbul; production planner, process/quality analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Masdaf (Masgrup)** — `https://masdaf.com/en/career` — open — pumps; production planner, process analyst, PM; email: ik@masdaf.com
- **E.C.A. / Elginkan Holding (Serel, Valfsel, Emar)** — `https://elginkankariyer.com/` — open — taps, ceramics, valves, heating; PM, supply-chain/demand planner, ERP-SAP analyst, financial/BI analyst; email: none found
- **Daikin Türkiye** — `https://www.daikin.com.tr/daikin-insan-kaynaklari` — open — HVAC manufacturing, Hendek/Sakarya; production planner, supply-chain, process/quality analyst; email: none found
- **Demirdöküm (BDR Thermea)** — `https://www.demirdokum.com.tr/kurumsal/insan-kaynaklar/` (parent Workday `bdrthermea.wd103.myworkdayjobs.com/External`) — open — heating/HVAC; supply-chain/demand planner, ERP analyst, financial analyst; email: none found
- **Baymak (BDR Thermea)** — `https://www.baymak.com.tr/kariyer` — open — boilers/HVAC, Tuzla; production planner, process analyst, ERP analyst; email: none found
- **Friterm** — `https://www.friterm.com/tr-TR/kariyer-firsatlari/13025` — open — heat exchangers, İstanbul; production/process analyst, PM; email: none found
- **Form Şirketler Grubu** — `https://www.formgroup.com/home/kariyer/` — open — HVAC & industrial systems, Maslak/İstanbul; PM, sales/BI analyst; email: none found

### Pharma manufacturing
- **Abdi İbrahim** — `https://www.kariyer.net/firma-profil/abdi-ibrahim-ilac-9435-34313` — login-to-apply — largest TR pharma, Maslak/İstanbul; PM, supply/demand planner, ERP-SAP analyst, BI/financial analyst, process/quality analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Bilim İlaç** — `https://www.bilimilac.com.tr/kariyer` — open — Gebze + Çerkezköy plants; supply-chain/demand planner, ERP analyst, BI/data analyst, PM; email: none found
- **Deva Holding** — `https://www.kariyer.net/firma-profil/deva-holding-a-s-18492-9321` — login-to-apply — Çerkezköy/Kartepe plants; production-planning supervisor, demand planner, ERP/SAP analyst, financial analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Sanovel İlaç** — `https://www.kariyer.net/firma-profil/sanovel-ilac-14864-222692` — login-to-apply — İstanbul + Silivri plant; production/process analyst, supply planner, business-development/data analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Nobel İlaç** — `https://www.nobel.com.tr/en-us/career-at-nobel/applying-to-nobel` (Peoplise) — login-to-apply — Düzce/Gebze plants, HQ İstanbul; supply/demand planner, PM, BI analyst; email: none found
- **Koçak Farma** — `https://www.kariyer.net/firma-profil/kocak-farma-7404-41747` — login-to-apply — Çerkezköy/Tekirdağ; production planner, QC, business-development/data analyst, R&D PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Santa Farma İlaç** — `https://www.santafarma.com.tr/en/career/santa-farma-li-olun` — open — İstanbul + Lüleburgaz plant; production/process analyst, R&D analyst; email: none found
- **Mustafa Nevzat / Amgen Türkiye (+ Gensenta)** — `https://www.amgen.com.tr/careers` — login-to-apply — Amgen-owned; parenteral manufacturing; supply-chain, PM, data/BI analyst, financial analyst; email: none found
- **World Medicine İlaç** — `https://www.kariyer.net/firma-profil/world-medicine-ilac-san-ve-tic-a-s-30360-222797` — login-to-apply — Çerkezköy plant; production/warehouse planner, technical-documentation, process analyst; email: ik@wmo.com.tr (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Polifarma İlaç** — `https://www.polifarma.com.tr/insan-kaynaklari/is-basvurusu` — open — Ergene/Tekirdağ plant; project/investment analyst, production planner, process analyst; email: none found
- **Neutec İlaç** — `https://www.kariyer.net/firma-profil/neutec-ilac-329129-378656` — login-to-apply — Adapazarı plants + R&D; production/process analyst, supply planner; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Drogsan İlaçları** — `https://drogsan.com.tr/tr/kariyer-tr.html` — open — Ankara HQ + plant; R&D/QC analyst, technical-documentation; email: none found
- **Gen İlaç** — `https://www.genilac.com.tr/career-at-gen/?lang=en` — login-to-apply — Ankara manufacturing + R&D; product-transfer specialist, microbiology/QC, PM; email: none found
- **İlko İlaç (Selçuklu Holding)** — `https://www.ilko.com.tr/tr/is-basvurulari` — open — Sancaktepe/İstanbul; production/QC analyst, supply-chain, BI analyst; email: none found
- **Recordati İlaç Türkiye** — `https://careers.recordati.com/?locale=tr_TR` — login-to-apply — Çerkezköy/Tekirdağ plant; supply-chain, PM, financial analyst, process/QC analyst; email: none found

### Defense-industrial manufacturers
(All restricted unless noted: typically require Turkish citizenship + security clearance.)
- **Roketsan** — `https://kariyer.roketsan.com.tr/jobs` (HRPeak) — restricted — missiles & rockets, Elmadağ/Ankara; reliability/safety analyst, PM, supply-chain; email: none found
- **FNSS Savunma Sistemleri** — `https://www.fnss.com.tr/tr/kariyer` — restricted — armored vehicles, Gölbaşı/Ankara; manufacturing/process engineer-analyst, supply-chain/logistics, PM; email: none found
- **Nurol Makina** — `http://www.nurolmakina.com.tr/tr/kariyer` — restricted — armored vehicles (Ejder Yalçın), Ankara; production planner, process/quality analyst, PM; email: none found
- **TEI – TUSAŞ Engine Industries** — `https://tei.hrpeak.com/jobs` (HRPeak) — restricted — aero engines, Eskişehir; production planner, process/quality analyst, supply-chain, PM, data analyst; email: none found
- **Alp Havacılık / Alp Aviation** — `https://alpinsankaynaklari.com/acik-pozisyonlar` — restricted — aero components, Eskişehir; production/process planner, quality analyst, PM; email: none found
- **Kale Havacılık / Kale Aero** — `https://www.kariyer.net/firma-profil/kale-havacilik-san-a-s-31033-223329` — login-to-apply — aero structures, Tuzla; production planner, process/quality analyst, supply-chain; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **MKE – Makina ve Kimya Endüstrisi** — `https://kariyer.mke.gov.tr/ilanlar` — restricted — ammunition/weapons (state), Ankara; production planner, process/quality analyst, ERP analyst; email: kurumsaliletisim@mke.gov.tr
- **Meteksan Savunma** — `https://www.meteksan.com/en/kariyer` — restricted — radar/sonar/comms, Bilkent/Ankara; PM, systems/process analyst, supply-chain; email: none found
- **Samsun Yurt Savunma / Canik** — `https://www.canik.com/global/careers` — open — firearms, Samsun; production planner, process/quality analyst, supply-chain, PM; email: none found
- **Sarsılmaz Silah** — `https://www.sarsilmaz.com/tr/ik` — login-to-apply — firearms, Düzce/İstanbul; production planner, process/quality analyst; email: none found
- **Katmerciler** — `https://www.kariyer.net/firma-profil/katmerciler-arac-ustu-ekipman-san-ve-tic-a-s-26296-17902` — login-to-apply — armored & special vehicles, Çiğli/İzmir; PM, process/quality analyst, supply-chain, ERP analyst; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **CES İleri Kompozit ve Savunma Teknolojileri** — `https://www.kariyer.net/firma-profil/ces-ileri-kompozit-ve-savunma-teknolojileri-a-s-366272-424328` — login-to-apply — composites/defense, Sincan/Ankara; production/process analyst, quality, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Repkon** — `https://repkonuretim.com/tr/kariyer/kariyer-bilgileri` — open — flow-forming machinery & defense, Dilovası/Kocaeli + Tekirdağ; manufacturing/process engineer-analyst, production planner, PM; email: none found
- **Transvaro** — `https://www.kariyer.net/firma-profil/transvaro-elektron-aletleri-san-ve-tic-a-s-1277-223534` — login-to-apply — optronics/night-vision, Küçükçekmece/İstanbul; production/process analyst, supply-chain, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Ayesaş** — `https://www.ayesas.com/tr/kariyer` — open — defense electronics, İstanbul; PM, process analyst, supply-chain; email: IK@ayesas.com
- **Best Transformer (Balıkesir Elektromekanik)** — `https://www.kariyer.net/firma-profil/best-a-s-best-transformer-7242-32120` — login-to-apply — power/defense transformers, Balıkesir; production planner, process/quality analyst, PM; email: none found (read-only: no ATS alternative found 2026-06-21; Mode C human-apply)
- **Aspilsan Enerji** — `https://www.aspilsan.com/en/corporate/about_us/` — restricted — military Li-ion/Ni-Cd batteries (TSKGV), Kayseri; production/process analyst, supply-chain, PM; email: none found

## 8. Job boards, tech communities & government
- **Kariyer.net** — `https://www.kariyer.net/is-ilanlari/<role>` (e.g. `veri+analisti`, `veri+bilimci`); city prefix `istanbul-` / `istanbul-asya-`; firma-profil per company — open browse / login-to-apply. **Largest TR board.** (restricted for automated apply.)
- **Yenibiriş** — `https://www.yenibiris.com/is-ilanlari/<role>` (e.g. `data-analyst`, `big-data-analyst`) — open.
- **SecretCV** — `https://www.secretcv.com/is-ilanlari/<role>-is-ilanlari` and query `?k=<keyword>` (`project_manager`, `is_analisti_business_analyst`) — open — ~590 PM postings observed.
- **Eleman.net** — `https://www.eleman.net/is-ilanlari?aranan=<keyword>` — open (SME-heavy).
- **Toptalent.co** — `https://toptalent.co/is-ilanlari/istanbul-avrupa-is-ilanlari` / `-anadolu-` / `/yeni-mezun-` / `/yazilim-` — open (new-grad emphasis).
- **techcareer.net** — `https://www.techcareer.net/jobs` (`/uzaktan` remote, `/hibrit`, `/is-yerinde`; `/jobs/positions/<role>`) — open — IT/Data/DS/PM.
- **coderspace.io** — `https://coderspace.io/en/jobs` (hiring-challenge model; data hiring events) — login.
- **Kommunity** — `https://kommunity.com/techistanbul` — open — community/event sourcing (not a job feed).
- **İŞKUR** (government) — `https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx` — restricted (ASP.NET postback + e-Devlet apply; supervised). Authoritative, high volume.
- **Indeed Türkiye** — `https://tr.indeed.com/Data-Analyst-jobs-in-Istanbul` (`/q-<role>-l-istanbul-is-ilanlari.html`) — open, bot-sensitive (supervised).
- **Glassdoor** — `https://www.glassdoor.com/Job/istanbul-turkey-data-analyst-jobs-...htm` (IM1160=Istanbul, IN238=Turkey) — login/bot-gated (supervised).
- **Startup Jobs Istanbul** — `https://startupjobs.istanbul/job-category/bi-data/` — open, already Istanbul-scoped.
- **Youthall** — `https://www.youthall.com/en/jobs/?page=N` — open — junior/new-grad/internships + grad talent programs.

## 9. ATS platforms & cross-company discovery (the scale unlock)
Confirmed example tenants and the discovery recipe:
- **Lever** examples: trendyol, insiderone, papara, iyzico, picus, dreamgames, spyke-games. API: `api.lever.co/v0/postings/<token>?mode=json`.
- **Greenhouse** examples: gramgamescareers, medsien. API: `boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true`.
- **Ashby** examples: hostinger, quora. API: `POST api.ashbyhq.com/posting-api/job-board/<token>`.
- **SmartRecruiters**: DeliveryHero (Yemeksepeti). API: `api.smartrecruiters.com/v1/companies/<token>/postings`.
- **Workday** examples: ing (ICSGBLCOR), pladis, accenture (wd103/AccentureCareers), pwc (wd3/Global_Experienced_Careers), sanofi, citi, viatris, clarivate, spgi, unilever, vodafone. API: `POST <tenant>.<wdN>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs`.
- **SuccessFactors**: Koç (career5...?company=Koc), Borusan, Eczacıbaşı, Anadolu, Çalık, CCI, EY, SAP, Deloitte. No clean API → supervised browser; pattern `career[2/5].successfactors.eu/careers?company=<tenant>`.
- **Recruitee** / **Personio** / **HRPeak** / **Peoplise** / **Talentics** / **PeopleBox** / **Zoho Recruit** / **onenewone** / **JazzHR (applytojob)** / **Workable** — per-company boards; several expose JSON/XML (Recruitee `/api/offers/`, Personio `/xml`).

**Discovery operators** (find NEW Turkish employers per ATS):
```
site:jobs.lever.co ("Istanbul" OR "Türkiye")
site:myworkdayjobs.com ("Istanbul" OR "Turkey") "data analyst"
site:boards.greenhouse.io OR site:job-boards.greenhouse.io "Istanbul"
site:jobs.ashbyhq.com ("Istanbul" OR "Türkiye")
site:recruitee.com "Istanbul"     site:jobs.personio.com "Istanbul"
site:successfactors.eu "Türkiye"
```
For each discovered token, call that ATS's public API and filter location = Istanbul/Türkiye.

## 9b. ATS-token long-tail expansion — 2026-06-17 (batch JAC-38): 123 verified companies
NEW employers harvested by running the section-9 discovery operators against public ATS boards (Lever, Greenhouse, Ashby, SmartRecruiters, Workday CXS, Recruitee, Personio, Workable, Teamtailor, JazzHR, Zoho Recruit, Jobvite) and verifying each token against its live board/API with a current Türkiye/Istanbul role. Each entry carries the machine-queryable token/endpoint so Step 1 discovery can fetch it directly. Strict dedup against sections 9, 3b and the rest of the catalog; same-brand duplicates already listed (Binance, Bosch, H&M, Metro, Mondelez, Peak, Volt Lines) were dropped. Most boards route applications internally, so emails are mostly "none found".

### Lever-hosted
- **Firefly** — `https://jobs.lever.co/fireflyon` (API `https://api.lever.co/v0/postings/fireflyon?mode=json`) — open — out-of-home/car-top advertising data network; Business Operations Associate, Customer Success, Marketing; Istanbul; email: none found
- **Capital.com** — `https://jobs.lever.co/capital` (API `https://api.lever.co/v0/postings/capital?mode=json`) — open — fintech/online trading; AML Officer, Automation & AI Analyst, onboarding & ops; Istanbul; email: none found
- **Jobgether** — `https://jobs.lever.co/jobgether` (API `https://api.lever.co/v0/postings/jobgether?mode=json`) — open — remote-work talent marketplace hiring Turkey roles; Operations Manager, Product Owner, Project & Resource Manager, Customer Success; Turkey (remote); email: none found
- **Welo Data (Welocalize)** — `https://jobs.lever.co/weloglobal` (API `https://api.lever.co/v0/postings/weloglobal?mode=json`) — open — AI data services/localization; Turkish audio/transcription analysts, data-labelling raters; Turkey (remote); email: none found
- **Ajax Systems** — `https://jobs.lever.co/ajax` (API `https://api.lever.co/v0/postings/ajax?mode=json`) — open — security hardware manufacturer with Turkey facility; Business Development Manager, Quality Engineer, QMS Specialist; Istanbul; email: none found
- **TSMG** — `https://jobs.lever.co/tsmg` (API `https://api.lever.co/v0/postings/tsmg?mode=json`) — open — mapping/geospatial & technical data services with Istanbul (aviation/EMEA) ops; Junior Team Lead - EMEA + engineering; Istanbul; email: none found
- **Surpass Games** — `https://jobs.lever.co/surpassgames` (API `https://api.lever.co/v0/postings/surpassgames?mode=json`) — login-to-apply — hybrid-casual mobile game studio (has Director of Data & Analytics); board live; Istanbul; email: none found

### Greenhouse-hosted
- **OLIVER** — `https://job-boards.greenhouse.io/oliver` (API `https://boards-api.greenhouse.io/v1/boards/oliver/jobs?content=true`) — open — creative/marketing production agency; Account Manager (AM/PM hybrid), adaptation/ops roles; Istanbul; email: none found
- **Constructor Tech** — `https://job-boards.eu.greenhouse.io/constructortech` (API `https://boards-api.greenhouse.io/v1/boards/constructortech/jobs?content=true`) — open — EdTech/AI SaaS with Istanbul entity; Senior Product Manager, Mobile QA, software/security eng; Istanbul; email: none found
- **Sezzle** — `https://job-boards.greenhouse.io/sezzle` (API `https://boards-api.greenhouse.io/v1/boards/sezzle/jobs?content=true`) — open — fintech/BNPL; Türkiye-remote software/mobile/QA & analyst-adjacent eng; Türkiye (remote); email: none found
- **Taboola** — `https://job-boards.greenhouse.io/taboola` (API `https://boards-api.greenhouse.io/v1/boards/taboola/jobs?content=true`) — open — adtech/content recommendation; Advertiser Sales Manager, Advertising Director, Client Success Lead; Istanbul; email: none found
- **Bybit** — `https://job-boards.greenhouse.io/bybit` (API `https://boards-api.greenhouse.io/v1/boards/bybit/jobs?content=true`) — open — crypto exchange; AML Manager, Business Continuity Manager, ID Verification Officer; Istanbul; email: none found
- **Appier** — `https://job-boards.greenhouse.io/appier` (API `https://boards-api.greenhouse.io/v1/boards/appier/jobs?content=true`) — open — AI/SaaS martech; QA Automation Engineer (Türkiye-remote) + product/data org; Istanbul/Türkiye (remote); email: none found
- **OKX** — `https://boards.greenhouse.io/okx` (API `https://boards-api.greenhouse.io/v1/boards/okx/jobs?content=true`) — open — crypto exchange; Operations Analyst, Specialist Customer Due Diligence Operations; Istanbul; email: none found
- **WPP Media (GroupM)** — `https://boards.greenhouse.io/wppmedia` (API `https://boards-api.greenhouse.io/v1/boards/wppmedia/jobs?content=true`) — open — media/advertising; Digital Investment Manager, Investment Director, Sr Programmatic Buying; Istanbul; email: none found
- **Wunderman Thompson (VML)** — `https://boards.greenhouse.io/wundermanthompson` (API `https://boards-api.greenhouse.io/v1/boards/wundermanthompson/jobs?content=true`) — open — advertising agency; Brand Asset Manager (ops-adjacent), Community Manager, creative roles; Istanbul; email: none found

### Ashby-hosted
- **MUBI** — `https://jobs.ashbyhq.com/MUBI` (API `https://api.ashbyhq.com/posting-api/job-board/MUBI`) — open — film streaming/distribution, Turkish-founded with Istanbul HQ; Product/Program Managers, Designer (Turkey); Istanbul; email: none found
- **Lavendo** — `https://jobs.ashbyhq.com/lavendo` (API `https://api.ashbyhq.com/posting-api/job-board/lavendo`) — open — data-privacy/security SaaS recruiting; Technical Project Manager (Data Privacy), Data Privacy Engineer, Enterprise BDR (Istanbul-eligible remote); Istanbul; email: none found
- **Keyrock** — `https://jobs.ashbyhq.com/keyrock` (API `https://api.ashbyhq.com/posting-api/job-board/keyrock`) — open — crypto market-making/fintech; Senior Data Engineer (Istanbul among offices); Istanbul; email: none found
- **Pragmatike** — `https://jobs.ashbyhq.com/pragmatike` (API `https://api.ashbyhq.com/posting-api/job-board/pragmatike`) — open — AI/ML engineering services (EMEA remote); ML Ops Engineer, AI Infrastructure Engineer (Türkiye-eligible); Türkiye (remote); email: none found

### SmartRecruiters-hosted
- **NielsenIQ** — `https://careers.smartrecruiters.com/NielsenIQ` (API `https://api.smartrecruiters.com/v1/companies/NielsenIQ/postings`) — open — market research/consumer intelligence; eData Delivery Analyst, Operations Client Partner, Research Sales Manager; Istanbul; email: none found
- **Lesaffre** — `https://careers.smartrecruiters.com/Lesaffre` (API `https://api.smartrecruiters.com/v1/companies/Lesaffre/postings`) — open — fermentation/food ingredients; Regional Treasury Manager, Treasury Specialist, Lean & Industry 4.0 Manager; Istanbul; email: none found
- **CRENNO** — `https://careers.smartrecruiters.com/CRENNO` (API `https://api.smartrecruiters.com/v1/companies/CRENNO/postings`) — open — software/game tech; Business Analyst, Senior Product Manager & Product Owner, Lead Game Product Manager; Istanbul; email: none found
- **Believe** — `https://careers.smartrecruiters.com/Believe` (API `https://api.smartrecruiters.com/v1/companies/Believe/postings`) — open — digital music/media; Strategic PMI Project Manager, Project Manager – M&A; Istanbul; email: none found
- **Exinity** — `https://careers.smartrecruiters.com/Exinity` (API `https://api.smartrecruiters.com/v1/companies/Exinity/postings`) — open — fintech/online trading (CFD/FX); Business Development Manager; Istanbul; email: none found
- **Reload** — `https://careers.smartrecruiters.com/Reload1` (API `https://api.smartrecruiters.com/v1/companies/Reload1/postings`) — open — mobile apps/internet infrastructure; Data Analyst, Product Designer, devs; Antalya, Türkiye; email: none found
- **Catalysor** — `https://careers.smartrecruiters.com/Catalysor` (API `https://api.smartrecruiters.com/v1/companies/Catalysor/postings`) — open — data-driven growth/digital marketing agency; Growth Marketing Manager, SEO Specialist; Istanbul (Beşiktaş); email: none found
- **WordSmith Advertising** — `https://careers.smartrecruiters.com/WordSmithAdvertising` (API `https://api.smartrecruiters.com/v1/companies/WordSmithAdvertising/postings`) — open — English-language advertising agency; Strategy & Marketing Intern, UX Intern, Content Writer; Istanbul (Beyoğlu); email: none found
- **Red Bull** — `https://careers.smartrecruiters.com/RedBull` (API `https://api.smartrecruiters.com/v1/companies/RedBull/postings`) — open — FMCG/beverages; Trade Marketing Analyst, Brand Manager Portfolio & Insights, FP&A Specialist; Istanbul; email: none found
- **AbbVie** — `https://careers.smartrecruiters.com/abbvie` (API `https://api.smartrecruiters.com/v1/companies/abbvie/postings`) — open — pharma; Product Manager (Allergan Aesthetics), Controller, Clinical Research Associate; Istanbul; email: none found
- **Securitas** — `https://careers.smartrecruiters.com/Securitas` (API `https://api.smartrecruiters.com/v1/companies/Securitas/postings`) — open — security services; Budget & Reporting Manager, Product Manager (Ürün Yöneticisi); Istanbul (Beykoz); email: none found
- **Accor** — `https://careers.smartrecruiters.com/AccorHotel` (API `https://api.smartrecruiters.com/v1/companies/AccorHotel/postings`) — open — hospitality; Sales Manager, General Accountant, Leasing Specialist; Istanbul; email: none found
- **Jacobs Douwe Egberts (JDE)** — `https://careers.smartrecruiters.com/JACOBSDOUWEEGBERTS` (API `https://api.smartrecruiters.com/v1/companies/JACOBSDOUWEEGBERTS/postings`) — open — FMCG/coffee; Brand Manager, Key Accounts Sales Supervisor; Istanbul (Ataşehir); email: none found
- **Lostar** — `https://careers.smartrecruiters.com/Lostar` (API `https://api.smartrecruiters.com/v1/companies/Lostar/postings`) — login-to-apply — cybersecurity/infosec SME; IT & InfoSec GRC Consultant (analyst), Penetration Tester; Istanbul; email: info@lostar.com.tr
- **Monotect** — `https://jobs.smartrecruiters.com/Monotect` (API `https://api.smartrecruiters.com/v1/companies/Monotect/postings`) — login-to-apply — software SME (SAP C/4HANA / CX); Senior Java Developer; Istanbul (Maltepe); email: none found

### Workday CXS
- **Maersk** — `https://maersk.wd3.myworkdayjobs.com/Maersk_Manual` (CXS `https://maersk.wd3.myworkdayjobs.com/wday/cxs/maersk/Maersk_Manual/jobs`) — open — logistics & shipping; ops/SCM & customer-experience roles incl. intern; Istanbul; email: none found
- **Pfizer** — `https://pfizer.wd1.myworkdayjobs.com/PfizerCareers` (CXS `https://pfizer.wd1.myworkdayjobs.com/wday/cxs/pfizer/PfizerCareers/jobs`) — login-to-apply — pharma; marketing/regulatory/commercial; Istanbul; email: none found
- **Analog Devices** — `https://analogdevices.wd1.myworkdayjobs.com/External` (CXS `https://analogdevices.wd1.myworkdayjobs.com/wday/cxs/analogdevices/External/jobs`) — open — semiconductors; engineering/applications & analyst-adjacent; Istanbul (Bilişim Vadisi); email: none found
- **Roche** — `https://roche.wd3.myworkdayjobs.com/roche-ext` (CXS `https://roche.wd3.myworkdayjobs.com/wday/cxs/roche/roche-ext/jobs`) — open — pharma/diagnostics; Product Manager, Finance Partner, medical; Istanbul; email: none found
- **GE HealthCare** — `https://gehc.wd5.myworkdayjobs.com/GEHC_ExternalSite` (CXS `https://gehc.wd5.myworkdayjobs.com/wday/cxs/gehc/GEHC_ExternalSite/jobs`) — open — medical imaging; Project Manager, Finance Manager, sales specialist; Istanbul; email: none found
- **GSK** — `https://gsk.wd5.myworkdayjobs.com/GSKCareers` (CXS `https://gsk.wd5.myworkdayjobs.com/wday/cxs/gsk/GSKCareers/jobs`) — open — pharma; Omnichannel/Marketing Cloud Lead, Supply Chain Planner; Istanbul; email: none found
- **Avon** — `https://avon.wd5.myworkdayjobs.com/AvonCareers` (CXS `https://avon.wd5.myworkdayjobs.com/wday/cxs/avon/AvonCareers/jobs`) — open — beauty/e-commerce; SEO/Generative-Search Lead, content & platform roles; Istanbul; email: none found
- **PVH (Tommy Hilfiger / Calvin Klein)** — `https://pvh.wd1.myworkdayjobs.com/PVH_Careers` (CXS `https://pvh.wd1.myworkdayjobs.com/wday/cxs/pvh/PVH_Careers/jobs`) — open — apparel/retail; Finance Business Partner, finance/marketing intern, retail mgmt; Istanbul; email: none found
- **Philips** — `https://philips.wd3.myworkdayjobs.com/jobs-and-careers` (CXS `https://philips.wd3.myworkdayjobs.com/wday/cxs/philips/jobs-and-careers/jobs`) — open — health tech; Services Leader, Account/Sales Manager, customer-service; Istanbul; email: none found
- **Kantar** — `https://kantar.wd3.myworkdayjobs.com/KANTAR` (CXS `https://kantar.wd3.myworkdayjobs.com/wday/cxs/kantar/KANTAR/jobs`) — open — market research/data & insights; Client Manager (analyst/PM-adjacent); Istanbul; email: none found
- **Novartis** — `https://novartis.wd3.myworkdayjobs.com/Novartis_Careers` (CXS `https://novartis.wd3.myworkdayjobs.com/wday/cxs/novartis/Novartis_Careers/jobs`) — open — pharma; Deployment Manager, Process Specialist, manufacturing; Istanbul (Kurtköy/Ataşehir); email: none found
- **Haleon (GSK Consumer Healthcare)** — `https://gsknch.wd3.myworkdayjobs.com/GSKCareers` (CXS `https://gsknch.wd3.myworkdayjobs.com/wday/cxs/gsknch/GSKCareers/jobs`) — open — consumer health; commercial/sales roles; Istanbul; email: none found
- **ICON plc** — `https://icon.wd3.myworkdayjobs.com/broadbean_external` (CXS `https://icon.wd3.myworkdayjobs.com/wday/cxs/icon/broadbean_external/jobs`) — open — clinical research/CRO; Contract Analyst, Clinical Trial/Operations Manager; Istanbul; email: none found
- **The Coca-Cola Company** — `https://coke.wd1.myworkdayjobs.com/coca-cola-careers` (CXS `https://coke.wd1.myworkdayjobs.com/wday/cxs/coke/coca-cola-careers/jobs`) — open — FMCG/beverages (global brand owner, distinct from the CCI bottler); R&D intern (analyst/ops pipeline); Istanbul; email: none found
- **Visa** — `https://visa.wd5.myworkdayjobs.com/Visa` (CXS `https://visa.wd5.myworkdayjobs.com/wday/cxs/visa/Visa/jobs`) — open — payments/fintech; Senior Account Executive (commercial/analyst-adjacent); Istanbul; email: none found
- **Gartner** — `https://gartner.wd5.myworkdayjobs.com/EXT` (CXS `https://gartner.wd5.myworkdayjobs.com/wday/cxs/gartner/EXT/jobs`) — open — research/advisory; Business Development & Account Executive (GTS); Istanbul; email: none found
- **Medtronic** — `https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers` (CXS `https://medtronic.wd1.myworkdayjobs.com/wday/cxs/medtronic/MedtronicCareers/jobs`) — open — medtech; Commercial Leader, Technical Consultant, Marketing Specialist; Istanbul; email: none found
- **JLL** — `https://jll.wd1.myworkdayjobs.com/jllcareers` (CXS `https://jll.wd1.myworkdayjobs.com/wday/cxs/jll/jllcareers/jobs`) — open — commercial real estate; ops/facilities (PM/BA-adjacent); Istanbul; email: none found
- **LivaNova** — `https://livanova.wd5.myworkdayjobs.com/Search` (CXS `https://livanova.wd5.myworkdayjobs.com/wday/cxs/livanova/Search/jobs`) — open — medical devices; Field Clinical Specialist; Istanbul; email: none found
- **AstraZeneca** — `https://astrazeneca.wd3.myworkdayjobs.com/Careers` (CXS `https://astrazeneca.wd3.myworkdayjobs.com/wday/cxs/astrazeneca/Careers/jobs`) — login-to-apply — pharma; Product Manager, Medical/Marketing Manager, internships; Istanbul; email: none found
- **Abbott** — `https://abbott.wd5.myworkdayjobs.com/abbottcareers` (CXS `https://abbott.wd5.myworkdayjobs.com/wday/cxs/abbott/abbottcareers/jobs`) — login-to-apply — medical devices & pharma; Enterprise Solutions Director, Digital Health Solutions Consultant; Istanbul; email: none found
- **Mastercard** — `https://mastercard.wd1.myworkdayjobs.com/CorporateCareers` (CXS `https://mastercard.wd1.myworkdayjobs.com/wday/cxs/mastercard/CorporateCareers/jobs`) — login-to-apply — payments/fintech (Mastercard Inc., distinct from Provus); Product Management, Senior Analyst (Dispute Resolution), Consultant; Istanbul (Beşiktaş); email: none found
- **Stryker** — `https://stryker.wd1.myworkdayjobs.com/StrykerCareers` (CXS `https://stryker.wd1.myworkdayjobs.com/wday/cxs/stryker/StrykerCareers/jobs`) — login-to-apply — medical devices; Logistics Operations Associate Manager, TA Business Partner; Istanbul; email: none found
- **SC Johnson** — `https://scj.wd5.myworkdayjobs.com/External_Career_Site` (CXS `https://scj.wd5.myworkdayjobs.com/wday/cxs/scj/External_Career_Site/jobs`) — login-to-apply — FMCG/consumer goods; Sales Account Management Associate, Regulatory Compliance Associate; Istanbul; email: none found
- **3M** — `https://3m.wd1.myworkdayjobs.com/Search` (CXS `https://3m.wd1.myworkdayjobs.com/wday/cxs/3m/Search/jobs`) — login-to-apply — industrial/safety; Key Account Supervisor (Personal Safety); Istanbul; email: none found
- **GE Aerospace** — `https://geaerospace.wd5.myworkdayjobs.com/GE_ExternalSite` (CXS `https://geaerospace.wd5.myworkdayjobs.com/wday/cxs/geaerospace/GE_ExternalSite/jobs`) — login-to-apply — aerospace/engineering; Supplier Fulfillment Leader, engineering & software interns; Istanbul; email: none found
- **Dentsu** — `https://dentsuaegis.wd3.myworkdayjobs.com/DAN_GLOBAL` (CXS `https://dentsuaegis.wd3.myworkdayjobs.com/wday/cxs/dentsuaegis/DAN_GLOBAL/jobs`) — login-to-apply — media/advertising; Account Manager, Performance Marketing Manager, Digital Media Manager; Istanbul; email: none found
- **Danaher** — `https://danaher.wd1.myworkdayjobs.com/danaherjobs` (CXS `https://danaher.wd1.myworkdayjobs.com/wday/cxs/danaher/danaherjobs/jobs`) — login-to-apply — life sciences & diagnostics conglomerate; Field Service Engineer, supply/demand analyst, PM; Istanbul; email: none found
- **Envista (Nobel Biocare / Kerr / Ormco)** — `https://envista.wd1.myworkdayjobs.com/envistacareers` (CXS `https://envista.wd1.myworkdayjobs.com/wday/cxs/envista/envistacareers/jobs`) — login-to-apply — dental devices; Business Development Rep, Digital Content & Design Specialist, Sales; Istanbul; email: none found
- **IQVIA** — `https://iqvia.wd1.myworkdayjobs.com/IQVIA` (CXS `https://iqvia.wd1.myworkdayjobs.com/wday/cxs/iqvia/IQVIA/jobs`) — login-to-apply — healthcare data & CRO; Data Analyst, Systems Support Analyst, Consultant, Key Account Manager; Istanbul; email: none found
- **Edwards Lifesciences** — `https://edwards.wd5.myworkdayjobs.com/EdwardsCareers` (CXS `https://edwards.wd5.myworkdayjobs.com/wday/cxs/edwards/EdwardsCareers/jobs`) — login-to-apply — structural-heart medtech; Field Clinical Specialist; Türkiye; email: none found
- **Thermo Fisher Scientific** — `https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers` (CXS `https://thermofisher.wd5.myworkdayjobs.com/wday/cxs/thermofisher/ThermoFisherCareers/jobs`) — login-to-apply — lab equipment & CRO; Clinical Operations, Clinical Trial Coordinator, CRA; Istanbul/Türkiye; email: none found
- **Johnson Controls** — `https://jci.wd5.myworkdayjobs.com/JCI` (CXS `https://jci.wd5.myworkdayjobs.com/wday/cxs/jci/JCI/jobs`) — login-to-apply — building tech & HVAC; Territory Account Manager, Sales Manager, HR Specialist (İzmir); Istanbul; email: none found
- **IFF (International Flavors & Fragrances)** — `https://iff.wd5.myworkdayjobs.com/IFF_Careers` (CXS `https://iff.wd5.myworkdayjobs.com/wday/cxs/iff/IFF_Careers/jobs`) — login-to-apply — flavors, fragrances & enzymes; Technical Sales Manager, Account Manager, Production Supervisor; Istanbul/Gebze; email: none found
- **TD SYNNEX** — `https://synnex.wd5.myworkdayjobs.com/tdsynnexcareers` (CXS `https://synnex.wd5.myworkdayjobs.com/wday/cxs/synnex/tdsynnexcareers/jobs`) — login-to-apply — IT distribution; Technical Presales Consultant, Account Manager; Istanbul; email: none found
- **Dyson** — `https://dyson.wd3.myworkdayjobs.com/dyson_careers` (CXS `https://dyson.wd3.myworkdayjobs.com/wday/cxs/dyson/dyson_careers/jobs`) — login-to-apply — consumer electronics; Delivery Lead, Sales Planning Manager, Comms Manager; Istanbul/Ankara; email: none found
- **Samsung Electronics** — `https://sec.wd3.myworkdayjobs.com/Samsung_Careers` (CXS `https://sec.wd3.myworkdayjobs.com/wday/cxs/sec/Samsung_Careers/jobs`) — login-to-apply — electronics manufacturing; Tax Accounting, EHS Planning, R&D Management, inspection; Çerkezköy/Tekirdağ; email: none found
- **Kraft Heinz** — `https://heinz.wd1.myworkdayjobs.com/KraftHeinz_Careers` (CXS `https://heinz.wd1.myworkdayjobs.com/wday/cxs/heinz/KraftHeinz_Careers/jobs`) — login-to-apply — FMCG food; Demand Planner, Procurement Intern, Regional Sales Manager; Istanbul; email: none found
- **HP Inc.** — `https://hp.wd5.myworkdayjobs.com/EXTEU-AC-CareerSite` (CXS `https://hp.wd5.myworkdayjobs.com/wday/cxs/hp/EXTEU-AC-CareerSite/jobs`) — login-to-apply — IT hardware; Commercial/Public Account Manager; Istanbul/Ankara; email: none found
- **PerkinElmer** — `https://newperkinelmer.wd1.myworkdayjobs.com/External` (CXS `https://newperkinelmer.wd1.myworkdayjobs.com/wday/cxs/newperkinelmer/External/jobs`) — login-to-apply — analytical instruments; Food Sales Specialist; Ankara/Türkiye; email: none found
- **BorgWarner** — `https://borgwarner.wd5.myworkdayjobs.com/BorgWarner_Careers` (CXS `https://borgwarner.wd5.myworkdayjobs.com/wday/cxs/borgwarner/BorgWarner_Careers/jobs`) — login-to-apply — automotive components; Purchasing Manager, Manufacturing/Quality Engineering; İzmir; email: none found
- **Cisco** — `https://cisco.wd5.myworkdayjobs.com/Cisco_Careers` (CXS `https://cisco.wd5.myworkdayjobs.com/wday/cxs/cisco/Cisco_Careers/jobs`) — login-to-apply — networking & cloud; Inside Account Executive (Security); Istanbul; email: none found
- **Hitachi** — `https://hitachi.wd1.myworkdayjobs.com/hitachi` (CXS `https://hitachi.wd1.myworkdayjobs.com/wday/cxs/hitachi/hitachi/jobs`) — login-to-apply — industrial/energy (Hitachi Ltd, distinct from Hitachi Vantara); Commercial Account Manager, Mechanical Design Engineer, Order Management Specialist; Istanbul; email: none found
- **GE Vernova** — `https://gevernova.wd5.myworkdayjobs.com/Vernova_ExternalSite` (CXS `https://gevernova.wd5.myworkdayjobs.com/wday/cxs/gevernova/Vernova_ExternalSite/jobs`) — login-to-apply — power & energy; Project Manager, Lead Manufacturing Operations Finance Analyst, Supply Chain Specialist; Gebze; email: none found
- **Autodesk** — `https://autodesk.wd1.myworkdayjobs.com/Ext` (CXS `https://autodesk.wd1.myworkdayjobs.com/wday/cxs/autodesk/Ext/jobs`) — login-to-apply — design/engineering software; Solution Sales Executive (MFG), Construction Cloud Sales Specialist; Istanbul; email: none found
- **Air Liquide** — `https://airliquidehr.wd3.myworkdayjobs.com/AirLiquideExternalCareer` (CXS `https://airliquidehr.wd3.myworkdayjobs.com/wday/cxs/airliquidehr/AirLiquideExternalCareer/jobs`) — login-to-apply — industrial gases; Direct Procurement Buyer, Sales Rep, Business Developer; Istanbul/Ankara/Manisa; email: none found
- **Hewlett Packard Enterprise (HPE)** — `https://hpe.wd5.myworkdayjobs.com/WFMathpe` (CXS `https://hpe.wd5.myworkdayjobs.com/wday/cxs/hpe/WFMathpe/jobs`) — login-to-apply — enterprise IT; Senior Network Engineer; Istanbul; email: none found
- **Red Hat** — `https://redhat.wd5.myworkdayjobs.com/jobs` (CXS `https://redhat.wd5.myworkdayjobs.com/wday/cxs/redhat/jobs/jobs`) — login-to-apply — open-source software; Account Executive (Banking); Istanbul; email: none found
- **Solventum (former 3M Health Care)** — `https://healthcare.wd1.myworkdayjobs.com/Search` (CXS `https://healthcare.wd1.myworkdayjobs.com/wday/cxs/healthcare/Search/jobs`) — login-to-apply — healthcare/medtech; Trade Operations Analyst; Ankara/Türkiye; email: none found
- **Sandvik** — `https://sandvik.wd3.myworkdayjobs.com/sandvik-jobs` (CXS `https://sandvik.wd3.myworkdayjobs.com/wday/cxs/sandvik/sandvik-jobs/jobs`) — login-to-apply — industrial tooling & mining; Sales Professional EMEA, Customer Service Specialist, Sales Engineer; Istanbul/Ankara; email: none found
- **Electrolux** — `https://electrolux.wd3.myworkdayjobs.com/ElectroluxCareerSite` (CXS `https://electrolux.wd3.myworkdayjobs.com/wday/cxs/electrolux/ElectroluxCareerSite/jobs`) — login-to-apply — home appliances; Trade Marketing Manager, Service Operations Manager; Istanbul; email: none found
- **Avnet** — `https://avnet.wd1.myworkdayjobs.com/External` (CXS `https://avnet.wd1.myworkdayjobs.com/wday/cxs/avnet/External/jobs`) — login-to-apply — electronics distribution; Account Manager, EMEA Engineering Graduate Program; Istanbul; email: none found
- **Corteva Agriscience** — `https://corteva.wd5.myworkdayjobs.com/Corteva` (CXS `https://corteva.wd5.myworkdayjobs.com/wday/cxs/corteva/Corteva/jobs`) — login-to-apply — agriculture/seeds & crop protection; Credit Analyst; Adana/Türkiye; email: none found

### Recruitee-hosted
- **oBilet (oBilet Bilişim Sistemleri)** — `https://obilet.recruitee.com` (API `https://obilet.recruitee.com/api/offers/`) — open — travel/ticketing tech; Strategic Planning & Business Specialist, Global Expansion Intern, Digital Marketing, SW Team Lead; Istanbul; email: none found
- **Nucs AI** — `https://nucsai.recruitee.com` (API `https://nucsai.recruitee.com/api/offers/`) — open — AI/medical-imaging startup with Istanbul engineering hub; Machine Learning Engineer, Senior Software Engineer; Istanbul; email: none found
- **Aikido Security** — `https://aikidosecurity.recruitee.com` (API `https://aikidosecurity.recruitee.com/api/offers/`) — open — cybersecurity SaaS; Account Executive Turkey; Istanbul/Ankara; email: none found

### Personio-hosted
- **Sungrow (Sungrow Turkey / EMEA)** — `https://sungrow-emea.jobs.personio.de` (API `https://sungrow-emea.jobs.personio.de/xml`) — open — renewable energy (solar/EV/storage), Istanbul office; EVC Sales Manager - Turkey, ESS Technical Sales Manager - Türkiye; Istanbul; email: none found

### Workable-hosted
- **FERASET** — `https://apply.workable.com/feraset/` (API `https://apply.workable.com/api/v1/widget/accounts/feraset?details=true`) — open — mobile/AI apps scaleup; Senior User Acquisition Manager, AI Engineer, general application; Istanbul; email: none found
- **NewMind AI** — `https://apply.workable.com/newmindai/` (API `https://apply.workable.com/api/v1/widget/accounts/newmindai?details=true`) — open — legal/AI big-data; Business Analyst, Taxonomy Expert, ML/backend; Istanbul (Maslak); email: none found
- **World Business Lenders** — `https://apply.workable.com/commercial-lending/` (API `https://apply.workable.com/api/v1/widget/accounts/commercial-lending?details=true`) — open — fintech/commercial lending; Data Engineering Analyst, Internal Audit Analyst, Marketing Creative Analyst, Operations; Istanbul + İzmir; email: none found
- **Teltonika** — `https://apply.workable.com/teltonika/` (API `https://apply.workable.com/api/v1/widget/accounts/teltonika?details=true`) — open — IoT/electronics; Network Software Engineer + R&D/sales; Istanbul/Ankara; email: none found
- **Ember** — `https://apply.workable.com/ember-1/` (API `https://apply.workable.com/api/v1/widget/accounts/ember-1?details=true`) — open — clean-energy data think tank; Data Engineer, Data Analyst (Clean Power); Istanbul; email: none found
- **VavaCars** — `https://apply.workable.com/vavacars/` (API `https://apply.workable.com/api/v1/widget/accounts/vavacars?details=true`) — open — used-car marketplace; Controlling & Reporting Exec, Customer Center Manager, Vehicle Purchase Manager; Istanbul (Levent/Ümraniye); email: none found
- **TransferGo** — `https://apply.workable.com/transfergo/` (API `https://apply.workable.com/api/v1/widget/accounts/transfergo?details=true`) — open — fintech/money transfers; Senior Data Analyst, Growth Marketing Manager (Turkey); remote-from-Turkey; email: none found
- **Blueground** — `https://apply.workable.com/blueground/` (API `https://apply.workable.com/api/v1/widget/accounts/blueground?details=true`) — open — proptech; Data Analyst, Senior Accounting Associate, People Partner Turkey; Istanbul; email: none found
- **UserWise Services** — `https://apply.workable.com/userwise-services/` (API `https://apply.workable.com/api/v1/widget/accounts/userwise-services?details=true`) — open — mobile F2P games; Data Analyst, Senior Product Manager - Games, Level Designer; remote-from-Turkey; email: none found
- **Huawei (Türkiye)** — `https://apply.workable.com/huawei-telekomunikasyon-dis-ticaret-ltd/` (API `https://apply.workable.com/api/v1/widget/accounts/huawei-telekomunikasyon-dis-ticaret-ltd?details=true`) — open — telecom/R&D; Business Analyst, Data Annotator, Full Stack/Network roles; Istanbul/Ankara; email: none found
- **Symphony Solutions** — `https://apply.workable.com/symphony-solutions/` (API `https://apply.workable.com/api/v1/widget/accounts/symphony-solutions?details=true`) — open — cloud/AI software house; Senior Business Analyst, FullStack Engineer, Lead Gen Manager; remote-from-Turkey; email: none found
- **Emerging Travel Group (RateHawk)** — `https://apply.workable.com/emerging-travel-group/` (API `https://apply.workable.com/api/v1/widget/accounts/emerging-travel-group?details=true`) — open — travel-tech; PR Manager / Area Manager Mediterranean; Ankara; email: none found
- **Intetics** — `https://apply.workable.com/intetics-2/` (API `https://apply.workable.com/api/v1/widget/accounts/intetics-2?details=true`) — open — software/data services; Senior Python Engineer (Airflow/Data Platform); Istanbul; email: none found
- **Oredata** — `https://apply.workable.com/oredata/` (API `https://apply.workable.com/api/v1/widget/accounts/oredata?details=true`) — open — data/IT consulting (Google Cloud partner); Project Manager, Data Analyst, Data Science Team Lead; Istanbul; email: none found
- **Rapsodo** — `https://apply.workable.com/rapsodo/` (API `https://apply.workable.com/api/v1/widget/accounts/rapsodo?details=true`) — open — sports-analytics hardware; Technical Project Manager, BI Intern, Software Architect; İzmir (Bayraklı); email: none found
- **Lucida AI** — `https://apply.workable.com/lucida-ai/` (API `https://apply.workable.com/api/v1/widget/accounts/lucida-ai?details=true`) — open — AI mobile app startup; Product Manager (Mobile), Lead Product Designer, UA Manager; Istanbul; email: none found
- **Sanction Scanner** — `https://apply.workable.com/sanction-scanner/` (API `https://apply.workable.com/api/v1/widget/accounts/sanction-scanner?details=true`) — open — AML/RegTech SaaS; Senior Product Manager, Growth Marketing Lead, Eng Manager; Istanbul (Üsküdar); email: none found
- **Pulse Games** — `https://apply.workable.com/pulsegames/` (API `https://apply.workable.com/api/v1/widget/accounts/pulsegames?details=true`) — open — mobile games; Backend Developer, Game Developer, 3D Artist; remote-from-Turkey; email: none found
- **Cyrex** — `https://apply.workable.com/cyrex/` (API `https://apply.workable.com/api/v1/widget/accounts/cyrex?details=true`) — open — games cybersecurity; Game Reverse Engineer; remote/Istanbul; email: none found
- **Guess Europe Sagl** — `https://apply.workable.com/guess-europe-sagl/` (API `https://apply.workable.com/api/v1/widget/accounts/guess-europe-sagl?details=true`) — open — fashion retail; Marketplace Account Manager, Jr Accounting Specialist, store management; Istanbul (Maslak + malls); email: none found
- **Udelta** — `https://apply.workable.com/udelta/` (API `https://apply.workable.com/api/v1/widget/accounts/udelta?details=true`) — open — car-rental tech; Account Manager (hybrid); Istanbul; email: none found

### Teamtailor-hosted
- **DFDS Türkiye** — `https://dfdsturkey.teamtailor.com` (API `https://dfdsturkey.teamtailor.com/jobs.json`) — open — logistics/shipping; Financial Control & Reporting Manager, Financial Reporting Expert, Project Logistics Lead, Purchaser; Istanbul (Ataşehir/Sultanbeyli); email: none found
- **ÖğretmenBulun** — `https://ogretmenbulun.teamtailor.com` (API `https://ogretmenbulun.teamtailor.com/jobs.json`) — open — edtech/tutoring marketplace; online tutor & programming-tutor roles; Türkiye-wide incl. Istanbul; email: none found
- **TradingView** — `https://tradingview.teamtailor.com` (API `https://tradingview.teamtailor.com/jobs.json`) — open — fintech/charting SaaS; Growth Manager – Türkiye (B2B); remote, must be based in Turkey; email: none found
- **Gamdom** — `https://gamdom.teamtailor.com/jobs` (API `https://gamdom.teamtailor.com/jobs.json`) — open — iGaming/crypto casino; VIP Portfolio Manager (Turkish & English); Istanbul; email: Melanie@teamgamdom.com

### JazzHR-hosted
- **Armut Teknoloji** — `https://armut.applytojob.com` (API `https://armut.applytojob.com/api/v1/jobs`) — open — home-services marketplace; Data Scientist, Growth Marketing Associate Manager, Junior Financial Controller; Istanbul; email: destek@armut.com (general)
- **DefineX Consulting** — `https://definexconsulting.applytojob.com` (API `https://definexconsulting.applytojob.com/api/v1/jobs`) — open — consulting & technology; Technology Design Consultant, Senior Financial Controller, Senior AI Engineer, Siebel Developer; Istanbul; email: none found

### Zoho Recruit-hosted
- **viravira.co** — `https://viravira.zohorecruit.com/jobs/Careers` — open — online yacht-charter marketplace; UI/UX Designer, Digital Communication & Content Specialist, International Sales Expert; Istanbul; email: none found
- **Bentego** — `https://bentego.zohorecruit.com/jobs/Careers` — open — IT services / big-data consulting (Cloudera partner); ETL Developer, Project Manager, Big Data Engineer; Istanbul; email: none found
- **Cloudyflex** — `https://cloudyflex.zohorecruit.com/jobs/Careers` — open — Zoho premium reseller / business-software consulting; Solution Consultant / Business Analyst, Software Development Consultant, Sales; Istanbul; email: info@cloudyflex.com

### Jobvite-hosted
- **RES Group (Renewable Energy Systems)** — `https://jobs.jobvite.com/resgroup` (API `https://jobs.jobvite.com/resgroup/jobs`) — login-to-apply — renewable energy (wind/solar EPC & O&M); Civil Design Engineer (Renewable Energy Projects); Istanbul (Şişli); email: none found

## 10. Platform-coverage additions — 2026-06-21 (batch JAC-58): new-ATS readers + recovered boards

Two new readable ATS platforms now have harvester fetchers: **Hirex** (parsed from the org-page JSON-LD `CollectionPage`) and **BambooHR** (`<token>.bamboohr.com/careers/list` JSON). Every board below was live-verified — a real read returned the listed sample roles. Sipay and Paribu (already catalogued at their `app.gethirex.com/o/...` URLs) became machine-readable automatically via the new Hirex detector, so they need no new row here.

### Hirex boards (`app.gethirex.com/o/<slug>/` — JSON-LD; readable)
- **Çalık Holding** — `https://app.gethirex.com/o/calik-holding/` (Hirex) — open — diversified holding (energy, construction, finance, textile), İstanbul; verified roles incl. İş Analitikleri Danışmanı (Power BI), Kıdemli İş Analitikleri Danışmanı (BPC-BW), Ücret Yönetimi ve İK Analitiği Uzmanı; email: none found
- **Anadolu Hayat Emeklilik** — `https://app.gethirex.com/o/anadolu-hayat-emeklilik/` (Hirex) — open — life-insurance & pensions (İş Bankası group), İstanbul; verified roles incl. Veri Tabanı Uzmanı, Orta Katman Uzmanı, Gelecek Planlama Uzmanı; email: none found
- **Mobven** — `https://app.gethirex.com/o/mobven/` (Hirex) — open — mobile & fintech software house, İstanbul; verified roles incl. Product Manager, Senior Backend Developer (Java), QA Engineer; email: none found
- **SabancıDx** — `https://app.gethirex.com/o/sabancidx/` (Hirex) — open — data/AI & digital tech services (Sabancı Holding), İstanbul/Ankara; verified roles incl. Data & AI Architect, Digital Financial Solutions Manager, Sec Ops & Security Specialist; email: none found
- **Scorp** — `https://app.gethirex.com/o/scorp/` (Hirex) — open — social / creator-tech app, İstanbul; verified roles incl. BI Engineer / Analytics Engineer, AI / ML Engineer; email: none found
- **Invent Analytics** — `https://app.gethirex.com/o/invent-analytics/` (Hirex) — open — retail supply-chain & pricing analytics SaaS (Turkish-founded), İstanbul / remote; verified roles incl. Senior/Staff Software Engineer; email: none found
- **Bruin** — `https://app.gethirex.com/o/bruin/` (Hirex) — open — data platform / developer tooling, İstanbul; verified roles incl. Senior Software Engineer (Golang - Data Platform); email: none found
- **Koton** — `https://app.gethirex.com/o/koton/` (Hirex) — open — retail / fast-fashion, İstanbul HQ + nationwide; verified roles incl. Senior Merchandise Planner, Strategic Finance Manager, Buying Manager; email: none found
- **WorqCompany** — `https://app.gethirex.com/o/worqcompany/` (Hirex) — open — e-commerce marketplace / online-store enablement, Üsküdar İstanbul; verified roles incl. Marketing Analyst, Budget & Controlling Specialist; email: none found
- **GAP İnşaat (Çalık Group)** — `https://app.gethirex.com/o/gap-insaat/` (Hirex) — open — construction / EPC, İstanbul + project sites; verified roles incl. BIM Information Lead, Doküman Kontrol Uzmanı; email: none found
- **Çalık Enerji (Çalık Group)** — `https://app.gethirex.com/o/calik-enerji/` (Hirex) — open — power-plant EPC / energy, İstanbul + project sites; verified roles incl. Master Data & Process Management Specialist, Bütçe Planlama ve Raporlama Uzmanı; email: none found
- **Anbean** — `https://app.gethirex.com/o/anbean/` (Hirex) — open — employer-branding / young-talent comms agency, İstanbul; verified roles incl. Event & Project Specialist, Community Management Specialist; email: none found

### BambooHR boards (`<slug>.bamboohr.com/careers/list` — JSON; readable)
- **Sestek** — `https://sestek.bamboohr.com/careers/list` (BambooHR token `sestek`) — open — conversational AI / speech & NLP analytics, Ankara + İstanbul; verified roles incl. Site Reliability Engineer, DevOps Engineer; email: none found
- **Commencis** — `https://commencis.bamboohr.com/careers/list` (BambooHR token `commencis`) — open — digital product & engineering consultancy, İstanbul; verified roles incl. Backend Developer, Senior Backend Developer, Android Developer; email: none found
- **Paribu (BambooHR board)** — `https://paribu.bamboohr.com/careers/list` (BambooHR token `paribu`) — open — crypto exchange (second readable board alongside its Hirex one), İstanbul; verified roles incl. Digital Marketing Specialist; email: none found

### SmartRecruiters additions (already-supported platform; tokens were missing from the catalog)
- **Bosch (Bosch Group)** — `https://api.smartrecruiters.com/v1/companies/BoschGroup/postings?country=tr` (SmartRecruiters token `BoschGroup`) — open — industrial / mobility / IoT multinational, İstanbul; 49 İstanbul/TR roles verified incl. Solution Architect, CX Analyst; email: none found
- **Experian** — `https://api.smartrecruiters.com/v1/companies/Experian/postings?country=tr` (SmartRecruiters token `Experian`) — open — credit data & analytics / financial services, İstanbul (hybrid); verified role Senior Marketing Specialist; email: none found
- **Tomra** — `https://api.smartrecruiters.com/v1/companies/Tomra/postings?country=tr` (SmartRecruiters token `Tomra`) — open — recycling / sensor-based sorting technology, İstanbul; verified role Sales Manager (MEA); email: none found

### Lever additions (already-supported platform; tokens were missing from the catalog)
- **Trendyol Go** — `https://jobs.lever.co/trendyol-go` (Lever token `trendyol-go`) — open — q-commerce / instant grocery (Trendyol group), İstanbul; verified roles incl. Growth Strategy & Analytics Professional, Consumer Revenue Strategy; email: none found
- **Dataroid** — `https://jobs.lever.co/dataroid` (Lever token `dataroid`) — open — digital analytics & customer-experience SaaS, İstanbul; verified roles incl. Senior Backend Engineer, Customer Success Specialist; email: none found

### Ashby additions (already-supported platform; token was missing from the catalog)
- **Cambly** — `https://jobs.ashbyhq.com/Cambly` (Ashby token `Cambly`) — open — EdTech / online English tutoring (İstanbul marketing hub), İstanbul / remote; verified roles incl. Senior Performance Marketing Specialist, Sales Development Representative; email: none found

### Workable additions (already-supported platform; token was missing from the catalog)
- **Hex Trust** — `https://apply.workable.com/hextrust/` (Workable token `hextrust`) — open — digital-asset custody & wealth management, İstanbul / Turkey; verified roles incl. Institutional Sales Analyst / Associate; email: none found

## 11. Oracle Recruiting Cloud boards — 2026-06-21 (batch JAC-59): new-ATS reader

A new harvester fetcher reads Oracle Fusion Recruiting Cloud (ORC) boards via the public REST list (`<host>/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=<site>`). Each company runs its own host + CX site, so entries carry both (parsed from the CandidateExperience URL and/or the `Oracle host \`…\` site \`…\`` annotation). The boards below were live-verified to return real Turkey postings. The reader reads the 200 most-recent requisitions, so Turkey-concentrated boards are read in full; huge global boards that bury TR jobs (e.g. Hilton, Marriott, Tiffany, Emerson, Wood) were intentionally not catalogued (see `discovery-coverage-audit-2026-06-21.md`).

### Oracle Recruiting Cloud boards (`<host>/hcmUI/CandidateExperience/.../sites/<site>/` — REST; readable)
- **DP World** — `https://ehpv.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs` (Oracle host `ehpv.fa.em2.oraclecloud.com` site `CX_1`) — open — ports / logistics / freight, Kocaeli + İstanbul; 23 TR roles verified incl. Road Freight Operation Specialist, Liquid Operations Manager, Customer Service Specialist; email: none found
- **UN Women (UN shared ORC instance)** — `https://estm.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/jobs` (Oracle host `estm.fa.em2.oraclecloud.com` site `CX`) — open — UN agency, İstanbul (EECARO regional office); verified roles incl. ICT Analyst (NOB), Regional Programme Specialist, Admin & Procurement Associate; email: none found
- **UNDP (UN shared ORC instance)** — `https://estm.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs` (Oracle host `estm.fa.em2.oraclecloud.com` site `CX_1`) — open — UN agency, İstanbul + Ankara; verified roles incl. Programme Analyst, Project Associate; email: none found
- **IOM (International Organization for Migration)** — `https://fa-evlj-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs` (Oracle host `fa-evlj-saasfaprod1.fa.ocs.oraclecloud.com` site `CX_1001`) — open — UN migration agency, İstanbul + Ankara; verified roles incl. Protection Officer (Information Management & Reporting), Senior Programme Support Associate; email: none found
- **Sensient Technologies** — `https://eour.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/jobs` (Oracle host `eour.fa.us2.oraclecloud.com` site `CX`) — open — specialty ingredients / chemicals manufacturing, Gebze (Kocaeli); verified roles incl. Quality Assurance Specialist, Innovation Technician; email: none found
- **Fater** — `https://iaahwm.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1/jobs` (Oracle host `iaahwm.fa.ocs.oraclecloud.eu` site `CX_1`) — open — FMCG (baby & personal care; P&G/Angelini JV), İstanbul + Gebze (Kocaeli); verified roles incl. F&A Assistant, Quality Engineer; email: none found
- **J.P. Morgan Chase** — `https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs` (Oracle host `jpmc.fa.oraclecloud.com` site `CX_1001`) — open — corporate & investment banking, İstanbul; verified TR roles incl. Global Corporate Banking Mid-Cap Associate / Vice President (large global board; only recent postings are fetched per run); email: none found

## 12. Ankara, İzmir & Bursa regional-HQ employers — 2026-06-21 (batch JAC-39): 97 city-headquartered companies

Employers HEADQUARTERED in Ankara, İzmir, or Bursa (prioritizing companies with no İstanbul head office) that the İstanbul-first batches (sections 1b–9b) systematically missed. Each row carries its home city so the Step 0.5 scope filter routes Turkey-outside-İstanbul runs correctly. Most are own-careers-page or Kariyer.net (Mode C, human-apply) sources; few expose a keyless ATS API (regional firms favour own sites, SuccessFactors, Workday, or Kariyer.net). Verified via the JAC-39 parallel research sweep: own-domain careers pages were WebFetch-confirmed to load; Kariyer.net `firma-profil` pages 403 to bots but were confirmed live via search and are human-readable in Mode C.

### Ankara
- **SDT Uzay ve Savunma Teknolojileri** — `https://www.sdt.com.tr/tr/kariyer` — open — defense electronics / radar / EW / satellite ground systems, Ankara (ODTÜ Teknokent); software & production-planning eng; email: hr@sdt.com.tr
- **Simsoft Bilgisayar Teknolojileri** — `https://www.simsoft.com.tr/tr/insan-kaynaklari` — login-to-apply — simulation & serious-games / defense software, Ankara (ODTÜ Teknokent); Unity/C++/Java eng; email: info@simsoft.com.tr
- **BİTES Savunma, Havacılık ve Uzay** — `https://www.bites.com.tr/en/career` — login-to-apply — defense/aerospace software, AR/AI/simulation (ASELSAN subsidiary), Ankara (ODTÜ Teknokent); software/avionics test eng; email: none found
- **Yeter Savunma ve Havacılık** — `https://www.yetersavunma.com/en/open-positions/` — login-to-apply — defense/aerospace precision machining, Ankara (Ostim/Yenimahalle); design/manufacturing eng; email: info@yetersavunma.com
- **TUALCOM Elektronik** — `https://www.tualcomkariyer.com/` — open — RF / defense electronics / anti-jamming / EW, Ankara (Çankaya); RF/embedded eng; email: ik@tualcom.com.tr
- **ULAK Haberleşme** — `https://www.ulakhaberlesme.com.tr/kariyer/` — open — 4G/5G telecom infrastructure & public-safety comms, Ankara; software/network eng, PM; email: info@ulakhaberlesme.com.tr
- **ENOVAS Savunma Teknolojileri** — `https://enovas.com.tr/careers/` — open — EW / radar / RF hardware, Ankara (ODTÜ Teknopark); PM, QA manager, RF/DSP/DevOps eng; email: info@enovas.com.tr
- **ANKA Mikroelektronik Sistemler (ANKASYS)** — `https://www.kariyer.net/firma-profil/anka-mikroelektronik-sistemler-ankasys-137163-60668` — login-to-apply — ASIC/FPGA design & GNSS receivers, Ankara; RTL/verification eng; email: none found
- **ASARTECH Ar-Ge Tasarım Mühendislik** — `https://www.kariyer.net/firma-profil/asartech-ar-ge-tasarim-muhendislik-164415-89192` — login-to-apply — RF/microwave defense & comms electronics, Ankara (Hacettepe Teknokent); PM, RF design eng; email: none found
- **INTECRO Robotik** — `https://www.kariyer.net/firma-profil/intecro-robotik-a-s-43944-211596` — login-to-apply — industrial robotics/automation for defense, Ankara (Yenimahalle); robotics/automation/welding eng; email: none found
- **Teknokar Savunma ve Havacılık** — `https://www.kariyer.net/firma-profil/teknokar-savunma-ve-havacilik-a-s-40123-195882` — login-to-apply — defense/aerospace machining supplier, Ankara (Kahramankazan, Aerospace OSB); manufacturing/quality eng; email: none found
- **Netcad Yazılım** — `https://www.netcad.com/tr/kurumsal/kariyer` — login-to-apply — GIS / smart-city / mapping software (defense & gov geospatial), Ankara (Bilkent Cyberpark); software eng, GIS analyst, BA/PM; email: none found
- **Labris Networks** — `https://labrisnetworks.com/career/` — open — cybersecurity (NG firewall, DDoS, SOC/CERT), Ankara (ODTÜ Technopolis); network-security & full-stack eng, pre-sales; email: info@labrisnetworks.com
- **Miltron Savunma ve Bilişim** — `https://www.miltron.com.tr/en/` — login-to-apply — defense software engineering & test, Ankara (METU Technopolis); software/test eng; email: none found
- **Magnetron Savunma ve Uzay Teknoloji** — `https://www.kariyer.net/firma-profil/magnetron-savunma-ve-uzay` — login-to-apply — defense/space electronics & computer systems, Ankara (Ostim OSB); electronics/software eng; email: info@magnetrontr.com
- **SEKİZA Savunma, Havacılık ve Uzay** — `https://www.kariyer.net/firma-profil/sekiza-savunma-havacilik-ve-uzay-teknolojileri-a-196149-214756` — login-to-apply — defense, civil comms & early-warning systems, Ankara (İvedik OSB); structural-design eng, electronics tech; email: none found
- **RST Uzaktan Algılama ve Güvenlik** — `https://www.kariyer.net/firma-profil/rst-uzaktan-algilama-39005-210768` — login-to-apply — remote sensing & geospatial/security tech, Ankara (Hacettepe Teknokent); software/RS eng; email: none found
- **UDO Games** — `https://udogames.com/career-page/` — open — mobile game publishing (hybrid-casual), Ankara (Çankaya); Live-Ops/UA/BD manager, Data Analyst, backend eng; email: staj@udogames.com
- **Oreon Studios** — `https://oreonstudios.com/jobs/` — open — hypercasual/hybridcasual mobile games, Ankara (Hacettepe Teknopolis); Unity dev, 3D game artist; email: jobs@oreonstudios.com
- **Otsimo** — `https://otsimo.com/en/careers/` — open — special-education / game-based learning apps, Ankara (ODTÜ Teknokent); software, Unity dev; email: none found
- **Başarsoft** — `https://kariyer.basarsoft.com.tr/` — login-to-apply — GIS/mapping software (public-sector CBS), Ankara (Balgat); software, GIS specialist; email: none found
- **Defne Yazılım** — `https://www.defne.com.tr/careers` — login-to-apply — telecom/govtech software, Ankara (ODTÜ Teknokent); software, product; email: hr@defne.com.tr
- **Sisoft Sağlık Bilgi Sistemleri** — `https://www.kariyer.net/firma-profil/sisoft-saglik-bilgi-sistemleri-anonim-sirketi-4486-29369` — login-to-apply — health IT / HBYS, Ankara (ODTÜ Teknokent); software, R&D; email: none found
- **Keydata Bilgi İşlem** — `https://www.kariyer.net/firma-profil/keydata-bilgi-islem-teknoloji-sistemleri-a-s-23093-301220` — login-to-apply — health IT / HBYS (public hospitals), Ankara (Çankaya); Data Analyst, Business Analyst; email: none found
- **Mobiliz** — `https://www.kariyer.net/firma-profil/mobiliz-bilgi-ve-iletisim-teknolojileri-a-s-4940-29823` — login-to-apply — fleet-telematics / IoT SaaS, Ankara (Bilkent Cyberpark); software, IoT/data; email: none found
- **Ekinoks Yazılım** — `https://ekinokssoftware.com/tr/open_positions.html` — open — enterprise / GIS / cloud software, Ankara (Bilkent Cyberpark); .NET/software eng, system support; email: hr@ekinokssoftware.com
- **Lokman Hekim Sağlık Grubu** — `https://www.kariyer.net/firma-profil/lokman-hekim-saglik-grubu-8627-223131` — login-to-apply — private hospital group (BIST: LKMNH), Ankara (Çankaya); PM, finance/data analyst, BI, ops; email: none found
- **Güven Hastanesi (Ankara Güven Hospital)** — `https://www.guven.com.tr/insan-kaynaklari` — open — private hospital, Ankara (Kavaklıdere); finance, ops/data, project; email: none found
- **Özel Çankaya Hastanesi** — `https://www.cankayahastanesi.com.tr/tr/insan-kaynaklari/` — open — private hospital, Ankara (Çankaya); finance, ops, project; email: none found
- **Koru Sağlık Grubu** — `https://www.koruhastanesi.com/ik` — open — private hospital group, Ankara (Çankaya/Balgat); finance, ops/data, project; email: none found
- **Başkent Üniversitesi Hastaneleri** — `https://ankara.baskenthastaneleri.com/tr/insan-kaynaklari/acik-pozisyonlar` — open — foundation-university hospital network, Ankara (Bahçelievler); technical, finance, admin; email: none found
- **TOBB ETÜ Hastanesi** — `https://www.kariyer.net/firma-profil/ozel-tobb-etu-hastanesi-3659-28542` — login-to-apply — university hospital, Ankara (Söğütözü); admin, finance, HR, ops; email: none found
- **Türk İlaç ve Serum Sanayi (Battal Holding)** — `https://www.turkilac.com.tr/tr/kariyer.php` — open — pharmaceutical & serum manufacturer, Ankara (Akyurt); production, QC/R&D, supply-chain, finance, PM; email: insankaynaklari@battalholding.com.tr
- **Başkentgaz (Başkent Doğalgaz Dağıtım GYO)** — `https://www.kariyer.net/firma-profil/baskent-dogalgaz-dagitim-gyo-a-s-160048-120675` — login-to-apply — natural-gas distribution utility, Ankara (Çankaya); finance/data analyst, process, PM, eng; email: none found
- **Özaltın İnşaat** — `https://www.kariyer.net/firma-profil/ozaltin-ins-ve-agac-isleri-tic-ve-san-ltd-sti-22351-13565` — login-to-apply — construction/contracting (dams, rail, metro), Ankara (Çankaya); PM, planning/cost eng, finance/procurement; email: none found
- **Yüksel İnşaat** — `https://www.kariyer.net/firma-profil/yuksel-insaat-a-s-5666-30549` — login-to-apply — construction/infrastructure (dams, HEPP, metro, airports), Ankara; PM, planning, cost, finance analyst; email: none found
- **Mapa İnşaat ve Ticaret (MNG Holding)** — `https://www.kariyer.net/firma-profil/mapa-insaat-ve-ticaret-a-s-31304-223331` — login-to-apply — construction/contracting, Ankara; PM, site/planning, purchasing, finance analyst; email: none found
- **Onur Taahhüt Taşımacılık İnşaat** — `https://www.kariyer.net/firma-profil/onur-taahhut-tasimacilik-insaat-tic-ve-sanayi-a-s-23611-14950` — login-to-apply — transport/infrastructure construction, Ankara (Çankaya); PM, purchasing, planning, finance; email: none found
- **Yiğit Akü** — `http://www.yigitaku.com/tr/insan-kaynaklari` — open — automotive/industrial battery manufacturer, Ankara (Akyurt); production planning, supply-chain, process/quality, finance, PM; email: insankaynaklari@yigitaku.com
- **Mapa Petrol (Mapa A.Ş.)** — `https://mapatr.com/kariyer/` — open — Mobil lubricants distributor, Ankara (Çankaya); sales, supply-chain, finance, ops; email: none found
- **PTT (Posta ve Telgraf Teşkilatı)** — `https://www.ptt.gov.tr/basvuru-online-basvuru-ve-on-basvuru` — restricted — national postal operator + PTTBank, Ankara (Ulus); ops/finance/IT/analyst cadres (exam / Kariyer Kapısı); email: none found

### İzmir
- **Dalan Kimya Endüstri** — `https://www.dalan.com.tr/tr/insan-kaynaklari` — open — soap, oleochemicals & cleaning products, İzmir (Pınarbaşı); production planning, process/quality, R&D, supply-chain; email: none found
- **Ege Profil (Egepen Deceuninck)** — `https://www.kariyer.net/firma-profil/ege-profil-ticaret-ve-sanayi-a-s-8619-33497` — login-to-apply — PVC window/door profiles (BIST), İzmir (Menemen/Çiğli); production/process/quality analyst, PM; email: none found
- **İzmir Demir Çelik (İDÇ)** — `https://www.izdemir.com.tr/en/career/hr-policy` — login-to-apply — steel long products, İzmir (Aliağa); production/process, quality, logistics, financial analyst; email: info@izdemir.com.tr
- **SMS Savunma Sanayi** — `https://www.smssavunma.com.tr/en/kariyer` — restricted — defense (armored-vehicle & artillery components), İzmir (AOSB/Çiğli); design/manufacturing/quality eng, PM; email: info@smssavunma.com.tr
- **Folkart (Folkart Yapı / Saya Holding)** — `https://folkart.com.tr/folkartta-kariyer` — open — real-estate development & construction, İzmir (Bayraklı); PM, BD architect, finance, sales, data; email: insan.kaynaklari@folkart.com.tr
- **Ekoten Tekstil (Sun Group)** — `https://www.kariyer.net/firma-profil/ekoten-tekstil-1452-223980` — login-to-apply — knitted fabric producer (H&M/Zara supplier), İzmir (Torbalı); production planning, process/quality eng, data/BI analyst, PM; email: none found
- **Orva İlaç** — `https://www.orva.com.tr/kariyer` — open — dermatology pharma / cosmetics, İzmir; production, QC/QA, regulatory; email: none found
- **Kent Hospital (Özel Kent Sağlık)** — `https://www.kariyer.net/firma-profil/ozel-kent-saglik-hizmetleri-ve-malzemeleri-a-s-6805-31684` — login-to-apply — private hospital group, İzmir (Çiğli); healthcare admin, finance, HR, IT/data; email: none found
- **Flowla** — `https://careers.flowla.com/` — open — B2B SaaS (AI digital sales rooms), İzmir (also remote); software eng, product, sales, CS, data; email: none found
- **Tariş Zeytin ve Zeytinyağı** — `https://www.kariyer.net/firma-profil/taris-zeytin-a-s-12038-2226` — login-to-apply — olive & olive-oil producer (TA-ZE), İzmir (Çiğli AOSB); production/process, quality, supply-chain, finance; email: none found
- **Tariş Üzüm Tarım Satış Kooperatifleri Birliği** — `https://www.kariyer.net/firma-profil/s-s-taris-uzum-tarimsatis-kooperatifleri-birligi-2613-17719` — login-to-apply — raisin/grape agricultural cooperative union, İzmir (Konak); production, quality, logistics, finance, sales; email: none found
- **Tariş Pamuk Tarım Satış Kooperatifleri Birliği** — `https://www.kariyer.net/firma-profil/taris-pamuk-tarim-satis-kooperatifleri-birligi-27246-18947` — login-to-apply — cotton agricultural cooperative union, İzmir; production, quality, supply-chain, finance; email: none found
- **Kütaş (Kütaş Tarım Ürünleri)** — `https://www.kutas.com.tr/contact-us` — open — food/agri (spices, pasteurized egg, export), İzmir (Kemalpaşa OSB); production, food-safety/quality, supply-chain, export; email: info@kutas.com.tr
- **Roteks Tekstil** — `https://www.roteks.com.tr/human-resources.aspx` — open — apparel/textile manufacturer & exporter (COJ Denim), İzmir (Çiğli AOSB); production planning, process/quality, supply-chain, BI; email: none found
- **Egeplast (Ege Yıldız Group)** — `https://egeplast.com.tr/insan-kaynaklari-politikasi/` — open — plastic pipe manufacturer, İzmir (AOSB/Çiğli); production planning, process/quality, supply-chain, finance; email: ik@egeyildiz.com
- **Çimentaş (Çimentaş İzmir Çimento, OYAK)** — `https://www.cimentas.com.tr/kariyer.aspx` — open — cement producer, İzmir (Bornova); planning, process/quality, finance, supply-chain, data/BI; email: hr@cimentas.com
- **İzeltaş (İzeltaş Demir Çelik)** — `https://izeltas.com.tr/i-k-basvuru-formu/` — open — hand-tools manufacturer, İzmir (Bornova/Işıkkent); production planning, process/quality, supply-chain, finance; email: info@izeltas.com.tr

### Bursa
- **Beyçelik Gestamp Otomotiv** — `https://beycelik.peoplebox.biz/portal/open-positions` — open — automotive Tier-1, chassis / body-in-white stampings, Bursa (Işıktepe OSB, Nilüfer); PM, production/demand planner, quality/process analyst, BI/data, maintenance eng; email: none found
- **Çelikform Gestamp Otomotiv** — `https://www.kariyer.net/firma-profil/celikform-gestamp-otomotiv-as-11799-47597` — login-to-apply — automotive Tier-1, sheet-metal/aluminium forming, Bursa (BOSB Nilüfer); production planner, quality/process analyst, supply-chain, PM; email: none found
- **Rollmech Automotive** — `https://www.kariyer.net/firma-profil/rollmech-automotive-sanayi-ve-ticaret-a-s-4903-29786` — login-to-apply — automotive Tier-1, roll-formed chassis components, Bursa (Minareliçavuş OSB); procurement, sales eng, production, planner, quality; email: none found
- **Ermetal Otomotiv** — `https://www.kariyer.net/firma-profil/ermetal-otomotiv-ve-esya-sanayi-ticaret-a-s-7246-223827` — login-to-apply — automotive Tier-1, metal stamping/welded assemblies & dies, Bursa (Demirtaş OSB); production, quality control, logistics, process eng; email: none found
- **Farba Otomotiv (Bayraktarlar Holding)** — `https://www.kariyer.net/firma-profil/farba-otomotiv-anonim-sirketi-7285-32163` — login-to-apply — automotive exterior lighting & plastics, Bursa; production, quality/process analyst, R&D, supply-chain; email: none found
- **Matay Otomotiv** — `https://www.kariyer.net/firma-profil/matay-otomotiv-a-s` — login-to-apply — automotive Tier-1, exhaust systems, Bursa (Görükle + Karacabey); production, quality, process eng, supply-chain; email: none found
- **Diniz Adient Oto Donanım** — `https://www.dinizadient.com/insan-kaynaklari-2/` — open — automotive Tier-1, seating systems, Bursa (Nilüfer; Diniz Holding); production, quality, planner, PM, supply-chain; email: none found
- **Grammer Koltuk Sistemleri** — `https://www.kariyer.net/firma-profil/grammer-koltuk-sistemleri-sanayi-ve-ticaret-a-s-3643-28526` — login-to-apply — automotive Tier-1, commercial-vehicle & driver seating, Bursa; production planner, quality control, R&D, supply-chain, IT/ERP; email: none found
- **Feka Otomotiv** — `https://fekaautomotive.com/insankaynaklari` — open — automotive Tier-1, fluid systems / pipes, Bursa (Fethiye OSB, Nilüfer); quality, production, planner; email: none found
- **A-Plas Genel Otomotiv** — `https://www.kariyer.net/firma-profil/a-plas-genel-otomotiv-mamulleri-sanayi-ve-ticaret-7127-32005` — login-to-apply — automotive Tier-1, injection-molded plastics, Bursa (DOSAB + Çalı OSB); production, quality/process, supply-chain, planner; email: none found
- **FKT Koltuk Sistemleri** — `https://www.kariyer.net/firma-profil/fkt-27970-19744` — login-to-apply — automotive Tier-1, bus/coach seating, Bursa (OSB); production, quality, R&D, supply-chain; email: none found
- **Aktaş Holding** — `https://www.kariyer.net/firma-profil/aktas-holding-5210-39335` — login-to-apply — automotive Tier-1, air springs / rubber bellows, Bursa; PM, production planner, quality/process analyst, supply-chain, R&D, BI; email: none found
- **SKT Yedek Parça ve Makina (Diniz Holding)** — `https://www.kariyer.net/firma-profil/skt-1234` — login-to-apply — automotive Tier-1/2, rotary shaft / oil seals, Bursa (BOSB); production, quality, process eng, supply-chain; email: none found
- **Burçelik Bursa Çelik Döküm** — `https://www.kariyer.net/firma-profil/burcelik-a-s-7121-31999` — login-to-apply — steel casting/foundry & machining, Bursa (BOSB); production planner, quality/process analyst, casting/metallurgy eng, supply-chain; email: none found
- **Aunde Teknik Tekstil** — `https://www.kariyer.net/firma-profil/aunde-teknik-tekstil-san-a-s-49234-173169` — login-to-apply — automotive Tier-2, seat-cover technical textiles, Bursa; textile/production eng, planner, quality, R&D, supply-chain; email: none found
- **FSS Fren Sistemleri** — `https://www.kariyer.net/firma-profil/fss-fren-sistemleri-sanayi-tic-ltd-sti-22186-13383` — login-to-apply — automotive Tier-1/2, brake systems, Bursa (DOSAB, Osmangazi); production, quality, process eng, supply-chain; email: none found
- **Ak-Pres Metal Yedek Parça** — `https://www.kariyer.net/firma-profil/ak-pres-metal-yedek-parca-san-ve-tic-a-s-5604-30487` — login-to-apply — automotive Tier-1/2, sheet-metal stamping / dies, Bursa (Nilüfer); die design, production, quality/process, planner; email: none found
- **İpeker Tekstil** — `https://www.kariyer.net/firma-profil/ipeker-tekstil-san-ve-tic-a-s-18278-9085` — login-to-apply — woven fashion-fabric textile, Bursa (Nilüfer); planning, supply-chain, finance, process/quality, BA, DA; email: none found
- **Saydam Tekstil** — `https://www.kariyer.net/firma-profil/saydam-tekstil-2917-21063` — login-to-apply — textile, Bursa (Nilüfer, A.O. Sönmez OSB); planning, supply-chain, finance, process/quality; email: none found
- **Nihat Bursalı Tekstil** — `https://www.kariyer.net/firma-profil/nihat-bursali-tekstil-sanayi-ve-ticaret-a-s-14451-4879` — login-to-apply — home-textile (towels, bathrobes), Bursa (Demirtaş OSB); planning, supply-chain, finance, process/quality, BA; email: none found
- **Bursalı Tekstil** — `https://www.kariyer.net/firma-profil/bursali-4292-42679` — login-to-apply — home-textile (towels, cotton yarn), Bursa (DOSAB); planning, supply-chain, finance, process/quality, BA; email: none found
- **Gül Tekstil** — `https://www.gultekstil.com.tr/contact` — open — textile (weaving, fabric & yarn dyeing), Bursa (Demirtaş OSB); planning, supply-chain, finance, process/quality, DA; email: info@gultekstil.com.tr
- **Marteks (Marmara Tekstil)** — `https://www.marteks.com.tr/insan-kaynaklari` — open — home-textile (curtain/upholstery fabric), Bursa (İnegöl OSB); planning, supply-chain, finance, process/quality, BA; email: none found
- **Minteks** — `https://minteks.com.tr/is-basvuru-formu/` — open — home-textile (towels, bathrobes), Bursa (Nilüfer/Başköy); planning, supply-chain, cost-accounting, process/quality, BA; email: info@minteks.com.tr
- **Akbaş Holding (Akbaşlar Tekstil)** — `https://akbasholding.com/insan-kaynaklari/bize-katilin` — open — diversified holding (textile/energy/food), Bursa (Gürsu); production, eng, finance, admin; email: insankaynaklari@akbaslar.com
- **Sönmez Holding (Sönmez ASF)** — `https://www.kariyer.net/firma-profil/sonmez-asf-a-s-330396-380080` — login-to-apply — diversified holding (textile/cement/composites/logistics), Bursa (Demirtaş OSB); production, planning, finance, admin; email: asf.personel@sonmezholding.com.tr
- **Eker Süt Ürünleri** — `https://eker.com/sayfa/Kariyer` — login-to-apply — dairy / food, Bursa (Nilüfer/Odunluk); planning, supply-chain, finance, process/quality, DA, BA; email: none found
- **Marmarabirlik** — `http://www.marmarabirlikakademi.com/tr/insan-kaynaklari-ve-kariyer` — open — olive & olive-oil cooperative union, Bursa (Mudanya); planning, finance, supply-chain, process/quality, food eng; email: marmarabirlik@marmarabirlik.com.tr
- **Köfteci Yusuf** — `https://kofteciyusuf.com/kurumsal/kariyer-firsatlari/` — open — integrated meat & prepared-food + restaurant chain, Bursa (Yenişehir); BA, planning, finance, supply-chain, process/quality; email: none found
- **Saloni Mobilya** — `https://www.kariyer.net/firma-profil/saloni-mobilya-sanayi-ve-ticaret-anonim-sirketi-7775-32653` — login-to-apply — furniture (home/upholstery), Bursa (İnegöl); interior architect, supply-chain, process/quality, export sales; email: ik@saloni.com.tr
- **Starwood Orman Ürünleri** — `https://www.kariyer.net/firma-profil/starwood-orman-urunleri-sanayi-a-s-14131-4527` — login-to-apply — wood panels (chipboard/MDF/melamine), Bursa (İnegöl/Hamzabey); planning, process/quality, supply-chain, export; email: none found
- **Özhan Marketler Zinciri** — `https://www.ozhan.com.tr/kariyer/basvuru` — open — grocery / supermarket chain, Bursa (Nilüfer, NOSAB); store ops, supply-chain, finance, HR; email: insankaynaklari@ozhan.com.tr
- **Akyapak Makina** — `https://akyapak.com/en/kariyer` — open — metal-processing machine-tools, Bursa (Hasanağa OSB/HOSAB); process/maintenance/IT/software eng, planning, production; email: none found
- **Üçge Mağaza Ekipmanları** — `https://ucgegroup.com/career/` — open — metal store-equipment / shelving manufacturer, Bursa (Işıktepe OSB); production, eng, planning, supply-chain, finance; email: none found
- **Alta Metal** — `https://www.altametal.com/Home/Career?language=TR` — open — spare parts & mold / metal manufacturing, Bursa (Işıktepe OSB); production, mold/tooling, quality, eng; email: info@altametal.com
- **B Plas (Gökçen Group)** — `http://www.bplas.com.tr/ikopen.aspx` — open — plastics for white-goods / construction / packaging, Bursa (DOSAB); mold/design, production, process/quality; email: bplas@bplas.com.tr
- **Bursa Beton** — `https://www.bursabeton.com.tr/tr/kariyer` — open — ready-mix concrete / construction materials, Bursa (Osmangazi); plant chief, quality control, production supervisor, planning; email: none found
- **Türk Prysmian Kablo** — `https://prysmiangroup.wd3.myworkdayjobs.com/Careers` — login-to-apply — energy & telecom cable manufacturing, Bursa (Mudanya); production-planning chief, quality/R&D/material eng, HSE, supply-chain; email: none found
- **Bursagaz (EWE Turkey)** — `https://www.kariyer.net/firma-profil/bursagaz-bursa-sehirici-dogalgaz-dgt-tic-tah-a-s-27712-224934` — login-to-apply — natural-gas distribution, Bursa; engineering, technical, admin; email: none found

## 13. Anatolian-hub & regional-HQ employers — 2026-06-21 (batch JAC-61): 71 city-headquartered companies

Second-pass regional expansion (follow-up to section 12 / JAC-39). Employers HEADQUARTERED in the Ankara/İzmir/Bursa deep tails and in Turkey's other industrial hubs (Kocaeli, Konya, Gaziantep, Kayseri, Denizli, Eskişehir, Adana, Manisa, Mersin), each with no İstanbul head office. Own-domain careers pages were WebFetch-verified to load; Kariyer.net `firma-profil` rows are live Mode-C (human-apply) sources. Each row carries its home city for the Step 0.5 scope filter. Few expose a keyless ATS API (regional firms favour own forms / Kariyer.net). A large additional Kariyer.net-only regional SME tail exists (those pages 403 to bots, so a strict loader could not confirm them) and is best captured in a later supervised Mode-C pass.

### Ankara
- **ANOVA Ar-Ge Teknolojileri** — `https://anova.com.tr/career/?lang=en` — open — defense R&D / indigenous subsystems engineering, Ankara (ODTÜ Teknokent); PM, safety/reliability eng, embedded software, finance/process; email: ik@anova.com.tr
- **Asisguard** — `https://www.asisguard.com.tr/en/career/` — open — defense (drones, electro-optic surveillance), Ankara (Çankaya); software/design eng, PM, purchasing, BD/marketing, quality; email: ik@asisguard.com.tr
- **Arvento Mobil Sistemler** — `https://www.kariyer.net/firma-profil/arvento-mobil-sistemler-a-s-21454-188366` — login-to-apply — IoT / M2M fleet-tracking & telematics SaaS, Ankara (Çankaya); fullstack/software eng, data/IoT; email: none found
- **Pavotek (Pavo Tasarım Üretim Elektronik)** — `https://www.pavotek.com.tr/acik-pozisyonlar/` — open — defense electronics / IP-comms & avionics power systems, Ankara (ODTÜ Teknokent); hardware/software design eng, pre-sales network eng; email: none found
- **DivvyDrive (Bilişim Teknolojileri)** — `https://www.kariyer.net/firma-profil/divvydrive-bilisim-teknolojileri-150471` — login-to-apply — corporate cloud file-management & secure storage (govtech), Ankara (Bilkent); software eng, product, ops, PM/BA; email: info@divvydrive.com
- **SciPlay Games Turkey (ex-Alictus)** — `https://www.sciplaygamesturkey.com/` — open — mobile games + game-tech / ML / BI, Ankara (ODTÜ Teknokent); game dev/design, BI, Data Analyst, ML, UA/growth; email: none found
- **Enhencer** — `https://enhencer.com/career` — open — AI advertising / e-commerce performance-marketing SaaS, Ankara (METU Technopolis); full-stack dev, performance-marketing, account mgr, data; email: none found
- **ArgosAI Teknoloji** — `https://www.kariyer.net/firma-profil/argosai-teknoloji-a-s-156691-81421` — login-to-apply — computer-vision / AI for airport ground-ops (FOD detection), Ankara (METU Technopolis); software/AI eng, ops specialist, finance; email: hr@argosai.com
- **BEAM Teknoloji** — `https://www.kariyer.net/firma-profil/beam-teknoloji-as-44417-37806` — login-to-apply — cybersecurity testing & evaluation lab, Ankara (ODTÜ Teknokent); security/software/test eng, accounting; email: none found
- **Agrovisio** — `https://agrovisio.com.tr/` — open — agritech / satellite & AI rural intelligence, Ankara (ODTÜ Teknokent); ML/data eng, agronomy/remote-sensing, data analyst; email: none found
- **Bridgewiz Mühendislik** — `https://www.kariyer.net/firma-profil/bridgewiz-muhendislik-insaat-yazilim-arge-a-s-158456-83133` — login-to-apply — bridge engineering consultancy + bridge-design software R&D, Ankara (ODTÜ Teknokent); civil/bridge eng, software dev, PM; email: none found
- **Dronsan Savunma Havacılık** — `https://www.kariyer.net/firma-profil/dronsan-savunma-havacilik-sanayi-ve-ticaret-limite-292193-336079` — login-to-apply — UAV / unmanned aerial systems, Ankara (OSTİM OSB); UAV/Ardupilot eng, electronics/mechanical eng; email: none found

### İzmir
- **Abalıoğlu Yağ Sanayi** — `https://www.kariyer.net/firma-profil/abalioglu-yag-sanayi-ve-ticaret-a-s-116453-314130` — login-to-apply — vegetable oils & feed raw materials, İzmir (Kemalpaşa); production planner, process/quality analyst, finance analyst, PM; email: none found
- **Abalıoğlu Lezita Gıda** — `https://www.kariyer.net/firma-profil/abalioglu-lezita-gida-sanayi-a-s-1891-9779` — login-to-apply — poultry meat & processed food, İzmir (Kemalpaşa/Bağyurdu); ERP specialist, production/maintenance eng, demand/supply analyst, PM; email: none found
- **Kar-El Demir Tel (Kareltel)** — `https://www.kareltel.com.tr/is-basvurusu/` — open — steel wire (galvanized/armor/mesh/rebar), İzmir (Aliağa); production, quality control, process/maintenance, logistics, eng; email: none found
- **Fıratteks Tekstil (FIRATGROUP)** — `https://www.firatgroup.com.tr/insan-kaynaklari` — open — denim & apparel manufacturing & export, İzmir (Gaziemir); HR, accounting, procurement, sales, production/process/quality, PM; email: info@firatgroup.com.tr
- **Egesim Elektrik** — `https://www.kariyer.net/firma-profil/egesim-elektrik-sanayi-ve-ticaret-anonim-sirketi-11999-2183` — login-to-apply — industrial electrical & automation contracting / panels, İzmir (Menemen); electrical/automation/project eng, PM, HR; email: egesim@egesim.com
- **Ege Vitrifiye Sağlık Gereçleri** — `https://www.egevitrifiye.com/hakkimizda/insan-kaynaklari` — open — ceramic sanitaryware (vitreous china), İzmir; shift supervisor, env technician, export sales chief, production/process/quality; email: none found
- **Ruby Game Studio (Ruby Games)** — `https://rubygamestudio.com/careers` — open — mobile hyper/hybrid-casual games (Rovio-owned İzmir studio), İzmir (Bornova); game designer, 2D/3D artist, developer, product, UA, data/analytics; email: none found

### Bursa
- **AKP Otomotiv** — `https://www.akp.tr/insan-kaynaklari` — open — automotive Tier-1/2, sheet-metal & welded chassis parts, dies, Bursa (Hasanağa OSB/HOSAB); production, quality/process eng, die design, planner, supply-chain; email: akp@akp.com.tr
- **TKG Otomotiv** — `https://www.tkg.com.tr/tr/insan-kaynaklari` — open — automotive Tier-1/2, press-formed sheet metal, heat shields, dies, Bursa (Fethiye OSB/BOSB); production, quality/process eng, planner, supply-chain, R&D, PM; email: none found
- **Kurvalf Vana** — `https://kurvalf.com/job-application/` — open — industrial valves, actuators, wellhead equipment, Bursa (Çalı); design eng, sales support, procurement, production, quality; email: kurvalf@kurvalf.com
- **İnoksan** — `https://www.inoksan.com/corporate/carreer` — open — industrial/commercial kitchen equipment, Bursa (Işıktepe OSB); production, R&D, sales, HR, planning, process eng, PM; email: none found
- **Class CNC** — `https://classcnc.com.tr/kariyer/` — open — CNC machining / precision contract manufacturing, Bursa (Alaaddinbey); CNC operator, machining eng, quality, planning; email: none found
- **Soylu Kalıp (Soylu Aparat Kalıp Otomotiv)** — `https://soylukalip.com/human-resources` — open — automotive Tier-2, sheet-metal parts, dies/molds, Bursa (NOSAB); die maintenance, CNC/press operator, quality control, shift supervisor; email: none found
- **Balakan Plastik** — `https://www.balakan.com.tr/insan-kaynaklari.html` — open — automotive plastic injection parts & mold manufacturing, Bursa (NOSAB); project eng, injection mold maker, production, quality; email: none found
- **Ons Makina (Ons Havacılık)** — `https://nosabistihdam.org.tr/acik-pozisyonlar` — open — aerospace/automotive/rail tooling & assembly lines, Bursa (NOSAB); CNC turning operator, manufacturing eng, assembly, quality; email: none found
- **Gökçelik Çelik Eşya** — `https://nosabistihdam.org.tr/acik-pozisyonlar` — open — store shelving & storage-systems manufacturing, Bursa (NOSAB); robot welding operator, production, planning, quality, supply-chain; email: none found
- **İnallar Otomotiv** — `https://inallar.com.tr/inallar-kariyer` — open — automotive dealer / after-sales service, Bursa (Osmangazi/Ovaakça); service advisor, body/paint master, mechanical technician; email: none found
- **Autoneum Erkurt (Erkurt Holding JV)** — `https://nosabistihdam.org.tr/acik-pozisyonlar` — open — automotive Tier-1, interior trim, acoustic & thermal insulation, Bursa (NOSAB); electrical maintenance technician, production, quality/process eng, supply-chain; email: none found

### Kocaeli
- **Cengiz Makina** — `https://www.cengizmakina.com.tr/kariyer/` — open — automotive precision casting & CNC-machined components (IMPRO group), Kocaeli (TOSB/Çayırova); production/process & quality eng, supply-chain/planning, finance, PM; email: ik@cengizmakina.com.tr
- **Kanca El Aletleri Dövme Çelik** — `https://www.kanca.com.tr/tr/kurumsal/kariyer` — login-to-apply — forged steel hand tools & forged automotive/industrial components, Kocaeli (TOSB/Çayırova); production/process/quality eng, maintenance, design, HR, finance; email: none found
- **EKU Fren ve Döküm** — `https://www.eku.com.tr/careers` — open — automotive brake components & ferrous casting, Kocaeli (TOSB/Çayırova); foundry/machining, engineering, quality/process, planning/logistics, finance, IT; email: none found
- **Takosan** — `https://www.takosan.com.tr/tr/insan-kaynaklari` — login-to-apply — automotive instrument clusters & gauges (Tier-1), Kocaeli (TOSB/Çayırova); production/process/quality, electronics eng, supply-chain, admin; email: none found

### Konya
- **AYD Otomotiv Endüstri** — `https://kariyer.aydtr.com/` — open — automotive components (steering, suspension, brake, aluminum casting), Konya (Konya OSB/Selçuklu); engineering, quality, finance, IT, manufacturing, logistics; email: none found
- **Vaden Otomotiv (VADEN ORIGINAL)** — `https://www.kariyer.net/firma-profil/vaden-otomotiv-sanayi-ve-ticaret-anonim-sirketi-25087-16572` — login-to-apply — commercial-vehicle spare parts & air-brake systems, Konya (Konya OSB/Selçuklu); method/process eng, production, quality, supply-chain; email: none found
- **Bera Holding (ex-Kombassan)** — `https://beraholding.com.tr/kariyer/tr` — open — diversified industrial holding (PVC, bearings, food, paper), Konya (Selçuklu); production manager, electrical-electronics eng, PM/analyst across group; email: info@beraholding.com.tr
- **Pakpen** — `https://www.kariyer.net/firma-profil/pakpen-a-s-1943-10351` — login-to-apply — plastics (PVC windows/doors, insulation, pipe), Konya (Büyükkayacık OSB); production, engineering, quality, sales, planning/analyst; email: none found
- **Enka Süt ve Gıda** — `https://www.enkasut.com/kariyer/` — open — dairy / food, Konya; production, mechanical eng, technician, HR/planning; email: none found
- **Özduman Tarım Makinaları** — `https://www.kariyer.net/firma-profil/ozduman-tarim-mak-san-ve-tic-a-s-148736-73160` — login-to-apply — agricultural machinery (seeders, tillage, cabins), Konya (Büyükkayacık OSB); mechanical/manufacturing eng, CNC, quality, planning; email: none found
- **Çelikel Tarım Makinaları** — `https://www.kariyer.net/firma-profil/celikel-tarim-makinalari-sanayi-ve-ticaret-anonim-47880-42098` — login-to-apply — agricultural machinery (feed mixers, harvesters, balers), Konya (Büyükkayacık OSB); engineering, production, quality, export/sales; email: none found
- **Galipoğlu Hidromas** — `https://www.hidromas.com/kariyer/` — open — hydraulic pumps, cylinders, valves & equipment, Konya (2. OSB/Büyükkayacık); mechanical eng, international sales, after-sales service mgr; email: hidromas@hidromas.com

### Gaziantep
- **Köksan Pet ve Plastik Ambalaj** — `https://koksan.com/tr/insan-kaynaklari-politikamiz` — open — PET preforms & flexible packaging, Gaziantep (4. OSB/Başpınar); HR, production planning, process/quality, supply-chain, finance analyst, eng; email: none found
- **Mutlu Makarnacılık** — `https://www.mutlumakarna.com.tr/tr/iletisim` — open — food (pasta), Gaziantep (2. OSB); production, quality control, logistics, sales, HR; email: none found
- **Erdemoğlu Holding (Merinos)** — `https://erdemoglukariyer.com/` — open — machine carpet & home textiles, yarn, furniture, Gaziantep (Başpınar OSB); broad corporate/engineering roles, internships; email: none found
- **Royal Halı** — `https://www.royalhali.com/insan-kaynaklari` — open — machine carpet manufacturing, Gaziantep (4. OSB); management, specialists, departmental roles; email: none found
- **Beşler Makarna Un İrmik** — `https://www.beslerpasta.com/kurumsal/is-basvuru-formu-6.html` — open — food (pasta, flour/semolina), Gaziantep (Başpınar OSB); production, quality, logistics, sales; email: none found
- **Antepsan Kuruyemiş Gıda** — `https://www.antepsanshop.com/insan-kaynaklarimiz` — open — food (snacks, nuts, confectionery), Gaziantep (5. OSB); HR, production/quality, corporate; email: none found
- **Kadooğlu Holding (Kadoil)** — `https://kadoil.com/en/human-resources/` — open — vegetable oils & margarine + fuel distribution, Gaziantep (4. OSB/Başpınar); engineers (env/OHS), corporate, finance, regional; email: none found

### Kayseri
- **Kaydöksan (Kayseri Döküm)** — `https://www.kaydoksan.com.tr/ikkariyer.html` — open — iron casting / foundry, Kayseri (Kayseri OSB); production/process eng, quality, planning, supply-chain, maintenance; email: bilgi@kaydoksan.com.tr
- **Kayseri Şeker** — `https://www.kayseriseker.com.tr/kurumsal/insan-kaynaklari` — open — sugar / food processing, Kayseri (Kocasinan); production/process eng, planning, finance, agronomy, IT; email: none found
- **HES Kablo (Hes Hacılar Elektrik)** — `https://www.hes.com.tr/ise-alim` — login-to-apply — cable & wire manufacturing, Kayseri (Hacılar); engineering, production, sales, planning, supply-chain; email: none found
- **Erbosan (Erciyas Boru)** — `https://erbosan.com.tr/insan-kaynaklari/` — open — welded steel pipe & box profile (BIST), Kayseri (Kayseri OSB); production/maintenance eng, quality, planning, finance, sales; email: none found
- **Has Çelik (Hasçelik)** — `https://hascelik.com/kariyer` — login-to-apply — steel wire, rope & cable, Kayseri (Kayseri OSB); engineering, production, quality, planning, supply-chain; email: none found
- **Kilim Mobilya** — `https://kilimmobilya.com.tr/insan-kaynaklari` — open — furniture manufacturing, Kayseri (Kayseri OSB); HR, sales, accounting, production, design, logistics; email: none found
- **Femaş Metal** — `https://www.kariyer.net/firma-profil/femas-metal-sanayi-ve-ticaret-a-s-29612-21547` — login-to-apply — kitchen appliances / cookers & ovens, Kayseri (Kayseri OSB); planning/quality eng, accounting, export specialist, marketing; email: none found
- **Erciyes Çelik Halat-Tel** — `https://www.erciyesanadolu.com/tr/insan-kaynaklari/ise-alim` — login-to-apply — steel wire & rope manufacturing, Kayseri (Mimarsinan OSB); production/process eng, quality, planning, supply-chain; email: none found

### Denizli
- **Abalıoğlu Holding** — `https://www.abalioglu.com.tr/career.aspx?groupId=9&Id=35` — open — diversified conglomerate (feed, poultry/food, energy, textiles), Denizli (Honaz/Denizli OSB); budget/reporting, accounting/finance, PM, HR, supply-chain, IT/data; email: none found
- **Er-Bakır Elektrolitik Bakır** — `https://www.erbakir.com.tr/is-ilanlari` — open — electrolytic copper wire & conductors, Denizli (Bozburun/Merkezefendi); accounting, R&D lab, metallurgy/mechanical/electrical/chemical eng, quality, maintenance, logistics; email: erbakir@erbakir.com.tr
- **Kocaer Çelik (Kocaer Steel)** — `https://www.kocaersteel.com/en/job-application` — open — structural steel profile manufacturing & export (BIST), Denizli (Gümüşçay/Merkezefendi); R&D, IT, budget/finance, foreign trade, ops, industrial sales, quality, HR; email: none found
- **Başaranlar Mermer** — `https://basaranlar.com.tr/en/person` — open — marble & travertine quarrying/processing & export, Denizli (Honaz/Denizli OSB); engineering, quality, finance, sales/export, production; email: none found
- **Gamateks Tekstil** — `https://www.gamateks.com/human-resources/` — open — integrated home & apparel textiles, Denizli (Denizli OSB); HR, planning, industrial eng, e-commerce/digital marketing, sales; email: insankaynaklari@gamateks.com.tr
- **Deniz Tekstil** — `https://www.deniztekstil.com.tr/human-resources` — open — integrated textile (yarn, knitting, printing, garment), Denizli (Honaz OSB); HR, planning, industrial eng, production, quality; email: personel@deniztekstil.com.tr
- **Altınbaşak Tekstil** — `https://www.kariyer.net/firma-profil/altinbasak-tekstil-san-tic-a-s-7160-32038` — login-to-apply — home textiles (bed-linen, towel/bathrobe), Denizli (Honaz/Denizli OSB); export marketing, regional sales, QA, planning, industrial eng; email: none found

### Eskişehir & Adana
- **Tat Nişasta** — `https://www.tatnisasta.com.tr/tr/HumanResources` — open — corn starch / glucose-fructose syrup, Adana (Hacı Sabancı OSB/Sarıçam); production eng, maintenance, quality, R&D, planning, finance/process analyst; email: none found
- **Yüksel Makina** — `http://www.yukselmakina.com.tr/` — open — CNC machining / machined parts for automotive & white-goods, Eskişehir (Eskişehir OSB/Odunpazarı); manufacturing/production eng, CNC planning, quality, maintenance; email: none found

### Manisa & Mersin
- **Klimasan Klima (Metalfrio group)** — `https://www.klimasan.com.tr/kariyer` — open — commercial refrigeration & cooling cabinets, Manisa (Manisa OSB/Yunusemre); production planner, supply-chain/process analyst, HR, finance, PM, eng; email: none found
- **Olgun Çelik (Çelik Holding)** — `https://www.olguncelik.com.tr/kariyer` — open — leaf springs & automotive metal forming, Manisa (Keçiliköy OSB/Yunusemre); production/process eng, quality analyst, supply-chain, PM; email: none found
- **Yonca Gıda** — `https://www.yonca.com.tr/tr/insan-kaynaklari/` — open — food processing (edible oils, tomato paste, canned, sauces), Manisa (Manisa OSB/Yunusemre); manager-candidate program, supply-chain, production planner, finance, quality, PM; email: none found
- **Mersin Gıda** — `https://mersingida.com/en/human-resources/` — open — food production & storage/logistics, Mersin (Akdeniz); production, logistics/supply-chain, sales, corporate; email: mersin@mersingida.com
- **Gülmer Lojistik** — `https://www.gulmer.com.tr/insankaynaklari.html` — open — integrated logistics & freight forwarding, Mersin (Karaduvar/Akdeniz); logistics/ops specialist, customs, supply-chain, sales; email: ik@gulmer.com.tr

## 13b. Regional SME tail (Kariyer.net Mode-C) — 2026-06-21 (batch JAC-61, Mode-C pass): 122 city-headquartered companies

Mode-C continuation of section 13. Regional-HQ SMEs (OSB suppliers, food/agri, textile, machinery) whose public job listing is a Kariyer.net `firma-profil` page (human-apply, Mode C); the real Kariyer.net URL for each was found via web search (these pages 403 to bots, so apply is human-only per the catalog convention). A few carry an own careers page (tier `open`). Each row is tagged with its home city for the Step 0.5 scope filter; no keyless ATS APIs (these firms recruit via Kariyer.net or own forms).

### Ankara
- **Atel Teknoloji ve Savunma Sanayi** — `https://www.kariyer.net/firma-profil/atel-teknoloji-ve-savunma-sanayi-a-s-20792-11850` — login-to-apply — defense electronics (EW, RF jamming, comms), Ankara (OSTİM/Yenimahalle); RF/electronics design eng, card design, electromechanical assembly; email: none found
- **2G Havacılık Elektronik** — `https://www.kariyer.net/firma-profil/2g-havacilik-elektronik-san-ve-tic-a-s-172381-211931` — login-to-apply — defense/aerospace electromechanical assembly & harness, Ankara (OSTİM); electrical-electronic eng, mechanical eng, production tech; email: none found
- **3EN Savunma ve Havacılık Sistemleri** — `https://www.kariyer.net/firma-profil/3en-savunma-ve-havacilik-sistemleri-a-s-140681-83995` — login-to-apply — defense/aviation cable & RF assemblies, Ankara (Etimesgut); R&D eng, electrical-electronic tech, harness/RF assembly; email: none found
- **Arca Savunma Sanayi** — `https://www.kariyer.net/firma-profil/arca-savunma-sanayi-324454-373352` — login-to-apply — defense (heavy ammunition steel), Ankara (Başkent OSB); manufacturing/quality eng, production, procurement, planning; email: none found
- **HESA Savunma Sistemleri** — `https://www.kariyer.net/firma-profil/hesa-savunma-sistemleri-anonim-sirketi-214374-245832` — login-to-apply — defense cable & harness production, platform integration, Ankara (Yenimahalle/Macun); harness tech, electromechanical assembly, integration; email: none found
- **Savtam Elektronik Yazılım (Digitest)** — `https://www.kariyer.net/firma-profil/savtam-elektronik-yazilim-a-s-5029-46880` — login-to-apply — defense electronics, automatic test equipment, software, Ankara (OSTİM OSB); test-systems eng, electronics eng, software, procurement eng; email: none found
- **Barko-Med Elektronik** — `https://www.kariyer.net/firma-profil/barko-med-elektronik-ticaret-a-s-43648-37873` — login-to-apply — defense & medical electronics, Ankara (İvedik OSB); electronics eng, embedded/hardware, production, quality; email: none found
- **Dora Makina İmalat** — `https://www.kariyer.net/firma-profil/dora-makina-imalat-sanayi-ve-tic-ltd-sti-204211-234836` — login-to-apply — precision CNC machining (aerospace/space/energy/medical), Ankara (OSTİM OSB); production chief, CNC operator, CAD/CAM tech, quality; email: none found
- **Yeter Makina (Tasarım İmalat Otomasyon)** — `https://www.kariyer.net/firma-profil/yeter-makina-muhendislik-tasarim-imalat-otomasyon-152677-77328` — login-to-apply — special-purpose machinery & automation, Ankara (OSTİM OSB); mechanical/design eng, automation, machining; email: none found
- **Hakan Makina XCMG** — `https://www.kariyer.net/firma-profil/hakan-makina-xcmg-206743-237574` — login-to-apply — construction-machinery distribution & after-sales (XCMG Türkiye), Ankara (OSTİM OSB); sales/project-sales eng, service eng, spare-parts, after-sales; email: none found
- **Hidropar Ankara (Hidrolik Pnömatik)** — `https://hidroparankara.com.tr/kariyer/` — open — industrial hydraulics/pneumatics & motion control (Bosch Rexroth distributor), Ankara (OSTİM OSB); application/sales eng, automation eng, technical service, supply-chain; email: info@hidroparankara.com.tr
- **Hidroan Ankara (Hidrolik Makina)** — `https://www.kariyer.net/firma-profil/hidroan-ankara-hidrolik-mak-san-tic-ltd-sti-117760-112199` — login-to-apply — industrial & mobile hydraulics + defense integration, Ankara (OSTİM OSB); mechanical/hydraulics design eng, electrical-electronics, production; email: none found
- **Megasoft Teknoloji** — `https://www.kariyer.net/firma-profil/megasoft-teknoloji-a-s-283389-325764` — login-to-apply — custom software & ERP (1C:Enterprise), Ankara (Çankaya); web/full-stack dev, ERP consultant, business-process analyst; email: none found

### Bursa
- **Presmetal** — `https://www.kariyer.net/firma-profil/presmetal-5775-30658` — login-to-apply — automotive Tier-2, welded sheet-metal parts & molds, Bursa (HOSAB/Nilüfer); production, quality/process eng, planner, die/mold, supply-chain; email: none found
- **Vatan Pres Otomotiv** — `https://www.kariyer.net/firma-profil/vatan-pres-11691-1845` — login-to-apply — automotive Tier-2, sheet-metal stamping & welded assemblies, Bursa (Mudanya); press operator, sales eng, production, quality, planner; email: none found
- **Körüstan Bursa Sac Pres** — `https://www.kariyer.net/firma-profil/korustan-bursa-sac-pres-sanayi-ve-ticaret-a-s-63636-139159` — login-to-apply — metal cutting/pressing/bending (automotive sub-industry), Bursa (Beşevler KSS/Nilüfer); production, quality, process, planning, supply-chain; email: none found
- **Presimsan** — `https://www.kariyer.net/firma-profil/presimsan-15410-5934` — login-to-apply — automotive Tier-2, deep-drawing sheet-metal & progressive dies, Bursa (Kestel 2. OSB); press/die, production, quality, welding, planner; email: none found
- **Sonar Otomotiv** — `https://www.kariyer.net/firma-profil/sonar-otomotiv-sanayi-ve-ticaret-anonim-sirketi-337160-387760` — login-to-apply — automotive Tier-2/3, precision/progressive press parts, Bursa (DOSAB/Demirtaş OSB); production, quality/process eng, die, planner, supply-chain; email: none found
- **NSK Group ROTA** — `https://www.kariyer.net/firma-profil/nsk-group-rota-22214-213084` — login-to-apply — automotive Tier-1/2, hot/closed-die forging (steering/suspension), Bursa (Karacabey); forging/machining eng, production, quality/process, planner, supply-chain; email: none found
- **Gürsoylar** — `https://www.kariyer.net/firma-profil/gursoylar-a-s-8163-33041` — login-to-apply — hot forging + machining (automotive/industrial), Bursa (NOSAB/Nilüfer); forging/machining eng, production, quality, planner, supply-chain; email: none found
- **OK-LAS Okyanus Lastik** — `https://www.kariyer.net/firma-profil/ok-las-okyanus-lastik-96797-164555` — login-to-apply — rubber, anti-vibration mounts, seals (automotive), Bursa (Çalı/Nilüfer); rubber-press, production, quality, R&D, planner; email: none found
- **Elatek Kauçuk** — `https://www.kariyer.net/firma-profil/elatek-kaucuk-sanayi-ticaret-a-s-4920-29803` — login-to-apply — automotive Tier-1, rubber compounds/hoses/molded parts, Bursa (Alaşar OSB/Osmangazi); production, quality/process eng, R&D, planner, supply-chain; email: none found
- **Plaskar Plastik Enjeksiyon (Orakçı Group)** — `https://www.kariyer.net/firma-profil/plaskar-plastik-enjeksiyon-otomotiv-a-s-14942-37053` — login-to-apply — automotive Tier-1/2, plastic injection parts & molds, Bursa (Kayapa OSB/Nilüfer); injection/mold, production, quality/process eng, planner; email: none found
- **Gürplast Plastik** — `https://www.kariyer.net/firma-profil/gurplast-plastik-sanayi-ve-ticaret-a-s-12603-2847` — login-to-apply — automotive plastics, air-suspension pistons, Bursa (Alaşar OSB/Osmangazi); injection, production, quality/process, planner, supply-chain; email: none found
- **Etka-D Otomotiv Plastik Kalıp** — `https://www.kariyer.net/firma-profil/etka-d-otomotiv-plastik-kalip-san-ve-tic-ltd-st-31527-23653` — login-to-apply — automotive Tier-2, plastic injection parts & molds, Bursa (Minareliçavuş OSB/Nilüfer); mold design, R&D, injection, production, quality; email: none found
- **Burplast Bursa Plastik** — `https://www.kariyer.net/firma-profil/burplast-bursa-plastik-san-tic-anonim-sti-58860-135383` — login-to-apply — plastic extrusion / PVC compound, Bursa (Kayapa/Nilüfer); extrusion, mold, production, quality/process, planner; email: none found
- **ECS Elektrik Enjeksiyon ve Kablo Sistemleri** — `https://www.kariyer.net/firma-profil/ecs-elektrik-enjeksiyon-ve-kablo-sistemleri-san-17265-7973` — login-to-apply — automotive Tier-2, wiring harnesses, Bursa (NOSAB/Nilüfer); production, quality/process eng, supply-chain, planner; email: none found
- **Odelo Otomotiv Aydınlatma (Bayraktarlar Holding)** — `https://www.kariyer.net/firma-profil/odelo-7285-225818` — login-to-apply — automotive Tier-1, exterior lighting, Bursa (Minareliçavuş OSB/Nilüfer); R&D/design eng, production, quality/process, planner, BI; email: none found
- **Can Metal (Yeşilova Holding)** — `https://www.kariyer.net/firma-profil/can-metal-1945-225274` — login-to-apply — aluminium/metal & casting (automotive), Bursa (Nilüfer); production, casting/process eng, quality, planner, supply-chain; email: none found
- **Marsteks (Yılmaz Group)** — `https://www.kariyer.net/firma-profil/marsteks-dosemelik-kumas-dokuma-tekstil-konf-san-t-8456-388142` — login-to-apply — home textile, upholstery & curtain fabric, Bursa (DOSAB/Osmangazi); planning, supply-chain, process/quality, finance, export; email: none found
- **Rekor Dokumacılık** — `https://www.kariyer.net/firma-profil/rekor-dokumacilik-san-ve-tic-a-s-4826-29709` — login-to-apply — textile weaving (upholstery/curtain/tulle), Bursa (BOSB/Nilüfer); planning, supply-chain, process/quality, industrial eng, sales; email: none found
- **Kaçar Tekstil** — `https://www.kariyer.net/firma-profil/kacar-tekstil-6107-30988` — login-to-apply — textile, jacquard upholstery & curtain fabric, Bursa (BOSB/Nilüfer); planning, supply-chain, process/quality, export sales, finance; email: none found
- **Polteks Tekstil Makinaları** — `https://www.kariyer.net/firma-profil/polteks-tekstil-makinalari-san-ve-tic-ltd-sti-9932-34810` — login-to-apply — textile machinery & PU/rubber machine parts, Bursa (Kayapa/Nilüfer); machine/mechanical eng, production, design, quality, planner; email: none found

### İzmir
- **İmbat Soğutma Isıtma Makina** — `https://www.kariyer.net/firma-profil/imbat-sogutma-isitma-makina-sanayi-ve-ticaret-a-s-8388-209948` — login-to-apply — industrial refrigeration & HVAC machinery, İzmir (Kemalpaşa OSB); production, process/quality, supply-chain, project/sales eng; email: none found
- **SESA Ambalaj ve Plastik** — `https://www.kariyer.net/firma-profil/sesa-ambalaj-ve-plastik-san-tic-as-33077-25358` — login-to-apply — flexible packaging / barrier films, İzmir (Kemalpaşa OSB); production planner, process/quality analyst, supply-chain, PM; email: none found
- **Kastaş Sızdırmazlık Teknolojileri** — `https://www.kastas.com.tr/kurumsal` — login-to-apply — hydraulic/pneumatic sealing & engineering plastics, İzmir (Menemen/Atatürk Plastik OSB); production planner, process/quality, R&D, supply-chain, data/BI, PM; email: none found
- **Dirinler Makina / Döküm** — `https://www.kariyer.net/firma-profil/dirinler-makina-7514-32392` — login-to-apply — machinery & cast-iron foundry, İzmir (Çiğli AOSB); casting/metallurgy eng, production planner, quality/process analyst, supply-chain; email: none found
- **Baylan Ölçü Aletleri** — `https://www.kariyer.net/firma-profil/baylan-olcu-aletleri-aosb-cigli-19535-10467` — login-to-apply — water & electricity meters, İzmir (Çiğli AOSB); production planner, process/quality, R&D, supply-chain, ERP; email: none found
- **Atik Metal** — `https://www.kariyer.net/firma-profil/atik-metal-sanayi-ve-ticaret-a-s-71558-145022` — login-to-apply — grey/ductile iron casting foundry, İzmir (Çiğli AOSB/Aliağa); foundry/metallurgy eng, production planner, quality/process analyst, supply-chain, PM; email: none found
- **TP Elektrik Malzemeleri** — `https://www.kariyer.net/firma-profil/tp-elektrik-malzemeleri-san-ve-tic-a-s-7208-201749` — login-to-apply — industrial electrical products (cable management/busbar), İzmir (Kemalpaşa OSB); production planner, process/quality analyst, export sales, supply-chain, R&D; email: none found
- **Viking Temizlik ve Kozmetik (Avcı Kimya)** — `https://www.kariyer.net/firma-profil/viking-temizlik-ve-kozmetik-urn-paz-san-tic-a-28157-19949` — login-to-apply — detergents & cosmetics, İzmir (Kemalpaşa OSB); production planner, process/quality, R&D, demand planner, supply-chain, BI; email: none found
- **Ege Gübre Sanayii** — `https://www.kariyer.net/firma-profil/ege-gubre-sanayii-a-s-159410-120565` — login-to-apply — composite fertilizer / chemicals (BIST: EGGUB), İzmir (Aliağa/Nemrut); production planner, process/quality analyst, port/logistics, finance, PM; email: none found
- **Krom Mutfak** — `https://www.kariyer.net/firma-profil/krom-mutfak-san-tic-a-s-51319-38373` — login-to-apply — industrial kitchen equipment / stainless machinery, İzmir; production, CNC/manufacturing eng, project/sales, planning, quality; email: none found
- **Özdoğanplast (Özdoğan Plast)** — `https://www.kariyer.net/firma-profil/ozdogan-plast-plastik-ve-kimyevi-maddeler-paz-san-7582-32460` — login-to-apply — plastic pipes (PVC/PE/PPRC), İzmir (Kemalpaşa OSB); production planner, process/quality, export sales, supply-chain; email: none found
- **Vansan Makina** — `https://vansan.com.tr/en/human-resources/job-application` — open — submersible pumps & motors (Ebara affiliate), İzmir (Çiğli AOSB); production eng, demand/supply planner, process/quality, R&D, HR, supply-chain; email: none found
- **Levent Kağıt** — `https://www.kariyer.net/firma-profil/levent-kagit-san-ve-tic-a-s-13758-4116` — login-to-apply — packaging, industrial & tissue paper, İzmir (Kemalpaşa); production planner, process/quality analyst, supply-chain, finance, PM; email: none found
- **Ve-Ge Hassas Kağıt ve Yapıştırıcı Bant** — `https://www.kariyer.net/firma-profil/ve-ge-hassas-kagit-ve-yapistirici-bant-sanayi-ve-t-9592-34470` — login-to-apply — specialty paper & adhesive tape, İzmir (Kemalpaşa OSB); production planner, process/quality, R&D, supply-chain, export sales; email: none found
- **Fersan Fermantasyon Ürünleri** — `https://www.kariyer.net/firma-profil/fersan-fermantasyon-urunleri-san-ve-tic-a-s-25619-17157` — login-to-apply — vinegar, pickles & fermented food, İzmir (Kemalpaşa/Çınarköy); production planner, food-safety/quality, R&D, supply-chain, BI; email: none found

### Kocaeli
- **Aromsa** — `https://www.aromsa.com/is-ilanlari` — open — food aromas & flavour ingredients, Kocaeli (Gebze/GOSB); production/quality, R&D, supply-chain, finance, HR; email: none found
- **Pimsa Otomotiv** — `https://www.kariyer.net/firma-profil/pimsa-otomotiv-a-s-2904-20920` — login-to-apply — automotive interior/acoustic parts (Tier-1), Kocaeli (Çayırova/TOSB); process/quality analyst, supply-chain/planning, production, finance; email: none found
- **Çayırova Boru (Yücel Group)** — `https://www.kariyer.net/firma-profil/cayirova-boru-san-ve-tic-a-s-22545-201118` — login-to-apply — steel pipe & construction profiles, Kocaeli (Darıca); production/supply-chain planner, process/quality analyst, sales analyst; email: none found
- **Malva Kozmetik (Topface)** — `https://www.kariyer.net/firma-profil/malva-kozmetik-110496-107119` — login-to-apply — colour cosmetics manufacturing, Kocaeli (Gebze/GEPOSB); production/quality analyst, supply-chain, sales/marketing analyst; email: none found
- **SAMM Teknoloji İletişim** — `https://www.kariyer.net/firma-profil/samm-teknoloji-iletisim-san-ve-tic-a-s-15728-6283` — login-to-apply — fibre-optic cable & telecom (R&D center), Kocaeli (Gebze/GOSB); production/process eng-analyst, R&D, supply-chain, finance; email: none found
- **Bericap Kapak** — `https://www.kariyer.net/firma-profil/bericap-kapak-san-ve-a-s-11699-1853` — login-to-apply — plastic closures/caps (injection), Kocaeli (Gebze/Beylikbağı); production planner, process/quality analyst, supply-chain analyst; email: none found
- **Makersan Makina Otomotiv** — `https://www.kariyer.net/firma-profil/makersan-makina-otomotiv-sanayi-ticaret-anonim-sir-14113-40361` — login-to-apply — automotive/mechatronic sensors & metal parts, Kocaeli (Gebze); production/process & quality, supply-chain, electronics/R&D, finance; email: none found
- **Tepro Makina ve Otomasyon** — `https://www.kariyer.net/firma-profil/tepro-makina-ve-otomasyon-sistemleri-san-ve-tic-a-32840-25098` — login-to-apply — plastic-injection machinery & automation, Kocaeli (Gebze/Güzeller OSB); sales/projects, technical service, finance, supply-chain; email: none found
- **BM Makina** — `https://www.kariyer.net/firma-profil/bm-makina-san-ve-tic-as-29921-21887` — login-to-apply — crane/lifting & cable-reel industrial equipment, Kocaeli (Gebze/Güzeller OSB); design/mechanical eng-analyst, production planner, sales, finance; email: none found
- **Sunkem Endüstri Ürünleri** — `https://www.kariyer.net/firma-profil/sunkem-endustri-urunleri-san-tic-a-s-261826-300879` — login-to-apply — paints, construction chemicals & pigment pastes, Kocaeli (Çayırova); production eng-analyst, R&D, export/sales, quality; email: none found
- **Tayaş Gıda** — `https://www.kariyer.net/firma-profil/tayas-gida-san-tic-a-s-6056-30937` — login-to-apply — confectionery, caramel & chocolate, Kocaeli (Gebze); production/quality, supply-chain/planning, export sales, finance; email: none found
- **Toksan Yedek Parça (Küçükoğlu Holding)** — `https://www.kariyer.net/firma-profil/toksan-yedek-parca-imalat-tic-ve-san-a-s-5604-37304` — login-to-apply — automotive sheet-metal parts (Tier-1, R&D center), Kocaeli (Çayırova/TOSB); process/quality analyst, production planner, supply-chain, R&D, finance; email: none found
- **Coster Aerosol Valf (Aerosol Valf Sanayi)** — `https://www.kariyer.net/firma-profil/aerosol-valf-sanayi-a-s-25663-17206` — login-to-apply — aerosol valves & spray systems, Kocaeli (Gebze/GEPOSB); production/shift supervisor, quality control, OHS, mixing eng; email: none found
- **Tekno Kauçuk Sanayii** — `https://www.kariyer.net/firma-profil/tekno-kaucuk-sanayii-anonim-sirketi-2060-11638` — login-to-apply — rubber parts (automotive/white-goods/rail/defense), Kocaeli (Gebze/GOSB); process/quality analyst, production planner, R&D, supply-chain; email: none found
- **Tork Bağlantı Elemanları** — `https://www.kariyer.net/firma-profil/tork-baglanti-elemanlari-sanayi-ve-ticaret-anonim-32577-24808` — login-to-apply — hose clamps & fastening systems, Kocaeli (Dilovası/İMES OSB); production, CNC/process, quality, regional sales; email: none found
- **Pimtaş Plastik İnşaat Malzeme** — `https://pimtas.com/kariyer/` — open — U-PVC/PP/HDPE pipes, fittings & valves, Kocaeli (Gebze/GEPOSB); production/process & quality, supply-chain, HR, digital marketing; email: ik@pimtas.com

### Konya
- **Özdöken Tarım Makinaları** — `https://www.kariyer.net/firma-profil/ozdoken-tarim-makineleri-27988-19763` — login-to-apply — agricultural machinery (seeders, soil-cultivation), Konya (Selçuklu/Horozluhan OSB); mechanical/manufacturing eng, CAD/CAM, foreign-trade, after-sales mgr, quality, planning; email: none found
- **Komsilaj (KOM Değirmen)** — `https://komsilajmakine.com/insan-kaynaklari` — open — agricultural machinery (silage/baler), Konya (Selçuklu/Büyükkayacık 5. OSB); mechanical eng, production, manufacturing, quality, HR; email: none found
- **Konya Anadolu Tarım Makinaları** — `https://www.kariyer.net/firma-profil/konya-anadolu-tarim-makinalari-hayvancilik-ve-insa-121383-114763` — login-to-apply — agricultural machinery (bale shredders), Konya (Konya OSB); manufacturing/mechanical eng, production, welding, quality, sales; email: none found
- **İmaş Makina (İttifak Holding)** — `https://www.kariyer.net/firma-profil/imas-makina-san-a-s-14070-36885` — login-to-apply — machinery (flour/feed milling plants), Konya (Konya OSB); machine/mechanical eng, R&D, HR, project, quality, foreign trade, automation; email: none found
- **Selva Gıda (İttifak/Loras Holding)** — `https://www.kariyer.net/firma-profil/selva-gida-san-a-s-14070-36908` — login-to-apply — food (pasta, flour, semolina), Konya (Konya OSB/Büyükkayacık); food eng, production, quality, supply-chain, export/sales, planning, HR; email: none found
- **Helvacızade Gıda İlaç Kimya (Zade)** — `https://www.kariyer.net/firma-profil/helvacizade-gida-ilac-kimya-sanayi-ve-ticaret-a-s-4293-201734` — login-to-apply — food/FMCG (edible oils), Konya (Selçuklu/Büyükkayacık OSB); food/chemical eng, production, quality, R&D, supply-chain, finance, sales; email: none found
- **Anı Bisküvi** — `https://www.kariyer.net/firma-profil/ani-biskuvi-10319-346` — login-to-apply — food (biscuits, chocolate, confectionery), Konya (Selçuklu); food eng, production, quality control, planning, sales, maintenance; email: none found
- **Meydan Group Otomotiv** — `https://www.kariyer.net/firma-profil/meydan-group-otomotiv-san-a-s-307542-353836` — login-to-apply — automotive supply (body sheet-metal parts, lighting, spares), Konya; production, foreign-trade/export, sales, logistics, finance, planning; email: none found
- **Konsantaş Konya Döküm Makine (Kayahan)** — `https://www.kariyer.net/firma-profil/konsantas-hidrolik-makine-a-s-47960-40313` — login-to-apply — industrial hydraulic/pneumatic cylinders & casting, Konya (Selçuklu/Büyükkayacık OSB); welding eng, mechanical/manufacturing eng, production, quality, supply-chain, export; email: none found
- **Akış Asansör Makina Motor Döküm** — `https://www.kariyer.net/firma-profil/akis-asansor-makina-motor-dokum-san-ve-tic-ltd-9487-34365` — login-to-apply — iron casting, elevator motors, brake components, Konya (Konya 3.&4. OSB); metallurgy/materials eng, purchasing eng, foreign-trade, production, quality; email: none found
- **Konya Metalurji Döküm** — `https://www.kariyer.net/firma-profil/konya-metalurji-dokum-san-ve-tic-ltd-sti-15585-6126` — login-to-apply — metal foundry (sfero/pik/steel casting), Konya (Konya OSB); metallurgy/materials eng, casting/foundry, machining, quality, planning, maintenance; email: none found
- **Konsa Ambalaj** — `https://www.kariyer.net/firma-profil/konsa-ambalaj-sanayi-ticaret-anonim-sirketi-19315-10225` — login-to-apply — IML plastic injection packaging, Konya (Selçuklu/Büyükkayacık 3. OSB); injection-mold/process eng, production, quality, planning, supply-chain, sales; email: none found
- **Düzgünler Plastik** — `https://www.kariyer.net/firma-profil/duzgunler-plastik-anonim-sirketi-212707-243964` — login-to-apply — PVC pipes & accessories, Konya (Konya 3. OSB); production, mechanical/process eng, quality, planning, export/sales, maintenance; email: none found

### Gaziantep
- **Naksan Plastik ve Enerji (Naksan Holding)** — `https://www.kariyer.net/firma-profil/naksan-plastik-ve-enerji-san-ve-tic-a-s-167961-179210` — login-to-apply — plastic packaging films & energy, Gaziantep (1. OSB/Şehitkamil); production planning, process/quality, supply-chain, finance, eng; email: none found
- **Empera Halı** — `https://www.empera.com/pages/kariyer` — open — machine carpet manufacturing, Gaziantep (4. OSB/Başpınar); foreign-sales, production/process/quality, planning, supply-chain, finance; email: kariyer@empera.com
- **Acarsan Holding** — `https://www.kariyer.net/firma-profil/acarsan-holding-17167-7865` — login-to-apply — diversified (pasta/flour/food, foreign trade, construction, automotive, energy), Gaziantep (3. OSB/Şehitkamil); production/process/quality, supply-chain, finance, foreign-trade, PM; email: none found
- **Gülsan Holding (Gülsan Sentetik Dokuma)** — `https://www.gulsanholding.com/` — open — synthetic weaving / PP carpet yarn, spunbond, sacks, Gaziantep (1. OSB/Şehitkamil); production/process/quality, planning, supply-chain, finance, eng; email: none found
- **Sanat Ambalaj** — `https://www.kariyer.net/firma-profil/sanat-ambalaj-san-tic-a-s-141873-78337` — login-to-apply — flexible packaging (film, lamination, printing), Gaziantep (5. OSB/Şehitkamil); production/process/quality, planning, supply-chain, printing, finance; email: none found
- **Ünal Sentetik Dokuma** — `https://www.kariyer.net/firma-profil/unal-sentetik-dokuma-san-ve-tic-a-s-25733-17283` — login-to-apply — synthetic weaving (PP sacks/fabric, carpet yarn), Gaziantep (3. OSB/Başpınar); OHS/HSE, production/process/quality, planning, supply-chain; email: none found
- **Tanış Değirmen Makina** — `https://www.kariyer.net/firma-profil/tanis-mill-28519-20347` — login-to-apply — mill machinery / grain-processing plants, Gaziantep (1. OSB); machine/manufacturing eng, draftsman, CNC operator, welder, quality; email: none found
- **Festival İplik ve Halı** — `https://www.kariyer.net/firma-profil/festival-iplik-ve-hali-san-tic-a-s-5381-30264` — login-to-apply — machine carpet & yarn, Gaziantep (5. OSB/Şehitkamil); production/process/quality, planning, export/sales, supply-chain, eng; email: none found
- **Has Sentetik Dokuma** — `https://www.hassentetik.com/kariyer/` — open — synthetic weaving (bigbag/PP sacks, agri covers, yarn), Gaziantep (4. OSB/Başpınar); production/process/quality, planning, supply-chain, sales, eng; email: info@hascuval.com

### Kayseri
- **Kumtel Dayanıklı Tüketim** — `https://www.kariyer.net/firma-profil/kumtel-17657-8404` — login-to-apply — white goods / built-in appliances, Kayseri (Kayseri OSB/Melikgazi); production/process/quality, planning, supply-chain, R&D, finance, eng; email: none found
- **Kaygun Çelik Metal** — `https://www.kariyer.net/firma-profil/kaygun-celik-metal-insaat-mobilya-sanayi-ve-ticare-250485-287485` — login-to-apply — steel construction / panel fencing, Kayseri (Kayseri OSB/Melikgazi); welders, steel-construction production, assembly, quality; email: none found
- **Milenyum Metal** — `https://www.kariyer.net/firma-profil/milenyum-metal-dis-tic-ve-san-a-s-22582-13819` — login-to-apply — metal industry (sheet metal / steel processing), Kayseri (Serbest Bölge/Melikgazi); production/process, quality, planning, supply-chain, metal-fabrication; email: none found

### Manisa
- **Reka Elektromekanik Plastik** — `https://www.kariyer.net/firma-profil/reka-elektromekanik-plastik-a-s-157185-81874` — login-to-apply — cable groups & plastic injection (white-goods/automotive), Manisa (Manisa OSB/Yunusemre); production, HR, quality, maintenance; email: none found
- **Sarıgözoğlu Hidrolik Makina ve Kalıp** — `https://www.kariyer.net/firma-profil/sarigozoglu-a-s-312816-359940` — login-to-apply — mold design, pressed-metal & hydraulic parts (automotive OEM), Manisa (Keçiliköy OSB/Yunusemre); SAP master-data specialist, production, warehouse, eng; email: none found
- **Manisa Özgür Elektrik (Özgür Kablo)** — `http://www.ozgurkablo.com/tr/kurumsal/kariyer.html` — open — cable groups & plastic injection (white-goods/automotive), Manisa (Manisa OSB/Yunusemre); production, R&D/project, mold, engineering; email: info@ozgurkablo.com
- **Union International Plastik Kablo Grubu** — `https://www.kariyer.net/firma-profil/union-international-plastik-kablo-grubu-sanayi-ve-225554-258565` — login-to-apply — plastic & cable groups (white-goods), Manisa (Manisa OSB/Yunusemre); industrial eng, purchasing, warehouse/shipping, machine operator; email: none found
- **Pasell Beyaz Eşya Yan Sanayi** — `https://www.kariyer.net/firma-profil/pasell-beyaz-esya-yan-san-ve-tic-a-s-39353-177171` — login-to-apply — white-goods components, Manisa (Muradiye OSB/Yunusemre); production, production eng, forklift operator; email: none found
- **Acro TK Plastik** — `https://www.kariyer.net/firma-profil/acro-tk-plastik-isleme-donusum-san-tic-ltd-sti-203443-233844` — login-to-apply — plastic injection, screen printing & assembly (white-goods), Manisa (Keçiliköy OSB/Yunusemre); quality control, accounting, maintenance supervisor; email: none found
- **İzmir Kalıp** — `https://www.kariyer.net/firma-profil/izmir-kalip-6478-31359` — login-to-apply — progressive/transfer mold & sheet-metal forming, Manisa (Manisa OSB/Yunusemre); mold design/manufacturing, welding, assembly, production; email: none found
- **Tirsan Kardan** — `https://www.kariyer.net/firma-profil/tirsan-kardan-a-s-5736-30619` — login-to-apply — cardan/propeller shafts for commercial vehicles, Manisa (Keçiliköy OSB/Yunusemre); CNC operator, quality inspector, R&D, production eng; email: none found
- **Ne-Ka Kalıp Makina Plastik** — `https://www.kariyer.net/firma-profil/ne-ka-38530-37274` — login-to-apply — mold & machine manufacturing, sheet-metal forming, Manisa (Manisa OSB/Yunusemre); project eng, mold maintenance, mold design chief; email: none found
- **Form Plastik** — `https://www.kariyer.net/firma-profil/form-plastik-sanayi-ve-ticaret-a-s-6289-31170` — login-to-apply — plastic injection (white-goods/electronics), Manisa (Muradiye OSB); planning eng, production, plastic-injection operator; email: info@formplastik.com.tr
- **Teknika Plast** — `https://www.kariyer.net/firma-profil/teknika-plast-5458-30341` — login-to-apply — industrial plastics & IML food packaging, Manisa (Manisa OSB/Yunusemre); production, plastic-injection, quality, planning; email: none found

### Denizli
- **Küçüker Tekstil** — `https://www.kucuker.com/human-resources/` — open — integrated home textile (towel, bathrobe, bedding, yarn), Denizli (Güzelköy/Pamukkale); production, weaving, dyeing, planning, e-commerce/digital marketing; email: info@kucuker.com
- **Turkuaz Tekstil** — `https://www.kariyer.net/firma-profil/turkuaz-tekstil-san-ve-tic-a-s-150543-75185` — login-to-apply — towel & bathrobe home textile (export), Denizli (Akçeşme/Merkezefendi); industrial eng, planning, sales/export, quality; email: none found
- **Özer Tekstil** — `https://www.kariyer.net/firma-profil/ozer-tekstil-san-tic-ltd-sti-46837-47679` — login-to-apply — decorated towel & bathrobe (export), Denizli (Gümüşler/Merkezefendi); design, production, planning, export sales; email: info@ozertekstil.com
- **Bahar Tekstil** — `https://www.kariyer.net/firma-profil/bahar-tekstil-san-tic-a-s-denizli-135821-59294` — login-to-apply — towel, bathrobe & home-textile fabric, Denizli (Honaz OSB 2.); production, weaving, planning, quality, sales; email: none found
- **Solemar (Solmaz Ege Mermer)** — `https://www.kariyer.net/firma-profil/solemar-12782-3044` — login-to-apply — marble & travertine quarrying/processing & export, Denizli (Honaz); quarry/production, export sales, quality, finance; email: none found
- **Vision Travertine Mermer** — `https://www.kariyer.net/firma-profil/vision-travertine-mermer-limited-sirketi-211786-242970` — login-to-apply — travertine/marble/onyx export, Denizli (Kınıklı/Pamukkale); production, export sales, quality; email: none found
- **D.M.S Denizli Döküm Makina** — `https://www.kariyer.net/firma-profil/d-m-s-denizli-dokum-makina-san-ve-tic-a-s-14231-4637` — login-to-apply — iron/stainless casting & casting machinery, Denizli (Kale/Pamukkale); production, foundry/metallurgy, maintenance, quality; email: info@denizlidokum.com
- **Erikoğlu Emaye Bakır Tel** — `https://www.kariyer.net/firma-profil/erikoglu-emaye-bakir-tel-sanayii-anonim-sirketi-279961-321787` — login-to-apply — enamelled/magnet copper wire (export), Denizli (Kale/Pamukkale); production, quality, maintenance, R&D; email: none found

### Eskişehir
- **Entil Endüstri (Zeytinoğlu Group)** — `https://www.kariyer.net/firma-profil/entil-endustri-yatirimlari-ve-ticaret-a-s-1530-5812` — login-to-apply — iron casting / railway & automotive cast parts, Eskişehir (Eskişehir OSB/Odunpazarı); planning chief, production/process, quality, casting eng, supply-chain; email: none found
- **Akar Makina (Akarmak)** — `https://www.kariyer.net/firma-profil/akar-makina-sanayi-ve-tic-a-s-10853-199855` — login-to-apply — autoclaves & pressure vessels (aerospace/defense composites), Eskişehir (Eskişehir OSB/Odunpazarı); manufacturing/mechanical eng, welding eng, quality, planning; email: none found
- **Esray Makina Otomotiv İnşaat** — `https://www.esray.com.tr/insan-kaynaklari` — open — freight wagons, bogies & rail components, Eskişehir (Eskişehir OSB/Odunpazarı); technical eng, industrial eng, production, warehouse; email: info@esray.com.tr
- **Dündarlar Makina** — `https://www.kariyer.net/firma-profil/dundarlar-makina-san-tic-ltd-sti-47008-127524` — login-to-apply — agricultural machinery (Dündarlar Group), Eskişehir (75. Yıl OSB/Odunpazarı); mechanical/manufacturing eng, CNC, production, quality, planning; email: none found

### Mersin
- **Narpak Narenciye Paketleme** — `https://www.kariyer.net/firma-profil/narpak-narenciye-paketleme-ve-dis-ticaret-as-19665-10610` — login-to-apply — citrus & fresh-produce packing / export, Mersin (Tarsus); production, quality (GlobalGAP/BRC), supply-chain, export, HR; email: none found
- **Ergünler Lojistik** — `https://ergunlerlogistics.com/insan-kaynaklari.html` — open — integrated logistics (sea/air/road/rail), Mersin (Akdeniz); logistics customer rep, customer service, ops, supply-chain, sales; email: none found
- **Nisa Lojistik (Nisa Logistics)** — `https://www.kariyer.net/firma-profil/nisa-logistics-37405-37146` — login-to-apply — container transport, warehousing & logistics, Mersin (Akdeniz, near MIP); logistics/ops specialist, warehouse, customs, supply-chain; email: none found
- **Arbel Bakliyat Hububat (AGT Food group)** — `https://www.kariyer.net/firma-profil/arbel-a-s-29193-21089` — login-to-apply — legumes & grains processing / export, Mersin (Akdeniz, near port/free zone); production/process, quality, planning, foreign trade, finance, supply-chain; email: none found
- **Berdan Cam** — `https://www.kariyer.net/firma-profil/berdan-cam-155871-80592` — login-to-apply — processed glass (flat/laminated/tempered/insulated), Mersin (Tarsus); production, process/quality, planning, sales, eng; email: none found

### Adana
- **Rimaş Group (Deri Gıda ve Hayvan Ürünleri)** — `https://www.kariyer.net/firma-profil/rimas-group-209361-240388` — login-to-apply — meat / animal-food export, Adana (Sarıçam/Acıdere OSB); production/process, quality, food eng, export, supply-chain, HR; email: none found
- **Oğuz Gıda** — `https://www.kariyer.net/firma-profil/oguz-gida-san-ve-tic-a-s-21821-12982` — login-to-apply — fruit juice, nectar & beverages, Adana (Sarıçam/Hacı Sabancı OSB); factory manager, food eng, production, quality, planning, supply-chain; email: none found
- **Bakırlar Tekstil** — `https://www.kariyer.net/firma-profil/bakirlar-tekstil-san-ve-tic-a-s-35672-28213` — login-to-apply — integrated textile (weaving, spinning, dyeing), Adana (Sarıçam/Hacı Sabancı OSB); production planner, process/quality eng, industrial eng, supply-chain, ERP; email: none found
- **Ulusoy Tekstil** — `https://www.kariyer.net/firma-profil/ulusoy-tekstil-san-ve-tic-a-s-23854-15217` — login-to-apply — fancy & chenille yarn / integrated textile (export), Adana (Sarıçam/Hacı Sabancı OSB); production/process, quality, planning, export marketing, supply-chain; email: none found
- **Abdioğulları Plastik ve Ambalaj (ABCO)** — `https://www.kariyer.net/firma-profil/abdiogullari-plastik-8205-33083` — login-to-apply — woven PP/PE packaging & technical textiles (export), Adana (Sarıçam/Hacı Sabancı OSB); production, process/quality, planning, supply-chain, finance, eng; email: none found

## Honesty notes
- Only a subset was individually WebFetch-verified (Koç Kariyerim, Arçelik, several SuccessFactors/Lever tenants); the rest are real URLs from search whose live access must be confirmed at fetch time.
- A few entries are platform PATTERNS (SuccessFactors/Recruitee/Personio) with no asserted Turkish tenant, to avoid inventing URLs — use the discovery operators to resolve real tenants.
- Two name-collision traps flagged: greenhouse `insider` (Business Insider) ≠ useinsider; greenhouse `pdbackend` (Peak Design) ≠ Peak Games.

## TR wave v3 additions — 2026-07-13

Additive union of the three finalized TR discovery lanes (docs/TR-Upgrade/TR-Jobs--Codex.md, TR-Jobs--Antigravity.md, TR-Jobs--Claude.md) onto the v2 base, mirroring the EU union gate (JAC-86) methodology. Dedup identity = normalized(company name) + registered domain (public-suffix aware for Turkish multi-label suffixes such as .com.tr/.gov.tr). Two lane lines collapse to one only when BOTH the Turkish-casefolded name AND the registered domain match; distinct-domain alternates for the same employer are kept as separate lines and never dropped. The 1671 v2 lines above are preserved verbatim and are NOT deduped against this block (additive, separately attributed).

**Provenance & counts** — incoming lane lines: 269 (Claude 101 + Antigravity 136 + Codex 32). After collapsing 75 cross-lane name+domain collisions: **194 union source lines / 158 distinct employers** in this block. Union of distinct emails/fetch methods carried onto each surviving line; no distinct email dropped (0 real-email merges were needed; the Borçelik collapse unions Company Career Site + OSB Directory Lookup onto the surviving line). Name normalization strips trailing parenthetical qualifiers before casefold, so `Sungrow (Turkey / EMEA)` and `Sungrow (Sungrow Turkey / EMEA)` collapse when the primary URL matches. Lane-superset assertion (every distinct name+domain pair from the 269 present here) passed with missing = 0; v2 body preserved byte-identical (1671 lines). Total catalog source lines: **1865** (1671 v2 base + 194 union additions).

**Liveness sample (2026-07-13)** — 55 random merged URLs probed live (deduped by host), 50 returned HTTP 200. The remaining 5 (`fico.myworkdayjobs.com`, `sestek.bamboohr.com`, `healthcare.wd1.myworkdayjobs.com`, `pwc.myworkdayjobs.com`, `accenture.myworkdayjobs.com`) failed DNS resolution in the build sandbox, not source death: a known-live control (`cisco.wd1.myworkdayjobs.com`) fails identically while a sibling tenant (`airliquidehr.wd3.myworkdayjobs.com`) resolves and returns 200 — intermittent sandbox DNS for Workday/BambooHR tenant hosts, each HTTP-200-verified by the lane authors at build time. No line is tagged dead because none is confirmed dead.

### holdings & conglomerates

**Istanbul**

- **SabancıDx** — `https://app.gethirex.com/o/sabancidx/` — open — holdings & conglomerates, Istanbul, Hirex API; email: none found
- **Çalık Holding** — `https://app.gethirex.com/o/calik-holding/` — open — holdings & conglomerates, Istanbul, Hirex API; email: none found
- **SabancıDx** — `https://www.kariyer.net/firma-profil/sabancidx` — open — holdings & conglomerates, Istanbul, Company Career Site; email: none found
- **SabancıDx** — `https://www.sabancidx.com/en/about-us/career/` — open — holding group, Istanbul, Company Career Site; email: none found
- **Çalık Holding** — `https://www.kariyer.net/firma-profil/calik-holding` — open — holdings & conglomerates, Istanbul, Company Career Site; email: none found

### banks & fintech

**Istanbul**

- **Anadolu Hayat Emeklilik** — `https://app.gethirex.com/o/anadolu-hayat-emeklilik/` — open — banks & fintech, Istanbul, Hirex API; email: none found
- **Bitfinex** — `https://bitfinex.recruitee.com` — open — banks & fintech, Istanbul, Recruitee API; email: none found
- **Bybit** — `https://job-boards.greenhouse.io/bybit` — open — banks & fintech, Istanbul, Greenhouse API; email: none found
- **Capital.com** — `https://jobs.lever.co/capital` — open — banks & fintech, Istanbul, Lever API; email: none found
- **Keyrock** — `https://jobs.ashbyhq.com/keyrock` — open — banks & fintech, Istanbul, Ashby API; email: none found
- **Midas (Midas Menkul Değerler)** — `https://jobs.lever.co/getmidas` — open — banks & fintech, Istanbul, Lever API; email: none found
- **Mobven** — `https://app.gethirex.com/o/mobven/` — open — banks & fintech, Istanbul, Hirex API; email: none found
- **OKX** — `https://job-boards.greenhouse.io/okx` — open — banks & fintech, Istanbul, Greenhouse API; email: none found
- **Paribu** — `https://app.gethirex.com/o/paribu/` — open — banks & fintech, Istanbul, Hirex API; email: none found
- **Sezzle** — `https://job-boards.greenhouse.io/sezzle` — open — banks & fintech, Türkiye (remote), Greenhouse API; email: none found
- **Sipay** — `https://app.gethirex.com/o/sipay/` — open — banks & fintech, Istanbul, Hirex API; email: none found
- **Sipay** — `https://sipay.com.tr/kariyer/` — open — banks & fintech, Istanbul, Company Career Site; email: none found
- **TradingView** — `https://tradingview.teamtailor.com` — open — banks & fintech, Istanbul, Teamtailor API; email: none found
- **iyzico** — `https://jobs.lever.co/iyzico` — open — banks & fintech, Istanbul, Lever API; email: none found
- **Anadolu Hayat Emeklilik** — `https://www.kariyer.net/firma-profil/anadolu-hayat-emeklilik` — open — banks & fintech, Istanbul, Company Career Site; email: none found
- **Capital.com** — `https://www.phillipcapital.com.tr/bize-katilin` — open — banking & finance, Istanbul, Company Career Site; email: none found
- **FICO Türkiye** — `https://fico.myworkdayjobs.com/External` — open — banking & finance, Istanbul, Workday CXS; email: none found
- **FICO Türkiye** — `https://www.fico.com/en/careers` — open — banking & finance, Istanbul, Company Career Site; email: none found
- **J.P. Morgan Chase** — `https://www.kariyer.net/firma-profil/jpmc.fa.oraclecloud.com|CX_1001` — open — banks & fintech, Istanbul, Company Career Site; email: none found
- **J.P. Morgan Chase** — `https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs` — open — banking & finance, Istanbul, Oracle Cloud CX; email: none found
- **Macellan** — `https://jobs.macellan.net/` — open — tech ecosystem, Istanbul, Company Career Site; email: none found
- **Mobven** — `https://www.kariyer.net/firma-profil/mobven` — open — banks & fintech, Istanbul, Company Career Site; email: none found
- **Mobven** — `https://mobven.com/careers/` — open — banking & finance, Istanbul, Company Career Site; email: none found
- **World Business Lenders** — `https://apply.workable.com/commercial-lending` — open — banks & fintech, Istanbul, Workable API; email: none found

**Türkiye — nationwide & other cities**

- **TradingView** — `https://www.kariyer.net/firma-profil/tradingview` — open — banks & fintech, Turkey, Company Career Site; email: none found

### tech, e-commerce & gaming

**Istanbul**

- **Ajax Systems** — `https://jobs.lever.co/ajax` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **AppSamurai** — `https://jobs.lever.co/appsamurai` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Appier** — `https://job-boards.greenhouse.io/appier` — open — tech, e-commerce & gaming, Istanbul, Greenhouse API; email: none found
- **Believe** — `https://api.smartrecruiters.com/v1/companies/Believe/postings` — open — tech, e-commerce & gaming, Istanbul, SmartRecruiters API; email: none found
- **Bigger Games** — `https://jobs.ashbyhq.com/biggergames` — open — tech, e-commerce & gaming, Istanbul, Ashby API; email: none found
- **Bruin** — `https://app.gethirex.com/o/bruin/` — open — tech, e-commerce & gaming, Istanbul, Hirex API; email: none found
- **Cambly** — `https://jobs.ashbyhq.com/Cambly` — open — tech, e-commerce & gaming, Istanbul, Ashby API; email: none found
- **Catalysor** — `https://careers.smartrecruiters.com/Catalysor` — open — tech, e-commerce & gaming, Istanbul, SmartRecruiters API; email: none found
- **Commencis** — `https://commencis.bamboohr.com/careers/list` — open — tech, e-commerce & gaming, Istanbul, BambooHR API; email: none found
- **Commencis** — `https://jobs.lever.co/commencis` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Constructor Tech** — `https://job-boards.greenhouse.io/constructortech` — open — tech, e-commerce & gaming, Istanbul, Greenhouse API; email: none found
- **Crenno** — `https://careers.smartrecruiters.com/CRENNO` — open — tech, e-commerce & gaming, Istanbul, SmartRecruiters API; email: none found
- **Dataroid** — `https://jobs.lever.co/dataroid` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Dream Games** — `https://jobs.lever.co/dreamgames` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Dream Games** — `https://www.dreamgames.com/open-positions` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Firefly** — `https://jobs.lever.co/fireflyon` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Good Job Games** — `https://job-boards.greenhouse.io/goodjobgames` — open — tech, e-commerce & gaming, Istanbul, Greenhouse API; email: none found
- **Grand Games** — `https://jobs.lever.co/grand` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Insider** — `https://jobs.lever.co/insiderone` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Insider** — `https://useinsider.com/careers/` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Macellan** — `https://macellan.recruitee.com` — open — tech, e-commerce & gaming, Istanbul, Recruitee API; email: none found
- **Nucs AI** — `https://nucsai.recruitee.com` — open — tech, e-commerce & gaming, Istanbul, Recruitee API; email: none found
- **OLIVER** — `https://job-boards.greenhouse.io/oliver` — open — tech, e-commerce & gaming, Istanbul, Greenhouse API; email: none found
- **Scorp** — `https://app.gethirex.com/o/scorp/` — open — tech, e-commerce & gaming, Istanbul, Hirex API; email: none found
- **Spyke Games** — `https://jobs.lever.co/spyke-games` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Taboola** — `https://job-boards.greenhouse.io/taboola` — open — tech, e-commerce & gaming, Istanbul, Greenhouse API; email: none found
- **Trendyol** — `https://jobs.lever.co/trendyol` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Trendyol Go** — `https://careers.trendyol.com/` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Trendyol Go** — `https://jobs.lever.co/trendyol-go` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **Voodoo Istanbul** — `https://jobs.ashbyhq.com/voodoo` — open — tech, e-commerce & gaming, Istanbul, Ashby API; email: none found
- **WPP Media** — `https://job-boards.greenhouse.io/wppmedia` — open — tech, e-commerce & gaming, Istanbul, Greenhouse API; email: none found
- **Wunderman Thompson (VML)** — `https://boards-api.greenhouse.io/v1/boards/wundermanthompson/jobs?content=true` — open — tech, e-commerce & gaming, Istanbul, Greenhouse API; email: none found
- **Yemeksepeti / Delivery Hero** — `https://careers.smartrecruiters.com/DeliveryHero` — open — tech, e-commerce & gaming, Istanbul, SmartRecruiters API; email: none found
- **Zynga Istanbul** — `https://job-boards.greenhouse.io/zyngacareers` — open — tech, e-commerce & gaming, Istanbul, Greenhouse API; email: none found
- **oBilet** — `https://obilet.recruitee.com` — open — tech, e-commerce & gaming, Istanbul, Recruitee API; email: none found
- **Çiçeksepeti** — `https://jobs.lever.co/ciceksepeti` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **ÖğretmenBulun** — `https://ogretmenbulun.teamtailor.com` — open — tech, e-commerce & gaming, Istanbul, Teamtailor API; email: none found
- **Ace Games** — `https://apply.workable.com/ace-games` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **Anbean** — `https://www.kariyer.net/firma-profil/anbean` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Anbean** — `https://app.gethirex.com/o/anbean/` — open — tech ecosystem, Istanbul, Hirex API; email: none found
- **Blueground** — `https://apply.workable.com/blueground` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **Bruin** — `https://www.kariyer.net/firma-profil/bruin` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Commencis** — `https://www.kariyer.net/firma-profil/commencis` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **DP World** — `https://www.kariyer.net/firma-profil/ehpv.fa.em2.oraclecloud.com|CX_1` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **DP World** — `https://ehpv.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs` — open — tech ecosystem, Istanbul, Oracle Cloud CX; email: none found
- **Decathlon Türkiye** — `https://job-boards.greenhouse.io/decathlontechnologyen` — open — logistics, Istanbul, Greenhouse API; email: none found
- **Dolap (Trendyol-owned 2nd-hand)** — `https://jobs.lever.co/trendyol` — open — tech, e-commerce & gaming, Istanbul, Lever API; email: none found
- **FERASET** — `https://apply.workable.com/feraset` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **Gamdom** — `https://www.kariyer.net/firma-profil/gamdom` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: Melanie@teamgamdom.com
- **Gamdom** — `https://gamdom.teamtailor.com/jobs` — open — tech ecosystem, Istanbul, Teamtailor API; email: Melanie@teamgamdom.com
- **Gram Games** — `https://job-boards.greenhouse.io/gramgamescareers` — open — tech ecosystem, Istanbul, Greenhouse API; email: none found
- **Guess Europe Sagl** — `https://apply.workable.com/guess-europe-sagl` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **Hex Trust** — `https://apply.workable.com/hextrust` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **IOM (International Organization for Migration)** — `https://www.kariyer.net/firma-profil/fa-evlj-saasfaprod1.fa.ocs.oraclecloud.com|CX_1001` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **IOM (International Organization for Migration)** — `https://fa-evlj-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs` — open — tech ecosystem, Istanbul, Oracle Cloud CX; email: none found
- **Intetics** — `https://apply.workable.com/intetics-2` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **Lavendo** — `https://jobs.ashbyhq.com/lavendo` — open — tech, e-commerce & gaming, Istanbul, Ashby API; email: none found
- **Lucida AI** — `https://apply.workable.com/lucida-ai` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **MUBI** — `https://jobs.ashbyhq.com/MUBI` — open — tech, e-commerce & gaming, Istanbul, Ashby API; email: none found
- **OLIVER** — `https://www.oliverwyman.com/careers.html` — open — tech ecosystem, Istanbul, Company Career Site; email: none found
- **Oredata** — `https://apply.workable.com/oredata` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **P.I. Works** — `https://www.kariyer.net/firma-profil/piworks` — open — tech ecosystem, Istanbul, Company Career Site; email: none found
- **P.I. Works** — `https://piworks.net/about/jobopportunities` — open — tech ecosystem, Istanbul, Company Career Site; email: none found
- **Paribu (BambooHR board)** — `https://www.kariyer.net/firma-profil/paribu` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Sanction Scanner** — `https://apply.workable.com/sanction-scanner` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **Scorp** — `https://www.kariyer.net/firma-profil/scorp` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Sensient Technologies** — `https://www.kariyer.net/firma-profil/eour.fa.us2.oraclecloud.com|CX` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Sensient Technologies** — `https://eour.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/jobs` — open — tech ecosystem, Istanbul, Oracle Cloud CX; email: none found
- **Sestek** — `https://www.kariyer.net/firma-profil/sestek` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **Sestek** — `https://www.sestek.com/careers` — open — tech ecosystem, Istanbul, Company Career Site; email: none found
- **Teltonika** — `https://apply.workable.com/teltonika` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **UN Women (UN shared ORC instance)** — `https://www.kariyer.net/firma-profil/estm.fa.em2.oraclecloud.com|CX` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **UN Women (UN shared ORC instance)** — `https://estm.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/jobs` — open — tech ecosystem, Istanbul, Oracle Cloud CX; email: none found
- **UNDP (UN shared ORC instance)** — `https://www.kariyer.net/firma-profil/estm.fa.em2.oraclecloud.com|CX_1` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **UNDP (UN shared ORC instance)** — `https://estm.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs` — open — tech ecosystem, Istanbul, Oracle Cloud CX; email: none found
- **VavaCars** — `https://apply.workable.com/vavacars` — open — tech, e-commerce & gaming, Istanbul, Workable API; email: none found
- **WorqCompany** — `https://www.kariyer.net/firma-profil/worqcompany` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found
- **WorqCompany** — `https://app.gethirex.com/o/worqcompany/` — open — tech ecosystem, Istanbul, Hirex API; email: none found
- **ÖğretmenBulun** — `https://www.kariyer.net/firma-profil/ogretmenbulun` — open — tech, e-commerce & gaming, Istanbul, Company Career Site; email: none found

**Türkiye — nationwide & other cities**

- **Picus Security** — `https://jobs.lever.co/picus` — open — tech, e-commerce & gaming, Ankara, Lever API; email: none found
- **Sestek** — `https://sestek.bamboohr.com/careers` — open — tech, e-commerce & gaming, Ankara, BambooHR API; email: none found
- **Reload** — `https://careers.smartrecruiters.com/Reload1` — open — tech, e-commerce & gaming, Antalya, SmartRecruiters API; email: none found
- **Cybersoft (C/S Enformasyon)** — `https://cs.com.tr/kariyer.html` — open — tech, e-commerce & gaming, Ankara (Bilkent Cyberpark), Company Career Site; email: none found
- **Tarım Kredi Teknoloji** — `https://www.tkteknoloji.com.tr/tr/kariyer` — open — tech, e-commerce & gaming, Ankara, Company Career Site; email: none found
- **Emerging Travel Group (RateHawk)** — `https://apply.workable.com/emerging-travel-group` — open — tech, e-commerce & gaming, Ankara, Workable API; email: none found
- **OpenZeka** — `https://openzeka.com/kariyer/` — open — tech ecosystem, Ankara, Anadolu Teknokent Portal; email: info@openzeka.com
- **Panteon Games** — `https://www.panteon.games/en/job-application-form/` — open — tech ecosystem, Ankara, Anadolu Teknokent Portal; email: none found
- **Pragmatike** — `https://jobs.ashbyhq.com/pragmatike` — open — tech, e-commerce & gaming, Turkey, Ashby API; email: none found
- **Pulse Games** — `https://apply.workable.com/pulsegames` — open — tech, e-commerce & gaming, Turkey, Workable API; email: none found
- **Rapsodo** — `https://apply.workable.com/rapsodo` — open — tech, e-commerce & gaming, İzmir, Workable API; email: none found
- **Simsoft** — `https://www.simsoft.com.tr/tr/insan-kaynaklari` — open — tech ecosystem, Ankara, Anadolu Teknokent Portal; email: info@simsoft.com.tr
- **Symphony Solutions** — `https://apply.workable.com/symphony-solutions` — open — tech, e-commerce & gaming, Turkey, Workable API; email: none found
- **UserWise Services** — `https://apply.workable.com/userwise-services` — open — tech, e-commerce & gaming, Turkey, Workable API; email: none found
- **V-Count** — `https://v-count.com/careers/` — open — tech ecosystem, Ankara, Anadolu Teknokent Portal; email: none found
- **Jobgether** — `https://jobs.lever.co/jobgether` — open — remote-work talent marketplace, Türkiye (nationwide), Lever API; email: none found

### retail & FMCG

**Istanbul**

- **Accor** — `https://careers.smartrecruiters.com/AccorHotel` — open — retail & FMCG, Istanbul, SmartRecruiters API; email: none found
- **Invent Analytics** — `https://app.gethirex.com/o/invent-analytics/` — open — retail & FMCG, Istanbul, Hirex API; email: none found
- **Koton** — `https://app.gethirex.com/o/koton/` — open — retail & FMCG, Istanbul, Hirex API; email: none found
- **Red Bull** — `https://careers.smartrecruiters.com/RedBull` — open — retail & FMCG, Istanbul, SmartRecruiters API; email: none found
- **Invent Analytics** — `https://www.kariyer.net/firma-profil/invent-analytics` — open — retail & FMCG, Istanbul, Company Career Site; email: none found
- **Guess Europe** — `https://apply.workable.com/guess-europe-sagl/` — open — fashion retail, Istanbul, Workable widget API; email: none found

**Türkiye — nationwide & other cities**

- **Metro Türkiye / Makro** — `https://api.smartrecruiters.com/v1/companies/metromakro/postings?country=tr` — open — retail & FMCG, Bursa/Bilecik, SmartRecruiters API; email: none found
- **Lesaffre** — `https://careers.smartrecruiters.com/lesaffre` — open — retail & FMCG, Adana/Kırklareli, SmartRecruiters API; email: none found
- **Anadolu Etap (AEP Penkon Gıda)** — `https://www.anadoluetap.com/kariyer` — open — retail & FMCG, Mersin/Denizli/Isparta, Company Career Site; email: none found
- **IC Hotels (IC Holding)** — `https://live.peoplise.com/icholding/career` — open — retail & FMCG (hospitality), Antalya, Company Career Site; email: none found

### manufacturing, industrial & energy

**Istanbul**

- **Sungrow (Turkey / EMEA)** — `https://sungrow-emea.jobs.personio.de` — open — manufacturing, industrial & energy, Istanbul, Personio XML; email: none found

**Türkiye — nationwide & other cities**

- **Bosch Türkiye** — `https://careers.smartrecruiters.com/BoschGroup` — open — manufacturing, industrial & energy, Bursa/Manisa/Kocaeli, SmartRecruiters API; email: none found
- **Borçelik (Borusan + ArcelorMittal JV)** — `https://www.borcelik.com/insan-ve-kariyer` — open — manufacturing, industrial & energy, Gemlik/Bursa, Company Career Site + OSB Directory Lookup; email: none found
- **Kerim Çelik (Borusan Holding)** — `https://kerimcelik.com/Tr/InsanveKariyer` — open — manufacturing, industrial & energy, Gemlik/Bursa, Company Career Site; email: none found
- **Kastamonu Entegre (Hayat Holding)** — `https://www.kastamonuentegre.com/en/human` — open — manufacturing, industrial & energy, Gebze/Kocaeli + Kastamonu, Company Career Site; email: kariyer@keas.com.tr
- **Eti Soda (Ciner Group)** — `https://www.etisoda.com/kariyer/` — open — manufacturing, industrial & energy, Beypazarı/Ankara, Company Career Site; email: none found
- **Polinas Plastik (Yıldız Holding)** — `https://www.polinas.com/tr/insan-kaynaklari/ik-uygulamalarimiz` — open — manufacturing, industrial & energy, Manisa, Company Career Site; email: info@polinas.com.tr
- **Boyteks Tekstil (Erciyes Anadolu Holding)** — `https://www.boyteks.com/tr/insan-kaynaklari/ise-alim/acik-pozisyonlar` — open — manufacturing, industrial & energy, Kayseri, Company Career Site; email: none found
- **Boyçelik (Erciyes Anadolu Holding)** — `https://www.boycelik.com/insan-kaynaklari/` — open — manufacturing, industrial & energy, Kayseri, Company Career Site; email: none found
- **Yıldız Entegre Ağaç (Yıldızlar Yatırım Holding)** — `https://www.yildizentegre.com/hakkimizda/kariyer` — open — manufacturing, industrial & energy, Kocaeli, Company Career Site; email: none found
- **Sanko Holding (Süper Film / Enko Enerji)** — `https://sanko.com.tr/en/career-at-sanko-holding/` — open — manufacturing, industrial & energy, Gaziantep/Adana, Company Career Site; email: none found
- **Modern Ambalaj (Eren Holding)** — `https://www.modern-ambalaj.com.tr/sayfa/kariyer-12` — open — manufacturing, industrial & energy, Çorlu/Manisa/Gebze, Company Career Site; email: none found
- **Adel Kalemcilik (Anadolu Grubu / Faber-Castell)** — `https://www.adel.com.tr/insan-kaynaklari` — open — manufacturing, industrial & energy, Çayırova/Kocaeli, Company Career Site; email: none found
- **Anadolu Motor / ANTOR (Anadolu Grubu)** — `https://www.anadolumotor.com/en/career/join-us` — open — manufacturing, industrial & energy, Gebze, Company Career Site; email: none found
- **Hexagon Studio (Kıraça Holding)** — `https://www.hexagonstudio.com.tr/en/career/career-opportunities/` — open — manufacturing, industrial & energy, Gebze/Kocaeli, Company Career Site; email: ik@hexagonstudio.com.tr
- **Hamitabat Elektrik (HEAŞ) (Limak Holding)** — `https://www.hamitabatelektrik.com/kariyer-firsatlari` — open — manufacturing, industrial & energy, Kırklareli, Company Career Site; email: none found
- **Nurol Enerji (Nurol Holding)** — `https://www.nurolenerji.com.tr/en/human-resources/` — open — manufacturing, industrial & energy, Ankara, Company Career Site; email: info@nurolenerji.com.tr
- **Gama Enerji (Gama Holding)** — `https://enerji.gama.com.tr/en/career/career-at-gama/general-application/` — open — manufacturing, industrial & energy, Ankara, Company Career Site; email: none found
- **Rönesans İnşaat (Rönesans Holding)** — `https://careers.ronesans.com/` — open — manufacturing, industrial & energy, Ankara, Company Career Site; email: none found
- **Nurol İnşaat ve Ticaret (Nurol Holding)** — `https://www.nurol.com.tr/en/job-applicaiton` — open — manufacturing, industrial & energy, Ankara, Company Career Site; email: none found
- **Akfen İnşaat (Akfen Holding)** — `https://www.akfen.com.tr/insan-kaynaklari/genel-basvuru/` — open — manufacturing, industrial & energy, Ankara, Company Career Site; email: none found
- **Limak İnşaat (Limak Holding)** — `https://www.limak.com.tr/kariyer/kariyer-firsatlari` — open — manufacturing, industrial & energy, Ankara, Company Career Site; email: none found
- **Gediz Elektrik Perakende (Bereket Enerji)** — `https://www.gedizperakende.com.tr/en/career` — open — manufacturing, industrial & energy, İzmir/Manisa, Company Career Site; email: none found
- **Aydem Elektrik Perakende (Bereket Enerji)** — `https://www.aydemperakende.com.tr/en/career` — open — manufacturing, industrial & energy, Aydın/Denizli/Muğla, Company Career Site; email: none found
- **ADM Elektrik Dağıtım (Bereket Enerji)** — `https://www.aydemenerji.com.tr/bilgi/45/kariyer-firsatlari/` — open — manufacturing, industrial & energy, Aydın/Denizli/Muğla, Company Career Site; email: none found
- **ENOVAS Savunma** — `https://enovas.com.tr/careers/` — open — manufacturing & industrial, Ankara, Anadolu Teknokent Portal; email: info@enovas.com.tr
- **Erdemir** — `https://www.erdemir.com.tr/kariyer` — open — manufacturing & industrial, Zonguldak, Fortune Turkey / ISO 500 Career Site; email: none found
- **Kardemir** — `https://www.kardemir.com/kariyer` — open — manufacturing & industrial, Karabük, Fortune Turkey / ISO 500 Career Site; email: none found
- **Kocaer Çelik** — `https://www.kocaersteel.com/tr/kariyer` — open — manufacturing & industrial, Izmir, Fortune Turkey / ISO 500 Career Site; email: none found
- **SDT Uzay ve Savunma** — `https://www.sdt.com.tr/tr/kariyer` — open — manufacturing & industrial, Ankara, Anadolu Teknokent Portal; email: hr@sdt.com.tr
- **Sasa Polyester** — `https://sasa.com.tr/kariyer` — open — manufacturing & industrial, Adana, Fortune Turkey / ISO 500 Career Site; email: none found
- **Star Rafineri** — `https://www.socar.com.tr` — open — manufacturing & industrial, Izmir, Fortune Turkey / ISO 500 Career Site; email: none found
- **Toyota Otomotiv** — `https://www.toyotatr.com/tr/insan-kaynaklari` — open — manufacturing & industrial, Sakarya, Fortune Turkey / ISO 500 Career Site; email: none found
- **Tusaş Engine Industries (TEI)** — `https://www.tei.com.tr/kariyer` — open — manufacturing & industrial, Eskişehir, Fortune Turkey / ISO 500 Career Site; email: none found
- **TÜPRAŞ** — `https://www.tupras.com.tr/kariyer-firsatlari` — open — manufacturing & industrial, Kocaeli, Fortune Turkey / ISO 500 Career Site; email: none found
- **Çimtaş** — `https://www.cimtas.com` — open — manufacturing & industrial, Bursa, OSB Directory Lookup; email: cimtas_gemlik@cimtas.com
- **İskenderun Demir Çelik** — `https://www.isdemir.com.tr/kariyer` — open — manufacturing & industrial, Hatay, Fortune Turkey / ISO 500 Career Site; email: none found
- **PerkinElmer** — `https://newperkinelmer.wd1.myworkdayjobs.com/External` — login-to-apply — analytical instruments, Ankara, Workday CXS; email: none found
- **BorgWarner** — `https://borgwarner.wd5.myworkdayjobs.com/BorgWarner_Careers` — login-to-apply — automotive components, İzmir, Workday CXS; email: none found
- **Air Liquide** — `https://airliquidehr.wd3.myworkdayjobs.com/AirLiquideExternalCareer` — login-to-apply — industrial gases, Ankara & Manisa, Workday CXS; email: none found

### telecom, IT services & consulting

**Istanbul**

- **Aikido Security** — `https://aikidosecurity.recruitee.com` — open — telecom, IT services & consulting, Istanbul, Recruitee API; email: none found
- **JumpCloud** — `https://jobs.lever.co/jumpcloud` — open — telecom, IT services & consulting, Türkiye (remote), Lever API; email: none found
- **Lostar** — `https://careers.smartrecruiters.com/Lostar` — open — telecom, IT services & consulting, Istanbul, SmartRecruiters API; email: none found
- **NielsenIQ** — `https://careers.smartrecruiters.com/NielsenIQ` — open — telecom, IT services & consulting, Istanbul, SmartRecruiters API; email: none found
- **Welo Data (Welocalize)** — `https://jobs.lever.co/weloglobal` — open — telecom, IT services & consulting, Türkiye (remote), Lever API; email: none found

**Türkiye — nationwide & other cities**

- **Karel Elektronik (Doğan Holding)** — `https://www.karel.com.tr/` — open — telecom, IT services & consulting, Ankara, Company Career Site; email: none found
- **Accenture Turkey** — `https://accenture.myworkdayjobs.com/AccentureCareers` — open — telecom, IT services & consulting, Turkey, Workday CXS; email: none found
- **ICterra** — `https://www.icterra.com/company/career/` — open — telecom & IT, Ankara, Anadolu Teknokent Portal; email: hr.tr@icterra.com
- **PwC Türkiye** — `https://pwc.myworkdayjobs.com/Global_Experienced_Careers` — open — telecom, IT services & consulting, Turkey, Workday CXS; email: none found

### healthcare & pharma

**Türkiye — nationwide & other cities**

- **AbbVie** — `https://careers.smartrecruiters.com/abbvie` — open — healthcare & pharma, Ankara, SmartRecruiters API; email: none found
- **Anadolu Sağlık Merkezi (Anadolu Grubu)** — `https://www.anadolusaglik.org/kariyer` — open — healthcare & pharma, Gebze/Kocaeli, Company Career Site; email: none found
- **Solventum** — `https://healthcare.wd1.myworkdayjobs.com/Search` — login-to-apply — healthcare technology, Ankara (remote), Workday CXS; email: none found

### logistics

**Istanbul**

- **DFDS Türkiye** — `https://dfdsturkey.teamtailor.com` — open — logistics, Istanbul, Teamtailor API; email: none found
- **DFDS Türkiye** — `https://www.kariyer.net/firma-profil/dfdsturkey` — open — logistics, Istanbul, Company Career Site; email: none found
- **Trendyol Express** — `https://jobs.lever.co/trendyol` — open — logistics, Istanbul, Lever API; email: none found
- **Trendyol Express** — `https://careers.trendyol.com/trendyol-express` — open — logistics, Istanbul, Company Career Site; email: none found

**Türkiye — nationwide & other cities**

- **OPLOG** — `https://oplog.recruitee.com` — open — logistics, Ankara (Bilkent) / Kocaeli-Dilovası, Recruitee API; email: none found

### public & education

**Türkiye — nationwide & other cities**

- **İŞKUR Ankara Search** — `https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx?city=ankara` — restricted — public & education, Ankara, İŞKUR Portal Search; email: none found
- **İŞKUR İzmir Search** — `https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx?city=izmir` — restricted — public & education, Izmir, İŞKUR Portal Search; email: none found
