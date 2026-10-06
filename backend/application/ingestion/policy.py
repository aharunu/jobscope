"""Pure geographic policy evaluation; never reads provider payloads or networks."""

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlsplit

from backend.application.job_discovery.dtos import DiscoveredJobDTO

# ISO 3166-1 alpha-2 (including territories); no online geocoding dependency.
COUNTRY_CODES = frozenset(
    [
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AL",
        "AM",
        "AO",
        "AQ",
        "AR",
        "AS",
        "AT",
        "AU",
        "AW",
        "AX",
        "AZ",
        "BA",
        "BB",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BL",
        "BM",
        "BN",
        "BO",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
        "CC",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CK",
        "CL",
        "CM",
        "CN",
        "CO",
        "CR",
        "CU",
        "CV",
        "CW",
        "CX",
        "CY",
        "CZ",
        "DE",
        "DJ",
        "DK",
        "DM",
        "DO",
        "DZ",
        "EC",
        "EE",
        "EG",
        "EH",
        "ER",
        "ES",
        "ET",
        "FI",
        "FJ",
        "FK",
        "FM",
        "FO",
        "FR",
        "GA",
        "GB",
        "GD",
        "GE",
        "GF",
        "GG",
        "GH",
        "GI",
        "GL",
        "GM",
        "GN",
        "GP",
        "GQ",
        "GR",
        "GS",
        "GT",
        "GU",
        "GW",
        "GY",
        "HK",
        "HM",
        "HN",
        "HR",
        "HT",
        "HU",
        "ID",
        "IE",
        "IL",
        "IM",
        "IN",
        "IO",
        "IQ",
        "IR",
        "IS",
        "IT",
        "JE",
        "JM",
        "JO",
        "JP",
        "KE",
        "KG",
        "KH",
        "KI",
        "KM",
        "KN",
        "KP",
        "KR",
        "KW",
        "KY",
        "KZ",
        "LA",
        "LB",
        "LC",
        "LI",
        "LK",
        "LR",
        "LS",
        "LT",
        "LU",
        "LV",
        "LY",
        "MA",
        "MC",
        "MD",
        "ME",
        "MF",
        "MG",
        "MH",
        "MK",
        "ML",
        "MM",
        "MN",
        "MO",
        "MP",
        "MQ",
        "MR",
        "MS",
        "MT",
        "MU",
        "MV",
        "MW",
        "MX",
        "MY",
        "MZ",
        "NA",
        "NC",
        "NE",
        "NF",
        "NG",
        "NI",
        "NL",
        "NO",
        "NP",
        "NR",
        "NU",
        "NZ",
        "OM",
        "PA",
        "PE",
        "PF",
        "PG",
        "PH",
        "PK",
        "PL",
        "PM",
        "PN",
        "PR",
        "PS",
        "PT",
        "PW",
        "PY",
        "QA",
        "RE",
        "RO",
        "RS",
        "RU",
        "RW",
        "SA",
        "SB",
        "SC",
        "SD",
        "SE",
        "SG",
        "SH",
        "SI",
        "SJ",
        "SK",
        "SL",
        "SM",
        "SN",
        "SO",
        "SR",
        "SS",
        "ST",
        "SV",
        "SX",
        "SY",
        "SZ",
        "TC",
        "TD",
        "TF",
        "TG",
        "TH",
        "TJ",
        "TK",
        "TL",
        "TM",
        "TN",
        "TO",
        "TR",
        "TT",
        "TV",
        "TW",
        "TZ",
        "UA",
        "UG",
        "UM",
        "US",
        "UY",
        "UZ",
        "VA",
        "VC",
        "VE",
        "VG",
        "VI",
        "VN",
        "VU",
        "WF",
        "WS",
        "YE",
        "YT",
        "ZA",
        "ZM",
        "ZW",
    ]
)


def normalize_codes(values: list[str]) -> list[str]:
    codes = sorted({v.strip().upper() for v in values})
    if any(v not in COUNTRY_CODES for v in codes):
        raise ValueError("Use valid ISO 3166-1 alpha-2 country codes")
    return codes


def folded(value: str) -> str:
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", value.casefold().replace("ı", "i"))
            if not unicodedata.combining(c)
        ).split()
    )


