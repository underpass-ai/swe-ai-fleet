#!/bin/bash
# Run unit tests with automatic protobuf generation
# Usage: ./scripts/test/unit.sh [pytest args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

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
    coverage html -d htmlcov
    coverage json -o coverage.json

    # Check for failures and report which test suites failed
    FAILED_SERVICES=()
    if [ $CORE_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Core modules")
    fi
    if [ $SERVICES_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Service modules")
    fi
    # Return non-zero if any test suite failed
    if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
        echo ""
        echo "❌ Tests failed in the following services:"
        for service in "${FAILED_SERVICES[@]}"; do
            echo "   - $service"
        done
        if [ $RAY_EXIT -ne 0 ]; then
            echo "   - Ray modules (core/ray_jobs, services/ray_executor)"
        fi
        echo ""
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
    echo "   📄 XML: coverage.xml"
    echo "   🌐 HTML: htmlcov/index.html"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

