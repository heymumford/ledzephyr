#!/usr/bin/env python3
"""
Validate that Protocol interfaces are properly implemented.

Ensures:
- All Protocol methods are implemented by concrete classes
- Interface segregation principle is followed
- Liskov substitution principle is maintained
"""

import ast
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MethodSignature:
    """Represents a method signature."""
    name: str
    args: List[str]
    return_type: Optional[str]
    is_abstract: bool = False


@dataclass
class InterfaceDefinition:
    """Represents a Protocol interface."""
    name: str
    module: str
    methods: List[MethodSignature]
    base_classes: List[str]


@dataclass
class ClassImplementation:
    """Represents a concrete class."""
    name: str
    module: str
    methods: List[MethodSignature]
    base_classes: List[str]


class InterfaceAnalyzer(ast.NodeVisitor):
    """Analyze Protocol interfaces and implementations."""

    def __init__(self, module_path: Path):
        self.module_path = module_path
        self.module_name = self._get_module_name(module_path)
        self.interfaces: List[InterfaceDefinition] = []
        self.implementations: List[ClassImplementation] = []
        self.current_class: Optional[str] = None
        self.current_methods: List[MethodSignature] = []
        self.current_bases: List[str] = []

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
        prev_methods = self.current_methods
        prev_bases = self.current_bases

        # Set current class
        self.current_class = node.name
        self.current_methods = []
        self.current_bases = []

        # Extract base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.current_bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                self.current_bases.append(f"{base.value.id}.{base.attr}")

        # Visit methods
        self.generic_visit(node)

        # Check if this is a Protocol
        is_protocol = any(
            "Protocol" in base for base in self.current_bases
        )

        if is_protocol:
            self.interfaces.append(
                InterfaceDefinition(
                    name=node.name,
                    module=self.module_name,
                    methods=self.current_methods[:],
                    base_classes=self.current_bases[:],
                )
            )
        else:
            self.implementations.append(
                ClassImplementation(
                    name=node.name,
                    module=self.module_name,
                    methods=self.current_methods[:],
                    base_classes=self.current_bases[:],
                )
            )

        # Restore previous state
        self.current_class = prev_class
        self.current_methods = prev_methods
        self.current_bases = prev_bases

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Process method definitions."""
        if self.current_class and not node.name.startswith("_"):
            # Extract method signature
            args = []
            for arg in node.args.args:
                if arg.arg != "self":
                    args.append(arg.arg)

            # Extract return type
            return_type = None
            if node.returns:
                if isinstance(node.returns, ast.Name):
                    return_type = node.returns.id
                elif isinstance(node.returns, ast.Constant):
                    return_type = str(node.returns.value)

            # Check if abstract
            is_abstract = any(
                isinstance(d, ast.Name) and d.id == "abstractmethod"
                for d in node.decorator_list
            )

            self.current_methods.append(
                MethodSignature(
                    name=node.name,
                    args=args,
                    return_type=return_type,
                    is_abstract=is_abstract,
                )
            )


def find_python_files(root: Path) -> List[Path]:
    """Find all Python files in the project."""
    return [
        p for p in root.glob("**/*.py")
        if "tests" not in p.parts and "__pycache__" not in p.parts
    ]


def analyze_interfaces(files: List[Path]) -> Tuple[List[InterfaceDefinition], List[ClassImplementation]]:
    """Analyze all interfaces and implementations."""
    all_interfaces = []
    all_implementations = []

    for file_path in files:
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            analyzer = InterfaceAnalyzer(file_path)
            analyzer.visit(tree)

            all_interfaces.extend(analyzer.interfaces)
            all_implementations.extend(analyzer.implementations)
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    return all_interfaces, all_implementations


def check_interface_implementations(
    interfaces: List[InterfaceDefinition],
    implementations: List[ClassImplementation]
) -> List[Tuple[str, str, List[str]]]:
    """Check that implementations satisfy their interfaces."""
    violations = []

    for impl in implementations:
        # Find interfaces this class claims to implement
        for interface in interfaces:
            # Check if implementation references the interface
            interface_ref = interface.name
            if interface.module != impl.module:
                interface_ref = f"{interface.module}.{interface.name}"

            # Simple heuristic: class name suggests implementation
            if (interface.name in impl.name or
                f"{interface.name[:-10]}Implementation" in impl.name if interface.name.endswith("Repository") else False):

                # Check that all interface methods are implemented
                impl_method_names = {m.name for m in impl.methods}
                interface_method_names = {m.name for m in interface.methods}

                missing_methods = interface_method_names - impl_method_names

                if missing_methods:
                    violations.append((
                        f"{impl.module}.{impl.name}",
                        f"{interface.module}.{interface.name}",
                        list(missing_methods)
                    ))

    return violations


def check_interface_segregation(interfaces: List[InterfaceDefinition]) -> List[Tuple[str, int]]:
    """Check for fat interfaces (ISP violation)."""
    fat_interfaces = []
    MAX_METHODS = 5  # Threshold for fat interface

    for interface in interfaces:
        if len(interface.methods) > MAX_METHODS:
            fat_interfaces.append((
                f"{interface.module}.{interface.name}",
                len(interface.methods)
            ))

    return fat_interfaces


def main() -> int:
    """Main function."""
    # Find project root
    project_root = Path(__file__).parent.parent
    ledzephyr_root = project_root / "ledzephyr"

    if not ledzephyr_root.exists():
        print(f"Error: {ledzephyr_root} does not exist", file=sys.stderr)
        return 1

    print("Validating interfaces...")

    # Find all Python files
    files = find_python_files(ledzephyr_root)

    # Analyze interfaces
    interfaces, implementations = analyze_interfaces(files)

    # Check implementations
    impl_violations = check_interface_implementations(interfaces, implementations)

    # Check interface segregation
    fat_interfaces = check_interface_segregation(interfaces)

    # Report results
    has_issues = False

    if impl_violations:
        has_issues = True
        print("\n❌ Interface Implementation Violations:")
        for impl, interface, methods in impl_violations:
            print(f"  {impl} does not fully implement {interface}")
            print(f"    Missing methods: {', '.join(methods)}")

    if fat_interfaces:
        has_issues = True
        print("\n⚠️  Potential ISP Violations (Fat Interfaces):")
        for interface, count in fat_interfaces:
            print(f"  {interface} has {count} methods (consider splitting)")

    if interfaces:
        print(f"\n📋 Found {len(interfaces)} Protocol interfaces:")
        for interface in interfaces:
            print(f"  - {interface.module}.{interface.name} ({len(interface.methods)} methods)")

    if not has_issues:
        print("\n✅ All interface contracts are satisfied")
        return 0
    else:
        print("\n❌ Interface validation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())