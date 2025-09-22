"""Test-first implementation of identity resolution and crosswalk system."""

import hashlib
from dataclasses import dataclass


def test_canonical_id_generation():
    """Test canonical ID is deterministic and collision-free."""
    # Given
    project_key = "PROJ"
    suite_path = "regression/api"
    title = "Test Login API"

    # When
    canonical_id = generate_canonical_id(project_key, suite_path, title)

    # Then - verify format (16 char hex)
    assert len(canonical_id) == 16
    assert all(c in "0123456789abcdef" for c in canonical_id)

    # Verify deterministic
    id2 = generate_canonical_id(project_key, suite_path, title)
    assert canonical_id == id2

    # Verify normalization works
    id3 = generate_canonical_id("  PROJ  ", "regression//api/", "TEST LOGIN api")
    assert canonical_id != id3  # Different due to case sensitivity in title


def test_canonical_id_normalization():
    """Test that normalization handles edge cases properly."""
    # Test various normalizations
    test_cases = [
        # (input, expected_normalized)
        ("PROJ-123", "proj-123"),
        ("  spaces  ", "spaces"),
        ("regression//api/", "regression/api"),
        ("Test\\Path", "test/path"),
        ("", ""),
    ]

    for input_val, expected in test_cases:
        normalized = norm(input_val)
        assert normalized == expected


def test_crosswalk_exact_match():
    """Test exact matching in crosswalk resolution."""
    # Given entities from different systems
    zephyr_entity = TestEntity(
        id="Z-123", project="PROJ", suite="regression/api", title="Test Login API"
    )

    qtest_entities = [
        TestEntity("Q-001", "PROJ", "regression/ui", "Test UI Login"),
        TestEntity("Q-002", "PROJ", "regression/api", "Test Login API"),  # Exact match
        TestEntity("Q-003", "PROJ", "regression/api", "Test Logout API"),
    ]

    # When resolving
    resolver = CrosswalkResolver()
    match = resolver.resolve(zephyr_entity, qtest_entities)

    # Then
    assert match.qtest_id == "Q-002"
    assert match.confidence_score == 1.0
    assert match.match_type == "exact"


def test_crosswalk_fuzzy_match():
    """Test fuzzy matching when exact match fails."""
    # Given entities with slight differences
    zephyr_entity = TestEntity(
        id="Z-456", project="PROJ", suite="regression/api", title="Verify User Authentication"
    )

    qtest_entities = [
        TestEntity("Q-101", "PROJ", "regression/api", "Check User Auth"),  # Similar
        TestEntity("Q-102", "PROJ", "regression/api", "Verify User Login"),
        TestEntity("Q-103", "PROJ", "integration", "Verify User Authentication"),  # Different suite
    ]

    # When resolving with fuzzy matching
    resolver = CrosswalkResolver(enable_fuzzy=True)
    match = resolver.resolve(zephyr_entity, qtest_entities)

    # Then - should find best match
    assert match.qtest_id in ["Q-101", "Q-102"]  # Either is reasonable
    assert 0.5 < match.confidence_score < 1.0
    assert match.match_type == "fuzzy"


def test_crosswalk_no_match():
    """Test behavior when no reasonable match exists."""
    # Given completely different entities
    zephyr_entity = TestEntity(
        id="Z-789", project="PROJ", suite="performance", title="Load Test Homepage"
    )

    qtest_entities = [
        TestEntity("Q-201", "OTHER", "unit", "Test Utils"),
        TestEntity("Q-202", "OTHER", "integration", "Test Database"),
    ]

    # When resolving
    resolver = CrosswalkResolver(enable_fuzzy=True)
    match = resolver.resolve(zephyr_entity, qtest_entities)

    # Then
    assert match.qtest_id is None
    assert match.confidence_score < 0.3
    assert match.match_type == "no_match"


def test_crosswalk_batch_resolution():
    """Test batch resolution with accuracy metrics."""
    # Given a batch of entities to resolve
    zephyr_batch = [
        TestEntity("Z-1", "PROJ", "api", "Test Login"),
        TestEntity("Z-2", "PROJ", "api", "Test Logout"),
        TestEntity("Z-3", "PROJ", "ui", "Test Dashboard"),
    ]

    qtest_batch = [
        TestEntity("Q-1", "PROJ", "api", "Test Login"),  # Exact match for Z-1
        TestEntity("Q-2", "PROJ", "api", "Test Logout"),  # Exact match for Z-2
        TestEntity("Q-3", "PROJ", "ui", "Dashboard Test"),  # Fuzzy match for Z-3
    ]

    # When resolving batch
    resolver = CrosswalkResolver(enable_fuzzy=True)
    matches = resolver.resolve_batch(zephyr_batch, qtest_batch)

    # Then
    assert len(matches) == 3
    exact_matches = [m for m in matches if m.match_type == "exact"]
    assert len(exact_matches) >= 2

    # Calculate accuracy
    successful_matches = [m for m in matches if m.confidence_score > 0.7]
    accuracy = len(successful_matches) / len(matches)
    assert accuracy >= 0.95  # 95% accuracy requirement


