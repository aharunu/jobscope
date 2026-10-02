"""Structural/source-quote verification, not an assertion of semantic truth."""

import re

from backend.application.matching.ai.schema import EvidenceOutput

SECTIONS = {
    "SKILL": "skills",
    "EXPERIENCE": "experiences",
    "EDUCATION": "educations",
    "PROJECT": "projects",
}


def source_text(value):
    if isinstance(value, dict):
        return "\n".join(source_text(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(source_text(v) for v in value)
    return "" if value is None else str(value)


def validate_evidence(evidence: list[EvidenceOutput], context):
    validated = []
    valid_count = 0
    for item in evidence:
        reference = re.fullmatch(
            r"profile\.(skills|experiences|educations|projects)\[(\d+)\]",
            item.source_reference,
        )
        valid = False
        if reference and reference[1] == SECTIONS.get(item.evidence_type):
            records = context["profile"][reference[1]]
            index = int(reference[2])
            valid = (
                index < len(records)
                and len(item.source_quote.strip()) >= 3
                and item.source_quote in source_text(records[index])
            )
        if valid:
            valid_count += 1
            validated.append(item)
        else:
            validated.append(
                item.model_copy(
                    update={
                        "evidence_type": "NONE",
                        "source_reference": "INSUFFICIENT_EVIDENCE",
                        "source_quote": "",
                        "reason": "Unsupported claim: source could not be verified.",
                    }
                )
            )
    return validated, valid_count
