#!/usr/bin/env python3
"""Verify bundled curriculum, or vendor it from an explicit authoring source."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_ROOT = Path(__file__).resolve().parent.parent
DESTINATION_ROOT = SKILL_ROOT / "curriculum"
RUNTIME_FILES = (
    "sources.json",
    "scene-map.json",
    "sample-packs.json",
    "target-extensions.json",
    "topic-catalog.json",
)


def load(source_root: Path, name: str):
    with (source_root / name).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def payloads(source_root: Path) -> dict[str, object]:
    sources = [source for source in load(source_root, "sources.json") if source.get("scope") == "multilingual"]
    return {
        "sources.json": sources,
        "scene-map.json": load(source_root, "scene-map.json"),
        "sample-packs.json": load(source_root, "sample-packs.json"),
        "target-extensions.json": load(source_root, "target-extensions.json"),
        "topic-catalog.json": load(source_root, "topic-catalog.json"),
    }


def serialize(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def manifest(serialized: dict[str, str]) -> dict:
    return {
        "schema_version": 1,
        "source": "bundled",
        "portable": True,
        "files": {
            name: {
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "bytes": len(content.encode("utf-8")),
            }
            for name, content in serialized.items()
        },
    }


def verify_bundled() -> int:
    manifest_path = DESTINATION_ROOT / "manifest.json"
    if not manifest_path.is_file():
        print("bundled curriculum manifest is missing", file=sys.stderr)
        return 1
    with manifest_path.open(encoding="utf-8-sig") as handle:
        bundled_manifest = json.load(handle)
    if bundled_manifest.get("source") != "bundled" or bundled_manifest.get("portable") is not True:
        print("bundled curriculum manifest is not marked portable", file=sys.stderr)
        return 1
    listed_files = set(bundled_manifest.get("files", {}))
    if listed_files != set(RUNTIME_FILES):
        missing = sorted(set(RUNTIME_FILES) - listed_files)
        extra = sorted(listed_files - set(RUNTIME_FILES))
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unexpected: " + ", ".join(extra))
        print("bundled curriculum manifest file list mismatch (" + "; ".join(details) + ")", file=sys.stderr)
        return 1
    mismatches = []
    for name, expected in bundled_manifest.get("files", {}).items():
        path = DESTINATION_ROOT / name
        if not path.is_file():
            mismatches.append(name)
            continue
        content = path.read_bytes()
        if len(content) != expected.get("bytes") or hashlib.sha256(content).hexdigest() != expected.get("sha256"):
            mismatches.append(name)
    if mismatches:
        print("bundled curriculum integrity failure: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    print("Bundled curriculum is complete and self-contained.")
    return 0


def sync(source_root: Path, check: bool) -> int:
    serialized = {name: serialize(payload) for name, payload in payloads(source_root).items()}
    serialized["manifest.json"] = serialize(manifest(serialized))
    if check:
        mismatches = []
        for name, expected in serialized.items():
            path = DESTINATION_ROOT / name
            if not path.is_file() or path.read_text(encoding="utf-8-sig") != expected:
                mismatches.append(name)
        if mismatches:
            print("out of sync: " + ", ".join(mismatches), file=sys.stderr)
            return 1
        print("Bundled curriculum is in sync.")
        return 0

    DESTINATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name, content in serialized.items():
        (DESTINATION_ROOT / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"Synced {len(serialized) - 1} curriculum files to {DESTINATION_ROOT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if bundled data differs from the supplied authoring source")
    parser.add_argument("--source-root", type=Path, help="explicit canonical authoring curriculum directory")
    args = parser.parse_args()
    if args.source_root is None:
        return verify_bundled()
    source_root = args.source_root.expanduser().resolve()
    missing = [name for name in RUNTIME_FILES if not (source_root / name).is_file()]
    if missing:
        print(f"authoring curriculum missing from {source_root}: {', '.join(missing)}", file=sys.stderr)
        return 2
    return sync(source_root, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