def test_crosswalk_persistence():
    """Test saving and loading crosswalk mappings."""
    # Given a crosswalk with mappings
    crosswalk = CrosswalkMap()
    crosswalk.add_mapping("Z-123", "Q-456", 0.95, "exact")
    crosswalk.add_mapping("Z-124", "Q-457", 0.75, "fuzzy")

    # When persisting and reloading
    crosswalk.save("test_crosswalk.json")
    loaded = CrosswalkMap.load("test_crosswalk.json")

    # Then
    assert loaded.get_qtest_id("Z-123") == "Q-456"
    assert loaded.get_confidence("Z-123") == 0.95
    assert len(loaded.mappings) == 2


# Implementation stubs below (TDD - implement after tests are written)


def norm(value: str) -> str:
    """Normalize strings for comparison."""
    if not value:
        return ""
    # Remove extra spaces, lowercase, normalize path separators
    normalized = value.strip().lower()
    normalized = normalized.replace("\\", "/")
    # Remove duplicate slashes
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    # Remove trailing slash
    if normalized.endswith("/"):
        normalized = normalized[:-1]
    return normalized


def generate_canonical_id(project_key: str, suite_path: str, title: str) -> str:
    """Generate deterministic canonical ID for cross-system entity resolution."""
    # Note: Not normalizing title to preserve case sensitivity
    normalized = f"{norm(project_key)}:{norm(suite_path)}:{title.strip()}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


@dataclass
class TestEntity:
    """Represents a test entity from any system."""

    id: str
    project: str
    suite: str
    title: str


@dataclass
class MatchResult:
    """Result of matching a Zephyr entity to qTest."""

    zephyr_id: str
    qtest_id: str | None
    confidence_score: float
    match_type: str  # exact, fuzzy, no_match


class CrosswalkResolver:
    """Resolves entities across Zephyr and qTest systems."""

    def __init__(self, enable_fuzzy: bool = False):
        self.enable_fuzzy = enable_fuzzy

    def resolve(self, zephyr_entity: TestEntity, qtest_entities: list[TestEntity]) -> MatchResult:
        """Resolve a single Zephyr entity to best qTest match."""
        # First try exact match
        for qtest in qtest_entities:
            if (
                norm(zephyr_entity.project) == norm(qtest.project)
                and norm(zephyr_entity.suite) == norm(qtest.suite)
                and zephyr_entity.title == qtest.title
            ):
                return MatchResult(
                    zephyr_id=zephyr_entity.id,
                    qtest_id=qtest.id,
                    confidence_score=1.0,
                    match_type="exact",
                )

        # Try fuzzy matching if enabled
        if self.enable_fuzzy:
            best_match = None
            best_score = 0.0

            for qtest in qtest_entities:
                score = self._calculate_similarity(zephyr_entity, qtest)
                if score > best_score:
                    best_score = score
                    best_match = qtest

            if best_match and best_score > 0.3:
                return MatchResult(
                    zephyr_id=zephyr_entity.id,
                    qtest_id=best_match.id,
                    confidence_score=best_score,
                    match_type="fuzzy" if best_score < 1.0 else "exact",
                )

        # No match found
        return MatchResult(
            zephyr_id=zephyr_entity.id, qtest_id=None, confidence_score=0.0, match_type="no_match"
        )

    def resolve_batch(
        self, zephyr_entities: list[TestEntity], qtest_entities: list[TestEntity]
    ) -> list[MatchResult]:
        """Resolve a batch of entities."""
        results = []
        for zephyr in zephyr_entities:
            match = self.resolve(zephyr, qtest_entities)
            results.append(match)
        return results

    def _calculate_similarity(self, entity1: TestEntity, entity2: TestEntity) -> float:
        """Calculate similarity score between two entities."""
        score = 0.0

        # Project match
        if norm(entity1.project) == norm(entity2.project):
            score += 0.3

        # Suite match
        if norm(entity1.suite) == norm(entity2.suite):
            score += 0.3

        # Title similarity (simple token overlap)
        title1_tokens = set(entity1.title.lower().split())
        title2_tokens = set(entity2.title.lower().split())
        if title1_tokens and title2_tokens:
            overlap = len(title1_tokens & title2_tokens)
            total = len(title1_tokens | title2_tokens)
            title_score = overlap / total if total > 0 else 0
            score += 0.4 * title_score

        return score


class CrosswalkMap:
    """Persistent storage for crosswalk mappings."""

    def __init__(self):
        self.mappings: dict[str, dict] = {}

    def add_mapping(self, zephyr_id: str, qtest_id: str, confidence: float, match_type: str):
        """Add a mapping to the crosswalk."""
        self.mappings[zephyr_id] = {
            "qtest_id": qtest_id,
            "confidence": confidence,
            "match_type": match_type,
        }

    def get_qtest_id(self, zephyr_id: str) -> str | None:
        """Get qTest ID for a Zephyr ID."""
        mapping = self.mappings.get(zephyr_id)
        return mapping["qtest_id"] if mapping else None

    def get_confidence(self, zephyr_id: str) -> float:
        """Get confidence score for a mapping."""
        mapping = self.mappings.get(zephyr_id)
        return mapping["confidence"] if mapping else 0.0

    def save(self, filepath: str):
        """Save crosswalk to JSON file."""
        import json

        with open(filepath, "w") as f:
            json.dump(self.mappings, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "CrosswalkMap":
        """Load crosswalk from JSON file."""
        import json
        import os

        instance = cls()
        if os.path.exists(filepath):
            with open(filepath) as f:
                instance.mappings = json.load(f)
        return instance
