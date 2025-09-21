"""
School of Fish Integration Testing

Each 'school' represents orthogonal test concerns that can run in parallel:
- Atomic: 1 clear goal per kata
- Testable: validation built-in
- Composable: leads to next layer
- Orthogonal: schools don't interfere with each other

School Categories:
- API School: External API integration patterns
- Data School: Data flow and transformation
- Config School: Configuration and environment
- Performance School: Timing and resource usage
- Security School: Authentication and permissions
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class SchoolStatus(Enum):
    PENDING = "pending"
    SWIMMING = "swimming"  # running
    SCHOOLED = "schooled"  # completed
    SCATTERED = "scattered"  # failed


@dataclass
class Kata:
    """Atomic test unit within a school."""

    name: str
    goal: str
    test_func: callable
    dependencies: list[str] = None
    timeout_seconds: float = 30.0


@dataclass
class School:
    """Collection of related kata that test orthogonal concerns."""

    name: str
    description: str
    katas: list[Kata]
    parallel_safe: bool = True

    @property
    def size(self) -> int:
        return len(self.katas)


class SchoolRunner(Protocol):
    """Protocol for running schools in parallel."""

    async def swim_school(self, school: School) -> dict[str, bool]:
        """Run all katas in a school, return results."""
        ...

    async def swim_all(self, schools: list[School]) -> dict[str, dict[str, bool]]:
        """Run all schools in parallel."""
        ...


# School registry for discovery
SCHOOLS: dict[str, School] = {}


def register_school(school: School) -> School:
    """Register a school for parallel execution."""
    SCHOOLS[school.name] = school
    return school


def get_orthogonal_schools() -> list[School]:
    """Get all registered schools that can run in parallel."""
    # Import all schools to trigger registration
    from . import api_school, config_school, data_school, performance_school  # noqa: F401

    return [s for s in SCHOOLS.values() if s.parallel_safe]
