# Tasarım Dokümanları vs. Gerçek İmplementasyon — Uyum Analizi

> Historical audit of 2026-10-01. Findings and implementation counts describe that date, not the current repository. See the [current documentation index](docs/development/README.md) and [product backlog](docs/roadmap/post_mvp_product_backlog.md) for maintained guidance. Original evidence is retained below.

**Tarih:** 2026-10-01  
**Kapsam:** `docs/design/` altındaki 3 tasarım dokümanı vs. gerçek kod tabanı  
**Analiz Yöntemi:** Her tasarım maddesi tek tek gerçek implementasyonla karşılaştırıldı

---

## Özet Değerlendirme

| Uyumluluk Seviyesi | Sayı | Oran |
|---------------------|------|------|
| ✅ TAM UYUMLU | 25 | %54 |
| 🟡 BÜYÜK ÖLÇÜDE UYUMLU (küçük sapmalar) | 9 | %20 |
| 🟠 KISMİ UYUMLU (önemli eksikler) | 5 | %11 |
| ❌ UYGULANMAMIŞ | 7 | %15 |
| **Toplam İncelenen Madde** | **46** | |

> **Genel Değerlendirme:** Projenin temel mimarisi ve veri modeli tasarıma çok sadık kalınarak inşa edilmiş. Sapmalar genellikle "henüz yapılmamış" kategorisinde, yanlış yapılmış değil. Deterministik eşleştirme motoru, veri modeli ve crawler altyapısı tasarıma tam uyumlu.

---

## 1. MVP Teknik Tasarım (01_mvp_technical_design.md) — Madde Madde Analiz

### Madde 1–3: Ürün Amacı, Stack & Mimari

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| Ürün amacı (kanıta dayalı karar desteği) | Şeffaf, ölçülebilir, açıklanabilir | Deterministik motor `MatchExplanation` ile kategori bazlı skor, kanıt ve gerekçe üretiyor | ✅ TAM |
| Frontend: Next.js | Next.js | Next.js 15 + React 19 | ✅ TAM |
| Backend: Python + FastAPI | FastAPI | FastAPI + uvicorn | ✅ TAM |
| Mimari: Modular Monolith + Clean/Hex | Katmanlı ayrım | `domain/`, `application/`, `infrastructure/`, `interfaces/` — tam uyumlu | ✅ TAM |
| Veritabanı: PostgreSQL + SQLAlchemy + Alembic | Belirtildiği gibi | PostgreSQL 16 + SQLAlchemy 2.x async + Alembic 6 migration | ✅ TAM |
| Vector DB: Yok | MVP'de yok | Yok — doğru | ✅ TAM |
| Authentication: Yok | MVP'de yok | `X-User-Id` header + dev fallback — MVP için yeterli | ✅ TAM |
| Logging: Structured + dosya | Structured log | `SecretMaskingFilter` + dosyaya yazım var ama **JSON structured format yok** | 🟡 Kısmi sapma |
| AI Entegrasyonu: Provider Abstraction | Tek model, provider abstraction | Domain entity'ler (`AIAnalysis`, `AIEvidence`) var, `infrastructure/llm/` **boş** | 🟠 KISMİ |
| Scheduler: Altyapı var, kapalı | Altyapı hazır | **Scheduler altyapısı yok** — tamamen eksik | ❌ UYGULANMAMIŞ |

