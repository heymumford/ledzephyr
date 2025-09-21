#!/usr/bin/env python3
"""
Check architectural boundaries and compliance with clean architecture.

Validates:
- Layer boundaries are respected
- No infrastructure details leak into domain
- Proper use of dependency injection
- Framework independence in core layers
"""

import ast
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass
import re


# Framework imports that should not appear in domain/application layers
FRAMEWORK_IMPORTS = {
    "httpx", "requests", "aiohttp",  # HTTP clients
    "sqlalchemy", "django", "flask",  # Web frameworks
    "fastapi", "starlette", "uvicorn",  # ASGI frameworks
    "boto3", "azure",  # Cloud SDKs
    "redis", "pymongo", "psycopg2",  # Database drivers
    "celery", "rq",  # Task queues
}

# Infrastructure patterns that should not appear in domain
INFRASTRUCTURE_PATTERNS = [
    re.compile(r"\.get\(.*https?://"),  # Direct HTTP calls
    re.compile(r"SELECT.*FROM"),  # SQL queries
    re.compile(r"@app\.(get|post|put|delete)"),  # Web route decorators
    re.compile(r"os\.environ"),  # Direct environment access
    re.compile(r"open\(.*\)"),  # Direct file I/O
]

# Allowed standard library imports in domain
ALLOWED_STDLIB = {
    "typing", "dataclasses", "enum", "datetime", "uuid",
    "decimal", "fractions", "collections", "itertools",
    "functools", "abc", "re", "json", "math",
}


@dataclass
class ArchitecturalViolation:
    """Represents an architectural violation."""
    file_path: Path
    line_number: int
    violation_type: str
    message: str
    severity: str  # "error", "warning"


