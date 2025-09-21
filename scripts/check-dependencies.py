#!/usr/bin/env python3
"""
Check for import cycles and validate dependency boundaries.

Enforces clean architecture layers:
- Domain → No dependencies
- Application → Domain only
- Infrastructure → Domain, Application
- Presentation → Domain, Application
"""

import ast
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict

# Define layer boundaries
ALLOWED_DEPENDENCIES = {
    "domain": [],
    "application": ["domain"],
    "infrastructure": ["domain", "application"],
    "presentation": ["domain", "application"],
    "_internal": ["domain", "application"],  # Internal utilities
}

# Map module names to layers
MODULE_LAYERS = {
    "ledzephyr.domain": "domain",
    "ledzephyr.application": "application",
    "ledzephyr.infrastructure": "infrastructure",
    "ledzephyr.presentation": "presentation",
    "ledzephyr.cli": "presentation",  # CLI is part of presentation
    "ledzephyr._internal": "_internal",
}


class ImportAnalyzer(ast.NodeVisitor):
    """Analyze imports in Python files."""

    def __init__(self, module_path: Path):
        self.module_path = module_path
        self.imports: Set[str] = set()
        self.module_name = self._get_module_name(module_path)

    def _get_module_name(self, path: Path) -> str:
        """Convert file path to module name."""
        parts = path.with_suffix("").parts
        try:
            idx = parts.index("ledzephyr")
            return ".".join(parts[idx:])
        except ValueError:
            return str(path)

    def visit_Import(self, node: ast.Import) -> None:
        """Process import statements."""
        for alias in node.names:
            if alias.name.startswith("ledzephyr"):
                self.imports.add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Process from...import statements."""
        if node.module and node.module.startswith("ledzephyr"):
            self.imports.add(node.module)


def get_layer(module: str) -> str:
    """Determine which layer a module belongs to."""
    for prefix, layer in MODULE_LAYERS.items():
        if module.startswith(prefix):
            return layer
    return "unknown"


def find_python_files(root: Path) -> List[Path]:
    """Find all Python files in the project."""
    return [
        p for p in root.glob("**/*.py")
        if "tests" not in p.parts and "__pycache__" not in p.parts
    ]


def analyze_dependencies(files: List[Path]) -> Dict[str, Set[str]]:
    """Analyze dependencies for all files."""
    dependencies = {}

    for file_path in files:
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            analyzer = ImportAnalyzer(file_path)
            analyzer.visit(tree)

            if analyzer.imports:
                dependencies[analyzer.module_name] = analyzer.imports
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    return dependencies


def find_cycles(dependencies: Dict[str, Set[str]]) -> List[List[str]]:
    """Detect import cycles using DFS."""
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(module: str, path: List[str]) -> None:
        visited.add(module)
        rec_stack.add(module)
        path.append(module)

        for dep in dependencies.get(module, []):
            if dep not in visited:
                dfs(dep, path[:])
            elif dep in rec_stack:
                # Found a cycle
                cycle_start = path.index(dep)
                cycle = path[cycle_start:] + [dep]
                cycles.append(cycle)

        rec_stack.remove(module)

    for module in dependencies:
        if module not in visited:
            dfs(module, [])

    return cycles


def check_layer_violations(dependencies: Dict[str, Set[str]]) -> List[Tuple[str, str, str, str]]:
    """Check for layer boundary violations."""
    violations = []

    for module, deps in dependencies.items():
        module_layer = get_layer(module)

        if module_layer == "unknown":
            continue

        allowed_layers = ALLOWED_DEPENDENCIES.get(module_layer, [])

        for dep in deps:
            dep_layer = get_layer(dep)

            if dep_layer == "unknown":
                continue

            # Check if this dependency is allowed
            if dep_layer not in allowed_layers and dep_layer != module_layer:
                violations.append((module, module_layer, dep, dep_layer))

    return violations


def main() -> int:
    """Main function."""
    # Find project root
    project_root = Path(__file__).parent.parent
    ledzephyr_root = project_root / "ledzephyr"

    if not ledzephyr_root.exists():
        print(f"Error: {ledzephyr_root} does not exist", file=sys.stderr)
        return 1

    print("Analyzing dependencies...")

    # Find all Python files
    files = find_python_files(ledzephyr_root)

    # Analyze dependencies
    dependencies = analyze_dependencies(files)

    # Check for cycles
    cycles = find_cycles(dependencies)

    # Check for layer violations
    violations = check_layer_violations(dependencies)

    # Report results
    has_issues = False

    if cycles:
        has_issues = True
        print("\n❌ Import Cycles Detected:")
        for cycle in cycles:
            print(f"  Cycle: {' → '.join(cycle)}")

    if violations:
        has_issues = True
        print("\n❌ Layer Boundary Violations:")
        for module, m_layer, dep, d_layer in violations:
            print(f"  {module} ({m_layer}) → {dep} ({d_layer})")
            print(f"    {m_layer} layer cannot depend on {d_layer} layer")

    if not has_issues:
        print("✅ No dependency violations found")
        return 0
    else:
        print("\n❌ Dependency check failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())