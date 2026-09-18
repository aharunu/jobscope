# Personal Job Intelligence — MVP Teknik Tasarım

Bu doküman, sistem için alınan tüm mimari ve teknik kararların konsolide edildiği nihai MVP teknik tasarım referansıdır.

---

## 1. Ürün Amacı

Sistem, iş arama ve eşleştirme sürecini şeffaf, ölçülebilir ve kanıta dayalı bir karar destek mekanizmasına dönüştürmeyi amaçlar.

### Sistem Uçtan Uca Akışı
```
Job Sources
    ↓
Job Discovery
    ↓
Raw Job
    ↓
Normalization
    ↓
Validation
    ↓
Deduplication
    ↓
PostgreSQL
    ↓
Deterministic Matching
    ↓
User
    ↓
[AI ile Detaylı Analiz Et]
    ↓
AI Matching
    ↓
Final Match + Explanation
```

> **Temel Prensip:**  
> Sistem kullanıcının yerine başvuru kararı vermez. Kullanıcıya karar verebilmesi için ölçülebilir, denetlenebilir ve açıklanabilir bilgi sağlar.

---

## 2. Teknoloji Stack

| Katman | MVP Seçimi |
| :--- | :--- |
| **Frontend** | Next.js |
| **Backend** | Python + FastAPI |
| **Mimari** | Modular Monolith + Clean/Hexagonal İlkeleri |
| **Veritabanı** | PostgreSQL |
| **ORM** | SQLAlchemy |
| **Migration** | Alembic |
| **Vector DB** | Yok |
| **Authentication** | Yok |
| **API Erişimi** | Localhost |
| **Logging** | Structured log + Dosyaya yazım |
| **Test** | Unit Tests + Kritik Integration Tests |
| **AI Entegrasyonu** | Provider Abstraction + MVP'de tek model |
| **Scheduler** | Altyapı var, varsayılan olarak kapalı |
| **Crawler** | Manuel tetikleme aktif |

---

## 3. Backend Mimarisi

İlk aşamada mikroservis mimarisi kullanılmayacak; modüler monolit prensiplerine göre yapılandırılacaktır.

```
backend/
│
├── domain/
│   ├── user/
│   ├── profile/
│   ├── search_profile/
│   ├── job/
│   ├── source/
│   ├── application/
│   └── matching/
│
├── application/
│   ├── job_discovery/
│   ├── job_processing/
│   ├── job_matching/
│   ├── profile_management/
│   └── application_tracking/
│
├── infrastructure/
│   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   └── migrations/
│   │
│   ├── ats/
│   │   ├── lever/
│   │   ├── greenhouse/
│   │   ├── workday/
│   │   ├── ashby/
│   │   └── ...
│   │
│   ├── parsers/
│   ├── llm/
│   └── logging/
│
└── interfaces/
    └── api/
```

---

## 4. Job Discovery

Discovery mekanizmasının başlangıç referans noktası mevcut kaynak kataloğudur.

### Discovery Akışı
```
MD Source Catalog
       ↓
Source Registry Import
       ↓
PostgreSQL
       ↓
Crawler
```

- **Başlangıç:** Markdown (MD) dosyası sistemin başlangıç kataloğudur.
- **Runtime:** Çalışma zamanında crawler doğrudan MD dosyasına bağlı değildir; PostgreSQL üzerindeki Source Registry tablosu üzerinden beslenir.
- **Senkronizasyon:**
  - Manuel import / sync desteklenir.
  - Otomatik sync altyapısı hazır tutulacak.
  - Otomatik sync varsayılan olarak **KAPALI** olacaktır.

---

## 5. Source Registry

Her kaynak için sadece statik bir URL tutulmaz. Kaynak modelinde adapter ve çalışma yapılandırmaları saklanır:

```
Source
├── name
├── company
├── url
├── country
├── ats_type
├── active
├── adapter_config
├── pagination_config
├── endpoint_config
├── rate_limit_config
└── metadata
```

Adapter bazlı özel yapılandırmalar veritabanında yönetilebilir:
```
Greenhouse
    ↓
adapter = greenhouse
    ↓
board_token = ...
    ↓
pagination = ...
```

---

## 6. Crawler

