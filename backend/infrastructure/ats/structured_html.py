"""Small standard-library HTML/JSON-LD reader shared by public board pages."""

import json
from html.parser import HTMLParser

from backend.infrastructure.ats.acquisition import location, mapping


class JsonLdReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.current: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if (
            tag.lower() == "script"
            and (dict(attrs).get("type") or "").strip().lower() == "application/ld+json"
        ):
            self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.current is not None:
            self.blocks.append("".join(self.current))
            self.current = None


def job_postings(html: str) -> tuple[list[dict], bool]:
    reader = JsonLdReader()
    reader.feed(html)
    malformed = reader.current is not None
    postings = []
    for block in reader.blocks:
        try:
            root = json.loads(block)
        except (ValueError, RecursionError):
            malformed = True
            continue
        stack = [root]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(reversed(node))
            elif isinstance(node, dict):
                types = node.get("@type")
                if (
                    types == "JobPosting"
                    or isinstance(types, list)
                    and "JobPosting" in types
                ):
                    postings.append(node)
                else:
                    stack.extend(reversed(list(node.values())))
    return postings, malformed


def structured_location(posting: dict) -> str | None:
    value = posting.get("jobLocation")
    if isinstance(value, list):
        return "; ".join(filter(None, (location(v) for v in value))) or None
    return location(value)


def structured_identifier(posting: dict):
    value = posting.get("identifier")
    return mapping(value).get("value") if isinstance(value, dict) else value
