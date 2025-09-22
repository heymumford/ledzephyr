"""Identity resolution and crosswalk system for Zephyr to qTest migration."""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


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
class CanonicalIdentity:
    """Represents a unified identity across systems."""

    canonical_id: str
    zephyr_id: str | None = None
    qtest_id: str | None = None
    jira_key: str | None = None
    project: str | None = None
    suite: str | None = None
    title: str | None = None


@dataclass
class TestEntity:
    """Represents a test entity from any system."""

    id: str
    project: str
    suite: str
    title: str
    system: str  # zephyr or qtest
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class MatchResult:
    """Result of matching a Zephyr entity to qTest."""

    zephyr_id: str
    qtest_id: str | None
    confidence_score: float
    match_type: str  # exact, fuzzy, no_match
    canonical_id: str | None = None


class CrosswalkResolver:
    """Resolves entities across Zephyr and qTest systems."""

    def __init__(self, enable_fuzzy: bool = True, min_confidence: float = 0.7):
        self.enable_fuzzy = enable_fuzzy
        self.min_confidence = min_confidence

    def resolve(self, zephyr_entity: TestEntity, qtest_entities: list[TestEntity]) -> MatchResult:
        """Resolve a single Zephyr entity to best qTest match."""
        # Generate canonical ID for Zephyr entity
        canonical_id = generate_canonical_id(
            zephyr_entity.project, zephyr_entity.suite, zephyr_entity.title
        )

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
                    canonical_id=canonical_id,
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

            if best_match and best_score >= self.min_confidence:
                return MatchResult(
                    zephyr_id=zephyr_entity.id,
                    qtest_id=best_match.id,
                    confidence_score=best_score,
                    match_type="fuzzy",
                    canonical_id=canonical_id,
                )

        # No match found
        return MatchResult(
            zephyr_id=zephyr_entity.id,
            qtest_id=None,
            confidence_score=0.0,
            match_type="no_match",
            canonical_id=canonical_id,
        )

    def resolve_batch(
        self, zephyr_entities: list[TestEntity], qtest_entities: list[TestEntity]
    ) -> tuple[list[MatchResult], float]:
        """Resolve a batch of entities and return accuracy."""
        results = []
        for zephyr in zephyr_entities:
            match = self.resolve(zephyr, qtest_entities)
            results.append(match)

        # Calculate accuracy
        successful = sum(1 for r in results if r.confidence_score >= self.min_confidence)
        accuracy = successful / len(results) if results else 0.0

        return results, accuracy

    def _calculate_similarity(self, entity1: TestEntity, entity2: TestEntity) -> float:
        """Calculate similarity score between two entities."""
        score = 0.0

        # Project match (30% weight)
        if norm(entity1.project) == norm(entity2.project):
            score += 0.3

        # Suite match (30% weight)
        if norm(entity1.suite) == norm(entity2.suite):
            score += 0.3

        # Title similarity (40% weight)
        title_sim = self._title_similarity(entity1.title, entity2.title)
        score += 0.4 * title_sim

        return score

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity using token overlap."""
        # Tokenize and normalize
        tokens1 = set(title1.lower().split())
        tokens2 = set(title2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        return intersection / union if union > 0 else 0.0


class CrosswalkMap:
    """Persistent storage for crosswalk mappings."""

    def __init__(self, filepath: str | None = None):
        self.filepath = filepath or "crosswalk_map.json"
        self.mappings: dict[str, dict] = {}
        self.canonical_map: dict[str, CanonicalIdentity] = {}

    def add_mapping(self, match_result: MatchResult):
        """Add a mapping from match result."""
        self.mappings[match_result.zephyr_id] = {
            "qtest_id": match_result.qtest_id,
            "confidence": match_result.confidence_score,
            "match_type": match_result.match_type,
            "canonical_id": match_result.canonical_id,
        }

        # Update canonical map
        if match_result.canonical_id:
            if match_result.canonical_id not in self.canonical_map:
                self.canonical_map[match_result.canonical_id] = CanonicalIdentity(
                    canonical_id=match_result.canonical_id
                )

            canonical = self.canonical_map[match_result.canonical_id]
            canonical.zephyr_id = match_result.zephyr_id
            if match_result.qtest_id:
                canonical.qtest_id = match_result.qtest_id

    def get_qtest_id(self, zephyr_id: str) -> str | None:
        """Get qTest ID for a Zephyr ID."""
        mapping = self.mappings.get(zephyr_id)
        return mapping["qtest_id"] if mapping else None

    def get_canonical_id(self, system_id: str) -> str | None:
        """Get canonical ID for any system ID."""
        # Check direct mapping
        mapping = self.mappings.get(system_id)
        if mapping:
            return mapping.get("canonical_id")

        # Check reverse mapping in canonical map
        for canonical_id, identity in self.canonical_map.items():
            if identity.zephyr_id == system_id or identity.qtest_id == system_id:
                return canonical_id

        return None

    def get_confidence(self, zephyr_id: str) -> float:
        """Get confidence score for a mapping."""
        mapping = self.mappings.get(zephyr_id)
        return mapping["confidence"] if mapping else 0.0

    def get_statistics(self) -> dict[str, int]:
        """Get mapping statistics."""
        stats = {
            "total_mappings": len(self.mappings),
            "exact_matches": sum(1 for m in self.mappings.values() if m["match_type"] == "exact"),
            "fuzzy_matches": sum(1 for m in self.mappings.values() if m["match_type"] == "fuzzy"),
            "no_matches": sum(1 for m in self.mappings.values() if m["match_type"] == "no_match"),
            "high_confidence": sum(1 for m in self.mappings.values() if m["confidence"] >= 0.9),
            "canonical_entities": len(self.canonical_map),
        }
        return stats

    def save(self):
        """Save crosswalk to JSON file."""
        data = {
            "mappings": self.mappings,
            "canonical_map": {k: asdict(v) for k, v in self.canonical_map.items()},
        }

        # Ensure directory exists
        Path(self.filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Load crosswalk from JSON file."""
        if os.path.exists(self.filepath):
            with open(self.filepath) as f:
                data = json.load(f)
                self.mappings = data.get("mappings", {})

                # Reconstruct canonical map
                canonical_data = data.get("canonical_map", {})
                self.canonical_map = {}
                for canonical_id, identity_dict in canonical_data.items():
                    self.canonical_map[canonical_id] = CanonicalIdentity(**identity_dict)