# All 81 Turkish provinces plus Gebze, a common career-board location.
TURKISH_LOCATIONS = (
    "Adana|Adıyaman|Afyonkarahisar|Ağrı|Amasya|Ankara|"
    "Antalya|Artvin|Aydın|Balıkesir|Bilecik|Bingöl|"
    "Bitlis|Bolu|Burdur|Bursa|Çanakkale|Çankırı|"
    "Çorum|Denizli|Diyarbakır|Edirne|Elazığ|Erzincan|"
    "Erzurum|Eskişehir|Gaziantep|Giresun|Gümüşhane|Hakkari|"
    "Hatay|Isparta|Mersin|İstanbul|İzmir|Kars|"
    "Kastamonu|Kayseri|Kırklareli|Kırşehir|Kocaeli|Konya|"
    "Kütahya|Malatya|Manisa|Kahramanmaraş|Mardin|Muğla|"
    "Muş|Nevşehir|Niğde|Ordu|Rize|Sakarya|"
    "Samsun|Siirt|Sinop|Sivas|Tekirdağ|Tokat|"
    "Trabzon|Tunceli|Şanlıurfa|Uşak|Van|Yozgat|"
    "Zonguldak|Aksaray|Bayburt|Karaman|Kırıkkale|Batman|"
    "Şırnak|Bartın|Ardahan|Iğdır|Yalova|Karabük|"
    "Kilis|Osmaniye|Düzce|Gebze"
)
ALIASES = {
    "TR": ["Turkey", "Türkiye", *TURKISH_LOCATIONS.split("|")],
    "US": ["United States", "United States of America", "USA"],
    "DE": ["Germany", "Deutschland"],
    "GB": ["United Kingdom", "UK"],
    "NL": ["Netherlands"],
    "FR": ["France"],
    "IN": ["India"],
    "PL": ["Poland"],
    "CA": ["Canada"],
    "AU": ["Australia"],
    "ES": ["Spain", "España", "İspanya"],
    "IT": ["Italy"],
    "AE": ["United Arab Emirates", "UAE"],
}


class CountryResolver:
    """Conservative resolver with explicit, structured and location precedence."""

    def resolve(self, job: DiscoveredJobDTO) -> str | None:
        explicit = job.country_code
        if isinstance(explicit, str) and explicit.strip().upper() in COUNTRY_CODES:
            return explicit.strip().upper()
        for key in ("country_code", "country"):
            value = job.metadata.get(key)
            if isinstance(value, str):
                result = self._country(value)
                if result:
                    return result
        location = job.metadata.get("location")
        return self._country(location) if isinstance(location, str) else None

    def _country(self, value: str) -> str | None:
        text = folded(value)
        # A whole country/location field containing an ISO code is unambiguous,
        # including lower-case provider values such as Hirex's "tr" or "es".
        # Codes embedded in ordinary prose still require uppercase spelling.
        if value.strip().upper() in COUNTRY_CODES:
            return value.strip().upper()
        matches = set()
        for code, names in ALIASES.items():
            # Short ISO codes require uppercase upstream spelling, preventing
            # ordinary words such as "in" from being interpreted as countries.
            if re.search(rf"(?<!\w){code}(?!\w)", value):
                matches.add(code)
            for name in names:
                if re.search(rf"(?<!\w){re.escape(folded(name))}(?!\w)", text):
                    matches.add(code)
        return next(iter(matches)) if len(matches) == 1 else None


@dataclass(frozen=True)
class PolicySnapshot:
    origin: str
    allowed_country_codes: tuple[str, ...] = ()
    include_unknown_country: bool = False
    enabled: bool = True

    @property
    def active(self) -> bool:
        return self.enabled and bool(self.allowed_country_codes)

    def decide(self, job: DiscoveredJobDTO) -> tuple[str, str, str | None]:
        country = CountryResolver().resolve(job)
        try:
            url = urlsplit(job.url)
            valid_url = (
                url.scheme in ("https", "http")
                and bool(url.hostname)
                and not url.username
                and not url.password
            )
        except ValueError:
            valid_url = False
        if not job.title or not job.title.strip() or not valid_url:
            return "REJECTED", "INVALID_DISCOVERED_JOB", country
        if not self.active:
            return "ACCEPTED", "NO_COUNTRY_FILTER", country
        if country is None:
            return (
                ("ACCEPTED", "UNKNOWN_INCLUDED", None)
                if self.include_unknown_country
                else ("REJECTED", "COUNTRY_UNKNOWN", None)
            )
        if country in self.allowed_country_codes:
            return "ACCEPTED", "COUNTRY_ALLOWED", country
        return "REJECTED", "COUNTRY_NOT_ALLOWED", country

    def rejects_known_country(self, job: DiscoveredJobDTO) -> bool:
        """Skip expensive enrichment only when list geography proves rejection."""
        country = CountryResolver().resolve(job)
        return (
            self.active
            and country is not None
            and country not in self.allowed_country_codes
        )


def resolve_policy(
    request: dict, source_policy: dict | None, global_policy: dict | None
) -> PolicySnapshot:
    """A disabled override deliberately overrides an enabled global filter."""
    if request["policy_mode"] == "OVERRIDE_SELECTED_SOURCES":
        return PolicySnapshot(
            "RUN_OVERRIDE",
            tuple(request["allowed_country_codes"]),
            request["include_unknown_country"],
            request.get("enabled", True),
        )
    saved = source_policy if source_policy is not None else global_policy
    if saved is None:
        return PolicySnapshot("NO_FILTER", enabled=False)
    return PolicySnapshot(
        "SOURCE_OVERRIDE" if source_policy is not None else "GLOBAL_DEFAULT",
        tuple(saved["allowed_country_codes"]),
        saved["include_unknown_country"],
        saved["enabled"],
    )
