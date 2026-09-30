"""Dependency-free validation and split audit; produces no skill scores."""
import argparse
import json
from .data import load_rows, parse_date, split_rows, split_summary, check_manifest


def arguments(parser):
    parser.add_argument("--csv", required=True)
    parser.add_argument("--validation-start", type=parse_date, required=True)
    parser.add_argument("--test-start", type=parse_date, required=True)
    parser.add_argument("--observation-lag-days", type=int, default=0)
    parser.add_argument("--holdout-events", nargs="*", default=[])
    return parser


def main():
    parser = arguments(argparse.ArgumentParser(description=__doc__))
    parser.add_argument("--manifest", help="Validate provenance attestations too")
    args = parser.parse_args()
    try:
        rows = load_rows(args.csv)
        splits, purged = split_rows(rows, args.validation_start, args.test_start,
                                    args.observation_lag_days, args.holdout_events)
        if args.manifest:
            check_manifest(args.manifest)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(split_summary(splits, purged), indent=2))
    if not rows[0].enso_event_id:
        print("WARNING: No event IDs; temporal holdout is not an event-independent experiment.")


if __name__ == "__main__":
    main()