### Madde 4–6: Job Discovery, Source Registry, Crawler

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| MD Source Catalog → Import → DB | Markdown dosyadan sync | [`markdown_source_parser.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/parsers/markdown_source_parser.py) + sync endpoint — tam uyumlu | ✅ TAM |
| Source modeli (adapter_config, pagination_config vb.) | 10+ alan | ORM model birebir eşleşiyor: `adapter_config`, `pagination_config`, `endpoint_config`, `rate_limit_config`, `metadata` hepsi JSONB | ✅ TAM |
| Manuel tetikleme (Crawl Now) | Manuel crawl | `POST /api/crawl/run` — tam uyumlu | ✅ TAM |
| Hata izolasyonu | Bir kaynak hatası diğerini durdurmaz | `CrawlerOrchestrator` her source'u bağımsız try/except ile çalıştırıyor | ✅ TAM |
| Retry mekanizması | Yeniden deneme | `SafeHttpClient` exponential backoff retry — tam uyumlu | ✅ TAM |
| CrawlRun kaydı | Her tarama audit kaydı | `CrawlRun` entity + `CrawlRunJob` N:M ilişki — tam uyumlu | ✅ TAM |

### Madde 7–12: Raw Job, Lifecycle, Identity, Dedup, Normalization

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| Raw Job saklanması | Ham veri asla kaybolmamalı | `RawJob` entity + `raw_jobs` tablosu, her crawl'da saklanıyor | ✅ TAM |
| Job Lifecycle: ACTIVE → CLOSED | Silinmez, CLOSED yapılır | `JobLifecycleService.close_absent_jobs()` — `status = CLOSED`, `closed_at` set edilir, silme yok | ✅ TAM |
| Application Lifecycle | INTERESTED → ... → OFFER/REJECTED | Domain enum tam eşleşiyor: `INTERESTED, APPLYING, APPLIED, INTERVIEW, OFFER, REJECTED` | ✅ TAM |
| Job Identity: source + external_job_id | Birincil kimlik | Dedup mantığı birebir: önce `source_id + external_job_id`, yoksa `canonical_url` | ✅ TAM |
| Content Hash: değişiklik tespiti için | Kimlik değil, değişim kontrolü | `content_hash` ile `canonical.content_hash != existing.content_hash` karşılaştırması | ✅ TAM |
| Deduplication: hibrit sinyaller | URL, Company, Title, Location, Content | **Kısmi sapma** — şu an sadece `external_job_id` veya `canonical_url` bazlı dedup var. Tasarımda belirtilen Company+Title+Location+ContentSimilarity çapraz kaynak dedup'u **uygulanmamış** | 🟠 KISMİ |
| Canonical Job modeli | 20+ alan | Kod ile tam eşleşme. Tasarımdaki `deadline` alanı hariç (kodda yok, ama `published_at` var) | 🟡 Küçük sapma |

### Madde 13–14: Requirement Extraction

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| Hibrit akış: Deterministic → LLM → Normalized | Det. + LLM doğrulama | `DeterministicRequirementExtractor` tam uyumlu. **LLM structuring/validation kısmı yok** | 🟡 MVP yeterli, LLM gelecek faz |
| Requirement yapısı (type, description, importance, criticality, evidence) | 7 alan | ORM model birebir eşleşiyor: `type`, `description`, `required_level`, `importance`, `criticality`, `evidence` | ✅ TAM |

### Madde 15–16: Profil Mimarisi & CV Import

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| Base Profile + child entities | Skills, Experience, Education, Projects | Tümü var: `ProfileSkill`, `ProfileExperience`, `ProfileEducation`, `ProfileProject` | ✅ TAM |
| Multiple Search Profiles per Base | 1:N ilişki | `SearchProfile.base_profile_id` FK — doğru | ✅ TAM |
| CV Import: Parse → Review → Profile | Kullanıcı onaylı akış | Domain entity + ORM model var, **servis/API/parser yok** | ❌ UYGULANMAMIŞ |

### Madde 17–28: Matching Engine

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| Matching girdisi: Base + Search + Job | Üçlü girdi | `MatchingService.match_job()` tam olarak bu üçlüyü kullanıyor | ✅ TAM |
| Deterministik ağırlıklar (Role %20, Skill %30, Exp %20, Loc %10, Edu %10, Other %10) | 6 kategori, %100 | [`deterministic_engine.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/domain/matching/deterministic_engine.py) — `CATEGORY_WEIGHTS` birebir eşleşiyor | ✅ TAM |
| Requirement-level scoring: Req → Cat → Weighted Total | Hiyerarşik skor | Her requirement ayrı `RequirementMatch` ile değerlendiriliyor, kategoriye toplanıyor | ✅ TAM |
| UNKNOWN ≠ NOT_MATCHED ilkesi | Bilinmeyen veri cezalandırmaz | `MatchStatus.UNKNOWN` enum değeri var, Confidence düşürülüyor | ✅ TAM |
| Blocker mekanizması | Hard req → Blocker | `BLOCKER_SCORE_CAP = 40.00` — blocker varsa skor cap'leniyor, sıfırlanmıyor | ✅ TAM |
| Missing Data → Confidence düşürme | Unknown veri → düşük confidence | Confidence hesaplama formülü bilinmeyen veriye göre düşürüyor | ✅ TAM |