Crawler çalışma prensipleri ve dayanıklılık kuralları:
- Manuel tetiklenebilir (`Crawl Now`).
- Scheduler altyapısı mevcut fakat MVP'de kapalıdır.
- **Hata İzolasyonu:** Bir kaynaktaki hata tüm crawler sürecini durdurmaz.
- Hata durumunda yeniden deneme (retry) uygulanır ve structured log üretilir.
- Her tarama çalışması `CrawlRun` tablosuna kaydedilir.

### Crawl Akışı
```
Source → Adapter → Raw Job → Validation → Normalization → Deduplication → Job DB
```

---

## 7. Raw Job

Ham verinin hiçbir koşulda kaybedilmemesi esastır.

```
Raw Job ──→ Normalization ──→ Canonical Job
```

- Raw HTML veya ham API yanıtları ilk aşamada kalıcı olarak saklanır.
- **Sağladığı Avantajlar:**
  - Parser hatalarını sonradan inceleme imkânı
  - Adapter seviyesinde debugging
  - Parser güncellendiğinde geriye dönük yeniden işleme (re-processing)
  - Extraction problemlerini kök neden analiziyle çözme
- İlerleyen fazlarda saklama süresi politikası (retention policy) tanımlanabilir.

---

## 8. Job & Application Lifecycle

İlanın kendi yaşam döngüsü ile kullanıcının başvuru yaşam döngüsü birbirinden kesin olarak ayrılmıştır.

### Job Lifecycle
```
ACTIVE ──→ CLOSED
```
- Kaynakta artık bulunmayan ilan `ACTIVE → CLOSED` durumuna geçer.
- İlan veritabanından **silinmez**.

### Application Lifecycle
İlandan bağımsız olarak kullanıcının başvuru durumunu modeller:
```
INTERESTED ──→ APPLYING ──→ APPLIED ──→ INTERVIEW ──→ OFFER
                                ↓
                             REJECTED
```

---

## 9. Job Identity

Bir ilanın tekil harici kimliği (Primary External Identity):
```
source + external_job_id
```
- `external_job_id` bulunamıyorsa: `canonical_url` kullanılır.
- **Content Hash:** Kimlik belirleme (identity) amacıyla değil, yalnızca içerik değişikliği tespiti ve karşılaştırma amacıyla kullanılır.

---

## 10. Deduplication (Yineleme Engelleme)

Deduplication hibrit sinyallerle gerçekleştirilir:
- URL
- Şirket (Company)
- Başlık (Title)
- Lokasyon (Location)
- Normalleştirilmiş İçerik (Normalized Content)
- İçerik Benzerliği (Content Similarity)

> **Amaç:** Aynı iş ilanının farklı URL, kaynak veya ATS kombinasyonlarıyla kullanıcıya mükerrer olarak sunulmasını önlemek.

---

## 11. Crawl Run

Her tarama işlemi bağımsız bir çalışma kaydı olarak tutulur:

```
CrawlRun
├── source
├── started_at
├── finished_at
├── status
├── jobs_found
├── jobs_created
├── jobs_updated
└── errors
```

- **İlişki:** `CrawlRun ↔ Job` ilişkisi kurulur.
- **Kullanım:** Crawler performansı, ilk görülme anı (`first_seen_at`) ve audit metrikleri için temel teşkil eder.

---

## 12. Job Normalization

Farklı ATS ve kaynaklardan gelen tüm veri yapıları standart **Canonical Job** modeline dönüştürülür:

```
Canonical Job
├── title
├── company
├── description
├── responsibilities
├── requirements
├── skills
├── experience
├── education
├── location
├── work_mode
├── salary
├── employment_type
├── published_at
├── deadline
├── source
├── external_job_id
├── canonical_url
├── first_seen_at
├── last_seen_at
└── closed_at
```

---

## 13. Requirement Extraction

Gereksinim çıkarma süreci hibrit bir akışla yürütülür:

```
Raw Job ──→ Deterministic Extraction ──→ LLM Structuring / Validation ──→ Normalized Requirements
```

- LLM doğrudan ve denetimsiz tüm eşleştirme kararını vermez.
- **Requirement Yapısı:**
```
Requirement
├── type
├── description
├── required / preferred
├── importance
├── criticality
├── evidence
└── match status
```

---

## 14. Requirement Importance

Gereksinim önemi statik bir katsayıdan ibaret değildir; üç kaynağın birleşiminden beslenir:

```
Job Wording + Role/Skill Taxonomy + Observed Job Data ──→ Requirement Importance
```

