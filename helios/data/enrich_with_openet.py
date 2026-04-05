from __future__ import annotations

import argparse

import pandas as pd

from helios.utils.openet import fetch_monthly_et


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch monthly OpenET ET data for a field and write to CSV."
    )
    parser.add_argument("--lon", type=float, required=True, help="Field longitude (decimal degrees)")
    parser.add_argument("--lat", type=float, required=True, help="Field latitude (decimal degrees)")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, required=True, help="Output CSV file path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    records = fetch_monthly_et(
        longitude=args.lon,
        latitude=args.lat,
        start_date=args.start,
        end_date=args.end,
    )

    df = pd.DataFrame(records)
    df = df.rename(columns={"time": "date", "et": "openet_et_mm"})
    df.to_csv(args.output, index=False)

    print(f"Wrote {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