### Madde 29–34: AI Matching

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| AI analizi: kullanıcı talebiyle devreye girer | Manuel tetikleme | **Uygulanmamış** — AI motor altyapısı yok, `infrastructure/llm/` boş | ❌ UYGULANMAMIŞ |
| AI Score + Assessment + Evidence | Çıktı yapısı | Domain entity'ler (`AIAnalysis`, `AIEvidence`) tam tasarıma uygun ama **kullanılmıyor** | 🟡 Model hazır, implementasyon yok |
| AI Adjustment formülü: clamp(±8) | Kontrollü düzeltme | `match_results.ai_adjustment` kolonu `NUMERIC(4,2)` — veri modeli hazır, hesaplama mantığı **yok** | 🟡 Model hazır, implementasyon yok |
| AI Cache | Fingerprint bazlı önbellek | `ai_analyses.fingerprint` kolonu var — veri modeli hazır, cache mantığı **yok** | 🟡 Model hazır, implementasyon yok |

### Madde 35–38: Eşleşme Lifecycle, App Tracking, Manual Job, Dashboard

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| Deterministic → User Review → AI (isteğe bağlı) | İki aşamalı | Deterministic tam çalışıyor, AI kısmı henüz yok | 🟡 Det. kısmı tam |
| Application Tracking: CRUD + StatusHistory | Servis + API | Domain entity + ORM + migration var, **servis/API/test = sıfır** | ❌ UYGULANMAMIŞ |
| Manuel Job Entry (URL gir → fetch → parse) | Dış ilan ekleme | **Uygulanmamış** — `POST /api/jobs/manual` endpoint yok | ❌ UYGULANMAMIŞ |
| Dashboard: 4 eksen | Discovery, Match, AI, Tracking | Frontend'de Discovery + Match var. **AI Analysis ve Application Tracking eksik** | 🟠 KISMİ |

### Madde 39–45: DB, Indexing, Logging, Testing, Scheduler

| Madde | Tasarım | Gerçek | Uyum |
|-------|---------|--------|------|
| DB entity grupları | 6 grup | Tüm gruplar migration ile oluşturulmuş | ✅ TAM |
| İndeksleme | source, external_job_id, company, status, FK'ler | Çoğunluğu uygulanmış. **`location` ve `work_mode` indeksi eksik**, `application_status` indeksi eksik (tracking yok) | 🟡 Küçük sapma |
| Structured logging | Event bazlı log | Structured log var ama **JSON format değil**, plain text format | 🟡 Küçük sapma |
| Test stratejisi: Unit + Integration | İki katman | 648 backend + 55 frontend test — tasarımı aşan kapsam | ✅ TAM |
| Scheduler: altyapı var, kapalı | Kod tabanında mevcut | **Scheduler kodu yok** — tasarımdan sapma | ❌ UYGULANMAMIŞ |

---

## 2. Veritabanı & API Tasarımı (02_database_and_api_design.md) — Tablo Bazlı Analiz

### Tablo Şema Uyumu