- Sistem zaman içinde toplanan verilerden belirli roller için hangi gereksinimlerin ne kadar kritik/yaygın olduğunu öğrenebilir.
- Bu gözlemsel veri tek başına mutlak gerçek olarak kabul edilmez, ağırlıklandırmaya destek sağlar.

---

## 15. Profil Mimarisi

Kullanıcı profili iki temel düzlemde modellenir:

### 1. Base Profile (Kullanıcının Stabil Bilgileri)
```
Base Profile
├── Skills
├── Experience
├── Education
├── Projects
└── Other qualifications
```

### 2. Search Profile (Arama Amacı & Hedefleri)
```
Search Profile
├── Target Roles
├── Seniority
├── Target Skills
├── Locations
├── Work Mode
├── Industry
├── Salary preferences
└── Other preferences
```

Bir Base Profile altında birden fazla Search Profile tanımlanabilir:
```
Base Profile
    ├── AI Engineer
    ├── Data Scientist
    └── Software Engineer
```

---

## 16. CV Import

CV içe aktarma süreci kullanıcı onayı odaklı tasarlanmıştır:

```
CV ──→ Deterministic Parser ──→ LLM Structuring / Validation ──→ Extracted Profile ──→ USER REVIEW ──→ Base Profile
```

- Kullanıcı onay vermeden CV'den çıkarılan bilgiler doğrudan profile yazılmaz.
- Profil üzerinde manuel düzenleme her zaman mümkündür.
- **Gelecek Faz (MVP Dışı):** İlana özel uyarlanmış CV (Per-job tailored CV) MVP kapsamında yer almaz.

---

## 17. Matching Girdisi

Eşleştirme motorunun temel girdi üçlüsü:
```
Base Profile + Search Profile + Job
```
*(CV tek başına bir eşleştirme girdisi değildir; profile dönüştürülmüş hali kullanılır).*

---

## 18. Deterministic Match Engine

Deterministik puanlama toplam 100 puan üzerinden ağırlıklandırılır:

| Kategori | Ağırlık |
| :--- | :---: |
| **Role Match** | %20 |
| **Skill Match** | %30 |
| **Experience** | %20 |
| **Location / Work Mode** | %10 |
| **Education** | %10 |
| **Other Requirements** | %10 |
| **Toplam** | **%100** |

---

## 19. Role Match (%20)

- Hibrit yaklaşım: Taksonomi + Başlık Benzerliği + AI desteği.
- Yalnızca katı (exact) unvan eşleşmesi yapılmaz.
- Örnek: `Data Scientist ↔ ML Engineer ↔ Data Engineer ↔ Analytics Engineer` bağlamına göre değerlendirilir.
- İlanın unvanı, rol taksonomisi, aranan yetenekleri ve sorumlulukları birlikte ele alınır.

---

## 20. Skill Match (%30)

- Hibrit taksonomi ve transfer edilebilir yetenek (transferable skills) değerlendirmesi.
- Örnek: `TensorFlow → Deep Learning → PyTorch` ilişkisinde kullanıcıda PyTorch yoksa doğrudan sıfır puan verilmez; aktarılabilir yetenek derinliği puanlamaya yansıtılır.

---

## 21. Experience (%20)

- Kullanıcı deneyim seviyesi (New Grad, Junior, Mid, Senior vb.) seçebilir.
- Kıdem filtresi opsiyoneldir.
- Kullanıcı açık bir filtre koyduysa bu doğrudan filtreleme kriteridir; eşleştirme skorunun bunu örtbas etmesi beklenmez.

---

## 22. Location / Work Mode (%10)

- Esnek uyumluluk (flexible compatibility) prensibi geçerlidir.
- Arama profili `İstanbul (Remote/Hybrid)` iken ilanın `Ankara (Remote)` olması tam bir lokasyon uyuşmazlığı sayılmaz.
- Ancak `Ankara (On-site)` olması uyumluluk puanını düşürür.

---

## 23. Education (%10)

- Derece şartı (Degree Requirement) + Bölüm Yakınlığı (Field Proximity) + İlgili Alan (Related Field).
- Örnek: Şart `Computer Science / Software Engineering or Related Field` ise ve kullanıcı `Mathematics Engineering` mezunuysa ilgili alan kapsamında değerlendirilir; doğrudan ret veya sıfır puan verilmez.

---

## 24. Other Requirements (%10)

