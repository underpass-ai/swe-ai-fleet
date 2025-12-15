#!/usr/bin/env python3
"""Combine multiple coverage.xml files into a single file with normalized paths.

This script merges coverage.xml files from different modules, ensuring all paths
are relative to the repository root for SonarCloud compatibility.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict


def find_coverage_xml_files(base_dir: Path) -> list[tuple[Path, str]]:
    """Find all coverage.xml files and determine their module path.
    
    Returns list of (file_path, module_path) tuples.
    """
    xml_files = []
    
    # Look for coverage.xml in known module locations
    for xml_file in base_dir.rglob("coverage.xml"):
        # Skip if it's the root coverage.xml (we're generating that)
        if xml_file.parent == base_dir:
            continue
            
        # Determine module path from file location
        # e.g., services/backlog_review_processor/coverage.xml -> services/backlog_review_processor
        parts = xml_file.parts
        if len(parts) >= 3:
            # Find the module root (services/* or core/*)
            module_path = None
            for i, part in enumerate(parts):
                if part in ("services", "core") and i + 1 < len(parts):
                    module_path = "/".join(parts[i:-1])  # Everything except coverage.xml
                    break
            
            if module_path:
                xml_files.append((xml_file, module_path))
    
    return xml_files


def normalize_filename(filename: str, module_path: str, source_path: str) -> str:
    """Normalize filename to be relative to repository root.
    
    Args:
        filename: Original filename from coverage.xml (may be relative to module)
        module_path: Module path (e.g., "services/backlog_review_processor")
        source_path: Source path from coverage.xml (absolute path to module)
    
    Returns:
        Normalized filename relative to repo root
    """
    # If filename is already absolute, extract relative part
    if filename.startswith("/"):
        # Try to find module path in absolute path
        if module_path.replace("/", "_") in filename or module_path in filename:
            # Extract the part after the module
            parts = filename.split(module_path)
            if len(parts) > 1:
                relative = parts[1].lstrip("/")
                return f"{module_path}/{relative}"
    
    # If filename is relative, prepend module path
    if not filename.startswith(module_path):
        return f"{module_path}/{filename}"
    
    return filename


def combine_coverage_xmls(xml_files: list[tuple[Path, str]], output_path: Path) -> None:
    """Combine multiple coverage.xml files into one.
    
    Args:
        xml_files: List of (file_path, module_path) tuples
        output_path: Path to write combined coverage.xml
    """
    if not xml_files:
        print("⚠️  No coverage.xml files found to combine")
        return
    
    # Create root coverage element
    root = ET.Element("coverage")
    root.set("version", "7.13.0")
    root.set("timestamp", str(int(Path().stat().st_mtime * 1000)))
    
    sources = ET.SubElement(root, "sources")
    source_elem = ET.SubElement(sources, "source")
    source_elem.text = "."
    
    packages_elem = ET.SubElement(root, "packages")
    
    # Aggregate statistics
    total_lines_valid = 0
    total_lines_covered = 0
    total_branches_valid = 0
    total_branches_covered = 0
    
    # Track packages to merge
    packages_dict: dict[str, ET.Element] = {}
    
    for xml_file, module_path in xml_files:
        print(f"  Processing: {xml_file} (module: {module_path})")
        try:
            tree = ET.parse(xml_file)
            file_root = tree.getroot()
            
            # Extract statistics
            total_lines_valid += int(file_root.get("lines-valid", 0))
            total_lines_covered += int(file_root.get("lines-covered", 0))
            total_branches_valid += int(file_root.get("branches-valid", 0))
            total_branches_covered += int(file_root.get("branches-covered", 0))
            
            # Get source path from original XML
            source_paths = file_root.findall(".//sources/source")
            source_path = source_paths[0].text if source_paths else ""
            
            # Process packages
            for package in file_root.findall(".//package"):
                package_name = package.get("name", "")
                
                # Normalize package name to include module path
                if package_name == ".":
                    normalized_package = module_path.replace("/", ".")
                else:
                    normalized_package = f"{module_path.replace('/', '.')}.{package_name}"
                
                # Get or create package element
                if normalized_package not in packages_dict:
                    pkg_elem = ET.SubElement(packages_elem, "package")
                    pkg_elem.set("name", normalized_package)
                    pkg_elem.set("line-rate", "0")
                    pkg_elem.set("branch-rate", "0")
                    pkg_elem.set("complexity", "0")
                    packages_dict[normalized_package] = pkg_elem
                else:
                    pkg_elem = packages_dict[normalized_package]
                
                # Process classes
                for class_elem in package.findall(".//class"):
                    # Normalize filename
                    orig_filename = class_elem.get("filename", "")
                    normalized_filename = normalize_filename(orig_filename, module_path, source_path)
                    
                    # Update class element
                    class_elem.set("filename", normalized_filename)
                    
                    # Update class name to match filename
                    class_name = normalized_filename.replace("/", ".").replace(".py", "")
                    class_elem.set("name", class_name)
                    
                    # Add to package
                    pkg_elem.append(class_elem)
        
        except Exception as e:
            print(f"    ⚠️  Error processing {xml_file}: {e}")
            continue
    
    # Calculate final rates
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
    
    print(f"✅ Combined {len(xml_files)} coverage.xml files into {output_path}")
    print(f"   Total classes: {sum(len(p.findall('.//class')) for p in packages_dict.values())}")
    print(f"   Total lines: {total_lines_valid} valid, {total_lines_covered} covered ({line_rate*100:.2f}%)")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: combine_coverage_xml.py <base_dir> [output_file]")
        sys.exit(1)
    
    base_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else base_dir / "coverage.xml"
    
    print(f"🔍 Searching for coverage.xml files in {base_dir}...")
    xml_files = find_coverage_xml_files(base_dir)
    
    if not xml_files:
        print("⚠️  No coverage.xml files found")
        sys.exit(1)
    
    print(f"📊 Found {len(xml_files)} coverage.xml files:")
    for xml_file, module_path in xml_files:
        print(f"  - {xml_file} ({module_path})")
    
    print(f"\n📊 Combining into {output_file}...")
    combine_coverage_xmls(xml_files, output_file)
    
    print("✅ Done!")


if __name__ == "__main__":
    main()
