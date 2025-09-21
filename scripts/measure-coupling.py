#!/usr/bin/env python3
"""
Measure coupling and cohesion metrics for the codebase.

Metrics calculated:
- Afferent Coupling (Ca): Number of classes that depend on this class
- Efferent Coupling (Ce): Number of classes this class depends on
- Instability (I): Ce / (Ca + Ce) - how likely to change
- Abstractness (A): Ratio of abstract classes/interfaces
- Distance from Main Sequence (D): |A + I - 1| - ideal is close to 0
"""

import ast
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import json


@dataclass
class ClassMetrics:
    """Metrics for a single class."""
    name: str
    module: str
    is_abstract: bool
    methods: int
    dependencies: Set[str]  # Classes this class depends on
    dependents: Set[str]    # Classes that depend on this class


@dataclass
class PackageMetrics:
    """Metrics for a package."""
    name: str
    classes: List[ClassMetrics]
    ca: int  # Afferent coupling
    ce: int  # Efferent coupling
    instability: float
    abstractness: float
    distance: float  # Distance from main sequence


class CouplingAnalyzer(ast.NodeVisitor):
    """Analyze coupling between classes."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.module_name = self._get_module_name(file_path)
        self.classes: List[ClassMetrics] = []
        self.current_class: Optional[str] = None
        self.current_dependencies: Set[str] = set()
        self.current_is_abstract = False
        self.current_method_count = 0

    def _get_module_name(self, path: Path) -> str:
        """Convert file path to module name."""
        parts = path.with_suffix("").parts
        try:
            idx = parts.index("ledzephyr")
            return ".".join(parts[idx:])
        except ValueError:
            return str(path)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Process class definitions."""
        # Store previous state
        prev_class = self.current_class
        prev_deps = self.current_dependencies
        prev_abstract = self.current_is_abstract
        prev_methods = self.current_method_count

        # Set current class
        self.current_class = node.name
        self.current_dependencies = set()
        self.current_method_count = 0

        # Check if abstract
        self.current_is_abstract = False
        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in ("ABC", "Protocol"):
                    self.current_is_abstract = True
                else:
                    # This is a dependency
                    self.current_dependencies.add(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle module.Class inheritance
                self.current_dependencies.add(base.attr)

        # Count methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.current_method_count += 1
                # Check for abstractmethod decorator
                for decorator in item.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                        self.current_is_abstract = True

        # Visit body
        self.generic_visit(node)

        # Store class metrics
        self.classes.append(
            ClassMetrics(
                name=node.name,
                module=self.module_name,
                is_abstract=self.current_is_abstract,
                methods=self.current_method_count,
                dependencies=self.current_dependencies.copy(),
                dependents=set(),
            )
        )

        # Restore previous state
        self.current_class = prev_class
        self.current_dependencies = prev_deps
        self.current_is_abstract = prev_abstract
        self.current_method_count = prev_methods

    def visit_Name(self, node: ast.Name) -> None:
        """Track class references."""
        if self.current_class and node.id != self.current_class:
            # Check if this looks like a class name (CamelCase)
            if node.id[0].isupper():
                self.current_dependencies.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Track attribute access that might be class references."""
        if isinstance(node.value, ast.Name):
            # Track potential class usage like module.ClassName
            if node.attr[0].isupper():
                self.current_dependencies.add(node.attr)
        self.generic_visit(node)


def find_python_files(root: Path) -> List[Path]:
    """Find all Python files in the project."""
    return [
        p for p in root.glob("**/*.py")
        if "tests" not in p.parts and "__pycache__" not in p.parts
    ]


def analyze_coupling(files: List[Path]) -> Dict[str, ClassMetrics]:
    """Analyze coupling for all classes."""
    all_classes = {}

    for file_path in files:
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            analyzer = CouplingAnalyzer(file_path)
            analyzer.visit(tree)

            for cls in analyzer.classes:
                class_key = f"{cls.module}.{cls.name}"
                all_classes[class_key] = cls

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    # Calculate dependents (reverse dependencies)
    for class_key, cls in all_classes.items():
        for dep in cls.dependencies:
            # Find the dependent class
            for other_key, other_cls in all_classes.items():
                if other_cls.name == dep or other_key.endswith(f".{dep}"):
                    other_cls.dependents.add(class_key)

    return all_classes


def calculate_package_metrics(classes: Dict[str, ClassMetrics]) -> Dict[str, PackageMetrics]:
    """Calculate metrics at the package level."""
    packages = defaultdict(list)

    # Group classes by package
    for class_key, cls in classes.items():
        # Extract package name (everything before the last dot)
        parts = cls.module.split(".")
        if len(parts) > 1:
            package = ".".join(parts[:-1])
        else:
            package = parts[0]
        packages[package].append(cls)

    # Calculate metrics for each package
    package_metrics = {}
    for package_name, package_classes in packages.items():
        # Calculate afferent coupling (Ca)
        external_dependents = set()
        for cls in package_classes:
            for dep in cls.dependents:
                if not any(dep.startswith(f"{c.module}.{c.name}") for c in package_classes):
                    external_dependents.add(dep)
        ca = len(external_dependents)

        # Calculate efferent coupling (Ce)
        external_dependencies = set()
        for cls in package_classes:
            for dep in cls.dependencies:
                # Check if dependency is outside this package
                is_external = True
                for other_cls in package_classes:
                    if other_cls.name == dep:
                        is_external = False
                        break
                if is_external:
                    external_dependencies.add(dep)
        ce = len(external_dependencies)

        # Calculate instability
        if ca + ce > 0:
            instability = ce / (ca + ce)
        else:
            instability = 0.0

        # Calculate abstractness
        abstract_count = sum(1 for cls in package_classes if cls.is_abstract)
        if package_classes:
            abstractness = abstract_count / len(package_classes)
        else:
            abstractness = 0.0

        # Calculate distance from main sequence
        distance = abs(abstractness + instability - 1)

        package_metrics[package_name] = PackageMetrics(
            name=package_name,
            classes=package_classes,
            ca=ca,
            ce=ce,
            instability=instability,
            abstractness=abstractness,
            distance=distance,
        )

    return package_metrics


def print_metrics_report(package_metrics: Dict[str, PackageMetrics]) -> None:
    """Print a formatted metrics report."""
    print("\n📊 Coupling and Cohesion Metrics\n")
    print("=" * 80)

    # Sort packages by distance from main sequence (best first)
    sorted_packages = sorted(
        package_metrics.items(),
        key=lambda x: x[1].distance
    )

    for package_name, metrics in sorted_packages:
        print(f"\n📦 {package_name}")
        print("-" * 40)
        print(f"  Classes: {len(metrics.classes)}")
        print(f"  Abstract: {sum(1 for c in metrics.classes if c.is_abstract)}")
        print(f"  Concrete: {sum(1 for c in metrics.classes if not c.is_abstract)}")
        print(f"\n  Metrics:")
        print(f"    Ca (Afferent Coupling):  {metrics.ca:3d}")
        print(f"    Ce (Efferent Coupling):  {metrics.ce:3d}")
        print(f"    I  (Instability):        {metrics.instability:.2f}")
        print(f"    A  (Abstractness):       {metrics.abstractness:.2f}")
        print(f"    D  (Distance):           {metrics.distance:.2f}", end="")

        # Evaluate the distance
        if metrics.distance < 0.1:
            print(" ✅ Excellent")
        elif metrics.distance < 0.3:
            print(" ✓ Good")
        elif metrics.distance < 0.5:
            print(" ⚠️  Needs attention")
        else:
            print(" ❌ Poor")

        # Show class details if there are issues
        if metrics.distance > 0.3:
            print("\n  Classes with high coupling:")
            for cls in metrics.classes:
                if len(cls.dependencies) > 3:
                    print(f"    - {cls.name}: {len(cls.dependencies)} dependencies")


def main() -> int:
    """Main function."""
    # Find project root
    project_root = Path(__file__).parent.parent
    ledzephyr_root = project_root / "ledzephyr"

    if not ledzephyr_root.exists():
        print(f"Error: {ledzephyr_root} does not exist", file=sys.stderr)
        return 1

    print("Measuring coupling and cohesion...")

    # Find all Python files
    files = find_python_files(ledzephyr_root)

    # Analyze coupling
    classes = analyze_coupling(files)

    if not classes:
        print("No classes found to analyze")
        return 0

    # Calculate package metrics
    package_metrics = calculate_package_metrics(classes)

    # Print report
    print_metrics_report(package_metrics)

    # Check for violations
    violations = []
    for package_name, metrics in package_metrics.items():
        if metrics.distance > 0.5:
            violations.append((package_name, metrics.distance))

    if violations:
        print("\n❌ Packages with poor coupling/cohesion balance:")
        for package, distance in violations:
            print(f"  - {package}: distance = {distance:.2f}")
        return 1
    else:
        print("\n✅ All packages have acceptable coupling/cohesion metrics")
        return 0


if __name__ == "__main__":
    sys.exit(main())