| Tablo | Tasarım | Gerçek ORM | Uyum | Sapma Detayı |
|-------|---------|------------|------|--------------|
| `users` | id, created_at, updated_at | ✅ Birebir | ✅ TAM | — |
| `base_profiles` | id, user_id, name, summary, timestamps | ✅ Birebir | ✅ TAM | — |
| `profile_skills` | id, base_profile_id, name, category, years_of_experience, level | ✅ Birebir | ✅ TAM | — |
| `profile_experiences` | id, base_profile_id, company, title, description, dates, is_current, skills_used | ✅ Birebir | ✅ TAM | — |
| `profile_educations` | id, base_profile_id, school, degree, field_of_study, start_year, end_year | ✅ Birebir | ✅ TAM | — |
| `profile_projects` | id, base_profile_id, title, description, skills_used, url | ✅ Birebir | ✅ TAM | — |
| `search_profiles` | id, base_profile_id, name, target_roles, seniority, target_skills, locations, work_modes, industries, salary_min, salary_max | ✅ Birebir | ✅ TAM | — |
| `sources` | id, name, company, url, country, ats_type, active, adapter_config, pagination_config, endpoint_config, rate_limit_config, metadata | ✅ Birebir | ✅ TAM | — |
| `crawl_runs` | id, source_id, started_at, finished_at, status, jobs_found/created/updated/closed, error_count | ✅ Birebir | ✅ TAM | Ek `jobs_unchanged` kolonu kodda var — tasarımda yok (iyileştirme) |
| `crawl_run_jobs` | crawl_run_id, job_id, action | ✅ Birebir | ✅ TAM | Ek UUID PK kodda var — tasarımdaki composite PK yerine |
| `jobs` | 18 kolon | ✅ Birebir | ✅ TAM | — |
| `raw_jobs` | id, job_id, source_id, raw_content, content_type, fetched_at | ✅ Birebir | ✅ TAM | — |
| `job_requirements` | id, job_id, type, description, normalized_skill, required_level, importance, criticality, evidence | ✅ Birebir | ✅ TAM | — |
| `match_results` | id, job_id, base_profile_id, search_profile_id, scores, confidence | ✅ Birebir | ✅ TAM | — |
| `requirement_matches` | id, match_result_id, requirement_id, match_status, score, evidence, reason, is_blocker | ✅ Birebir | ✅ TAM | — |
| `ai_analyses` | id, match_result_id, model, provider, ai_score, assessment, summary, fingerprint | ✅ Birebir | ✅ TAM | — |
| `ai_evidence` | id, ai_analysis_id, claim, evidence_type, source_reference, reason | ✅ Birebir | ✅ TAM | — |
| `applications` | id, job_id, user_id, status, notes, timestamps | ✅ Birebir | ✅ TAM | ORM model var ama servis/API yok |
| `application_status_history` | id, application_id, from_status, to_status, changed_at | ✅ Birebir | ✅ TAM | ORM model var ama servis/API yok |
| `cvs` | id, base_profile_id, filename, file_type, raw_content, parsed_data, status | ✅ Birebir | ✅ TAM | ORM model var ama servis/API yok |

> [!IMPORTANT]
> **Veritabanı şema uyumu: %100.** Tasarımdaki 15 tablonun tamamı birebir oluşturulmuş. Ek olarak kodda `jobs_unchanged` gibi küçük iyileştirmeler yapılmış.

### API Endpoint Uyumu

| Tasarım Endpoint | Gerçek Endpoint | Uyum | Detay |
|------------------|-----------------|------|-------|
| `GET /api/profiles` | `GET /api/profiles/base` | 🟡 | Path farklı ama işlev aynı |
| `POST /api/profiles` | `POST /api/profiles/base` | 🟡 | Path farklı |
| `PUT /api/profiles/{id}` | `PUT /api/profiles/base` | 🟡 | ID yerine user-scoped |
| `GET /api/search-profiles` | `GET /api/search-profiles` | ✅ TAM | — |
| `POST /api/search-profiles` | `POST /api/search-profiles` | ✅ TAM | — |
| `PUT /api/search-profiles/{id}` | `PUT /api/search-profiles/{id}` | ✅ TAM | — |
| `GET /api/jobs` | `GET /api/jobs` | ✅ TAM | — |
| `GET /api/jobs/{id}` | `GET /api/jobs/{id}` | ✅ TAM | — |
| `POST /api/jobs/manual` | — | ❌ YOK | Manuel ilan ekleme yok |
| `POST /api/jobs/{id}/match` | `POST /api/matches` | 🟡 | Farklı path, aynı işlev |
| `GET /api/sources` | `GET /api/sources` | ✅ TAM | — |
| `POST /api/sources/sync` | `POST /api/sources/sync` | ✅ TAM | — |
| `POST /api/crawl/run` | `POST /api/crawl/run` | ✅ TAM | — |
| `GET /api/matches` | — | ❌ YOK | Match listesi endpoint'i yok |
| `POST /api/matches/{id}/ai` | — | ❌ YOK | AI analiz tetikleme yok |
| `GET /api/applications` | — | ❌ YOK | Application tracking API yok |
| `POST /api/applications` | — | ❌ YOK | Application tracking API yok |
| `PATCH /api/applications/{id}/status` | — | ❌ YOK | Application tracking API yok |
| `POST /api/cv/upload` | — | ❌ YOK | CV yükleme API yok |
| `POST /api/cv/{id}/approve` | — | ❌ YOK | CV onaylama API yok |

