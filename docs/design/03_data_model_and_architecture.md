# Personal Job Intelligence — ER İlişkileri, SQLAlchemy Modelleri ve Clean Architecture

Bu doküman, veri modelinin nihai kardinalite ilişkilerini, Clean Architecture prensiplerine dayalı domain-repository ayrımını, SQLAlchemy model taslaklarını, Crawler ve Matching motoru soyutlamalarını (abstractions) tanımlar.

- **İlgili Dokümanlar:**
  - [01_mvp_technical_design.md](file:///c:/Users/aharu/Documents/GitHub/Crawler/docs/01_mvp_technical_design.md) — 45 Maddelik MVP Teknik Tasarım & Mimari Kararlar
  - [02_database_and_api_design.md](file:///c:/Users/aharu/Documents/GitHub/Crawler/docs/02_database_and_api_design.md) — PostgreSQL Tablo Şemaları ve FastAPI API Tasarımı

---

## 1. Nihai ER İlişkileri ve Kardinaliteler

### 1.1 Kullanıcı ve Profil Tarafı
```
User
 │
 ├── 1:N ── BaseProfile
 │              │
 │              ├── 1:N ── SearchProfile
 │              ├── 1:N ── ProfileSkill
 │              ├── 1:N ── ProfileExperience
 │              ├── 1:N ── ProfileEducation
 │              ├── 1:N ── ProfileProject
 │              └── 1:N ── CV
 │
 └── 1:N ── Application
```

### 1.2 Kaynak, İlan, Eşleştirme ve Başvuru Tarafı
```
Source
 │
 ├── 1:N ── CrawlRun
 │              │
 │              └── N:M ── crawl_run_jobs ── (Job)
 │
 └── 1:N ── Job
               │
               ├── 1:N ── RawJob
               ├── 1:N ── JobRequirement
               │
               ├── 1:N ── MatchResult
               │             │
               │             ├── 1:N ── RequirementMatch
               │             └── 1:1 ── AIAnalysis
               │                            │
               │                            └── 1:N ── AIEvidence
               │
               └── 1:N ── Application
                                │
                                └── 1:N ── ApplicationStatusHistory
```

---

## 2. Kritik Eşleştirme Varlığı: `MatchResult`

Bir eşleştirme işlemi (match) üç temel varlığı bir araya getirir:
$$\text{BaseProfile} + \text{SearchProfile} + \text{Job} \implies \text{MatchResult}$$

### 2.1 Çift Referans (`base_profile_id` & `search_profile_id`) Kararı
- Normalizasyon açısından `SearchProfile` zaten `BaseProfile`'a bağlıdır ve `base_profile_id` taşımak teorik olarak bir miktar redundacy (fazlalık) barındırır.
- **Mimari Karar:** MVP'de her iki ID de `MatchResult` tablosunda açıkça tutulur.
  - **Gerekçe:** "Bu eşleşme hangi ana profile ve hangi hedef arama profiline aittir?" sorgusu doğrudan indeks üzerinden tek adımda çözülür; JOIN maliyeti ve karmaşası ortadan kalkar.
  - **Veri Bütünlüğü:** DB constraint ve repository validasyonu ile `search_profile.base_profile_id == match_result.base_profile_id` güvence altına alınır.

### 2.2 Tekillik ve Overwrite Politikası
```sql
UNIQUE (job_id, base_profile_id, search_profile_id)
```
- Aynı profil kombinasyonu ile bir ilan yeniden eşleştirildiğinde eski sonuç silinir/üzerine yazılır (overwrite).
- MVP aşamasında versiyon geçmişi karmaşası oluşturulmaz; daima en güncel eşleştirme durumu tutulur.

---

## 3. Gereksinim Seviyesinde Eşleştirme: `JobRequirement` & `RequirementMatch`

Matching motoru ilana bir bütün olarak kör bir puan vermek yerine, ayrıştırılmış gereksinimler bazında çalışır:

```
Job (Örn: ML Engineer)
 │
 ├── Python      (REQUIRED,  HIGH,     CRITICAL)
 ├── PyTorch     (REQUIRED,  HIGH,     CRITICAL)
 ├── Docker      (PREFERRED, MEDIUM,   NORMAL)
 ├── English     (REQUIRED,  HIGH,     NORMAL)
 └── Kubernetes  (PREFERRED, LOW,      NORMAL)
```

### Akış
$$\text{JobRequirement} \xrightarrow{\text{RequirementMatcher}} \text{RequirementMatch}$$

### 3.1 Explainability ve Değerlendirme Çeşitliliği
`RequirementMatch` kaydı asla sadece `True/False` (boolean) olamaz. Sistem tam açıklanabilirlik sunar:

```
Requirement: PyTorch
Match Status: PARTIAL
Score:        0.65
Evidence:     "TensorFlow + Deep Learning project (Project #2)"
Reason:       "Transferable deep learning experience exists, but direct PyTorch experience is not specified."
Is Blocker:   false
```

### 3.2 `match_status` Enum Değerleri
- `MATCHED`: Profilde açık ve doğrudan karşılığı var.
- `PARTIAL`: Doğrudan aynı teknoloji değil, ancak aktarılabilir (transferable) yetkinlik mevcut.
- `NOT_MATCHED`: İlanda açıkça istenmiş ve kullanıcının kriterleriyle çelişen/olmayan durum.
- `UNKNOWN`: Profilde veya ilanda bu konuya dair yeterli veri yok.

### 3.3 Kritik Prensip: `UNKNOWN` Önemi
> **Kural:** Profilde ilgili gereksinime dair bir kayıt olmaması doğrudan `NOT_MATCHED` anlamına gelmez.

Örneğin ilanda *"Kubernetes production experience"* isteniyor ancak profil projelerinde Kubernetes'ten hiç bahsedilmiyorsa:
- Durum: `UNKNOWN`
- Skor etkisi: Skora orantısız negatif darbe vurulmaz.
- Güven etkisi: `Confidence` puanı düşürülür ve risk uyarısı olarak işaretlenir.

---

## 4. AI Değerlendirmesi & Kanıt Doğrulama: `AIAnalysis` & `AIEvidence`

Kullanıcı `[AI ile Detaylı Analiz Et]` butonuna bastığında:

```
MatchResult
     │
     └── 1:1 ── AIAnalysis
                     │
                     ├── deterministic_score: 82
                     ├── ai_score:            91
                     ├── ai_adjustment:       +2.7 (clamped ±8)
                     ├── final_score:         84.7
                     ├── confidence:          93%
                     │
                     └── 1:N ── AIEvidence
```

### 4.1 Kanıt Yapısı (`AIEvidence`)
AI modelinin havada kalan genel çıkarımlar yapması engellenir:

```
Claim:            "Candidate has strong ML project experience."
Source Reference: "BaseProfile.profile_projects[2]"
Reason:           "CNN-based traffic sign recognition project demonstrates practical deep learning experience."
```

- Dayanak bulunamıyorsa: `Source Reference: INSUFFICIENT_EVIDENCE` olarak etiketlenir.
- Kullanıcı arayüzde *"Model neden bu puanı verdi?"* sorusunun cevabını doğrudan kanıt kartlarında görür.

---

## 5. Başvuru Yönetimi: `Application` & `ApplicationStatusHistory`

İlan (`Job`) sistem tarafından taranan nesnel piyasa verisidir; Başvuru (`Application`) ise kullanıcının sürece dair iradesidir.

```
Job = ACTIVE   ───→  Application = INTERESTED
Job = CLOSED   ───→  Application = INTERVIEW (İlan kapansa bile süreç devam edebilir)
```

### Durum Geçiş Tarihçesi (`ApplicationStatusHistory`)
```
[DISCOVERED] ──→ INTERESTED ──→ APPLYING ──→ APPLIED ──→ INTERVIEW ──→ OFFER
                                                 │
                                                 └──→ REJECTED
```
Her aşama değişikliğinde `application_status_history` tablosuna `(from_status, to_status, changed_at)` kaydı düşülür. Bu sayede Sankey diyagramı ve başvuru dönüşüm hunisi (funnel) matematiksel olarak oluşturulabilir.

---

## 6. Kaynak & İlan İlişkisi ve Deduplication Mimarisi

- **MVP Kuralı:** Her canonical `Job` tek bir `source_id` üzerinden sisteme kaydedilir.
- **Hybrid Deduplication & Teknik Borç:** Aynı ilan hem Lever hem Greenhouse hem de bir şirket kariyer sayfasında yayınlandığında, hibrit deduplication ile tek bir `Job` olarak tutulur.
- **Phase 2:** İlerleyen aşamalarda bir ilanın tüm kaynak bağlantılarını tutmak için `job_sources (job_id, source_id, external_url)` ara tablosu eklenebilir. MVP'de bu karmaşıklık ötelenmiştir.

---

## 7. Clean Architecture & SQLAlchemy Model Taslağı

Domain modelleri (iş kuralları) ile veritabanı ORM modelleri birbirinden ayrılır.

```
Domain Entity  ──(iş kuralları)──┐
                                 ▼
Repository Interface (Protocol) ◄── Application Layer
                                 ▲
SQLAlchemy Repository ───────────┘
         │
         ▼
SQLAlchemy ORM Model
         │
         ▼
   PostgreSQL DB
```

### 7.1 SQLAlchemy ORM Modelleri Taslağı

```python
from datetime import datetime
import uuid
from typing import List, Optional
from sqlalchemy import (
    String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum

class Base(DeclarativeBase):
    pass

# --- Enums ---
class JobStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"

class RequirementType(str, enum.Enum):
    SKILL = "SKILL"
    EXPERIENCE = "EXPERIENCE"
    EDUCATION = "EDUCATION"
    LANGUAGE = "LANGUAGE"
    CERTIFICATION = "CERTIFICATION"
    OTHER = "OTHER"

class RequirementLevel(str, enum.Enum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"

class MatchStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    NOT_MATCHED = "NOT_MATCHED"
    UNKNOWN = "UNKNOWN"

class ApplicationStatus(str, enum.Enum):
    INTERESTED = "INTERESTED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"


# --- Core Models ---
class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    external_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    salary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.ACTIVE, nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source: Mapped["SourceModel"] = relationship(back_populates="jobs")
    raw_jobs: Mapped[List["RawJobModel"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    requirements: Mapped[List["JobRequirementModel"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    match_results: Mapped[List["MatchResultModel"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    applications: Mapped[List["ApplicationModel"]] = relationship(back_populates="job")

    __table_args__ = (
        UniqueConstraint("source_id", "external_job_id", name="uq_source_external_job_id"),
    )


class JobRequirementModel(Base):
    __tablename__ = "job_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[RequirementType] = mapped_column(SQLEnum(RequirementType), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_skill: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    required_level: Mapped[RequirementLevel] = mapped_column(SQLEnum(RequirementLevel), default=RequirementLevel.REQUIRED)
    importance: Mapped[str] = mapped_column(String(50), default="MEDIUM")
    criticality: Mapped[str] = mapped_column(String(50), default="NORMAL")
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    job: Mapped["JobModel"] = relationship(back_populates="requirements")
    matches: Mapped[List["RequirementMatchModel"]] = relationship(back_populates="requirement", cascade="all, delete-orphan")


class MatchResultModel(Base):
    __tablename__ = "match_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    base_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("base_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    search_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("search_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    deterministic_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    ai_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    ai_adjustment: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), default=0.0)
    final_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    job: Mapped["JobModel"] = relationship(back_populates="match_results")
    requirement_matches: Mapped[List["RequirementMatchModel"]] = relationship(back_populates="match_result", cascade="all, delete-orphan")
    ai_analysis: Mapped[Optional["AIAnalysisModel"]] = relationship(back_populates="match_result", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("job_id", "base_profile_id", "search_profile_id", name="uq_job_base_search_profile"),
    )


class RequirementMatchModel(Base):
    __tablename__ = "requirement_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match_results.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_requirements.id", ondelete="CASCADE"), nullable=False)
    match_status: Mapped[MatchStatus] = mapped_column(SQLEnum(MatchStatus), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    is_blocker: Mapped[bool] = mapped_column(Boolean, default=False)

    match_result: Mapped["MatchResultModel"] = relationship(back_populates="requirement_matches")
    requirement: Mapped["JobRequirementModel"] = relationship(back_populates="matches")


class AIAnalysisModel(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match_results.id", ondelete="CASCADE"), nullable=False, unique=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    assessment: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    match_result: Mapped["MatchResultModel"] = relationship(back_populates="ai_analysis")
    evidence_list: Mapped[List["AIEvidenceModel"]] = relationship(back_populates="ai_analysis", cascade="all, delete-orphan")


class AIEvidenceModel(Base):
    __tablename__ = "ai_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    ai_analysis: Mapped["AIAnalysisModel"] = relationship(back_populates="evidence_list")
```

---

## 8. Repository Yaklaşımı (Clean Ports & Adapters)

Domain katmanı veritabanı teknolojisinden (SQLAlchemy, PostgreSQL vb.) haberdar olmaz. Yalnızca Python `typing.Protocol` arayüzlerini tanımlar:

```python
# domain/job/repositories.py
from typing import Protocol, Optional, List
from uuid import UUID
from domain.job.entities import Job

class JobRepository(Protocol):
    async def get_by_id(self, job_id: UUID) -> Optional[Job]:
        ...

    async def get_by_canonical_url(self, url: str) -> Optional[Job]:
        ...

    async def get_active_jobs(self, limit: int = 50, offset: int = 0) -> List[Job]:
        ...

    async def save(self, job: Job) -> Job:
        ...

    async def close_inactive_jobs(self, source_id: UUID, seen_job_ids: List[UUID]) -> int:
        ...
```

Infrastructure katmanı bu protokolü SQLAlchemy oturumuyla (`AsyncSession`) uygular:

```python
# infrastructure/database/repositories/job_repository.py
from domain.job.repositories import JobRepository
from domain.job.entities import Job
from infrastructure.database.models.job import JobModel
from sqlalchemy.ext.asyncio import AsyncSession

class SQLAlchemyJobRepository(JobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, job_id: UUID) -> Optional[Job]:
        orm_model = await self.session.get(JobModel, job_id)
        return orm_model.to_domain() if orm_model else None

    async def save(self, job: Job) -> Job:
        orm_model = JobModel.from_domain(job)
        merged = await self.session.merge(orm_model)
        await self.session.commit()
        return merged.to_domain()
```

---

## 9. Crawler Abstraction (Ports & Adapters)

Tüm ATS ve web scraper bileşenleri ortak bir adaptör protokolü ile izole edilir.

```python
# application/job_discovery/ports.py
from typing import Protocol, List
from domain.source.entities import Source
from domain.job.entities import RawJob

class ATSAdapter(Protocol):
    """Her ATS (Lever, Greenhouse, Workday, Ashby vb.) bu adaptörü uygular."""
    
    async def discover_jobs(self, source: Source) -> List[RawJob]:
        """Kaynaktan tüm açık ilanların ham listesini çeker."""
        ...

    async def fetch_job(self, url: str) -> RawJob:
        """Belirli bir ilan sayfasını indirir."""
        ...
```

### Dizin Yerleşimi:
```
infrastructure/ats/
    ├── base_adapter.py
    ├── lever/
    │   ├── adapter.py
    │   └── parser.py
    ├── greenhouse/
    │   ├── adapter.py
    │   └── parser.py
    ├── workday/
    ├── ashby/
    └── custom/
```
Yeni bir ATS veya site adaptörü eklemek domain mantığını etkilemez; sadece `ATSAdapter` protokolünü uygulayan yeni bir klasör oluşturulur.

---

## 10. Matching Motoru Mimarisi

Deterministik motor ile AI motoru modüler alt matcher'lara bölünür.

```
Matching Engine
│
├── Matcher Alt Bileşenleri (Deterministic)
│   ├── role_matcher.py          (%20 Ağırlık)
│   ├── skill_matcher.py         (%30 Ağırlık)
│   ├── experience_matcher.py    (%20 Ağırlık)
│   ├── location_matcher.py      (%10 Ağırlık)
│   ├── education_matcher.py     (%10 Ağırlık)
│   └── requirement_matcher.py   (%10 Ağırlık)
│
├── deterministic_engine.py      (Ağırlıklı birleştirme + Confidence hesaplama)
│
└── ai/
    ├── analyzer.py              (AI orkestrasyonu)
    ├── prompt.py                (Role, Job, Profile şablonları)
    ├── schema.py                (Pydantic çıktı şemaları)
    ├── evidence.py              (Kanıt eşleme ve doğrulama)
    └── provider.py              (LLM Sağlayıcı Abstraction: Google / Anthropic / OpenAI)
```

### Motor Çalışma Döngüsü:
```
BaseProfile + SearchProfile + Job
               │
               ▼
      DeterministicEngine
               │
               ├── RoleMatcher.match()
               ├── SkillMatcher.match()
               ├── ExperienceMatcher.match()
               ├── LocationMatcher.match()
               ├── EducationMatcher.match()
               └── RequirementMatcher.match()
               │
               ▼
          MatchResult
    (deterministic_score = 0–100, requirement_matches listesi)
               │
               ▼
      [Kullanıcı Talebi: AI ile Analiz Et]
               │
               ▼
           AIAnalyzer
               │
               ├── LLM Prompt & Schema Execution
               ├── AIEvidence Extraction
               └── AI Adjustment: clamp((AI - Det) * α, -8, +8)
               │
               ▼
     Nihai MatchResult (final_score, confidence, ai_analysis)
```
