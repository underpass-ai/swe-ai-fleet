#!/usr/bin/env python3
"""Print a concise failure summary from pytest JUnit XML reports."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FailedTest:
    module: str
    file: str
    line: str
    test: str
    message: str


def module_from_report_name(report: Path) -> str:
    stem = report.stem.replace(".test-results-", "")
    if stem.startswith("core-"):
        return "core/" + stem.replace("core-", "", 1).replace("-", "_")
    if stem.startswith("services-"):
        return "services/" + stem.replace("services-", "", 1).replace("-", "_")
    return stem.replace("-", "/")


def first_meaningful_line(text: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Traceback") or line.startswith("File "):
            continue
        line = re.sub(r"^[A-Za-z_]+Error:\s*", "", line)
        return line[:200]
    return ""


def infer_file(module: str, testcase_name: str) -> str:
    if "::" in testcase_name:
        candidate = testcase_name.split("::", 1)[0]
        if candidate.endswith(".py"):
            return f"{module}/{candidate}" if not candidate.startswith(("core/", "services/")) else candidate
    return "unknown"


def parse_report(report: Path, project_root: Path) -> list[FailedTest]:
    try:
        root = ET.parse(report).getroot()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"WARN: unable to parse {report}: {exc}")
        return []

    module = module_from_report_name(report)
    failures: list[FailedTest] = []

    for testcase in root.findall(".//testcase"):
        failure = testcase.find("failure")
        error = testcase.find("error")
        if failure is None and error is None:
            continue

        err = failure if failure is not None else error
        test_name = testcase.get("name", "unknown")
        file_attr = testcase.get("file") or infer_file(module, test_name)
        line = testcase.get("line", "unknown")

        # normalize absolute file paths to repo-relative when possible
        file_path = file_attr
        if file_path and file_path.startswith("/"):
            p = Path(file_path)
            try:
                file_path = str(p.relative_to(project_root))
            except ValueError:
                file_path = p.name

        message = first_meaningful_line(err.text or "")
        failures.append(
            FailedTest(
                module=module,
                file=file_path or "unknown",
                line=line or "unknown",
                test=test_name,
                message=message,
            )
        )

    return failures


def print_summary(failed_tests: list[FailedTest]) -> None:
    if not failed_tests:
        print("No failed tests were found in JUnit reports.")
        return

    by_module: dict[str, list[FailedTest]] = defaultdict(list)
    for test in failed_tests:
        by_module[test.module].append(test)

    for module in sorted(by_module):
        print(f"Module: {module}")
        for test in by_module[module]:
            location = test.file
            if test.line != "unknown":
                location = f"{location}:{test.line}"
            print(f"  - {location} :: {test.test}")
            if test.message:
                print(f"    {test.message}")
        print("")

    print(f"Total failed tests: {len(failed_tests)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()

    reports = sorted(args.project_root.glob(".test-results-*.xml"))
    if not reports:
        print("No JUnit reports found (.test-results-*.xml).")
        return 0

    all_failures: list[FailedTest] = []
    for report in reports:
        all_failures.extend(parse_report(report, args.project_root.resolve()))

    print_summary(all_failures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
