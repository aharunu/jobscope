"""Job content cleaning and normalization utilities.

Handles converting raw ATS payloads (such as Lever JSON dumps or raw HTML)
into clean, human-readable description and responsibilities strings.
"""

from __future__ import annotations

import html
import json
import logging
import re

logger = logging.getLogger(__name__)


def clean_html_to_bullets(content: str) -> str:
    """Convert HTML list content (e.g. <li> items) into clean bullet lines."""
    if not content:
        return ""

    # Convert <li>...</li> to bullet points
    text = re.sub(
        r"<\s*li[^>]*>(.*?)(?:<\s*/\s*li\s*>|$)",
        r"- \1\n",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Strip any remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Replace non-breaking spaces and clean whitespace
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line and line != "-"]
    return "\n".join(lines)


def normalize_job_description_and_responsibilities(
    raw_desc: str | None,
    raw_resp: str | None = None,
) -> tuple[str, str | None]:
    """Normalize job description and responsibilities.

    If raw_desc is a serialized JSON object (e.g. from Lever ATS crawler),
    extracts the clean plain-text description, responsibilities, and structured
    lists instead of exposing raw JSON keys to users.
    """
    if not raw_desc or not raw_desc.strip():
        return "", raw_resp.strip() if raw_resp and raw_resp.strip() else None

    desc = raw_desc.strip()
    resp = raw_resp.strip() if raw_resp and raw_resp.strip() else None

    if desc.startswith("{") and desc.endswith("}"):
        try:
            data = json.loads(desc)
            if isinstance(data, dict):
                body_plain = data.get("descriptionPlain") or data.get(
                    "descriptionBodyPlain"
                )
                body_html = data.get("description") or data.get("descriptionBody")
                opening = data.get("openingPlain") or data.get("opening") or ""
                additional = data.get("additionalPlain") or data.get("additional") or ""

                parts: list[str] = []
                if opening and str(opening).strip():
                    parts.append(str(opening).strip())
                if body_plain and str(body_plain).strip():
                    parts.append(str(body_plain).strip())
                elif body_html and str(body_html).strip():
                    parts.append(str(body_html).strip())
                if additional and str(additional).strip():
                    parts.append(str(additional).strip())

                lists = data.get("lists")
                if isinstance(lists, list):
                    for lst in lists:
                        if not isinstance(lst, dict):
                            continue
                        section_title = str(lst.get("text") or "").strip()
                        section_content = str(lst.get("content") or "").strip()
                        if not section_content:
                            continue

                        # If responsibilities is not set and this list matches
                        if not resp and "responsibilit" in section_title.lower():
                            resp = clean_html_to_bullets(section_content)
                        else:
                            clean_items = clean_html_to_bullets(section_content)
                            if section_title:
                                parts.append(f"{section_title}:\n{clean_items}")
                            else:
                                parts.append(clean_items)

                if parts:
                    desc = "\n\n".join(parts).strip()
                elif body_plain or body_html:
                    desc = str(body_plain or body_html).strip()
        except Exception:
            # If not valid JSON, log diagnostic and preserve existing description
            logger.warning(
                "Could not parse structured job description; preserving fallback"
            )

    return desc, resp