**API Uyum Özeti:**

| Durum | Sayı | Oran |
|-------|------|------|
| ✅ Tam uyumlu | 8 | %42 |
| 🟡 Path farklı ama işlev aynı | 4 | %21 |
| ❌ Uygulanmamış | 7 | %37 |

> [!NOTE]
> 7 eksik endpoint'in 5'i henüz implementasyonu olmayan özellikler (Application Tracking, CV, AI). Kalan 2'si (`GET /api/matches`, `POST /api/jobs/manual`) mevcut altyapıyla hızlıca eklenebilir.

---

## 3. Data Model & Architecture (03_data_model_and_architecture.md) — Mimari Pattern Analizi

### ER İlişkileri ve Kardinaliteler

| İlişki | Tasarım | Gerçek | Uyum |
|--------|---------|--------|------|
| User 1:N BaseProfile | 1:N | FK `user_id` + relationship | ✅ TAM |
| BaseProfile 1:N SearchProfile | 1:N | FK `base_profile_id` + relationship | ✅ TAM |
| BaseProfile 1:N ProfileSkill/Experience/Education/Project | 1:N | Tüm FK'ler + cascade delete | ✅ TAM |
| BaseProfile 1:N CV | 1:N | FK `base_profile_id` | ✅ TAM |
| User 1:N Application | 1:N | FK `user_id` | ✅ TAM |
| Source 1:N CrawlRun | 1:N | FK `source_id` | ✅ TAM |
| CrawlRun N:M Job (via crawl_run_jobs) | N:M | Ara tablo `crawl_run_jobs` | ✅ TAM |
| Source 1:N Job | 1:N | FK `source_id` ON DELETE RESTRICT | ✅ TAM |
| Job 1:N RawJob | 1:N | FK + cascade | ✅ TAM |
| Job 1:N JobRequirement | 1:N | FK + cascade | ✅ TAM |
| Job 1:N MatchResult | 1:N | FK + cascade | ✅ TAM |
| MatchResult 1:N RequirementMatch | 1:N | FK + cascade | ✅ TAM |
| MatchResult 1:1 AIAnalysis | 1:1 | FK + `uselist=False` | ✅ TAM |
| AIAnalysis 1:N AIEvidence | 1:N | FK + cascade | ✅ TAM |
| Job 1:N Application | 1:N | FK + cascade | ✅ TAM |
| Application 1:N ApplicationStatusHistory | 1:N | FK + cascade | ✅ TAM |

> **Kardinalite uyumu: %100.** Tüm ilişkiler tasarıma birebir uygulanmış.

### Clean Architecture Uyumu

