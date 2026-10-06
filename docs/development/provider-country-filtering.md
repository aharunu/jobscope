# Provider country filtering

An active, frozen A4 country policy excluding unknown countries opts into provider
filtering. It applies to PREVIEW and PERSIST, including persist-from-preview's frozen
policy. Disabled policies, empty country selections, unknown-country inclusion and
ordinary direct crawls retain their existing full-board behavior.

## Implemented paths

- **SmartRecruiters:** send `country=tr` (or the selected ISO code) on every paginated
  list request. Multiple countries use independent offset/total sequences and a union
  by provider posting ID. Cross-query duplicates are expected; repeated IDs within
  one query still produce a coverage warning. Source budgets and host pacing apply
  across all queries. No undocumented comma-separated filter is assumed.
- **Workday:** one unfiltered page obtains public CXS facets. Resolve exact country
  names/codes using existing country aliases; support top-level and nested
  `locationMainGroup` country facets. Use the returned facet parameter and IDs in
  `appliedFacets`, restarting pagination at zero. Do not use fixed country IDs or
  `searchText=Turkey`. Missing, ambiguous, malformed or unrecognized mappings fall
  back to the unfiltered sequence, reusing the first page. A missing selected country
  is zero only if every facet label is recognized and its counts reconcile with the
  response total; otherwise fallback. A board can expose localized labels beyond
  the existing alias vocabulary; those remain conservative fallbacks.

Filtered acquisition carries `provider_country_scoped_acquisition`, returns
`is_complete=false`, and records country scope in execution metadata. Known Workday
coverage limitations remain. Local `PolicySnapshot.decide` still validates every
returned posting; provider filtering never replaces the canonical country decision.
Multi-location listings whose usable country evidence remains unknown can still be
rejected under an exclude-unknown policy. Filter membership does not manufacture a
canonical country value.

Full provider descriptions are still required for accepted persisted postings.
Preview summaries cannot be directly persisted. Scoping does not delete historical
jobs and **never authorizes absence closure**. Request delays, SSRF protections,
budgets, cancellation and concurrency limits are unchanged. No migration, new
provider, authentication integration or scheduler was added.

## Endpoint research (2026-10-06)

| Provider | Current acquisition endpoint | Decision / evidence |
|---|---|---|
| SmartRecruiters | Public company postings | Enabled: documented `country`, live TR reduction confirmed. |
| Workday | Hosted CXS `/jobs` | Enabled when board country facets can be resolved; live top-level 3M and nested Accenture confirmed. Unproven boards fall back. |
| Lever | Public v0 postings | Local filtering: provider explicitly says `country` is not filterable. Free-text location filtering is not equivalent to complete country selection. |
| Greenhouse | Public board jobs with content | Local filtering: documented list query supports content, not country. |
| Ashby | Public posting-api job board | Local filtering: full-list contract documents compensation option, no country selection. Private job APIs are different contracts. |
| Recruitee | Careers `/api/offers/` | Local filtering: documented filters are department/tag, not country. |
| Personio | Public `/xml` | Local filtering: full positions feed; no verified country query contract. |
| Teamtailor | Hosted `/jobs.json` feed | Local filtering: no verified country filter for this feed. Official keyed API has location filters but is not the current acquisition endpoint. |
| Workable | Public v1 widget account | Local filtering: widget full-list endpoint has no verified server country query. Official widget help distinguishes it from career-site search/filter controls. |
| BambooHR | Hosted careers/list plus public details | Local filtering: no verified country selection for this endpoint. HR/ATS private API location fields do not establish a public list filter. |
| Hirex | Public board HTML/JSON-LD | Local filtering: no verified server-side country contract for acquired board. |
| Oracle | Hosted recruitingCEJobRequisitions finder | Not enabled: documented `workLocationCountryCode=TR` returned the same 568-result total and 100-row first page on DP World. A documented parameter alone is insufficient proof of narrowed hosted-board behavior. |

“No verified filter” is an assessment of the current endpoint, not a claim that no
other provider API or tenant-specific career site can filter geography.

Primary references:

- [SmartRecruiters Posting API](https://developers.smartrecruiters.com/docs/endpoints)
- [Lever public API](https://github.com/lever/postings-api)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Ashby public postings](https://developers.ashbyhq.com/docs/public-job-posting-api)
- [Recruitee offers](https://docs.recruitee.com/reference/offers)
- [Personio positions XML](https://developer.personio.de/v1.0/reference/get_xml)
- [Teamtailor API](https://docs.teamtailor.com/)
- [Workable widget behavior](https://help.workable.com/hc/en-us/articles/115012801727-How-to-embed-jobs-on-your-website-job-widget)
- [BambooHR location API (different endpoint)](https://documentation.bamboohr.com/reference/get-locations)
- [Hirex product](https://gethirex.com/)
- [Oracle finder variables](https://docs.oracle.com/en/cloud/saas/human-resources/farws/op-recruitingcejobrequisitions-get.html)

Workday hosted CXS behavior was verified directly through the existing SafeHttpClient;
it has no universal public contract being claimed here. Optional live probes are
manual/read-only, paced, and never CI dependencies. Tests use fake clients and assert
request bodies, pagination, union behavior, malformed facets, fallbacks and closure
suppression.