- Dil bilgisi, sertifikalar, çalışma izinleri (work authorization), seyahat kısıtı vb. özel eşleştiriciler.
- Önem derecesi statik kurallar, gözlemlenen ilan verileri ve arama profiliyle şekillenir.

---

## 25. Requirement-Level Scoring

Kategoriye doğrudan kör bir skor vermek yerine ayrıştırılabilir hiyerarşi kullanılır:

```
Requirement ──→ Requirement Score ──→ Category Score ──→ Weighted Total
```

Kullanıcı arayüzünde tam açıklanabilirlik sağlanır:
```
Skill Match: 78/100
  Python       ✓
  FastAPI      ✓
  PyTorch      ~
  Kubernetes   ✗
```

---

## 26. Missing Data (Eksik Veri İlkesi)

> **Kritik Kural:** `Unknown ≠ Not Matched`

- İlanda maaş bilgisi yoksa: `Salary: Unknown / Not specified` olarak işaretlenir.
- Bilinmeyen veri, kullanıcı kriterleriyle çelişmediği sürece eşleştirme puanını haksız şekilde düşürmez. Ancak **Confidence** (güvenilirlik) değerini düşürebilir.

---

## 27. Hard Requirements

- Zorunlu şartlar (hard requirements) sistemde `Blocker` olarak etiketlenebilir.
- Ancak aşırı orantısız cezalar (skoru doğrudan sıfırlama vb.) yerine kontrollü, makul cezalandırma katsayıları uygulanır.
- Sistem hiçbir zaman `"Bu ilana başvuramazsın / başvurma"` demez; nihai karar her zaman kullanıcıdadır.

---

## 28. Deterministic Score

0–100 aralığında şeffaf ve denetlenebilir biçimde hesaplanır.

```
Role Match          17 / 20
Skills Match        26 / 30
Experience          18 / 20
Location / Mode      9 / 10
Education            8 / 10
Other Requirements   7 / 10
----------------------------
Deterministic Score 85 / 100
```
Gereksinim seviyesindeki tüm kanıtlar veri modelinde saklanır.

---

## 29. AI Matching

AI analizi deterministik süreçten bağımsız çalışır ve maliyet optimizasyonu gereği otomatik çalıştırılmaz.

```
Deterministic Result ──→ [AI ile Detaylı Analiz Et] ──→ AI Engine ──→ AI Score + Explanation + Evidence
```

- Kullanıcı arayüzde ilgili ilana tıklayıp talep ettiğinde devreye girer.
- Çıktılar:
  - AI Score
  - Gerekçeler (Reasons)
  - Güçlü Yönler (Strengths)
  - Eksiklikler (Gaps)
  - Riskler (Risks)
  - Kanıtlar (Evidence)

---

## 30. AI Score & Değerlendirme

AI, 0–100 arası bir skor ve kategorik değerlendirme sunar:
- **Skor:** 0–100
- **Assessment:** Strong / Moderate / Low
- **Strengths & Gaps:** Profil projeleri ve ilan gereksinimleri arasındaki doğrudan kanıtlar.

---

## 31. AI Evidence (Kanıta Dayalılık)

Önemli çıkarımlarda kanıt zorunludur:
```
Claim ──→ Evidence ──→ Reason
```
- Destekleyici kanıt yoksa: `Unknown` veya `Insufficient Evidence` olarak işaretlenir.
- Model halüsinasyonu olan doğrulanmamış çıkarımlar eşleştirmeye dahil edilmez.

---

## 32. AI Adjustment (Skor Ayarlama Formülü)

AI skoru, deterministik skorun üzerine yazılmaz; kontrollü bir düzeltme faktörü olarak eklenir:

```
Deterministic Score + AI Adjustment = Final Score
```

### Formül
$$\text{AI Adjustment} = \text{clamp}((\text{AI Score} - \text{Deterministic Score}) \times \alpha, -8, +8)$$

- **Maksimum Etki Limiti:** $\pm 8$ puan.
- Deterministik skor 86, AI skoru 94 ise hafif pozitif bir düzeltmeyle Final skor $\approx 88$ olur.
- $\alpha$ parametresi ilerleyen süreçte kalibrasyon testleriyle optimize edilecektir.

---

## 33. Confidence (Güven Skoru)