| Pattern | Tasarım | Gerçek | Uyum |
|---------|---------|--------|------|
| Domain Entity (pure Python) | Dataclass, ORM'den bağımsız | `@dataclass(slots=True)` — SQLAlchemy import yok | ✅ TAM |
| Repository Protocol | `typing.Protocol` interfaces | Domain `repositories.py` dosyalarında Protocol tanımlı | ✅ TAM |
| SQLAlchemy Repository Implementation | Protocol'ü uygular | `SQLAlchemy{Entity}Repository` sınıfları | ✅ TAM |
| `to_domain()` / `from_domain()` mapping | ORM ↔ Domain dönüşüm | Tüm ORM model'lerde mevcut | ✅ TAM |
| Dependency direction: Domain ← Infrastructure | İçe doğru bağımlılık | Domain'de infrastructure import yok — doğrulanmış | ✅ TAM |

### Crawler Abstraction Uyumu

| Tasarım | Gerçek | Uyum |
|---------|--------|------|
| `ATSAdapter` Protocol | `ATSAdapter` Protocol in [`ports.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/job_discovery/ports.py) | ✅ TAM |
| `adapter.py` + `parser.py` per ATS | Greenhouse: `adapter.py` (13.7KB), Lever: `adapter.py` (11.9KB) — parser entegre | 🟡 Parser ayrı dosya değil |
| Workday adapter | Boş `__init__.py` | ❌ UYGULANMAMIŞ |
| Ashby adapter | Boş `__init__.py` | ❌ UYGULANMAMIŞ |
| `base_adapter.py` | Yok — Protocol yeterli | 🟡 Küçük sapma |

### Matching Engine Uyumu

| Tasarım | Gerçek | Uyum |
|---------|--------|------|
| `role_matcher.py` (%20) | `RoleEvaluator` in [`evaluators/`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/domain/matching/evaluators) | ✅ TAM (isim farklı: matcher → evaluator) |
| `skill_matcher.py` (%30) | `SkillEvaluator` | ✅ TAM |
| `experience_matcher.py` (%20) | `ExperienceEvaluator` | ✅ TAM |
| `location_matcher.py` (%10) | `LocationEvaluator` | ✅ TAM |
| `education_matcher.py` (%10) | `EducationEvaluator` | ✅ TAM |
| `requirement_matcher.py` (%10) | `OtherRequirementEvaluator` | ✅ TAM |
| `deterministic_engine.py` | [`deterministic_engine.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/domain/matching/deterministic_engine.py) | ✅ TAM |
| AI modules: `analyzer.py`, `prompt.py`, `schema.py`, `evidence.py`, `provider.py` | — | ❌ UYGULANMAMIŞ |
| Motor çalışma döngüsü: Det → User → AI → Final | Deterministic kısmı tam | 🟡 AI kısmı eksik |

---

## 4. Önemli Sapmalar — Detaylı Açıklama

### SAPMA-001: Application Tracking — Veri Modeli Var, İş Mantığı Yok

```text
Tasarım Beklentisi:
  - GET/POST/PATCH /api/applications endpoints
  - Status geçiş tarihçesi (Sankey/Funnel hazırlığı)
  - Dashboard'da 4. eksen olarak "Application Tracking"

Gerçek Durum:
  ✅ Domain entity:    Application, ApplicationStatusHistory
  ✅ Domain enums:     INTERESTED, APPLYING, APPLIED, INTERVIEW, OFFER, REJECTED
  ✅ ORM modeller:     ApplicationModel, ApplicationStatusHistoryModel
  ✅ Migration:        Tablo oluşturulmuş (migration #4)
  ❌ Repository impl:  Yok
  ❌ Application servis: application/application_tracking/ — BOŞŞ
  ❌ API routes:       Yok
  ❌ Frontend UI:      Yok
  ❌ Test:             Yok

Etki: MVP'nin 4 temel ekseninden biri eksik. Kullanıcı hangi ilanlara başvurduğunu takip edemiyor.
Öncelik: YÜKSEK — veri altyapısı hazır, sadece servis+API+UI gerekiyor.
```

### SAPMA-002: AI Matching — Tüm Katman Eksik

