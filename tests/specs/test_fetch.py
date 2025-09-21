"""Test API specification fetching and validation."""

import json
from unittest.mock import Mock, patch

import pytest

from migrate_specs import config, fetch


@pytest.mark.unit
def test_fetch_and_cache_specs(tmp_path, monkeypatch):
    """Test fetching and caching API specs with validation."""
    # Arrange - redirect cache dir to temporary path
    monkeypatch.setattr(fetch, "SPECS_DIR", tmp_path)

    # Create a minimal valid OpenAPI spec for testing
    mock_spec_content = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {"/test": {"get": {"responses": {"200": {"description": "Success"}}}}},
    }

    # Mock HTTP client to avoid real network calls
    with patch("migrate_specs.fetch.httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.content = json.dumps(mock_spec_content).encode()
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Act & Assert - test each configured spec
        for spec in config.ALL:
            # Test caching behavior
            cache_path = fetch.fetch_spec(spec)

            # Verify file was created
            assert cache_path.is_file()
            assert cache_path.name == spec.filename

            # Verify content is parseable and contains OpenAPI marker
            content = cache_path.read_text()
            assert "openapi" in content.lower()

            # Verify it's valid JSON/YAML
            parsed = json.loads(content)
            assert "openapi" in parsed or "swagger" in parsed


@pytest.mark.unit
def test_fetch_spec_uses_cache_when_exists(tmp_path, monkeypatch):
    """Test that fetch_spec uses cached file when it exists."""
    # Arrange
    monkeypatch.setattr(fetch, "SPECS_DIR", tmp_path)
    test_spec = config.JIRA

    # Create cached file
    cached_file = tmp_path / test_spec.filename
    cached_content = {
        "openapi": "3.0.0",
        "info": {"title": "Cached API", "version": "1.0.0"},
        "paths": {},
    }
    cached_file.write_text(json.dumps(cached_content))

    # Mock HTTP client - should not be called
    with patch("migrate_specs.fetch.httpx.Client") as mock_client:
        # Act
        result_path = fetch.fetch_spec(test_spec)

        # Assert
        assert result_path == cached_file
        mock_client.assert_not_called()  # Should use cache, not make HTTP request


@pytest.mark.unit
def test_fetch_spec_validates_openapi(tmp_path, monkeypatch):
    """Test that fetch_spec validates OpenAPI specification."""
    # Arrange
    monkeypatch.setattr(fetch, "SPECS_DIR", tmp_path)
    test_spec = config.JIRA

    # Create invalid spec content
    invalid_spec = {"invalid": "not an openapi spec"}

    with patch("migrate_specs.fetch.httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.content = json.dumps(invalid_spec).encode()
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Act & Assert - should raise validation error
        with pytest.raises(Exception):  # openapi-spec-validator will raise
            fetch.fetch_spec(test_spec)