Confidence metriği eşleşme skorundan bağımsız ayrı bir güvenilirlik yüzdesidir:
```
Final Match: 84 | Deterministic: 82 | AI: 87 | Confidence: 91%
```
- **Beslendiği Kaynaklar:**
  - Profil doluluk oranı (Profile completeness)
  - İlan bilgi bütünlüğü (Job information completeness)
  - Çıkarım kalitesi (Extraction quality)
  - Kanıt kapsamı (Evidence coverage)
  - Deterministik ve AI skor tutarlılığı (Agreement)
- *Not:* Deterministik ve AI skorları arasındaki fark, AI güçlü bir kanıt sunuyorsa güven skorunu tek başına düşürmez.

---

## 34. AI Cache

- `Base Profile + Search Profile + Job` birleşimi için daha önce AI analizi üretildiyse sonuç önbellekten sunulur.
- Kullanıcı dilediğinde `Yeniden AI Analizi` seçeneğiyle cache'i atlayarak (bypass) yeni analiz tetikleyebilir.

---

## 35. Eşleşme Yaşam Döngüsü

```
Yeni İlan (New Job)
       ↓
Deterministic Match (Otomatik)
       ↓
Kullanıcı Sonucu İnceler
       ↓
[AI ile Detaylı Analiz Et] (İsteğe Bağlı)
       ↓
AI Match & Kanıt Çıkarımı
       ↓
Final Score & Confidence Hesaplanması
```

- **Deterministik Eşleştirme:** Yeni ilan geldiğinde, profil güncellendiğinde veya kullanıcı manuel tetiklediğinde çalışır.
- **AI Eşleştirme:** Yalnızca kullanıcı açıkça talep ettiğinde çalışır.

---

## 36. Application Tracking (Başvuru Takibi)

İlanın yayından kalkması ile kullanıcının başvuru durumu bağımsızdır:
- İlan: `ACTIVE` / `CLOSED`
- Başvuru: `INTERESTED` / `APPLYING` / `APPLIED` / `INTERVIEW` / `OFFER` / `REJECTED`
- Durum geçiş tarihçesi (`ApplicationStatusHistory`) tutulur.
- İleride dönüşüm analizleri ve Sankey/Funnel diyagramları için veri altyapısı sağlanır.

---

## 37. Manual Job Entry (Manuel İlan Ekleme)

Kullanıcı URL girerek crawler kapsamı dışındaki ilanları sisteme ekleyebilir:
```
URL Gir ──→ Fetch ──→ Parse ──→ Normalize ──→ Dedup Kontrolü ──→ Job DB
```

---

## 38. Dashboard

MVP kullanıcı arayüzü dört temel ekseni birleştirir:
1. **Job Discovery:** Taranan ve keşfedilen ilanlar listesi.
2. **Match Results:** Eşleşme özeti (Örn: 84 Final, 82 Det., 87 AI, %91 Conf.).
3. **AI Analysis & Detail:** Güçlü yönler, eksiklikler, kanıtlar ve bilinmeyenler.
4. **Application Tracking:** Başvuru aşamalarının takibi ve yönetimi.

---

## 39. Veritabanı Varlıkları (PostgreSQL)

ORM olarak **SQLAlchemy**, şema göçleri için **Alembic** kullanılır.

### Ana Entity Grupları
- **Kullanıcı & Profil:** `User`, `Profile`, `SearchProfile`
- **Kaynak & Tarama:** `Source`, `CrawlRun`
- **İlan Verisi:** `Job`, `RawJob`
- **Gereksinimler:** `Requirement`, `JobRequirement`
- **Eşleştirme:** `MatchResult`, `RequirementMatch`, `AIEvidence`
- **Başvuru Takibi:** `Application`, `ApplicationStatusHistory`

Standart sorgular ORM üzerinden, analitik veya performans gerektiren kısımlarda gerektiğinde Raw SQL ile yürütülür.

---

## 40. İndeksleme Stratejisi

MVP aşamasında yüksek sorgulama hacmine sahip alanlarda standart B-Tree indeksler kullanılır:
- `source`
- `external_job_id`
- `canonical_url`
- `company`
- `status`
- `published_at`, `first_seen_at`
- `application_status`
- Profil ve Search Profile yabancı anahtar (FK) ilişkileri

İleri seviye GIN, GiST ve Trigram indeksleri ihtiyaç doğdukça eklenecektir.

---

## 41. Logging (Kayıt Tutma)

