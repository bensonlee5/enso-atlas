# Verified real forecast downloads, 2026-09-30

All downloads worked with Python urllib.request over HTTPS, no credentials or payment. No synthetic forecast data used. All artifacts live outside the Site checkout.

## App-ready artifacts
- `cfs-weekly-raw-60days.json` (53 KB): Weeks 1–8 (56 days) from 60 days of raw CFS data. 434 sampled native-grid CONUS coordinates, 10 nearest-grid city samples. Initialization 2026-09-29 00Z, ensemble member 01 only. Explicit intervals and method in JSON. Temperature °C; precipitation rate mm/day equivalent. This is neither anomaly nor probability and must not be presented as calibrated city rainfall. Four instantaneous forecast samples per day are averaged, not a separately published weekly aggregate.
- `cfs-weekly-anomalies.json` (18 KB): Official CPC CFSv2 16-member ensemble mean anomalies. Four weekly periods 2026-09-29 through 2026-10-26; initialization 2026-09-28. Model climatology 1999–2010. 264 native 2.5-degree CONUS grid points. Temperature anomaly K equals °C anomaly (do NOT subtract 273.15); precipitation anomaly mm/day. Missing source values are null. This is real anomaly data, not probability.
- `enso-observations.json` (18 KB): 104 weekly actual SST observations and anomalies, Niño1+2/3/3.4/4, through 2026-09-23. Source 1991–2020 baseline. Niño3.4 is 29.7°C, anomaly +3.1°C. Not ONI/RONI or an ENSO forecast.
- `aifs-sample.json` (31 KB): actual ECMWF AIFS single deterministic snapshots at hours24,168,336,360. Initialization2026-09-29 12Z. Temp °C instantaneous; total precipitation mm accumulated since initialization. 434 2-degree sampled coordinates. These are snapshots, not complete daily means. Attribution ECMWF / CC BY4.0 required.
- `cfs-tmp2m-60days.json` and `cfs-prate-60days.json`: underlying 240 six-hourly frames each, horizon60d, native-coordinate samples.

## Retrieval recipes
Install official PyPI packages into local directory (no OS changes):
`pip install --target ./python-packages eccodes h5py`
Run `python download_process.py`, then `python summarize_cfs.py`. Dates in download_process.py are fixed to the verified run above. Resolve latest available dated directory for new runs; do not blindly assume current run is complete.

CFS per-variable index gives byte offsets. Download only bytes0 through the byte before record241. This yields240 fields/60days, approximately19MB temperature +9MB precipitation rather than140MB full ten-month files. Sources:
https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/cfs.20260929/00/time_grib_01/tmp2m.01.2026092900.daily.grb2
https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/cfs.20260929/00/time_grib_01/prate.01.2026092900.daily.grb2
Append `.idx` to each. Despite filename daily, records are six-hourly. HTTP Range returns206 and is checked. Decode with ecCodes; retain each GRIB's units, stepType, validityDate/Time. Source PRATE is instantaneous per metadata, so accumulation is not assumed.

Official weekly anomalies are very small NetCDF4 files (~183KB each):
https://www.cpc.ncep.noaa.gov/products/CFSv2/weekly/data/CFSv2.prec.20260928.wkly.anom.nc
https://www.cpc.ncep.noaa.gov/products/CFSv2/weekly/data/CFSv2.tmpsfc.20260928.wkly.anom.nc
Download into `prec-weekly.nc` / `tmpsfc-weekly.nc`, run `python process_weekly.py`. Actual file metadata contains the baseline, 16members, and exact weekly dates. Official landing page https://www.cpc.ncep.noaa.gov/products/CFSv2/weekly/ links these; its NorthAmerica precipitation Data link is malformed, but global Data link works and supplies CONUS cells.

AIFS: fetch each `.index` JSON-lines file from https://data.ecmwf.int/forecasts/20260929/12z/aifs-single/0p25/oper/ ; find param2t and tp, then Range download `_offset` through `_offset+_length-1` from matching `.grib2`. Example filename `20260929120000-360h-oper-fc.index`. Only~1.5MB for both fields per valid time, no need full~85MB GRIB. License https://www.ecmwf.int/en/forecasts/datasets/open-data .

ENSO: https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for (text) parsed with date and eight floats; adjacent negative anomalies require regex or fixed-width parsing, not whitespace-only split.

## Probability limits
No verified numeric probability grids were derived. Official weekly probability images are linked on CPC page, e.g. https://www.cpc.ncep.noaa.gov/products/CFSv2/weekly/images/fig.wk12.NaPrecProb.20260928.png . Do not invent probability or label raw anomalies as likelihood. An additional CPC International subseasonal binary was downloaded but not decoded because metadata was not established; do not use `week34.dat` as values.
