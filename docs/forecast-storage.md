# Forecast updates outside Git history

## Schedule and scientific scope

The GitHub workflow runs on the public `bensonlee5/enso-atlas` repository's default `main` branch:

- 15:17 UTC daily: discover a complete CFSv2 00Z reference suite, then align members 01–04 across four initialization days (16 members). Download/decode only when that complete reference suite changes. Refresh the archived-forecast verification report daily.
- 03:17, 09:17, 15:17 and 21:17 UTC: check the latest complete single-member CFS run and AIFS run. The worldwide single-member CFS map is extracted from the same downloaded GRIB bytes as the regional raw product, without another download; it is labeled independently from the daily ensemble. Unchanged issuances are reused without downloading their GRIB fields again. These are four checks, not a claim that four new products always exist.
- CPC anomalies and observed ENSO indices are checked in those runs but retain their actual upstream dates; no fabricated update timestamps or extra CFS ensemble cycles.
- A manual daily/fast run is available. A push changing the workflow or ingestion code performs a controlled daily validation run.

The 15:17 UTC CFS slot provides a conservative buffer: live NOMADS `Last-Modified` headers for 00Z member-01 temperature indexes were 11:43:54 UTC on October 1, 2026 and 11:47:31 UTC on October 2; member 02–04 indexes were around 09:08–09:14 UTC. This is observed availability, not a publication guarantee. Daily production requires the current UTC date's complete aligned suite. If unavailable, it retries discovery twice at 60-second intervals, then fails visibly while preserving the last-good feed instead of quietly treating yesterday's cycle as a successful new daily forecast. Unchanged complete reference cycles reuse their prior output and audit rather than decode again.

Times are deliberately away from the busiest top of each hour. GitHub may delay or drop scheduled jobs; this is not an exact-time service. Public scheduled workflows can be disabled after 60 days with no repository activity. Forecast refreshes no longer create repository commits, so they do not act as a keepalive. Inspect Actions and the feed's visible source/run dates; re-enable an inactive schedule through GitHub. No artificial data or heartbeat commits are made.

## Pipeline and access

1. A read-only prepare job restores the last published manifest and its digest-verified objects into temporary runner storage. Storage errors or corrupted established feeds fail closed; only an explicitly selected daily bootstrap can start from a missing manifest.
2. Python/ecCodes processes public NOAA/ECMWF data in a temporary staging directory. The Actions decoder environment is locked to exact Python 3.12/Linux wheel versions and hashes, including native/transitive libraries; installs require hashes and binary wheels. Its source units, model runs, member identities, valid-time alignment, finite fields and reproducible member quantiles are validated. All local outputs are copied only after the complete staged bundle passes browser acceptance.
3. A same-run immutable Actions artifact transfers the validated bundle to a separate minimal publisher job. It contains public weather data and an ETag, no credentials, expires after one day, and is not a repository commit or release asset. The publisher downloads the exact artifact ID emitted by this run, executes only checked-in code from the same commit, and installs no decoding dependencies.
4. The publisher requests a short-lived GitHub OIDC identity with the Site origin as audience. The Site verifies GitHub's signature, expiration, immutable repository/owner IDs, exact workflow path, `main` ref, and allowed event types. Fork/PR/other-workflow identities are rejected. No saved upload secret, arbitrary object key or general cloud-account privilege is granted.
5. Changed files are uploaded to immutable content-addressed R2 objects. Every name, byte size, SHA-256 and required source initialization is checked. The final complete manifest is promoted atomically using the predecessor ETag, so racing/older runs cannot overwrite a newer feed. An indeterminate retry is accepted only if an exact release readback confirms it succeeded.
6. Readers use the manifest's pinned object hashes. The old complete release remains available after a failed source fetch, verification, upload or promotion. Faster AIFS updates can legitimately have no exact-time CFS comparison; that comparison is withheld rather than interpolated into invented agreement.

The upload trust and R2 binding require the owner's explicit approval before activation. A successful local test is not evidence of a live scheduled upload: verify one actual GitHub run and the Site's manifest/object readback.

## Storage and costs

Browser JSON is bounded at 5 MB per file; the compressed member-mean audit at 8 MB; each archive/index JSON and the promotion manifest at 200 KB. The active transport bundle is capped at 64 MB with at most 410 objects, including at most 400 indexed forecast issuances. No more than 18 changed objects are promoted per transaction. These are validation limits, not a provider billing guarantee.

The measured initial bundle is about 11.34 MB (12 objects including three existing archived issuances). The unchanged ~3.92 MB ensemble JSON and ~4.22 MB compressed audit are deduplicated across the faster checks. The worldwide single-member CFS JSON adds roughly 2.8 MB per changed CFS cycle. At current sizes, daily ensemble/audit changes plus four changed single-member global-CFS/raw/AIFS cycles per day could add roughly 0.6 GB/month before any eventual retention policy. File sizes and compression vary. Existing archived issuances are about 29 KB each; later richer archives may be larger.

The initial policy does not automatically delete immutable R2 objects, old release manifests, historical Git data, or prior forecast archives. Only the latest 400 issuances are indexed for bounded verification. The active-bundle limit is not a cumulative-storage cap. Review provider usage and agree on retention before imposing destructive cleanup. An operational quota must fail visibly and preserve the last good release. Standard GitHub-hosted runner execution is free for this public repository under GitHub's documented policy; storage and any managed Sites charges are separate and must not be assumed free.

## Local commands

- `python -m unittest discover -s tests -p test_forecast_storage.py -v`
- `python ingestion/publish_forecasts.py restore --data /tmp/enso-data --state /tmp/enso-state.json`
- `python ingestion/refresh_bundle.py --mode fast --output /tmp/enso-data`
- `python ingestion/publish_forecasts.py validate --data /tmp/enso-data`

Publishing additionally requires the approved GitHub workflow's runtime OIDC identity; local credentials must not be pasted into files or committed. No generated forecast files should be staged in Git. Keep original archived forecast bytes immutable during bootstrap/migration. An empty feed’s explicit daily bootstrap restores the three original September 29, September 30, and October 1, 2026 issuance files from verified historical Git commit `f8e4c04a0db70228fe954e439bda0d41e67021bd`, with fixed SHA-256 checks and a 200 KB per-file limit. This one-time read-only migration continues to work after forecast data is removed from the current Git tip; it never commits new forecasts.

## References

- [GitHub scheduled workflows and inactivity](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub OIDC claims](https://docs.github.com/en/actions/reference/security/oidc)
- [Cloudflare R2 Workers API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)
