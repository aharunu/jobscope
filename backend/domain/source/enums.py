"""Source domain enumerations and classification."""

from __future__ import annotations

import enum


class KnownATSType(enum.StrEnum):
    """Recognized ATS platform types supported or tracked by JobScope."""

    LEVER = "lever"
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    ASHBY = "ashby"
    SMARTRECRUITERS = "smartrecruiters"
    RECRUITEE = "recruitee"
    PERSONIO = "personio"
    WORKABLE = "workable"
    BAMBOOHR = "bamboohr"
    HIREX = "hirex"
    TEAMTAILOR = "teamtailor"
    ORACLE = "oracle"
    KARIYER_NET = "kariyer_net"


def is_known_ats_type(ats_type: str) -> bool:
    """Check whether an ATS type string matches a recognized platform."""
    try:
        KnownATSType(ats_type.lower())
        return True
    except ValueError:
        return False