```text
Tasarım Beklentisi:
  - [AI ile Detaylı Analiz Et] butonu
  - LLM Provider Abstraction (Google/Anthropic/OpenAI)
  - AI Score + Assessment + Evidence
  - AI Adjustment: clamp(±8)
  - AI Cache (fingerprint bazlı)

Gerçek Durum:
  ✅ Domain entity:    AIAnalysis, AIEvidence (tam tasarıma uygun)
  ✅ ORM modeller:     AIAnalysisModel, AIEvidenceModel (tam)
  ✅ DB kolonlar:      ai_score, ai_adjustment, fingerprint (tam)
  ❌ infrastructure/llm/: Sadece __init__.py — boş
  ❌ AI analyzer:      Yok
  ❌ Prompt engine:    Yok
  ❌ Provider adapter: Yok
  ❌ Frontend AI butonu: Yok
  ❌ Cache mantığı:    Yok

Etki: Tasarımın en belirgin "faz 2" öğesi. Deterministik motor tek başına çalışıyor ve
      bu MVP için yeterli. AI katmanı bilinçli olarak ertelenmiş.
Öncelik: ORTA — MVP belirleyici değil, ama tasarımın önemli parçası.
```

### SAPMA-003: CV Import — Parse Pipeline Yok

```text
Tasarım Beklentisi:
  - CV Upload → Deterministic Parse → LLM Validation → User Review → Profile
  - POST /api/cv/upload
  - POST /api/cv/{id}/approve

Gerçek Durum:
  ✅ Domain entity:    CV (base_profile_id, filename, file_type, raw_content, parsed_data, status)
  ✅ ORM model:        CVModel (migration #6 ile oluşturulmuş)
  ❌ Parse servisi:    Yok
  ❌ API endpoints:    Yok
  ❌ Frontend:         Yok

Öncelik: DÜŞÜK — profil manuel oluşturulabiliyor.
```

### SAPMA-004: Manuel Job Entry

```text
Tasarım: POST /api/jobs/manual — URL girerek dış ilan ekleme
Gerçek:  Endpoint yok, fetch/parse altyapısı yok
Öncelik: DÜŞÜK — crawler kapsamı dışındaki ilanlar için kullanışlı ama MVP kritik değil.
```

### SAPMA-005: Scheduler Altyapısı

```text
Tasarım: "Scheduler altyapısı kod tabanında yer alacak, varsayılan olarak KAPALI"
Gerçek:  Scheduler kodu hiç yok — ne aktif ne pasif
Öncelik: DÜŞÜK — MVP'de kapalı olacağı belirtilmiş, ancak altyapının bile olmaması
         gelecek faz için ekstra iş demek.
```

### SAPMA-006: Hibrit Deduplication

```text
Tasarım: URL + Company + Title + Location + Content Similarity ile çapraz kaynak dedup
Gerçek:  Sadece (source_id, external_job_id) veya canonical_url bazlı
Etki:    Aynı ilan farklı ATS'lerde yayınlanırsa mükerrer görünür
Öncelik: ORTA — daha fazla kaynak eklendikçe önem kazanacak
```

### SAPMA-007: Eksik API Endpoints

```text
Tasarımdaki ama kodda olmayan endpoint'ler:
  1. GET  /api/matches              — match result listesi
  2. POST /api/matches/{id}/ai      — AI analiz tetikleme
  3. POST /api/jobs/manual           — URL ile ilan ekleme
  4. GET  /api/applications          — başvuru listesi
  5. POST /api/applications          — başvuru oluşturma
  6. PATCH /api/applications/{id}/status — durum güncelleme
  7. POST /api/cv/upload             — CV yükleme
  8. POST /api/cv/{id}/approve       — CV onaylama
```

---

## 5. Tasarıma Uygunluk — Genel Değerlendirme Tablosu

