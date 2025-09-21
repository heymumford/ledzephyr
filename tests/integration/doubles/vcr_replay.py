"""
VCR-style replay mechanism for deterministic E2E testing.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class VCRCassette:
    """Represents a single request-response recording."""

    def __init__(self, request: dict[str, Any], response: dict[str, Any]):
        self.request = request
        self.response = response
        self.request_hash = self._compute_request_hash(request)

    def _compute_request_hash(self, request: dict[str, Any]) -> str:
        """Compute deterministic hash of request for matching."""
        # Create canonical representation
        canonical = {
            "method": request.get("method", "GET"),
            "url": request.get("url", ""),
            "params": json.dumps(request.get("params", {}), sort_keys=True),
            "body": (
                json.dumps(request.get("body", {}), sort_keys=True) if request.get("body") else None
            ),
        }

        # Hash the canonical form
        hasher = hashlib.sha256()
        hasher.update(json.dumps(canonical, sort_keys=True).encode())
        return hasher.hexdigest()

    def matches(self, request: dict[str, Any]) -> bool:
        """Check if this cassette matches the given request."""
        request_hash = self._compute_request_hash(request)
        return request_hash == self.request_hash

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request": self.request,
            "response": self.response,
            "request_hash": self.request_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VCRCassette":
        """Create from dictionary."""
        return cls(data["request"], data["response"])


class VCRReplay:
    """VCR-style replay system for E2E tests."""

    def __init__(self, cassette_dir: str = "tests/cassettes", mode: str = "replay"):
        """
        Initialize VCR replay.

        Args:
            cassette_dir: Directory to store cassettes
            mode: 'record' to capture new, 'replay' to use existing, 'record_once' to record if missing
        """
        self.cassette_dir = Path(cassette_dir)
        self.cassette_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.cassettes: list[VCRCassette] = []
        self.current_cassette_name: str | None = None
        self.replay_index = 0

        # Statistics
        self.hits = 0
        self.misses = 0
        self.recordings = 0

    def use_cassette(self, name: str) -> "VCRReplay":
        """Load or prepare a cassette for use."""
        self.current_cassette_name = name
        cassette_path = self.cassette_dir / f"{name}.json"

        if cassette_path.exists() and self.mode != "record":
            # Load existing cassette
            with open(cassette_path) as f:
                data = json.load(f)
                self.cassettes = [VCRCassette.from_dict(c) for c in data["cassettes"]]
                print(f"Loaded {len(self.cassettes)} recordings from {name}")
        else:
            # Start with empty cassette
            self.cassettes = []
            if self.mode == "replay":
                print(f"Warning: No cassette found for {name}, will fail on requests")

        self.replay_index = 0
        return self

    def request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """Make a request, either replaying or recording."""
        request = {
            "method": method,
            "url": url,
            "headers": kwargs.get("headers", {}),
            "params": kwargs.get("params", {}),
            "body": kwargs.get("json") or kwargs.get("data"),
        }

        if self.mode == "replay":
            return self._replay_request(request)
        elif self.mode == "record":
            return self._record_request(request, kwargs.get("backend"))
        elif self.mode == "record_once":
            # Try replay first, record if not found
            try:
                return self._replay_request(request)
            except ValueError:
                return self._record_request(request, kwargs.get("backend"))
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _replay_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Replay a recorded request."""
        # Sequential matching (for deterministic tests)
        if self.replay_index < len(self.cassettes):
            cassette = self.cassettes[self.replay_index]
            if cassette.matches(request):
                self.replay_index += 1
                self.hits += 1
                return cassette.response

        # Fallback to searching all cassettes
        for cassette in self.cassettes:
            if cassette.matches(request):
                self.hits += 1
                return cassette.response

        self.misses += 1
        raise ValueError(f"No matching cassette found for {request['method']} {request['url']}")

    def _record_request(self, request: dict[str, Any], backend: Any) -> dict[str, Any]:
        """Record a new request."""
        if not backend:
            raise ValueError("Backend required for recording mode")

        # Make real request to backend
        response = backend.request(
            method=request["method"],
            url=request["url"],
            headers=request.get("headers"),
            params=request.get("params"),
            json_data=request.get("body"),
        )

        # Record the interaction
        cassette = VCRCassette(request, response)
        self.cassettes.append(cassette)
        self.recordings += 1

        # Auto-save after each recording
        self._save_cassette()

        return response

    def _save_cassette(self):
        """Save current cassette to disk."""
        if not self.current_cassette_name:
            return

        cassette_path = self.cassette_dir / f"{self.current_cassette_name}.json"

        data = {
            "version": "1.0",
            "recorded_at": datetime.now().isoformat(),
            "cassettes": [c.to_dict() for c in self.cassettes],
        }

        with open(cassette_path, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)

        print(f"Saved {len(self.cassettes)} recordings to {self.current_cassette_name}")

    def save(self):
        """Explicitly save current cassette."""
        self._save_cassette()

    def get_stats(self) -> dict[str, int]:
        """Get replay statistics."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "recordings": self.recordings,
            "total_cassettes": len(self.cassettes),
        }

    def clear(self):
        """Clear current cassette."""
        self.cassettes = []
        self.replay_index = 0
        self.hits = 0
        self.misses = 0
        self.recordings = 0


class VCRTransport:
    """Transport adapter that uses VCR for replay/recording."""

    def __init__(self, vcr: VCRReplay, backend: Any | None = None):
        """
        Initialize VCR transport.

        Args:
            vcr: VCR replay instance
            backend: Backend for recording mode (stub, fake, or real API)
        """
        self.vcr = vcr
        self.backend = backend

    def request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """Make request through VCR."""
        if self.vcr.mode in ["record", "record_once"]:
            kwargs["backend"] = self.backend

        return self.vcr.request(method, url, **kwargs)

    def get_stats(self) -> dict[str, int]:
        """Get VCR statistics."""
        return self.vcr.get_stats()