class ArchitectureAnalyzer(ast.NodeVisitor):
    """Analyze code for architectural violations."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.violations: List[ArchitecturalViolation] = []
        self.layer = self._determine_layer(file_path)
        self.imports: Set[str] = set()

    def _determine_layer(self, path: Path) -> str:
        """Determine which architectural layer a file belongs to."""
        parts = path.parts
        if "domain" in parts:
            return "domain"
        elif "application" in parts:
            return "application"
        elif "infrastructure" in parts:
            return "infrastructure"
        elif "presentation" in parts or "cli" in str(path):
            return "presentation"
        return "unknown"

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements."""
        for alias in node.names:
            self.imports.add(alias.name)
            self._check_import(alias.name, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from...import statements."""
        if node.module:
            self.imports.add(node.module)
            self._check_import(node.module, node.lineno)

    def _check_import(self, module: str, line: int) -> None:
        """Check if an import violates architectural rules."""
        # Domain layer checks
        if self.layer == "domain":
            # No framework imports allowed
            base_module = module.split(".")[0]
            if base_module in FRAMEWORK_IMPORTS:
                self.violations.append(
                    ArchitecturalViolation(
                        file_path=self.file_path,
                        line_number=line,
                        violation_type="framework_dependency",
                        message=f"Domain layer cannot import framework '{module}'",
                        severity="error"
                    )
                )

            # Only allowed stdlib and internal imports
            if not (base_module in ALLOWED_STDLIB or
                   base_module == "ledzephyr" or
                   base_module == "__future__"):
                self.violations.append(
                    ArchitecturalViolation(
                        file_path=self.file_path,
                        line_number=line,
                        violation_type="forbidden_import",
                        message=f"Domain layer cannot import '{module}'",
                        severity="warning"
                    )
                )

        # Application layer checks
        elif self.layer == "application":
            base_module = module.split(".")[0]
            if base_module in FRAMEWORK_IMPORTS:
                self.violations.append(
                    ArchitecturalViolation(
                        file_path=self.file_path,
                        line_number=line,
                        violation_type="framework_dependency",
                        message=f"Application layer should not directly import framework '{module}'",
                        severity="warning"
                    )
                )

    def visit_Call(self, node: ast.Call) -> None:
        """Check for direct infrastructure calls."""
        # Check for environment variable access
        if (isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == "os" and
            node.func.attr == "environ"):
            if self.layer in ("domain", "application"):
                self.violations.append(
                    ArchitecturalViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type="direct_environment_access",
                        message=f"{self.layer.capitalize()} layer cannot directly access os.environ",
                        severity="error"
                    )
                )

        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Check for direct file I/O."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                if isinstance(item.context_expr.func, ast.Name):
                    if item.context_expr.func.id == "open":
                        if self.layer == "domain":
                            self.violations.append(
                                ArchitecturalViolation(
                                    file_path=self.file_path,
                                    line_number=node.lineno,
                                    violation_type="direct_io",
                                    message="Domain layer cannot perform direct file I/O",
                                    severity="error"
                                )
                            )
        self.generic_visit(node)


def find_python_files(root: Path) -> List[Path]:
    """Find all Python files in the project."""
    return [
        p for p in root.glob("**/*.py")
        if "tests" not in p.parts and "__pycache__" not in p.parts
    ]


def check_file_content(file_path: Path, layer: str) -> List[ArchitecturalViolation]:
    """Check file content for infrastructure patterns."""
    violations = []

    if layer not in ("domain", "application"):
        return violations

    try:
        with open(file_path, "r") as f:
            content = f.read()
            lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern in INFRASTRUCTURE_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        ArchitecturalViolation(
                            file_path=file_path,
                            line_number=i,
                            violation_type="infrastructure_pattern",
                            message=f"Infrastructure pattern found in {layer} layer",
                            severity="error"
                        )
                    )
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return violations


def check_dependency_injection(files: List[Path]) -> List[ArchitecturalViolation]:
    """Check for proper use of dependency injection."""
    violations = []

    for file_path in files:
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            # Look for classes that might be using concrete dependencies
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check __init__ methods
                    for item in node.body:
                        if (isinstance(item, ast.FunctionDef) and
                            item.name == "__init__"):
                            # Look for direct instantiation of external services
                            for stmt in ast.walk(item):
                                if isinstance(stmt, ast.Call):
                                    if isinstance(stmt.func, ast.Name):
                                        # Check if creating infrastructure objects
                                        if stmt.func.id in ["JiraClient", "ZephyrClient", "QTestClient"]:
                                            analyzer = ArchitectureAnalyzer(file_path)
                                            layer = analyzer._determine_layer(file_path)
                                            if layer in ("domain", "application"):
                                                violations.append(
                                                    ArchitecturalViolation(
                                                        file_path=file_path,
                                                        line_number=stmt.lineno,
                                                        violation_type="concrete_dependency",
                                                        message=f"Use dependency injection instead of creating {stmt.func.id} directly",
                                                        severity="warning"
                                                    )
                                                )
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    return violations


def main() -> int:
    """Main function."""
    # Find project root
    project_root = Path(__file__).parent.parent
    ledzephyr_root = project_root / "ledzephyr"

    if not ledzephyr_root.exists():
        print(f"Error: {ledzephyr_root} does not exist", file=sys.stderr)
        return 1

    print("Checking architectural boundaries...")

    # Find all Python files
    files = find_python_files(ledzephyr_root)

    all_violations = []

    # Analyze each file
    for file_path in files:
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            analyzer = ArchitectureAnalyzer(file_path)
            analyzer.visit(tree)
            all_violations.extend(analyzer.violations)

            # Check content patterns
            content_violations = check_file_content(file_path, analyzer.layer)
            all_violations.extend(content_violations)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    # Check dependency injection
    di_violations = check_dependency_injection(files)
    all_violations.extend(di_violations)

    # Report results
    if all_violations:
        errors = [v for v in all_violations if v.severity == "error"]
        warnings = [v for v in all_violations if v.severity == "warning"]

        if errors:
            print(f"\n❌ Found {len(errors)} architectural errors:")
            for v in errors:
                print(f"  {v.file_path}:{v.line_number}")
                print(f"    {v.violation_type}: {v.message}")

        if warnings:
            print(f"\n⚠️  Found {len(warnings)} architectural warnings:")
            for v in warnings:
                print(f"  {v.file_path}:{v.line_number}")
                print(f"    {v.violation_type}: {v.message}")

        if errors:
            print("\n❌ Architecture check failed")
            return 1
        else:
            print("\n⚠️  Architecture check passed with warnings")
            return 0
    else:
        print("✅ No architectural violations found")
        return 0


if __name__ == "__main__":
    sys.exit(main())