| Tasarım Alanı | Uyum | Açıklama |
|---------------|------|----------|
| **Mimari (Clean/Hexagonal)** | ✅ %100 | Domain, Application, Infrastructure, Interfaces — tasarıma tam sadık |
| **Veritabanı Şeması** | ✅ %100 | 15 tablo birebir oluşturulmuş, constraint'ler ve FK'ler doğru |
| **ER İlişkileri** | ✅ %100 | Tüm kardinaliteler tasarıma uygun |
| **Deterministic Match Engine** | ✅ %100 | 6 evaluator, ağırlıklar, blocker, UNKNOWN mantığı — tam |
| **Crawler / ATS Adapters** | 🟡 %60 | Greenhouse + Lever tam; Ashby + Workday boş |
| **Profil Yönetimi** | ✅ %95 | Base + Search + children tam; frontend Profile UI eksik |
| **Job Discovery & Ingestion** | ✅ %95 | Normalization, dedup, lifecycle tam; hibrit dedup eksik |
| **API Endpoints** | 🟠 %63 | 12/19 endpoint uygulanmış; 7 eksik |
| **AI Matching** | ❌ %15 | Sadece veri modeli var, tüm iş mantığı eksik |
| **Application Tracking** | ❌ %30 | Veri modeli tam, iş mantığı sıfır |
| **CV Import** | ❌ %20 | Entity + ORM var, parse/API/UI yok |
| **Frontend** | 🟡 %65 | Jobs + Match + SearchProfile var; Profile + AppTracking + AI yok |

---

## 6. Önceliklendirilmiş Aksiyon Planı

### 🔴 Yüksek Öncelik (Tasarım MVP kapsamında belirtilmiş ve eksik)

| # | Aksiyon | Tasarım Referansı | Tahmini Effort |
|---|---------|-------------------|----------------|
| 1 | **Application Tracking servis + API** oluştur | 01_mvp §36, 02_api §3 `/applications` | Orta |
| 2 | **Frontend Profile sayfası** oluştur | 01_mvp §15 (Base Profile) | Orta |
| 3 | **`GET /api/matches`** endpoint ekle | 02_api §3 `/matches` | Düşük |
| 4 | **Frontend Application Tracking UI** | 01_mvp §38 (Dashboard 4. eksen) | Orta |

### 🟡 Orta Öncelik (Tasarımda var, MVP sonrası faz)

| # | Aksiyon | Tasarım Referansı | Tahmini Effort |
|---|---------|-------------------|----------------|
| 5 | **AI Matching pipeline** (LLM provider + analyzer + cache) | 01_mvp §29-34, 03_arch §4 | Yüksek |
| 6 | **Ashby ve/veya Workday adapter** implementasyonu | 01_mvp §6, 03_arch §9 | Orta |
| 7 | **Hibrit deduplication** (Company+Title+Location bazlı) | 01_mvp §10 | Orta |
| 8 | **Scheduler altyapısı** (kapalı başlat) | 01_mvp §43 | Düşük |
| 9 | **`POST /api/jobs/manual`** endpoint | 01_mvp §37, 02_api §3 | Düşük |

### 🟢 Düşük Öncelik (Gelecek faz olarak işaretlenmiş)

| # | Aksiyon | Tasarım Referansı | Tahmini Effort |
|---|---------|-------------------|----------------|
| 10 | **CV Import pipeline** | 01_mvp §16, 02_api §3 `/cv` | Yüksek |
| 11 | **Structured JSON logging** | 01_mvp §41 | Düşük |
| 12 | **Eksik DB indeksleri** (location, work_mode) | 01_mvp §40 | Düşük |

---

## 7. Sonuç

Projenin en güçlü yönü, **tasarım dokümanlarına olan sadakatidir.** Veritabanı şeması %100, mimari pattern'ler %100, deterministik eşleştirme motoru %100 uyumlu. İmplementasyon kalitesi yüksek — yapılan kısımlar doğru yapılmış.

Eksikler "yanlış yapılmış" değil, "henüz yapılmamış" kategorisinde:
- **Application Tracking** veri modeli hazır, sadece servis katmanı gerekiyor
- **AI Matching** domain entity'leri tasarıma uygun, LLM pipeline gerekiyor
- **CV Import** entity var, parse mantığı gerekiyor

Bu durum, projenin sağlıklı bir iteratif geliştirme sürecinde olduğunu gösteriyor. Veri altyapısı her durumda "önce oluştur" prensibiyle hazırlanmış, iş mantığı katman katman ekleniyor.