Yapılandırılmış (Structured) formatta dosyaya loglama yapılır. Örnek olaylar:
- `crawl_started`, `crawl_finished`
- `source_error`, `retry`
- `job_created`, `job_updated`, `dedup_detected`
- `match_completed`
- `ai_analysis_started`, `ai_analysis_completed`

---

## 42. Test Stratejisi

MVP kalite güvencesi iki katmanda yürütülür:
- **Unit Tests:** Parser fonksiyonları, normalizasyon kuralları, deterministik puanlama matematiği.
- **Kritik Integration Tests:** ATS adaptörleri, deduplication mantığı, profil çıkarımı, API endpoint'leri ve DB repository entegrasyonu.

---

## 43. Otomasyon & Zamanlayıcı

- Scheduler altyapısı kod tabanında yer alacak.
- **MVP Kuralı:** Otomatik tarama varsayılan olarak **KAPALIDIR**.
- Kullanıcı `Crawl Now` butonu ile manuel tarama gerçekleştirir.
- İleride periyodik aralıklar (6h, 12h, Daily) arayüzden aktif edilebilecektir.

---

## 44. MVP Kapsamı Dışında Bırakılanlar (Phase 2 / Technical Debt)

Aşağıdaki özellikler MVP odağını korumak adına bilinçli olarak hariç tutulmuştur:
- LinkedIn crawler
- Indeed vb. korumalı / anti-bot kaynaklar
- Agentic serbest web keşfi
- Mikroservis mimarisi
- Authentication / Çok kullanıcılı yetkilendirme
- Vector Database
- Şirket İstihbaratı (Company Intelligence)
- Yetenek / Piyasa İstihbaratı (Market Intelligence)
- Uyarlamalı kişiselleştirilmiş puanlama (Adaptive scoring)
- İlana özel CV uyarlama (Per-job CV tailoring)
- CV varyant eşleştirme
- Snapshot / versiyon geçmişi
- Gelişmiş zamanlayıcı arayüzü
- Gelişmiş anlamsal (semantic) DB indeksleri

---

## 45. MVP'nin Nihai Akış Şeması

```
                    ┌──────────────────┐
                    │  MD Source       │
                    │  Catalog         │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Source Registry  │
                    │   PostgreSQL     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     Crawler      │
                    │ ATS Adapters     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    Raw Job       │
                    └────────┬─────────┘
                             │
               ┌─────────────┴─────────────┐
               ▼                           ▼
        Normalization                Requirement
               ▼                      Extraction
        Validation                     (Hybrid)
               ▼                           │
        Deduplication                      │
               └─────────────┬─────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   PostgreSQL     │
                    │ Canonical Jobs   │
                    └────────┬─────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │  Deterministic Match     │
              │                          │
              │ Base Profile             │
              │ + Search Profile         │
              │ + Job                    │
              └────────────┬─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Match Result │
                    │   (0–100)    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │     User     │
                    └──────┬───────┘
                           │
                 [AI ile Detaylı Analiz]
                           │
                           ▼
                    ┌──────────────┐
                    │ AI Matching  │
                    │ Evidence     │
                    │ Explanation  │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Final Match  │
                    │ Confidence   │
                    └──────┬───────┘
                           │
                           ▼
                    Application Tracking
                           │
                           ▼
                  Sankey / Funnel / Analytics
```

---

## 46. Gelecek Adım ve İlgili Dokümanlar

Sistem mimarisinin sonraki aşamaları aşağıdaki dokümanlarda modüler olarak detaylandırılmıştır:

1. **[02_database_and_api_design.md](file:///c:/Users/aharu/Documents/GitHub/Crawler/docs/02_database_and_api_design.md)**:
   - PostgreSQL Varlık ve ER Modeli
   - Tablo Şemaları, Tipleri ve Kısıtları (Constraints)
   - FastAPI RESTful API Uç Noktaları

2. **[03_data_model_and_architecture.md](file:///c:/Users/aharu/Documents/GitHub/Crawler/docs/03_data_model_and_architecture.md)**:
   - Nihai ER İlişkileri ve Kardinaliteler (1:N, 1:1, N:M)
   - SQLAlchemy Declarative Modelleri
   - Clean Architecture Repository Protokolleri (`typing.Protocol`)
   - Crawler ve ATS Adaptör Soyutlamaları (`ATSAdapter`)
   - Modüler Eşleştirme Motoru Mimarisi (Deterministic Matchers & AI Provider)


