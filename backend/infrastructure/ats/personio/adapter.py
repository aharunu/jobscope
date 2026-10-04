"""Personio XML board; reject DTD/entities before standard-library parsing."""

import re
from xml.etree import ElementTree

from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    ProviderRuntimeConfig,
    employment,
    malformed,
    project,
    runtime_config,
)
from backend.infrastructure.ats.posting import posting_identity


class PersonioRuntimeConfig(ProviderRuntimeConfig):
    pass


class PersonioAdapter:
    ats_type = "personio"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, PersonioRuntimeConfig, self.ats_type)
        requests, coverage = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
        )
        response = await requests.response(f"https://{config.host}/xml")
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", response.text, re.I):
            raise malformed("XML DTD/entity declarations are unsupported.")
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            raise malformed("Malformed Personio XML.") from exc
        if root.tag != "workzag-jobs":
            raise malformed("Unexpected Personio XML root.")
        for item in root:
            if item.tag != "position":
                coverage.warn("unexpected_xml_position_element")
                continue
            identity = posting_identity(item.findtext("id"))
            sections = []
            for section in item.findall("./jobDescriptions/jobDescription"):
                value = section.find("value")
                body = "".join(value.itertext()).strip() if value is not None else ""
                if body:
                    sections.append(f"{section.findtext('name') or ''}\n{body}".strip())
            description = "\n".join(sections)
            raw = ElementTree.tostring(item, encoding="unicode")
            job = project(
                source,
                {"position_xml": raw},
                identity=identity,
                url=f"https://{config.host}/job/{identity}" if identity else None,
                title=item.findtext("name"),
                description=description,
                location=item.findtext("office"),
                employment_type=employment(item.findtext("schedule"))
                or employment(item.findtext("employmentType")),
                provider={child.tag: "".join(child.itertext()) for child in item},
            )
            if job:
                job.raw_content, job.content_type = raw, "application/xml"
            coverage.add(job)
        return coverage.result(True, requests, contract="personio_enabled_xml_feed")
