# Worldwide CFSv2 member percentiles

The current product contains real empirical P1/P5/P10/P50/P90/P95/P99 temperature and precipitation-rate maps across all longitudes and both hemispheres. It is **16-member lagged model spread, not calibrated event probability**.

## Grid and period

The pipeline keeps every fourth native Gaussian latitude row and longitude column from CFSv2's 384 × 190 grid, including the outermost native latitude rows: 4,704 samples, approximately 3.8° apart. Values cover land and ocean. The unsampled caps beyond ±89.2767° remain empty; maps do not extrapolate them. Bilinear shading and subdivided contours are display interpolation and add no physical resolution. City readings use a nearest model point, including wrapped longitude at the date line.

There are eight complete seven-day periods (56 days) and a separate four-day Days 57–60 period. Samples are instantaneous six-hourly right endpoints: week1 contains hours6 through168; the last sample lies at the nominal end boundary. `firstSampleHour`, `lastSampleHour` and `sampleCountPerMember` state actual coverage. The nine periods are not nine full weeks.

Four members (01–04) from each of four consecutive 00Z initializations contribute equally. An older member contains additional initial frames; these are cropped so all members refer to the same 240 six-hourly valid instants relative to the newest reference run. Averaging identical lead offsets across different initializations would be incorrect. Run identity, step type, units and every validity date/hour are verified before output.

## Statistics and uncertainty

Each member is averaged separately across the period, then NumPy linear quantiles (Hyndman–Fan type7) are calculated across the16 member averages. P50 is the median, not a nominated member. Source temperature is instantaneous2m air temperature in kelvin, converted to°C before aggregation. Precipitation is instantaneous PRATE in kg m⁻² s⁻¹, multiplied by86,400 for mm/day-equivalent mean sampled rate. This is not validated accumulated rainfall.

Nearby initializations share a model and correlated errors. P1/P99 lie near the sample extremes;16 members cannot resolve1% event odds. More members do not remove model bias, supply hindcast calibration, or validate local/long-range accuracy. The neural research pilot is not applied to these maps.

## Bounded browser transport and audit artifact

Schema3 `dist/data/ensemble-percentiles.json` contains map-ready quantiles, grid coordinates, 32 source URLs/GRIB hashes, member identities and aligned period provenance. Its current uncompressed budget is under4.5MB (~1.4MB gzip), instead of loading16.2MB of quantiles plus means into the browser.

The companion `dist/data/ensemble-member-means.json.gz` retains all member temporal means to six decimal places, keyed to the same members, coordinates and periods. Its filename, byte count and SHA256 are recorded in `memberMeansArtifact`; the browser never fetches or retains it. This precision is0.000001°C or mm/day-equivalent. Output quantiles are calculated from those retained means and rounded to0.001 units, so they are reproducible. All source GRIB subset hashes remain available.

`transport.validate_member_artifact` verifies the artifact hash/identity and independently recomputes every quantile before bundle publication. Browser validation verifies the public manifest hashes, bounded sizes, ordered finite seven-quantile fields, worldwide grid and exact provenance structure. It rejects the previous regional schema rather than silently reverting worldwide coverage.

## Reproduce and refresh

Install `ingestion/requirements.txt` from official PyPI, then run from the repository root:

```sh
python ingestion/ensemble/retrieve_ensemble.py --run latest --lag-days 4 --days 60 --output dist/data/ensemble-percentiles.json
python ingestion/refresh_bundle.py --manifest-only
```

An explicit run, such as `--run 2026100100`, is reproducible while the source remains in NOAA's rotating archive, or from preserved exact cached GRIB subsets passed with `--cache-dir`. Decoding uses at most two CPU processes. The full32-file subset is approximately450MB; existing exact files are reused. No paid service, new account or credentials are needed.

The daily GitHub workflow remains09:17 UTC (GitHub can start late), also runs on ingestion changes and can be dispatched manually. It validates source data, member-artifact quantiles, observations and browser acceptance before committing every generated file together. A failed retrieval, validation or conflicting rebase publishes nothing. Existing immutable issuance archives remain unchanged. The Site checks the hash-verified feed on open and hourly while visible; it does not require daily Site redeployment.

Official sources: [NOAA rotating archive](https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/), [NCEP CFSv2 paper, Appendix C](https://cfs.ncep.noaa.gov/cfsv2.info/CFSv2_paper.pdf), [CFSv2 downloads](https://cfs.ncep.noaa.gov/cfsv2/downloads.html)

## Checks

```sh
python tests/test_global_transport.py
PYTHONPATH=ingestion/ensemble python -m unittest discover -s tests -p test_ensemble_quantiles.py -v
node tests/public-data-test.cjs
node tests/global-grid-test.cjs
```

The raw single-member and published CPC anomaly products remain separately labeled regional products. The Global Daily maps include a distinct single-member CFS daily sampled mean, AIFS snapshots, historical reconstruction and explicit climatology; these statistics are never presented as equivalent ensemble forecasts.
