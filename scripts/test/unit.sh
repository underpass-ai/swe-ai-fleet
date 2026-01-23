#!/bin/bash
# Run unit tests with automatic protobuf generation
# Usage: ./scripts/test/unit.sh [pytest args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Setup cleanup trap for JUnit XML files
cleanup_junit_xml() {
    rm -f "$PROJECT_ROOT/.test-results-"*.xml 2>/dev/null || true
}
trap cleanup_junit_xml EXIT INT TERM

echo "🔧 Preparing test environment..."
echo ""

# Activate virtual environment (if exists - optional in CI)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "ℹ️  No .venv found (CI environment assumed)"
    # CI installs packages globally via 'make install-deps'
fi

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
echo ""

# Default args if none provided
if [ $# -eq 0 ]; then
    PY_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

    # Run core module tests individually
    echo "📦 Running core module tests..."
    CORE_MODULES=(
        "core/shared"
        "core/memory"
        "core/context"
        "core/ceremony_engine"
        "core/orchestrator"
        "core/agents_and_tools"
        # core/ray_jobs is Python 3.11-only; run it in the ray_executor Python 3.11 environment.
        "core/reports"
    )

    CORE_EXIT=0
    for module in "${CORE_MODULES[@]}"; do
        if [ -f "$module/pyproject.toml" ] && [ -d "$module/tests" ] || find "$module" -name "test_*.py" -o -name "*_test.py" | grep -q .; then
            echo ""
            echo "  Testing $module..."
            # Use test-module.sh which handles dev dependencies installation
            "$PROJECT_ROOT/scripts/test-module.sh" "$module" \
                --cov-report= \
                || CORE_EXIT=$?
        fi
    done

    # Run service module tests individually
    echo ""
    echo "🔧 Running service module tests..."
    SERVICE_MODULES=(
        "services/backlog_review_processor"
        "services/context"
        "services/orchestrator"
        "services/planning"
        # services/ray_executor is Python 3.11-only; run it separately below.
        "services/task_derivation"
        "services/workflow"
    )

    SERVICES_EXIT=0
    for module in "${SERVICE_MODULES[@]}"; do
        if [ -f "$module/pyproject.toml" ] && [ -d "$module/tests" ] || find "$module" -name "test_*.py" -o -name "*_test.py" | grep -q .; then
            echo ""
            echo "  Testing $module..."
            # Use test-module.sh which handles dev dependencies installation
            "$PROJECT_ROOT/scripts/test-module.sh" "$module" \
                --cov-report= \
                || SERVICES_EXIT=$?
        fi
    done

    # Run Ray modules (Python 3.11) in a container if host Python is not 3.11.
    # This keeps "make test-unit" as a single entry point for the whole monorepo.
    RAY_EXIT=0
    if [ "$PY_MINOR" = "3.11" ]; then
        echo ""
        echo "🧩 Running Ray modules locally (Python 3.11 detected)..."
        "$PROJECT_ROOT/scripts/test-module.sh" "core/ray_jobs" --cov-report= || RAY_EXIT=$?
        "$PROJECT_ROOT/scripts/test-module.sh" "services/ray_executor" --cov-report= || RAY_EXIT=$?
    else
        echo ""
        echo "🧩 Running Ray modules in an isolated Python 3.11 container..."
        bash "$PROJECT_ROOT/scripts/test/local-docker.sh" "core/ray_jobs" --cov-report= || RAY_EXIT=$?
        bash "$PROJECT_ROOT/scripts/test/local-docker.sh" "services/ray_executor" --cov-report= || RAY_EXIT=$?
    fi

    # Combine coverage from all modules and generate reports
    echo ""
    echo "📊 Combining coverage reports..."
    cd "$PROJECT_ROOT"

    # Install coverage if not already installed
    pip install coverage > /dev/null 2>&1 || true

    # Strategy: Combine individual coverage.xml files directly with normalized paths
    # This is more reliable than combining .coverage files which may have path conflicts
    echo "📊 Combining individual coverage.xml files..."
    XML_FILES=$(find . -name "coverage.xml" \( -path "*/core/*" -o -path "*/services/*" \) 2>/dev/null || true)

    if [ -n "$XML_FILES" ]; then
        XML_COUNT=$(echo "$XML_FILES" | wc -l)
        echo "Found $XML_COUNT coverage.xml files to combine"

        # Use Python script to properly combine XML files with path normalization
        python3 << 'PYEOF'
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

def combine_coverage_xmls_local(base_dir: str, output_path: str) -> None:
    """Combine coverage.xml files from local modules."""
    base_path = Path(base_dir)
    xml_files = []

    # Find all coverage.xml files in core/ and services/
    for xml_file in base_path.rglob("coverage.xml"):
        # Skip root coverage.xml if it exists
        if xml_file.parent == base_path:
            continue

        # Determine module path
        parts = xml_file.parts
        module_path = None
        for i, part in enumerate(parts):
            if part in ("services", "core") and i + 1 < len(parts):
                module_path = "/".join(parts[i:-1])
                break

        if module_path:
            xml_files.append((xml_file, module_path))

    if not xml_files:
        print("⚠️  No coverage.xml files found")
        return

    print(f"📊 Found {len(xml_files)} coverage.xml files to combine")

    # Create root
    root = ET.Element("coverage")
    root.set("version", "7.13.0")
    root.set("timestamp", str(int(Path().stat().st_mtime * 1000)))

    sources = ET.SubElement(root, "sources")
    source_elem = ET.SubElement(sources, "source")
    source_elem.text = "."

    packages_elem = ET.SubElement(root, "packages")
    packages_dict = {}

    total_lines_valid = 0
    total_lines_covered = 0
    total_branches_valid = 0
    total_branches_covered = 0

    for xml_file, module_path in xml_files:
        print(f"  Processing: {xml_file} -> {module_path}")
        try:
            tree = ET.parse(xml_file)
            file_root = tree.getroot()

            # Aggregate stats
            total_lines_valid += int(file_root.get("lines-valid", 0))
            total_lines_covered += int(file_root.get("lines-covered", 0))
            total_branches_valid += int(file_root.get("branches-valid", 0))
            total_branches_covered += int(file_root.get("branches-covered", 0))

            # Process packages and classes
            for package in file_root.findall(".//package"):
                pkg_name = package.get("name", "")
                normalized_pkg = f"{module_path.replace('/', '.')}.{pkg_name}" if pkg_name != "." else module_path.replace("/", ".")

                if normalized_pkg not in packages_dict:
                    pkg_elem = ET.SubElement(packages_elem, "package")
                    pkg_elem.set("name", normalized_pkg)
                    pkg_elem.set("line-rate", "0")
                    pkg_elem.set("branch-rate", "0")
                    pkg_elem.set("complexity", "0")
                    packages_dict[normalized_pkg] = pkg_elem
                else:
                    pkg_elem = packages_dict[normalized_pkg]

                for class_elem in package.findall(".//class"):
                    orig_filename = class_elem.get("filename", "")
                    # Normalize filename to include module path
                    if not orig_filename.startswith(module_path):
                        normalized_filename = f"{module_path}/{orig_filename}"
                    else:
                        normalized_filename = orig_filename

                    class_elem.set("filename", normalized_filename)
                    class_name = normalized_filename.replace("/", ".").replace(".py", "")
                    class_elem.set("name", class_name)
                    pkg_elem.append(class_elem)

        except Exception as e:
            print(f"    ⚠️  Error processing {xml_file}: {e}")
            continue

    # Set final stats
    line_rate = total_lines_covered / total_lines_valid if total_lines_valid > 0 else 0
    branch_rate = total_branches_covered / total_branches_valid if total_branches_valid > 0 else 0

    root.set("lines-valid", str(total_lines_valid))
    root.set("lines-covered", str(total_lines_covered))
    root.set("line-rate", f"{line_rate:.4f}")
    root.set("branches-valid", str(total_branches_valid))
    root.set("branches-covered", str(total_branches_covered))
    root.set("branch-rate", f"{branch_rate:.4f}")
    root.set("complexity", "0")

    # Write output
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    total_classes = sum(len(p.findall('.//class')) for p in packages_dict.values())
    print(f"✅ Combined coverage.xml: {total_classes} classes, {total_lines_covered}/{total_lines_valid} lines ({line_rate*100:.2f}%)")

combine_coverage_xmls_local(".", "coverage.xml")
PYEOF

        if [ -f "coverage.xml" ]; then
            echo "✅ Combined coverage.xml generated successfully"
        else
            echo "⚠️  Failed to generate combined coverage.xml"
            # Fallback: try combining .coverage files
            echo "📊 Fallback: Trying to combine .coverage files..."
            COVERAGE_DATA_FILES=$(find . -name ".coverage" \( -path "*/core/*" -o -path "*/services/*" \) 2>/dev/null || true)
            if [ -n "$COVERAGE_DATA_FILES" ]; then
                echo "$COVERAGE_DATA_FILES" | while read -r cov_file; do
                    if [ -f "$cov_file" ]; then
                        coverage combine "$cov_file" 2>/dev/null || true
                    fi
                done
                coverage xml -o coverage.xml 2>/dev/null || true
            fi
        fi
    else
        echo "⚠️  No coverage.xml files found"
    fi

    # Fix source path to be relative (SonarQube requirement)
    if [ -f "coverage.xml" ]; then
        python3 << 'EOF'
import xml.etree.ElementTree as ET
import os

try:
    # Read coverage.xml
    tree = ET.parse('coverage.xml')
    root = tree.getroot()

    # Fix all source paths to be relative
    for source in root.findall('.//sources/source'):
        if source.text and os.path.isabs(source.text):
            source.text = '.'

    # Write back
    tree.write('coverage.xml', encoding='utf-8', xml_declaration=True)
    print("✅ Fixed coverage.xml source paths to relative (.)")
except Exception as e:
    print(f"⚠️  Warning: Could not fix coverage.xml paths: {e}")
EOF
    fi

    # Generate HTML and JSON reports
    # Try to generate from .coverage if it exists, otherwise skip (coverage.xml is the important one for SonarCloud)
    if [ -f ".coverage" ]; then
        coverage html -d htmlcov 2>/dev/null || echo "⚠️  Could not generate HTML report"
        coverage json -o coverage.json 2>/dev/null || echo "⚠️  Could not generate JSON report"
    else
        echo "ℹ️  No .coverage file found - HTML/JSON reports skipped (coverage.xml is sufficient for SonarCloud)"
        # Create minimal JSON for compatibility if needed
        if [ ! -f "coverage.json" ]; then
            echo '{"meta": {"version": "7.13.0"}, "files": {}}' > coverage.json 2>/dev/null || true
        fi
    fi

    # Check for failures and report which test suites failed
    FAILED_SERVICES=()
    if [ $CORE_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Core modules")
    fi
    if [ $SERVICES_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Service modules")
    fi
    if [ $RAY_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Ray modules")
    fi
    
    # Return non-zero if any test suite failed
    if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
        echo ""
        echo "❌ Tests failed in the following services:"
        for service in "${FAILED_SERVICES[@]}"; do
            echo "   - $service"
        done
        echo ""
        
        # Generate detailed failure summary from JUnit XML reports
        echo "📋 Detailed test failure summary:"
        echo ""
        
        python3 << 'PYEOF'
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import re

def find_test_file_from_classname(project_path: Path, classname: str, module_name: str) -> str:
    """Try to find the actual test file from classname."""
    if not classname:
        return ""
    
    # classname format: tests.unit.module.TestClass or module.submodule.TestClass
    parts = classname.split(".")
    
    # Try to find core/ or services/ in the path
    module_root_idx = None
    for i, part in enumerate(parts):
        if part in ("core", "services") and i + 1 < len(parts):
            module_root_idx = i
            break
    
    if module_root_idx is None:
        # Try to infer from module_name
        if module_name.startswith("core/") or module_name.startswith("services/"):
            # Prepend module name to parts
            module_parts = module_name.split("/")
            parts = module_parts + parts
    
    # Convert classname parts to file path
    # Remove 'tests' and 'unit' if present
    path_parts = []
    skip_next = False
    for i, part in enumerate(parts):
        if part in ("tests", "unit") and i < len(parts) - 1:
            continue
        if part.endswith("_test") or part.startswith("test_"):
            # This is likely the test file name
            path_parts.append(part)
            break
        path_parts.append(part)
    
    # Try different path combinations
    test_class = parts[-1] if parts else ""
    potential_paths = []
    
    # If we have a module root, use it
    if module_root_idx is not None:
        module_root = "/".join(parts[module_root_idx:-1])
        potential_paths.extend([
            f"{module_root}/{test_class}.py",
            f"{module_root}/tests/{test_class}.py",
            f"{module_root}/tests/unit/{test_class}.py",
            f"{module_root}/tests/unit/test_{test_class.lower()}.py",
            f"{module_root}/tests/{test_class.lower()}_test.py",
        ])
    else:
        # Try with module_name
        if module_name:
            potential_paths.extend([
                f"{module_name}/{test_class}.py",
                f"{module_name}/tests/{test_class}.py",
                f"{module_name}/tests/unit/{test_class}.py",
                f"{module_name}/tests/unit/test_{test_class.lower()}.py",
            ])
    
    # Also try to find files matching the pattern
    for pp in potential_paths:
        full_path = project_path / pp
        if full_path.exists():
            return pp
    
    # Last resort: search for files matching the test class name
    if test_class:
        # Search in the module directory
        if module_name:
            module_path = project_path / module_name
            if module_path.exists():
                for test_file in module_path.rglob(f"*{test_class}*.py"):
                    rel_path = test_file.relative_to(project_path)
                    return str(rel_path)
                for test_file in module_path.rglob(f"test_*.py"):
                    # Check if classname matches
                    content = test_file.read_text(errors="ignore")
                    if test_class in content or test_class.replace("Test", "") in content:
                        rel_path = test_file.relative_to(project_path)
                        return str(rel_path)
    
    return ""

def parse_junit_xml_and_summarize_failures(project_root: str) -> None:
    """Parse all JUnit XML files and generate a summary of failed tests."""
    project_path = Path(project_root)
    junit_files = list(project_path.glob(".test-results-*.xml"))
    
    if not junit_files:
        print("   ⚠️  No JUnit XML reports found")
        return
    
    failed_tests = []
    
    for junit_file in junit_files:
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            # Extract module name from filename
            # Format: .test-results-core-ceremony-engine.xml -> core/ceremony_engine
            # Or: .test-results-services-backlog-review-processor.xml -> services/backlog_review_processor
            filename_base = junit_file.stem.replace(".test-results-", "")
            
            # Try to reconstruct the module path
            # The filename uses dashes, but module paths use underscores
            # We need to identify where core/ or services/ starts
            module_name = ""
            if filename_base.startswith("core-"):
                parts = filename_base.replace("core-", "", 1).split("-")
                module_name = "core/" + "_".join(parts)
            elif filename_base.startswith("services-"):
                parts = filename_base.replace("services-", "", 1).split("-")
                module_name = "services/" + "_".join(parts)
            else:
                # Fallback: try to guess
                parts = filename_base.split("-")
                if len(parts) >= 2:
                    if parts[0] in ("core", "services"):
                        module_name = f"{parts[0]}/" + "_".join(parts[1:])
                    else:
                        module_name = "/".join(parts)
                else:
                    module_name = filename_base.replace("-", "/")
            
            # Find all test cases that failed or errored
            for testcase in root.findall(".//testcase"):
                failure = testcase.find("failure")
                error = testcase.find("error")
                
                if failure is not None or error is not None:
                    test_name = testcase.get("name", "unknown")
                    class_name = testcase.get("classname", "")
                    file_path = testcase.get("file", "")
                    line_number = testcase.get("line", "")
                    
                    # Get error element first (needed for file path extraction)
                    error_elem = failure if failure is not None else error
                    
                    # Try to extract file path from classname if file attribute is missing
                    if not file_path and class_name:
                        file_path = find_test_file_from_classname(project_path, class_name, module_name)
                    
                    # If still no file path, try to extract from test name or classname
                    if not file_path or file_path == "unknown":
                        # Sometimes pytest includes file info in the test name
                        # Format: test_file.py::TestClass::test_method
                        if "::" in test_name:
                            parts = test_name.split("::")
                            potential_file = parts[0]
                            if potential_file.endswith(".py"):
                                # Try to find this file
                                for search_path in [module_name, f"{module_name}/tests", f"{module_name}/tests/unit"]:
                                    full_path = project_path / search_path / potential_file
                                    if full_path.exists():
                                        file_path = f"{search_path}/{potential_file}"
                                        break
                        
                        # For ImportError, try to extract file path from error message
                        if (not file_path or file_path == "unknown") and error_elem is not None:
                            error_text = error_elem.text or ""
                            # Look for file paths in the error message
                            # Format: "ImportError while importing test module '/path/to/file.py'"
                            import_match = re.search(r"test module ['\"]([^'\"]+\.py)['\"]", error_text)
                            if import_match:
                                found_path = import_match.group(1)
                                # Convert absolute path to relative
                                try:
                                    found_path_obj = Path(found_path)
                                    if found_path_obj.is_absolute():
                                        try:
                                            rel_path = found_path_obj.relative_to(project_path)
                                            file_path = str(rel_path)
                                        except ValueError:
                                            # Path is outside project root, use as-is but make relative-looking
                                            file_path = found_path
                                    else:
                                        file_path = found_path
                                except (ValueError, AttributeError):
                                    pass
                    
                    # Get error message
                    error_message = ""
                    error_type = ""
                    if error_elem is not None:
                        error_type = error_elem.get("type", "")
                        error_message = error_elem.text or ""
                        # Extract meaningful error message
                        if error_message:
                            lines = error_message.split("\n")
                            # For ImportError, try to get the actual import error message
                            if "ImportError" in error_type or "ModuleNotFoundError" in error_type:
                                # Look for the actual import error (usually after "ImportError:")
                                found_import_error = False
                                for i, line in enumerate(lines):
                                    line = line.strip()
                                    if ("ImportError" in line or "ModuleNotFoundError" in line) and ":" in line:
                                        # Extract the part after the colon
                                        parts = line.split(":", 1)
                                        if len(parts) > 1:
                                            error_message = parts[1].strip()
                                            found_import_error = True
                                            # Also check next line for more details
                                            if i + 1 < len(lines):
                                                next_line = lines[i + 1].strip()
                                                if next_line and not next_line.startswith("File"):
                                                    error_message += " " + next_line
                                            break
                                
                                # If not found, look for "cannot import" or similar messages
                                if not found_import_error:
                                    for line in lines:
                                        line = line.strip()
                                        if ("cannot import" in line.lower() or "No module named" in line) and ":" in line:
                                            parts = line.split(":", 1)
                                            if len(parts) > 1:
                                                error_message = parts[1].strip()[:250]
                                                break
                                
                                # If still not found, use the first meaningful line
                                if not error_message or len(error_message) < 10:
                                    for line in lines:
                                        line = line.strip()
                                        if line and not line.startswith("Traceback") and not line.startswith("File"):
                                            error_message = line[:250]
                                            break
                                
                                # Limit length
                                if error_message:
                                    error_message = error_message[:250]
                            else:
                                # For other errors, extract first meaningful line
                                for line in lines:
                                    line = line.strip()
                                    if line and not line.startswith("Traceback") and not line.startswith("File"):
                                        # Remove common prefixes
                                        line = re.sub(r"^(AssertionError|ValueError|TypeError|AttributeError|KeyError|IndexError|TimeoutError):\s*", "", line)
                                        if line:
                                            error_message = line[:250]  # Limit length
                                            break
                                else:
                                    # Fallback: use first non-empty line
                                    for line in lines:
                                        if line.strip():
                                            error_message = line.strip()[:250]
                                            break
                    
                    failed_tests.append({
                        "module": module_name,
                        "file": file_path or "unknown",
                        "line": line_number or "unknown",
                        "test": test_name,
                        "class": class_name,
                        "error_type": error_type,
                        "error_message": error_message
                    })
        
        except Exception as e:
            print(f"   ⚠️  Error parsing {junit_file}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            continue
    
    if not failed_tests:
        print("   ✅ No failed tests found in JUnit reports (may be a collection/import error)")
        return
    
    # Group by module
    by_module = defaultdict(list)
    for test in failed_tests:
        by_module[test["module"]].append(test)
    
    # Print summary
    for module, tests in sorted(by_module.items()):
        print(f"   📦 Module: {module}")
        for test in tests:
            file_display = test["file"]
            # Normalize file path display
            if file_display != "unknown":
                # Convert absolute paths to relative
                try:
                    file_path_obj = Path(file_display)
                    if file_path_obj.is_absolute():
                        try:
                            file_display = str(file_path_obj.relative_to(project_path))
                        except ValueError:
                            # Path is outside project, try to extract just the filename
                            file_display = file_path_obj.name
                except (ValueError, AttributeError):
                    pass
                
                # Remove module prefix if already included (avoid duplication)
                if file_display.startswith(module + "/"):
                    file_display = file_display
                elif file_display.startswith("/"):
                    # Absolute path that couldn't be made relative, extract relevant part
                    if module in file_display:
                        idx = file_display.find(module)
                        file_display = file_display[idx:]
                    else:
                        # Just use filename
                        file_display = Path(file_display).name
                elif not file_display.startswith("core/") and not file_display.startswith("services/"):
                    file_display = f"{module}/{file_display}"
            else:
                file_display = f"{module}/<unknown>"
            
            line_display = f":{test['line']}" if test["line"] != "unknown" and test["line"] else ""
            test_display = test["test"]
            # Simplify test name if it's too long
            if "::" in test_display:
                parts = test_display.split("::")
                if len(parts) > 2:
                    test_display = f"{parts[-2]}::{parts[-1]}"
            
            print(f"      ❌ {file_display}{line_display}::{test_display}")
            if test["error_message"]:
                # Truncate and indent error message
                error_msg = test["error_message"]
                if len(error_msg) > 150:
                    error_msg = error_msg[:147] + "..."
                print(f"         Error: {error_msg}")
        print("")
    
    print(f"   📊 Total failed tests: {len(failed_tests)}")

parse_junit_xml_and_summarize_failures(".")
PYEOF
        
        echo "💡 Tip: Scroll up to see detailed error messages from pytest"
        echo "💡 Or run tests for a specific module:"
        echo "   make test-module MODULE=<module-path>"
        
        exit 1
    fi
else
    pytest "$@"
fi

TEST_EXIT_CODE=$?

# Show result
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All unit tests passed! Coverage report:"
    echo "   📊 Terminal: see above"
    echo "   📄 XML: coverage.xml (for SonarCloud)"
    if [ -f "coverage.json" ]; then
        echo "   📄 JSON: coverage.json"
    fi
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

