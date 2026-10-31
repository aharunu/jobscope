"""Observed HRPeak public HTML boards; coverage is always PARTIAL."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    ProviderRuntimeConfig,
    bound_url,
    defer_detail,
    malformed,
    project,
    retain_partial,
    runtime_config,
)


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def text(self):
        return " ".join(
            c.text() if isinstance(c, Element) else c for c in self.children
        ).strip()

    def find(self, *, tag=None, css=None, id_=None):
        matches = []
        if (
            (tag is None or self.tag == tag)
            and (css is None or css in (self.attrs.get("class") or "").split())
            and (id_ is None or self.attrs.get("id") == id_)
        ):
            matches.append(self)
        for child in self.children:
            if isinstance(child, Element):
                matches.extend(child.find(tag=tag, css=css, id_=id_))
        return matches

    def html(self):
        attrs = "".join(
            f' {k}="{escape(v or "", quote=True)}"' for k, v in self.attrs.items()
        )
        body = "".join(
            c.html() if isinstance(c, Element) else escape(c) for c in self.children
        )
        return f"<{self.tag}{attrs}>{body}</{self.tag}>"


class BoardHTML(HTMLParser):
    """Minimal tree for the observed list and posting selectors."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def publication_date(row):
    for cell in row.find(tag="td"):
        try:
            return datetime.strptime(cell.text(), "%d.%m.%Y").date().isoformat()
        except ValueError:
            continue
    return None


class HRPeakAdapter:
    ats_type = "hrpeak"

    def __init__(self, http_client):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, ProviderRuntimeConfig, self.ats_type)
        requests = AcquisitionRequests(self.client, config.delay_seconds)
        coverage = Coverage(source)
        retain_partial(coverage, requests)
        base = f"https://{config.host}"
        response = await requests.response(f"{base}/jobs")
        tables = BoardHTML(response.text).root.find(tag="table", id_="C_G")
        if len(tables) != 1:
            raise malformed("HRPeak public jobs table is missing.")
        for row in tables[0].find(tag="tr"):
            links = row.find(tag="a", css="PL")
            if not links:
                continue
            link = links[0]
            url = bound_url(link.attrs.get("href"), base)
            path = urlsplit(url).path if url else ""
            if not re.fullmatch(r"/[a-z0-9]+\.job", path) or urlsplit(url).query:
                coverage.add(None)
                continue
            identity = path[1:-4]
            if identity in coverage.seen:
                coverage.warn("duplicate_or_overlapping_page_detected")
                continue
            locations = row.find(css="location")
            listing = {
                "id": identity,
                "title": link.text(),
                "url": url,
                "location": locations[0].text() if locations else None,
                "published_at": publication_date(row),
            }
            summary = project(
                source,
                listing,
                identity=identity,
                url=url,
                title=listing["title"],
                location=listing["location"],
                published_at=listing["published_at"],
            )
            if summary is None:
                coverage.add(None)
                continue
            if defer_detail(summary, coverage):
                continue
            detail = await requests.response(url)
            descriptions = BoardHTML(detail.text).root.find(css="ilanMetni")
            if len(descriptions) != 1 or not descriptions[0].text():
                raise malformed("HRPeak public posting description is missing.")
            description = descriptions[0].html()
            coverage.add(
                project(
                    source,
                    {"version": 1, "list": listing, "description": description},
                    identity=identity,
                    url=url,
                    title=listing["title"],
                    description=description,
                    location=listing["location"],
                    published_at=listing["published_at"],
                    provider=listing,
                )
            )
        coverage.warn("hrpeak_public_html_coverage_unverified")
        return coverage.result(False, requests)
