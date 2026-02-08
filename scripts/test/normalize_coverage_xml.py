#!/usr/bin/env python3
"""Normalize coverage.xml source paths for SonarCloud compatibility."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


def normalize_coverage_sources(path: Path) -> None:
    tree = ET.parse(path)
    root = tree.getroot()

    for source in root.findall(".//sources/source"):
        text = (source.text or "").strip()
        if text.startswith("/"):
            source.text = "."

    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_xml", type=Path, help="Path to coverage.xml")
    args = parser.parse_args()

    if not args.coverage_xml.exists():
        print(f"ERROR: coverage file not found: {args.coverage_xml}")
        return 1

    normalize_coverage_sources(args.coverage_xml)
    print(f"Normalized coverage sources in {args.coverage_xml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
