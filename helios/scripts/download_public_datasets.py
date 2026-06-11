from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "public_datasets.json"
DEFAULT_OUTPUT_ROOT = Path("data/public")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download registered public Helios datasets.")
    parser.add_argument("--source", default="usda_lirf_2012_2013", help="Dataset source_id from public_datasets.json.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--timeout-seconds", type=int, default=60)
    return parser.parse_args()


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def find_dataset(registry: dict[str, Any], source_id: str) -> dict[str, Any]:
    for dataset in registry["datasets"]:
        if dataset["source_id"] == source_id:
            return dataset
    raise ValueError(f"Unknown public dataset source_id: {source_id}")


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_dataset(
    *,
    source_id: str,
    output_root: str = str(DEFAULT_OUTPUT_ROOT),
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    registry = load_registry()
    dataset = find_dataset(registry, source_id)
    raw_dir = Path(output_root) / source_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    downloaded_files: list[dict[str, Any]] = []
    for file_info in dataset.get("raw_files", []):
        expected_md5 = file_info.get("md5")
        destination = raw_dir / file_info["name"]
        destination.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(file_info["download_url"], timeout=timeout_seconds)
        response.raise_for_status()
        destination.write_bytes(response.content)

        actual_md5 = _md5(destination)
        if expected_md5 and actual_md5 != expected_md5:
            destination.unlink(missing_ok=True)
            raise ValueError(
                f"Checksum mismatch for {file_info['name']}: expected {expected_md5}, got {actual_md5}"
            )

        downloaded_files.append(
            {
                "name": file_info["name"],
                "path": str(destination),
                "download_url": file_info["download_url"],
                "md5": actual_md5,
                "size_bytes": destination.stat().st_size,
            }
        )

    manifest = {
        "source_id": source_id,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_metadata_retrieved_at_utc": dataset.get("metadata_retrieved_at_utc"),
        "files": downloaded_files,
    }
    manifest_path = raw_dir / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    args = parse_args()
    manifest = download_dataset(
        source_id=args.source,
        output_root=args.output_root,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
