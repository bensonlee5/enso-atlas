#!/usr/bin/env python3
"""Bounded, source-hashed CPC temperature proxy diagnostics for archived CFSv2 runs.

Standard library only. Production never generates observations or scores a partial week.
CPC daily (Tmax+Tmin)/2 is a proxy, not the exact CFS sampled-mean target.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
import time
import urllib.parse
import urllib.request

VERSION = 1
UTC = timezone.utc
SOURCE_ROOT = 'https://psl.noaa.gov/thredds/dodsC/Datasets/cpc_global_temp'
SOURCE_DOCUMENTATION = 'https://psl.noaa.gov/data/gridded/data.cpc.globaltemp.html'
MAX_ISSUANCES = 400
MAX_LOCATIONS = 10
MIN_LATENCY_DAYS = 3  # Deliberate safety buffer, NOT a NOAA publication guarantee.
METRIC_LABEL = 'Temperature deviations against a CPC daily-extrema midpoint proxy'
WARNINGS = [
    'Proxy diagnostic, not exact forecast skill or evidence for model ranking: CFS uses 28 instantaneous six-hourly samples; CPC uses weekly averages of daily (Tmax+Tmin)/2.',
    'CPC metadata specifies nominal 06Z-to-06Z extrema windows. These do not exactly match the CFS nominal midnight-to-midnight interval or its sample timestamps.',
    'Observations are the nearest 0.5-degree CPC analysis grid cell to the native CFS model point, not a city station, city-center observation or downscaled truth. Missing land/ocean cells are withheld.',
    'The three-day minimum latency is an application safety buffer, not a guarantee of NOAA availability or final quality control. All seven paired finite daily observations are required; observations may later be revised.',
    'Bias is forecast minus observed proxy, so positive bias means warmer forecasts. Each verified forecast-location-week receives equal weight; overlapping runs and shared grid points are not independent.',
    'Only raw temperature p50 is evaluated. Anomalies, tail probabilities and ENSO contribution are not evaluated. Days 57–60 are a partial four-day period and are excluded from week1–8 diagnostics.',
    'Metrics describe deviations in the archived forecasts, not calibrated predictive uncertainty or a comparison against competing models.',
]


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamps must include a timezone')
    return result.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(f'Invalid JSON number: {v}')))


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def coordinate(value):
    if not isinstance(value, list) or len(value) != 2 or not all(finite(x) for x in value):
        raise ValueError('Coordinate must be two finite numbers')
    if not (-90 <= value[0] <= 90 and -180 <= value[1] <= 180):
        raise ValueError('Coordinate out of range')
    return tuple(value)


def load_archive(folder: Path):
    """Validate hashes and temporal shape before allowing any verification."""
    folder = folder.resolve()
    index = read_json(folder / 'index.json')
    entries = index.get('issuances')
    if index.get('schemaVersion') != VERSION or not isinstance(entries, list):
        raise ValueError('Unsupported archive index schema')
    if len(entries) > MAX_ISSUANCES:
        raise ValueError(f'Active archive index exceeds {MAX_ISSUANCES} issuance bound')
    issuances, seen_runs = [], set()
    for entry in entries:
        path = (folder / entry['path']).resolve()
        if not path.is_relative_to(folder) or path.suffix != '.json':
            raise ValueError('Archive path must be a JSON file inside archive-dir')
        raw = path.read_bytes()
        if digest(raw) != entry['sha256']:
            raise ValueError(f'Immutable archive hash mismatch: {entry["path"]}')
        issuance = read_json(path)
        if issuance.get('schemaVersion') != VERSION:
            raise ValueError('Unsupported issuance schema')
        run = utc(issuance['run'])
        archived = utc(issuance['archivedAt'])
        if issuance['run'] != entry['run'] or issuance['archivedAt'] != entry['archivedAt']:
            raise ValueError('Archive index metadata differs from issuance')
        if run in seen_runs or archived < run:
            raise ValueError('Duplicate model run or archive timestamp before model initialization')
        seen_runs.add(run)
        if run.hour or run.minute or run.second or run.microsecond:
            raise ValueError('This verifier supports midnight UTC initialization only')
        if not re.fullmatch(r'[a-fA-F0-9]{64}', issuance['sourceProductSha256']):
            raise ValueError('Missing source product SHA256')
        if issuance.get('units') != {'temperature': '°C', 'precipitationRate': 'mm/day'}:
            raise ValueError('Unexpected archived units')
        if issuance.get('model') != 'NOAA CFSv2' or issuance.get('memberCount') != 4:
            raise ValueError('Expected NOAA CFSv2 four-member p50 product')
        locations = issuance['locations']
        if not 1 <= len(locations) <= MAX_LOCATIONS:
            raise ValueError('Expected one to ten sampled locations')
        names = set()
        for location in locations:
            if not location.get('name') or location['name'] in names:
                raise ValueError('Empty or duplicate location name')
            names.add(location['name'])
            coordinate(location['requestedCoordinate'])
            coordinate(location['nativeGridCoordinate'])
            periods = location['periods']
            if sorted(p['leadWeek'] for p in periods) not in (list(range(1, 9)), list(range(1, 10))):
                raise ValueError('Eight full weeks and optional four-day period9 required')
            for period in periods:
                week = period['leadWeek']
                expected_start = run + timedelta(days=7 * (week - 1))
                days = 4 if week == 9 else 7
                if utc(period['intervalStart']) != expected_start or utc(period['intervalEndExclusive']) != expected_start + timedelta(days=days):
                    raise ValueError('Valid window differs from corresponding seven-day lead or four-day final period')
                if period['sampleCountPerMember'] != days * 4 or period['firstSampleHour'] != (week - 1) * 168 + 6 or period['lastSampleHour'] != (week - 1) * 168 + days * 24:
                    raise ValueError('Unexpected six-hour forecast sample coverage')
                for field in ['temperature', 'precipitationRate']:
                    qs = [period[field][q] for q in ['p10', 'p50', 'p90']]
                    if not all(finite(q) for q in qs) or qs != sorted(qs):
                        raise ValueError('Quantiles must be finite and ordered')
        issuance['_archivePath'] = entry['path']
        issuance['_archiveSha256'] = entry['sha256']
        issuances.append(issuance)
    return sorted(issuances, key=lambda item: utc(item['run']))


def parse_ascii(text: str, variable: str):
    """Parse only a constrained one-grid-cell DAP2 ASCII Grid response."""
    marker = re.search(r'^-+\s*$', text, re.M)
    if marker is None:
        raise ValueError('Missing DAP2 ASCII body separator')
    body = text[marker.end():]
    blocks = {}
    matches = list(re.finditer(r'^([A-Za-z][\w.]*)((?:\[\d+\])+)[ \t]*$', body, re.M))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        blocks[match.group(1)] = (match.group(2), body[match.end():end].strip())
    def values(key):
        if key not in blocks:
            raise ValueError(f'Missing DAP2 variable: {key}')
        _, block = blocks[key]
        return [float(value.strip()) for value in block.replace('\n', ',').split(',') if value.strip()]
    key = f'{variable}.{variable}'
    if key not in blocks:
        raise ValueError(f'Missing DAP2 grid: {key}')
    dimensions, rows = blocks[key]
    lengths = [int(x) for x in re.findall(r'\d+', dimensions)]
    if len(lengths) != 3 or lengths[1:] != [1, 1]:
        raise ValueError('Observation response must contain a single spatial grid cell')
    parsed = []
    for line in rows.splitlines():
        match = re.fullmatch(r'\[(\d+)\]\[0\],\s*([^,\s]+)\s*', line)
        if not match or int(match.group(1)) != len(parsed):
            raise ValueError('Unexpected or out-of-order DAP2 row')
        parsed.append(float(match.group(2)))
    times = values(f'{variable}.time')
    if len(parsed) != lengths[0] or len(parsed) != len(times):
        raise ValueError('Incomplete DAP2 time coverage')
    lats, lons = values(f'{variable}.lat'), values(f'{variable}.lon')
    if len(lats) != 1 or len(lons) != 1:
        raise ValueError('Observation coordinates not scalar')
    return times, parsed, (lats[0], lons[0])


class CPCProvider:
    kind = 'real_noaa_cpc_analysis'
    def __init__(self, evidence_dir: Path | None = None):
        self.evidence_dir = evidence_dir
        self.provenance = []
        self.errors = []
        self._metadata = {}
        self._points = {}
        self.latest_available_dates = {}
        self.request_count = 0
        self.deadline = time.monotonic() + 240

    def request(self, url):
        # These are fixed official data URLs. No arbitrary user-provided network targets.
        if not url.startswith(SOURCE_ROOT + '/'):
            raise ValueError('Only the official CPC dataset endpoint is allowed')
        self.request_count += 1
        if self.request_count > 80:
            raise ValueError('Observation request budget exceeded')
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('240-second observation network budget exhausted')
        request = urllib.request.Request(url, headers={'User-Agent': 'ENSO-Atlas-Verification/1.0'})
        with urllib.request.urlopen(request, timeout=min(25, remaining)) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError('Observation response exceeds 2 MB bound')
            content_type = response.headers.get('Content-Type', '')
            if 'html' in content_type.lower():
                raise ValueError('Unexpected HTML response from data endpoint')
        record = {'url': url, 'retrievedAt': iso(datetime.now(UTC)), 'sha256': digest(raw), 'bytes': len(raw)}
        if self.evidence_dir:
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
            target = self.evidence_dir / f'{record["sha256"]}.txt'
            try:
                with target.open('xb') as stream:
                    stream.write(raw)
            except FileExistsError:
                if target.read_bytes() != raw:
                    raise ValueError('Immutable observation evidence collision')
            record['evidenceFile'] = target.name
        self.provenance.append(record)
        return raw.decode('utf-8')

    def metadata(self, variable, year):
        key = (variable, year)
        if key not in self._metadata:
            base = f'{SOURCE_ROOT}/{variable}.{year}.nc'
            das, dds = self.request(base + '.das'), self.request(base + '.dds')
            # Fail closed if NOAA changes the fixed product/units/window/grid convention.
            for expected in ['units "degC"', 'hours since 1900-01-01 00:00:00', '6z to 6z', 'CPC GLOBAL TEMP']:
                if expected not in das:
                    raise ValueError(f'Unexpected CPC metadata: missing {expected}')
            if not re.search(r'Float32 lat\[lat = 360\]', dds) or not re.search(r'Float32 lon\[lon = 720\]', dds):
                raise ValueError('Unexpected CPC grid dimensions')
            found = re.search(r'Float64 time\[time = (\d+)\]', dds)
            if found is None:
                raise ValueError('CPC time dimension unavailable')
            count = int(found.group(1))
            if count < 1 or count > (date(year + 1, 1, 1) - date(year, 1, 1)).days:
                raise ValueError('Unexpected CPC annual time count')
            self._metadata[key] = count
            self.latest_available_dates[f'{variable}.{year}'] = (date(year, 1, 1) + timedelta(days=count - 1)).isoformat()
        return self._metadata[key]

    @staticmethod
    def nearest_grid(point):
        lat, lon = point
        # Regular 0.5-degree cell centers: 89.75 southward, 0.25 eastward.
        iy = min(359, max(0, int(math.floor((89.75 - lat) / 0.5 + 0.5))))
        longitude = lon % 360
        ix = int(math.floor((longitude - 0.25) / 0.5 + 0.5)) % 720
        return iy, ix, 89.75 - 0.5 * iy, 0.25 + 0.5 * ix

    def prepare(self, requests):
        """Fetch only native points and date spans needed by mature archived forecasts."""
        grouped = defaultdict(set)
        for point, dates in requests:
            for day in dates:
                grouped[(tuple(point), day.year)].add(day)
        if len({k[0] for k in grouped}) > MAX_LOCATIONS or len({k[1] for k in grouped}) > 3:
            raise ValueError('Observation work exceeds ten unique grid points or three years')
        for (point, year), days in sorted(grouped.items()):
            for variable in ['tmax', 'tmin']:
                try:
                    count = self.metadata(variable, year)
                    first = min(days)
                    last = min(max(days), date(year, 1, 1) + timedelta(days=count - 1))
                    if last < first:
                        continue
                    start = (first - date(year, 1, 1)).days
                    stop = (last - date(year, 1, 1)).days
                    iy, ix, lat, lon = self.nearest_grid(point)
                    query = f'{variable}[{start}:1:{stop}][{iy}:1:{iy}][{ix}:1:{ix}]'
                    url = f'{SOURCE_ROOT}/{variable}.{year}.nc.ascii?' + urllib.parse.quote(query, safe=':,.')
                    times, data, actual_point = parse_ascii(self.request(url), variable)
                    if actual_point != (lat, lon):
                        raise ValueError('Returned NOAA point differs from requested grid cell')
                    if len(times) != stop - start + 1:
                        raise ValueError('Returned NOAA date range has missing rows')
                    for offset, (hours, value) in enumerate(zip(times, data)):
                        expected = datetime.combine(first + timedelta(days=offset), datetime.min.time(), UTC)
                        actual = datetime(1900, 1, 1, tzinfo=UTC) + timedelta(hours=hours)
                        if actual != expected:
                            raise ValueError('Returned NOAA dates differ from requested daily sequence')
                    # Validate the entire response before caching any values.
                    for offset, value in enumerate(data):
                        day = first + timedelta(days=offset)
                        if math.isfinite(value) and -100 <= value <= 70:
                            self._points[(point, day, variable)] = value
                except (OSError, ValueError, OverflowError) as exc:
                    self.errors.append({'source': f'{variable}.{year}', 'nativeGridCoordinate': list(point), 'message': str(exc)})

    def daily(self, point, day):
        point = tuple(point)
        high = self._points.get((point, day, 'tmax'))
        low = self._points.get((point, day, 'tmin'))
        if high is None or low is None or high < low:
            return None
        return (high + low) / 2


def metrics(values):
    if not values:
        return {'n': 0, 'bias': None, 'mae': None, 'rmse': None}
    return {'n': len(values), 'bias': sum(values) / len(values), 'mae': sum(abs(v) for v in values) / len(values), 'rmse': math.sqrt(sum(v * v for v in values) / len(values))}


def build_report(issuances, as_of: datetime, provider, latency_days=MIN_LATENCY_DAYS):
    if latency_days < MIN_LATENCY_DAYS:
        raise ValueError('At least three full days of observation latency are required')
    as_of = as_of.astimezone(UTC)
    periods, needed = [], []
    counts = Counter(issuances=len(issuances), temperatureForecasts=0, verified=0, pending=0, missingObservations=0, archivedLate=0, invalidAsOf=0)
    for issuance in issuances:
        for location in issuance['locations']:
            for period in location['periods']:
                start, end = utc(period['intervalStart']), utc(period['intervalEndExclusive'])
                row = {'run': issuance['run'], 'archivedAt': issuance['archivedAt'], 'archivePath': issuance['_archivePath'], 'archiveSha256': issuance['_archiveSha256'], 'name': location['name'], 'nativeGridCoordinate': location['nativeGridCoordinate'], 'requestedCoordinate': location['requestedCoordinate'], 'leadWeek': period['leadWeek'], 'intervalStart': period['intervalStart'], 'intervalEndExclusive': period['intervalEndExclusive'], 'eligibleAfter': iso(end + timedelta(days=latency_days)), 'forecastP50': period['temperature']['p50'], 'observedProxy': None, 'error': None, 'archivedAfterValidStart': utc(issuance['archivedAt']) > start, 'daysExpected': (end-start).days, 'daysObserved': 0, 'partialPeriod': period['leadWeek'] == 9, 'periodLabel': 'Days 57–60 (4 days)' if period['leadWeek'] == 9 else f'Week {period["leadWeek"]}'}
                counts['temperatureForecasts'] += 1
                counts['archivedLate'] += int(row['archivedAfterValidStart'])
                dates = [start.date() + timedelta(days=i) for i in range(row['daysExpected'])]
                if utc(issuance['archivedAt']) > as_of:
                    row.update(status='archive_not_yet_captured_at_as_of')
                    counts['invalidAsOf'] += 1
                elif end + timedelta(days=latency_days) > as_of:
                    row.update(status='awaiting_mature_period')
                    counts['pending'] += 1
                else:
                    row.update(status='awaiting_observations')
                    needed.append((location['nativeGridCoordinate'], dates))
                periods.append((row, dates))
    provider.prepare(needed)
    pairs = []
    for row, dates in periods:
        if row['status'] == 'awaiting_observations':
            days = [{'date': day.isoformat(), 'temperatureProxyC': provider.daily(row['nativeGridCoordinate'], day)} for day in dates]
            row['daysObserved'] = sum(finite(day['temperatureProxyC']) for day in days)
            if row['daysObserved'] == row['daysExpected']:
                observed = sum(day['temperatureProxyC'] for day in days) / row['daysExpected']
                row.update(status='verified', observedProxy=observed, error=row['forecastP50'] - observed, dailyObservations=days)
                counts['verified'] += 1
            else:
                row.update(status='missing_observations', missingDates=[day['date'] for day in days if not finite(day['temperatureProxyC'])])
                counts['missingObservations'] += 1
            if hasattr(provider, 'nearest_grid'):
                _, _, lat, lon = provider.nearest_grid(row['nativeGridCoordinate'])
                row['observationGridCoordinate'] = [lat, ((lon + 180) % 360) - 180]
        pairs.append(row)
    names = sorted({p['name'] for p in pairs})
    verified = [p for p in pairs if p['status'] == 'verified']
    observed = [p for p in verified if not p['partialPeriod']]
    partial = [p for p in verified if p['partialPeriod']]
    by_lead = [{'leadWeek': lead, **metrics([p['error'] for p in observed if p['leadWeek'] == lead])} for lead in range(1, 9)]
    by_location = [{'name': name, **metrics([p['error'] for p in observed if p['name'] == name])} for name in names]
    by_both = [{'name': name, 'leadWeek': lead, **metrics([p['error'] for p in observed if p['name'] == name and p['leadWeek'] == lead])} for name in names for lead in range(1, 9)]
    warnings = list(WARNINGS)
    if counts['archivedLate']:
        warnings.append(f'{counts["archivedLate"]} forecast-location periods were first archived after their valid window began; they are flagged and cannot be claimed as strictly prospective issue-time captures.')
    grid_names = defaultdict(set)
    for p in pairs:
        grid_names[tuple(p['nativeGridCoordinate'])].add(p['name'])
    shared = [sorted(names) for names in grid_names.values() if len(names) > 1]
    if shared:
        warnings.append('Some locations use the same native forecast grid point; their errors are duplicates, not independent evidence: ' + '; '.join(', '.join(names) for names in shared))
    if provider.kind != 'real_noaa_cpc_analysis':
        warnings.insert(0, 'SYNTHETIC UNIT-TEST FIXTURE: NOT REAL VERIFICATION OR PRODUCTION DATA')
    if not issuances:
        status = 'no_archived_forecasts'
    elif verified:
        status = 'verified_with_gaps' if counts['missingObservations'] else 'verified'
    elif counts['missingObservations']:
        status = 'observations_unavailable'
    else:
        status = 'awaiting_mature_periods'
    return {'schemaVersion': VERSION, 'generatedAt': iso(datetime.now(UTC)), 'asOf': iso(as_of), 'status': status, 'counts': dict(counts), 'minimumLatencyDays': latency_days, 'temperature': {'units': '°C', 'label': METRIC_LABEL, 'truth': 'CPC (Tmax+Tmin)/2 weekly-mean proxy', 'truthKind': provider.kind, 'forecastStatistic': 'Four-member p50 of 28 six-hourly samples per member per week', 'observationStatistic': 'Seven-day arithmetic average of paired daily (Tmax+Tmin)/2; separate four-day final-period diagnostic', 'metricDefinition': 'error = forecastP50 − observedProxy; bias = mean(error); MAE = mean(abs(error)); RMSE = sqrt(mean(error²))', 'overall': metrics([p['error'] for p in observed]), 'byLead': by_lead, 'byLocation': by_location, 'byLeadLocation': by_both, 'partialDays57to60': {'label': 'Days 57–60 (4 days), excluded from full-week aggregates', **metrics([p['error'] for p in partial]), 'byLocation': [{'name': name, **metrics([p['error'] for p in partial if p['name'] == name])} for name in names]}, 'pairs': pairs}, 'precipitation': {'status': 'incompatible_statistic', 'n': 0, 'bias': None, 'mae': None, 'rmse': None, 'reason': 'Archived CFS precipitation is a mean sampled instantaneous rate in mm/day-equivalent. It is not a validated accumulated amount or time-integrated mean rate; direct scoring against daily accumulated rainfall would compare incompatible temporal statistics.'}, 'source': {'name': 'NOAA CPC Global Daily Temperature V1.0, served by NOAA PSL', 'documentation': SOURCE_DOCUMENTATION, 'endpointTemplate': SOURCE_ROOT + '/{tmax|tmin}.{year}.nc', 'latestAvailableDates': provider.latest_available_dates, 'actualAvailabilityCheck': 'NOAA annual time dimension plus exact per-row daily timestamps and complete finite Tmax/Tmin coverage', 'observationRevisionPolicy': 'Re-fetch needed source subsets on each run; immutable response hashes and optional evidence files preserve each evaluated source version.'}, 'sourceProvenance': provider.provenance, 'sourceErrors': provider.errors, 'warnings': warnings}


def write_report(path: Path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(raw)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--as-of', default=None, help='ISO8601 UTC timestamp; defaults to actual UTC now')
    parser.add_argument('--latency-days', type=int, default=MIN_LATENCY_DAYS)
    parser.add_argument('--evidence-dir', type=Path, help='Optional content-addressed immutable NOAA response evidence')
    parser.add_argument('--include-pairs', action='store_true', help='Include full per-forecast audit rows; omitted by default to keep public summaries small')
    args = parser.parse_args()
    as_of = utc(args.as_of) if args.as_of else datetime.now(UTC)
    if as_of > datetime.now(UTC) + timedelta(minutes=5):
        parser.error('--as-of may not be in the future')
    issuances = load_archive(args.archive_dir)
    report = build_report(issuances, as_of, CPCProvider(args.evidence_dir), args.latency_days)
    report['archiveProvenance'] = [{'run': i['run'], 'archivedAt': i['archivedAt'], 'path': i['_archivePath'], 'sha256': i['_archiveSha256'], 'sourceProductSha256': i['sourceProductSha256']} for i in issuances]
    report['verificationRecipe'] = {'scriptSha256': digest(Path(__file__).read_bytes()), 'minimumLatencyDays': args.latency_days, 'asOf': iso(as_of), 'fullPairsIncluded': args.include_pairs, 'maxActiveIssuances': MAX_ISSUANCES, 'networkBudgetSeconds': 240, 'requestBudget': 80}
    if not args.include_pairs:
        report['temperature']['auditPairCount'] = len(report['temperature'].pop('pairs'))
        report['temperature']['auditNote'] = 'Per-forecast rows omitted from public summary. Re-run identical immutable archive with --include-pairs for full native-grid coordinates, actual daily source dates, missing dates, archive timing and errors. Source revisions are identified by changed response SHA256.'
    write_report(args.output, report)
    print(json.dumps({'status': report['status'], 'counts': report['counts'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
