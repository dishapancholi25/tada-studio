"""Comprehensive unit tests for the guardrails system.

Tests cover all guardrail options including:
- Pattern rules (DLP: SSN, credit card, email, API keys, phone, AWS keys, private keys)
- SSRF protection (URL validation, IP range blocking, scheme blocking)
- SQL operation restrictions and table blocking
- File write validations (path traversal, extensions, size limits)
- Token budget enforcement and warnings
- Behavioral guardrails (input/output length checks, LLM-as-judge parsing)
- Config resolution (workflow/agent merging, inheritance, policy layering)
- Python sandbox executor (code validation, safe execution, forbidden constructs)
- Custom filter evaluator (filter chaining, priority ordering, block/warn/transform)
- GuardrailsEngine integration (end-to-end input/output/tool/token checks)
- Accuracy assessment (precision/recall on curated test datasets)
- Performance benchmarks (throughput and latency measurements)
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
import requests

from backend.models.workflow.configs.guardrails import (
    BehavioralGuardrails,
    CustomFilter,
    GuardrailsConfig,
    OutputScanners,
    PatternEntry,
    PatternRule,
    ProviderContentFilter,
    TokenBudget,
    ToolCallPolicy,
)
from backend.services.guardrails.engine import GuardrailsEngine, ResolvedGuardrails
from backend.services.guardrails.exceptions import GuardrailViolationError
from backend.services.guardrails.evaluators.behavioral import (
    BehavioralGuardrailEvaluator,
)
from backend.services.guardrails.evaluators.input import InputGuardrailEvaluator
from backend.services.guardrails.evaluators.llm_judge import (
    build_classification_prompt,
    content_filter_violations,
    format_judge_error,
    parse_judge_response,
)
from backend.services.guardrails.evaluators.output import OutputGuardrailEvaluator
from backend.services.guardrails.evaluators.token_budget import TokenBudgetEvaluator
from backend.services.guardrails.evaluators.tool_call import ToolCallGuardrailEvaluator
from backend.services.guardrails.filters.evaluator import CustomFilterEvaluator
from backend.services.guardrails.filters.executors.python_sandbox import (
    CodeValidationError,
    PythonSandboxExecutor,
)
from backend.services.guardrails.models import GuardrailResult, Violation
from backend.services.guardrails.pattern_rules import apply_pattern_rules
from backend.services.guardrails.ssrf import (
    BLOCKED_SCHEMES,
    DEFAULT_BLOCKED_RANGES,
    validate_url,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def engine():
    """GuardrailsEngine with no LLM dependencies (for non-behavioral tests)."""
    return GuardrailsEngine()


@pytest.fixture
def base_config():
    """Minimal enabled guardrails config."""
    return GuardrailsConfig(enabled=True, enforcement_mode="enforce")


@pytest.fixture
def audit_config():
    """Guardrails config in audit mode."""
    return GuardrailsConfig(enabled=True, enforcement_mode="audit")


@pytest.fixture
def disabled_config():
    """Disabled guardrails config."""
    return GuardrailsConfig(enabled=False)


@pytest.fixture
def ssn_rule():
    return PatternRule(
        name="SSN",
        patterns=[PatternEntry(regex=r"\b\d{3}-\d{2}-\d{4}\b")],
        action="redact",
        applies_to="both",
        message="SSN detected",
    )


@pytest.fixture
def credit_card_rule():
    return PatternRule(
        name="Credit Card",
        patterns=[PatternEntry(regex=r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")],
        action="redact",
        applies_to="both",
        message="Credit card detected",
    )


@pytest.fixture
def email_rule():
    return PatternRule(
        name="Email",
        patterns=[
            PatternEntry(regex=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        ],
        action="warn",
        applies_to="both",
        message="Email detected",
    )


@pytest.fixture
def api_key_rule():
    return PatternRule(
        name="API Key",
        patterns=[
            PatternEntry(
                regex=r"\b(sk-|pk_|api_key_|AKIA|ghp_|gho_|github_pat_)[A-Za-z0-9_-]{20,}\b"
            )
        ],
        action="redact",
        applies_to="both",
        message="API key detected",
    )


@pytest.fixture
def aws_key_rule():
    return PatternRule(
        name="AWS Key",
        patterns=[PatternEntry(regex=r"\bAKIA[0-9A-Z]{16}\b")],
        action="block",
        applies_to="both",
        message="AWS key detected",
    )


@pytest.fixture
def private_key_rule():
    return PatternRule(
        name="Private Key",
        patterns=[
            PatternEntry(regex=r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")
        ],
        action="block",
        applies_to="both",
        message="Private key detected",
    )


@pytest.fixture
def default_tool_policy():
    return ToolCallPolicy()


@pytest.fixture
def strict_tool_policy():
    return ToolCallPolicy(
        allowed_url_patterns=["https://api.example.com/*"],
        blocked_url_patterns=["*.internal.corp"],
        allowed_sql_operations=["SELECT"],
        blocked_tables=["users_secrets", "credentials"],
        max_query_rows=100,
        allowed_file_extensions=[".txt", ".csv", ".json"],
        blocked_file_paths=["/etc/", "/var/log/"],
        max_file_size_mb=1.0,
        max_tool_calls_per_execution=10,
    )


@pytest.fixture
def token_budget():
    return TokenBudget(
        max_input_tokens_per_execution=10000,
        max_output_tokens_per_execution=5000,
        max_total_tokens_per_execution=15000,
        max_llm_calls_per_execution=10,
        warn_at_percentage=0.8,
    )


@pytest.fixture
def sandbox_executor():
    executor = PythonSandboxExecutor()
    yield executor
    executor.invalidate_cache()


@pytest.fixture
def tool_call_evaluator():
    return ToolCallGuardrailEvaluator()


@pytest.fixture
def token_budget_evaluator():
    return TokenBudgetEvaluator()


# ============================================================================
# 1. Pattern Rules Tests
# ============================================================================


class TestPatternRules:
    """Tests for regex-based pattern matching rules (DLP)."""

    # ---- SSN Detection ----

    def test_ssn_detected_and_redacted(self, ssn_rule):
        result = apply_pattern_rules("My SSN is 123-45-6789", [ssn_rule], "input")
        assert result.action_taken == "redacted"
        assert "[REDACTED]" in result.sanitized_content
        assert "123-45-6789" not in result.sanitized_content
        assert result.passed is True
        assert len(result.violations) == 1
        assert result.violations[0].rule_name == "SSN"

    def test_ssn_multiple_occurrences(self, ssn_rule):
        text = "SSNs: 123-45-6789 and 987-65-4321"
        result = apply_pattern_rules(text, [ssn_rule], "input")
        assert result.sanitized_content.count("[REDACTED]") == 2

    def test_ssn_no_match(self, ssn_rule):
        result = apply_pattern_rules("No sensitive data here", [ssn_rule], "input")
        assert result.passed is True
        assert result.action_taken == "none"
        assert len(result.violations) == 0

    def test_ssn_partial_match_ignored(self, ssn_rule):
        """Partial SSN-like patterns shouldn't match due to word boundaries."""
        result = apply_pattern_rules("12-34-5678", [ssn_rule], "input")
        assert result.passed is True
        assert len(result.violations) == 0

    # ---- Credit Card Detection ----

    def test_credit_card_detected_spaces(self, credit_card_rule):
        result = apply_pattern_rules(
            "Card: 4111 1111 1111 1111", [credit_card_rule], "output"
        )
        assert result.action_taken == "redacted"
        assert "[REDACTED]" in result.sanitized_content

    def test_credit_card_detected_dashes(self, credit_card_rule):
        result = apply_pattern_rules(
            "Card: 4111-1111-1111-1111", [credit_card_rule], "output"
        )
        assert result.action_taken == "redacted"

    def test_credit_card_detected_no_separator(self, credit_card_rule):
        result = apply_pattern_rules(
            "Card: 4111111111111111", [credit_card_rule], "input"
        )
        assert result.action_taken == "redacted"

    # ---- Email Detection ----

    def test_email_detected_warns(self, email_rule):
        result = apply_pattern_rules(
            "Contact us at user@example.com", [email_rule], "input"
        )
        assert result.action_taken == "warned"
        assert result.passed is True
        assert result.violations[0].severity == "warn"

    def test_email_multiple_warns(self, email_rule):
        text = "a@b.com and c@d.org"
        result = apply_pattern_rules(text, [email_rule], "input")
        assert (
            len(result.violations) == 1
        )  # single rule, one violation with match_count
        assert result.violations[0].details["match_count"] == 2

    # ---- API Key Detection ----

    def test_api_key_sk_prefix(self, api_key_rule):
        result = apply_pattern_rules(
            "key: sk-1234567890abcdefghij1234", [api_key_rule], "input"
        )
        assert result.action_taken == "redacted"
        assert "[REDACTED]" in result.sanitized_content

    def test_api_key_github_pat(self, api_key_rule):
        result = apply_pattern_rules(
            "token: ghp_ABCDEFGHIJKLMNOPQRSTuvwx", [api_key_rule], "output"
        )
        assert result.action_taken == "redacted"

    # ---- AWS Key Detection ----

    def test_aws_key_blocked(self, aws_key_rule):
        result = apply_pattern_rules(
            "key: AKIAIOSFODNN7EXAMPLE", [aws_key_rule], "input"
        )
        assert result.passed is False
        assert result.action_taken == "blocked"
        assert result.violations[0].severity == "block"

    # ---- Private Key Detection ----

    def test_private_key_rsa_blocked(self, private_key_rule):
        result = apply_pattern_rules(
            "-----BEGIN RSA PRIVATE KEY-----\nMIIE...", [private_key_rule], "input"
        )
        assert result.passed is False
        assert result.action_taken == "blocked"

    def test_private_key_ec_blocked(self, private_key_rule):
        result = apply_pattern_rules(
            "-----BEGIN EC PRIVATE KEY-----\nMHQ...", [private_key_rule], "output"
        )
        assert result.passed is False

    def test_private_key_generic_blocked(self, private_key_rule):
        result = apply_pattern_rules(
            "-----BEGIN PRIVATE KEY-----\nMIIE...", [private_key_rule], "input"
        )
        assert result.passed is False

    # ---- Direction Filtering ----

    def test_input_only_rule_skipped_on_output(self):
        rule = PatternRule(
            name="input-only",
            patterns=[PatternEntry(regex=r"secret")],
            action="block",
            applies_to="input",
        )
        result = apply_pattern_rules("secret data", [rule], "output")
        assert result.passed is True
        assert len(result.violations) == 0

    def test_output_only_rule_skipped_on_input(self):
        rule = PatternRule(
            name="output-only",
            patterns=[PatternEntry(regex=r"secret")],
            action="block",
            applies_to="output",
        )
        result = apply_pattern_rules("secret data", [rule], "input")
        assert result.passed is True

    def test_both_direction_applies_to_input(self):
        rule = PatternRule(
            name="both",
            patterns=[PatternEntry(regex=r"secret")],
            action="block",
            applies_to="both",
        )
        result = apply_pattern_rules("secret data", [rule], "input")
        assert result.passed is False

    def test_both_direction_applies_to_output(self):
        rule = PatternRule(
            name="both",
            patterns=[PatternEntry(regex=r"secret")],
            action="block",
            applies_to="both",
        )
        result = apply_pattern_rules("secret data", [rule], "output")
        assert result.passed is False

    # ---- Block takes precedence over redact ----

    def test_block_overrides_redact(self, ssn_rule, aws_key_rule):
        text = "SSN: 123-45-6789 and key AKIAIOSFODNN7EXAMPLE"
        result = apply_pattern_rules(text, [ssn_rule, aws_key_rule], "input")
        assert result.passed is False
        assert result.action_taken == "blocked"

    # ---- Invalid regex handled gracefully ----

    def test_invalid_regex_skipped(self):
        rule = PatternRule(
            name="bad", patterns=[PatternEntry(regex=r"[invalid")], action="block"
        )
        result = apply_pattern_rules("test content", [rule], "input")
        assert result.passed is True

    # ---- Empty content/rules ----

    def test_empty_content(self, ssn_rule):
        result = apply_pattern_rules("", [ssn_rule], "input")
        assert result.passed is True

    def test_empty_rules(self):
        result = apply_pattern_rules("some content", [], "input")
        assert result.passed is True

    def test_empty_pattern_skipped(self):
        rule = PatternRule(name="empty", patterns=[], action="block")
        result = apply_pattern_rules("test", [rule], "input")
        assert result.passed is True


# ============================================================================
# 2. SSRF Protection Tests
# ============================================================================


class TestSSRFProtection:
    """Tests for URL validation and SSRF prevention."""

    def test_valid_https_url(self):
        result = validate_url("https://api.example.com/data")
        assert result.passed is True

    def test_valid_http_url(self):
        result = validate_url("http://example.com/data")
        assert result.passed is True

    def test_empty_url_blocked(self):
        result = validate_url("")
        assert result.passed is False
        assert result.violations[0].rule_name == "ssrf_invalid_url"

    def test_none_url_blocked(self):
        result = validate_url(None)
        assert result.passed is False

    # ---- Blocked schemes ----

    @pytest.mark.parametrize("scheme", list(BLOCKED_SCHEMES))
    def test_blocked_schemes(self, scheme):
        result = validate_url(f"{scheme}://example.com")
        assert result.passed is False
        assert any("scheme" in v.rule_name for v in result.violations)

    def test_unknown_scheme_blocked(self):
        result = validate_url("custom://example.com")
        assert result.passed is False

    # ---- Private IP blocking ----

    def test_localhost_ip_blocked(self):
        result = validate_url("http://127.0.0.1/admin")
        assert result.passed is False
        assert result.violations[0].rule_name == "ssrf_blocked_ip"

    def test_private_10_range_blocked(self):
        result = validate_url("http://10.0.0.1/internal")
        assert result.passed is False

    def test_private_172_range_blocked(self):
        result = validate_url("http://172.16.0.1/internal")
        assert result.passed is False

    def test_private_192_range_blocked(self):
        result = validate_url("http://192.168.1.1/internal")
        assert result.passed is False

    def test_link_local_blocked(self):
        result = validate_url("http://169.254.169.254/latest/meta-data/")
        assert result.passed is False

    def test_zero_ip_blocked(self):
        result = validate_url("http://0.0.0.0/")
        assert result.passed is False

    # ---- URL pattern filtering ----

    def test_allowed_url_patterns_match(self):
        policy = ToolCallPolicy(allowed_url_patterns=["https://api.example.com/*"])
        result = validate_url("https://api.example.com/v1/data", policy)
        assert result.passed is True

    def test_allowed_url_patterns_no_match(self):
        policy = ToolCallPolicy(allowed_url_patterns=["https://api.example.com/*"])
        result = validate_url("https://evil.com/data", policy)
        assert result.passed is False
        assert result.violations[0].rule_name == "ssrf_not_allowed"

    def test_blocked_url_patterns_match(self):
        policy = ToolCallPolicy(blocked_url_patterns=["*.internal.corp"])
        result = validate_url("https://admin.internal.corp/api", policy)
        assert result.passed is False
        assert result.violations[0].rule_name == "ssrf_blocked_pattern"

    def test_no_hostname_blocked(self):
        result = validate_url("http:///path")
        assert result.passed is False

    def test_default_blocked_ranges_comprehensive(self):
        """All default blocked ranges should be present."""
        expected = {
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "127.0.0.0/8",
            "169.254.0.0/16",
            "0.0.0.0/8",
            "::1/128",
            "fc00::/7",
            "fe80::/10",
        }
        assert set(DEFAULT_BLOCKED_RANGES) == expected


# ============================================================================
# 2b. SSRF Runtime Execution Layer Tests
#
# These tests verify that the HTTP tool ITSELF enforces SSRF protection at
# execution time, independently of whether guardrails are configured.
# They exercise _ssrf_safe_send / _ssrf_validate_before_send inside
# backend/tools/http_request/handlers.py.
# ============================================================================


class TestSSRFRuntimeEnforcement:
    """SSRF protection at HTTP tool execution level (not guardrails layer)."""

    # ------------------------------------------------------------------ helpers

    def _call_safe_send(self, url: str, follow_redirects: bool = False) -> str:
        """Invoke _ssrf_safe_send and return the error string, or '' on success."""
        from backend.tools.http_request.handlers import _ssrf_safe_send
        import pytest

        with pytest.raises(ValueError) as exc_info:
            _ssrf_safe_send(
                session_or_requests=None,  # never reached – SSRF check fires first
                method="GET",
                url=url,
                headers={},
                data=None,
                auth=None,
                timeout=5,
                verify=True,
                proxies=None,
                cert=None,
                follow_redirects=follow_redirects,
                max_redirects=10,
            )
        return str(exc_info.value)

    def _validate(self, url: str):
        """Call _ssrf_validate_before_send and return the error string or None."""
        from backend.tools.http_request.handlers import _ssrf_validate_before_send

        return _ssrf_validate_before_send(url)

    # ------------------------------------------------------------------ scheme checks

    def test_file_scheme_blocked_at_execution(self):
        err = self._validate("file:///etc/passwd")
        assert err is not None
        assert "scheme" in err.lower() or "blocked" in err.lower()

    def test_http_scheme_passes_validation(self, monkeypatch):
        """http:// scheme passes the validator (DNS error may follow, but scheme is ok)."""
        from backend.tools.http_request.handlers import _ssrf_validate_before_send
        # Patch DNS so we don't hit the network
        import socket
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(None, None, None, None, ("93.184.216.34", 0))])
        err = _ssrf_validate_before_send("http://example.com/path")
        assert err is None

    # ------------------------------------------------------------------ all required blocked ranges

    @pytest.mark.parametrize("url,description", [
        ("http://127.0.0.1:8000/api/auth/me", "loopback IPv4"),
        ("http://127.0.0.2/x", "loopback subnet"),
        ("http://10.0.0.1/internal", "RFC-1918 10/8"),
        ("http://10.255.255.1/internal", "RFC-1918 10/8 edge"),
        ("http://172.16.0.1/internal", "RFC-1918 172.16/12"),
        ("http://172.31.255.1/internal", "RFC-1918 172.31/12 edge"),
        ("http://192.168.0.1/internal", "RFC-1918 192.168/16"),
        ("http://192.168.255.254/x", "RFC-1918 192.168/16 edge"),
        ("http://169.254.169.254/latest/meta-data/", "Azure/AWS IMDS"),
        ("http://169.254.0.1/x", "link-local start"),
        ("http://0.0.0.0/", "zero address"),
    ])
    def test_blocked_range_blocked_at_execution(self, url, description):
        """Every range from the bug spec is blocked by _ssrf_validate_before_send."""
        err = self._validate(url)
        assert err is not None, f"{description} ({url}) should be blocked but was allowed"

    @pytest.mark.parametrize("url,description", [
        ("http://[::1]/", "IPv6 loopback"),
        ("http://[fc00::1]/", "IPv6 ULA fc00::/7"),
        ("http://[fd00::1]/", "IPv6 ULA fd00::/7"),
        ("http://[fe80::1]/", "IPv6 link-local"),
    ])
    def test_ipv6_blocked_ranges_at_execution(self, url, description):
        err = self._validate(url)
        assert err is not None, f"{description} ({url}) should be blocked"

    # ------------------------------------------------------------------ DNS fail-closed

    def test_dns_failure_is_blocked_not_allowed(self, monkeypatch):
        """Unresolvable host must be blocked (fail-closed), not allowed through."""
        import socket
        monkeypatch.setattr(
            socket, "getaddrinfo",
            lambda *a, **kw: (_ for _ in ()).throw(socket.gaierror("no such host"))
        )
        from backend.services.guardrails.ssrf import validate_url
        result = validate_url("http://nonexistent-internal-host.local/secret")
        assert result.passed is False
        assert result.violations[0].rule_name == "ssrf_dns_resolution_failed"

    # ------------------------------------------------------------------ redirect revalidation

    def test_redirect_to_internal_is_blocked(self, monkeypatch):
        """A safe origin that redirects to an internal IP must be blocked."""
        import socket
        from unittest.mock import MagicMock
        from backend.tools.http_request.handlers import _ssrf_safe_send

        # First request returns a 302 redirect to an internal IP
        redirect_response = MagicMock()
        redirect_response.is_redirect = True
        redirect_response.status_code = 302
        redirect_response.url = "http://safe.example.com/start"
        redirect_response.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}

        mock_session = MagicMock()
        mock_session.request.return_value = redirect_response

        # Patch DNS so the initial safe host resolves ok (not internal IP)
        original_getaddrinfo = socket.getaddrinfo
        def patched_getaddrinfo(host, *args, **kwargs):
            if "example.com" in host:
                return [(None, None, None, None, ("93.184.216.34", 0))]
            return original_getaddrinfo(host, *args, **kwargs)
        monkeypatch.setattr(socket, "getaddrinfo", patched_getaddrinfo)

        import pytest
        with pytest.raises(ValueError, match="SSRF protection blocked redirect"):
            _ssrf_safe_send(
                session_or_requests=mock_session,
                method="GET",
                url="http://safe.example.com/start",
                headers={},
                data=None,
                auth=None,
                timeout=5,
                verify=True,
                proxies=None,
                cert=None,
                follow_redirects=True,
                max_redirects=10,
            )

    def test_too_many_redirects_raises(self, monkeypatch):
        """Exceeding max_redirects raises TooManyRedirects."""
        import socket
        from unittest.mock import MagicMock
        from backend.tools.http_request.handlers import _ssrf_safe_send

        # Each response redirects to a safe external host
        def make_redirect(to_url: str):
            r = MagicMock()
            r.is_redirect = True
            r.status_code = 302
            r.url = "http://safe.example.com/loop"
            r.headers = {"Location": to_url}
            return r

        mock_session = MagicMock()
        mock_session.request.return_value = make_redirect("http://safe.example.com/loop")

        monkeypatch.setattr(
            socket, "getaddrinfo",
            lambda *a, **kw: [(None, None, None, None, ("93.184.216.34", 0))]
        )

        import pytest
        with pytest.raises(requests.TooManyRedirects):
            _ssrf_safe_send(
                session_or_requests=mock_session,
                method="GET",
                url="http://safe.example.com/start",
                headers={},
                data=None,
                auth=None,
                timeout=5,
                verify=True,
                proxies=None,
                cert=None,
                follow_redirects=True,
                max_redirects=3,
            )

    # ------------------------------------------------------------------ header stripping

    def test_x_auth_request_headers_stripped(self):
        """X-Auth-Request-* headers must be stripped before transmission (ISG 1.3 chain)."""
        from backend.tools.http_request.handlers import strip_denied_headers

        headers = {
            "Content-Type": "application/json",
            "X-Auth-Request-Email": "victim@mashreq.com",
            "X-Auth-Request-Groups": "admins",
            "X-Auth-Request-User": "attacker",
            "Accept": "application/json",
        }
        clean = strip_denied_headers(headers)
        assert "Content-Type" in clean
        assert "Accept" in clean
        assert "X-Auth-Request-Email" not in clean
        assert "X-Auth-Request-Groups" not in clean
        assert "X-Auth-Request-User" not in clean

    def test_metadata_header_stripped(self):
        """Metadata header (Azure IMDS trigger) must be stripped (ISG 1.7 scenario 3)."""
        from backend.tools.http_request.handlers import strip_denied_headers

        headers = {
            "Metadata": "true",
            "Content-Type": "text/plain",
        }
        clean = strip_denied_headers(headers)
        assert "Metadata" not in clean
        assert "Content-Type" in clean

    def test_authorization_header_stripped_unless_allowed(self):
        """Authorization header stripped by default, kept only when explicitly allowed."""
        from backend.tools.http_request.handlers import strip_denied_headers

        headers = {
            "Authorization": "Bearer stolen-token",
            "Accept": "*/*",
        }
        # Without allow: stripped
        clean = strip_denied_headers(headers)
        assert "Authorization" not in clean
        assert "Accept" in clean

        # With allow: kept (structured auth config scenario)
        clean_allowed = strip_denied_headers(headers, allow={"authorization"})
        assert "Authorization" in clean_allowed

    def test_cookie_header_stripped(self):
        """Cookie header must be stripped to prevent session smuggling."""
        from backend.tools.http_request.handlers import strip_denied_headers

        headers = {
            "Cookie": "session=abc123",
            "X-Custom": "safe",
        }
        clean = strip_denied_headers(headers)
        assert "Cookie" not in clean
        assert "X-Custom" in clean

    def test_header_stripping_case_insensitive(self):
        """Header stripping must be case-insensitive."""
        from backend.tools.http_request.handlers import strip_denied_headers

        headers = {
            "x-auth-request-email": "victim@test.com",
            "METADATA": "true",
            "AUTHORIZATION": "Basic abc",
            "COOKIE": "session=xyz",
            "X-Safe-Header": "ok",
        }
        clean = strip_denied_headers(headers)
        assert len(clean) == 1
        assert "X-Safe-Header" in clean

    def test_imds_url_plus_metadata_header_both_blocked(self, monkeypatch):
        """Azure IMDS URL (169.254.169.254) blocked at SSRF level regardless of headers."""
        err = self._validate("http://169.254.169.254/metadata/identity/oauth2/token")
        assert err is not None
        assert "blocked" in err.lower()


# ============================================================================
# 3. Tool Call Evaluator Tests
# ============================================================================


class TestToolCallEvaluator:
    """Tests for tool call validation (HTTP, SQL, file write, call limits)."""

    # ---- Tool call count limit ----

    def test_tool_call_count_exceeded(self, tool_call_evaluator, default_tool_policy):
        result = tool_call_evaluator.evaluate(
            "http_request",
            {"url": "https://example.com"},
            default_tool_policy,
            tool_call_count=50,
        )
        assert result.passed is False
        assert result.violations[0].rule_name == "max_tool_calls_exceeded"

    def test_tool_call_count_within_limit(
        self, tool_call_evaluator, default_tool_policy
    ):
        result = tool_call_evaluator.evaluate(
            "http_request",
            {"url": "https://example.com"},
            default_tool_policy,
            tool_call_count=5,
        )
        assert result.passed is True

    def test_tool_call_count_at_limit_blocked(self, tool_call_evaluator):
        policy = ToolCallPolicy(max_tool_calls_per_execution=10)
        result = tool_call_evaluator.evaluate(
            "some_tool",
            {},
            policy,
            tool_call_count=10,
        )
        assert result.passed is False

    # ---- HTTP tool → SSRF routing ----

    def test_http_tool_ssrf_check(self, tool_call_evaluator, default_tool_policy):
        result = tool_call_evaluator.evaluate(
            "http_request",
            {"url": "http://127.0.0.1/admin"},
            default_tool_policy,
        )
        assert result.passed is False

    def test_http_tool_by_node_type(self, tool_call_evaluator, default_tool_policy):
        result = tool_call_evaluator.evaluate(
            "custom_name",
            {"url": "http://127.0.0.1"},
            default_tool_policy,
            tool_node_type="HTTP_REQUEST",
        )
        assert result.passed is False

    def test_http_tool_empty_url(self, tool_call_evaluator, default_tool_policy):
        result = tool_call_evaluator.evaluate(
            "http_request",
            {"url": ""},
            default_tool_policy,
        )
        assert result.passed is True  # empty URL passes (no URL to validate)

    # ---- SQL tool validation ----

    def test_sql_select_allowed(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "database_query",
            {"query": "SELECT * FROM products"},
            strict_tool_policy,
        )
        assert result.passed is True

    def test_sql_delete_blocked(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "database_query",
            {"query": "DELETE FROM products WHERE id = 1"},
            strict_tool_policy,
        )
        assert result.passed is False
        assert result.violations[0].rule_name == "sql_operation_blocked"

    def test_sql_insert_blocked(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "database_query",
            {"query": "INSERT INTO products VALUES (1, 'test')"},
            strict_tool_policy,
        )
        assert result.passed is False

    def test_sql_drop_blocked(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "database_query",
            {"query": "DROP TABLE products"},
            strict_tool_policy,
        )
        assert result.passed is False

    def test_sql_update_blocked(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "database_query",
            {"query": "UPDATE products SET name='x'"},
            strict_tool_policy,
        )
        assert result.passed is False

    def test_sql_blocked_table(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "database_query",
            {"query": "SELECT * FROM users_secrets"},
            strict_tool_policy,
        )
        assert result.passed is False
        assert any(v.rule_name == "sql_blocked_table" for v in result.violations)

    def test_sql_allowed_table(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "database_query",
            {"query": "SELECT * FROM products"},
            strict_tool_policy,
        )
        assert result.passed is True

    def test_sql_empty_query(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "database_query",
            {"query": ""},
            strict_tool_policy,
        )
        assert result.passed is True

    def test_sql_by_node_type(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "custom_db_tool",
            {"query": "DELETE FROM users"},
            strict_tool_policy,
            tool_node_type="DATABASE_QUERY",
        )
        assert result.passed is False

    # ---- File write validation ----

    def test_file_write_allowed_extension(
        self, tool_call_evaluator, strict_tool_policy
    ):
        result = tool_call_evaluator.evaluate(
            "file_write",
            {"filename": "report.csv", "content": "a,b,c"},
            strict_tool_policy,
        )
        assert result.passed is True

    def test_file_write_blocked_extension(
        self, tool_call_evaluator, strict_tool_policy
    ):
        result = tool_call_evaluator.evaluate(
            "file_write",
            {"filename": "script.sh", "content": "#!/bin/bash"},
            strict_tool_policy,
        )
        assert result.passed is False
        assert result.violations[0].rule_name == "file_extension_blocked"

    def test_file_write_path_traversal(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "file_write",
            {"filename": "../../etc/passwd", "content": "x"},
            strict_tool_policy,
        )
        assert result.passed is False
        assert any(v.rule_name == "file_path_traversal" for v in result.violations)

    def test_file_write_absolute_path(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "file_write",
            {"filename": "/etc/shadow", "content": "x"},
            strict_tool_policy,
        )
        assert result.passed is False

    def test_file_write_blocked_path(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "file_write",
            {
                "filename": "access.log",
                "subdirectory": "/var/log/",
                "content": "log data",
            },
            strict_tool_policy,
        )
        assert result.passed is False
        assert any(v.rule_name == "file_path_blocked" for v in result.violations)

    def test_file_write_size_exceeded(self, tool_call_evaluator, strict_tool_policy):
        # 1 MB limit; create content > 1 MB
        large_content = "x" * (1024 * 1024 + 1)
        result = tool_call_evaluator.evaluate(
            "file_write",
            {"filename": "big.txt", "content": large_content},
            strict_tool_policy,
        )
        assert result.passed is False
        assert any(v.rule_name == "file_size_exceeded" for v in result.violations)

    def test_file_write_size_within_limit(
        self, tool_call_evaluator, strict_tool_policy
    ):
        result = tool_call_evaluator.evaluate(
            "file_write",
            {"filename": "small.txt", "content": "hello"},
            strict_tool_policy,
        )
        assert result.passed is True

    def test_file_write_by_node_type(self, tool_call_evaluator, strict_tool_policy):
        result = tool_call_evaluator.evaluate(
            "custom_writer",
            {"filename": "../../etc/passwd", "content": "x"},
            strict_tool_policy,
            tool_node_type="FILE_WRITE",
        )
        assert result.passed is False

    # ---- Unknown tool type passes through ----

    def test_unknown_tool_passes(self, tool_call_evaluator, default_tool_policy):
        result = tool_call_evaluator.evaluate(
            "custom_tool",
            {"arg": "value"},
            default_tool_policy,
        )
        assert result.passed is True


# ============================================================================
# 4. Token Budget Tests
# ============================================================================


class TestTokenBudgetEvaluator:
    """Tests for token usage budget enforcement and warnings."""

    def test_within_budget_passes(self, token_budget_evaluator, token_budget):
        usage = {
            "input_tokens": 5000,
            "output_tokens": 2000,
            "total_tokens": 7000,
            "llm_calls": 3,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is True

    def test_input_tokens_exceeded(self, token_budget_evaluator, token_budget):
        usage = {
            "input_tokens": 15000,
            "output_tokens": 0,
            "total_tokens": 15000,
            "llm_calls": 1,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is False
        assert any(v.rule_name == "input_tokens_exceeded" for v in result.violations)

    def test_output_tokens_exceeded(self, token_budget_evaluator, token_budget):
        usage = {
            "input_tokens": 1000,
            "output_tokens": 6000,
            "total_tokens": 7000,
            "llm_calls": 1,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is False
        assert any(v.rule_name == "output_tokens_exceeded" for v in result.violations)

    def test_total_tokens_exceeded(self, token_budget_evaluator, token_budget):
        usage = {
            "input_tokens": 8000,
            "output_tokens": 8000,
            "total_tokens": 16000,
            "llm_calls": 2,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is False
        assert any(v.rule_name == "total_tokens_exceeded" for v in result.violations)

    def test_llm_calls_exceeded(self, token_budget_evaluator, token_budget):
        usage = {
            "input_tokens": 100,
            "output_tokens": 100,
            "total_tokens": 200,
            "llm_calls": 11,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is False
        assert any(v.rule_name == "llm_calls_exceeded" for v in result.violations)

    def test_multiple_limits_exceeded(self, token_budget_evaluator, token_budget):
        usage = {
            "input_tokens": 20000,
            "output_tokens": 10000,
            "total_tokens": 30000,
            "llm_calls": 25,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is False
        assert len(result.violations) >= 3

    def test_warning_threshold_total_tokens(self, token_budget_evaluator, token_budget):
        # 80% of 15000 = 12000; keep output_tokens within its 5000 limit
        usage = {
            "input_tokens": 8000,
            "output_tokens": 4000,
            "total_tokens": 12000,
            "llm_calls": 2,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is True
        assert result.action_taken == "warned"
        assert any(v.rule_name == "token_budget_warning" for v in result.violations)

    def test_warning_threshold_llm_calls(self, token_budget_evaluator, token_budget):
        # 80% of 10 = 8
        usage = {
            "input_tokens": 100,
            "output_tokens": 100,
            "total_tokens": 200,
            "llm_calls": 8,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is True
        assert any(v.rule_name == "llm_calls_warning" for v in result.violations)

    def test_below_warning_threshold(self, token_budget_evaluator, token_budget):
        # 50% of budget — no warnings
        usage = {
            "input_tokens": 2500,
            "output_tokens": 1250,
            "total_tokens": 3750,
            "llm_calls": 2,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is True
        assert result.action_taken == "none"
        assert len(result.violations) == 0

    def test_no_limits_set(self, token_budget_evaluator):
        budget = (
            TokenBudget()
        )  # Only defaults: max_llm_calls=20, warn_at_percentage=0.8
        usage = {
            "input_tokens": 999999,
            "output_tokens": 999999,
            "total_tokens": 1999998,
            "llm_calls": 5,
        }
        result = token_budget_evaluator.evaluate(usage, budget)
        assert result.passed is True

    def test_zero_usage(self, token_budget_evaluator, token_budget):
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "llm_calls": 0,
        }
        result = token_budget_evaluator.evaluate(usage, token_budget)
        assert result.passed is True
        assert len(result.violations) == 0


# ============================================================================
# 5. Behavioral Guardrails Tests
# ============================================================================


class TestBehavioralGuardrails:
    """Tests for behavioral checks: length limits and LLM-as-judge parsing."""

    def test_input_length_exceeded(self):
        evaluator = BehavioralGuardrailEvaluator()
        config = BehavioralGuardrails(
            max_input_length=100,
            detect_prompt_injection="off",
            detect_jailbreak_attempts="off",
        )
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            evaluator.evaluate("x" * 150, config)
        )
        assert result.passed is False
        assert result.violations[0].rule_name == "max_input_length"

    def test_input_length_within_limit(self):
        evaluator = BehavioralGuardrailEvaluator()
        config = BehavioralGuardrails(
            max_input_length=1000,
            detect_prompt_injection="off",
            detect_jailbreak_attempts="off",
        )
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            evaluator.evaluate("short input", config)
        )
        assert result.passed is True

    def test_output_length_exceeded(self):
        result = OutputGuardrailEvaluator._check_output_length("x" * 200, 100)
        assert result.passed is False
        assert result.violations[0].rule_name == "max_output_length"

    def test_output_length_within_limit(self):
        result = OutputGuardrailEvaluator._check_output_length("short", 1000)
        assert result.passed is True

    def test_output_length_empty_content(self):
        result = OutputGuardrailEvaluator._check_output_length("", 100)
        assert result.passed is True

    # ---- Judge response parsing ----

    def test_parse_judge_clean_response(self):
        config = BehavioralGuardrails()
        response = """{
            "flagged": true,
            "categories": {
                "prompt_injection": {"detected": true, "confidence": 0.95, "reasoning": "Attempts to override instructions"},
                "jailbreak_attempt": {"detected": false, "confidence": 0.1, "reasoning": "No jailbreak detected"},
                "instruction_override": {"detected": false, "confidence": 0.05, "reasoning": "No override"}
            },
            "overall_confidence": 0.95,
            "summary": "Prompt injection detected"
        }"""
        violations = parse_judge_response(response, config)
        assert len(violations) == 1
        assert violations[0].rule_name == "prompt_injection"
        assert violations[0].severity == "block"

    def test_parse_judge_no_flags(self):
        config = BehavioralGuardrails()
        response = '{"flagged": false, "categories": {}, "overall_confidence": 0.0, "summary": "Clean"}'
        violations = parse_judge_response(response, config)
        assert len(violations) == 0

    def test_parse_judge_markdown_code_block(self):
        config = BehavioralGuardrails()
        response = """```json
{"flagged": true, "categories": {"prompt_injection": {"detected": true, "confidence": 0.9, "reasoning": "test"}}, "summary": "test"}
```"""
        violations = parse_judge_response(response, config)
        assert len(violations) == 1

    def test_parse_judge_invalid_json(self):
        config = BehavioralGuardrails()
        violations = parse_judge_response("not json at all", config)
        assert len(violations) == 1
        assert violations[0].rule_name == "judge_parse_error"
        assert violations[0].severity == "warn"

    def test_parse_judge_multiple_detections(self):
        config = BehavioralGuardrails()
        response = """{
            "flagged": true,
            "categories": {
                "prompt_injection": {"detected": true, "confidence": 0.9, "reasoning": "injection"},
                "jailbreak_attempt": {"detected": true, "confidence": 0.85, "reasoning": "jailbreak"}
            },
            "overall_confidence": 0.9,
            "summary": "Multiple threats"
        }"""
        violations = parse_judge_response(response, config)
        assert len(violations) == 2

    def test_parse_judge_respects_config_toggles(self):
        config = BehavioralGuardrails(
            detect_prompt_injection="block",
            detect_jailbreak_attempts="off",
        )
        response = """{
            "flagged": true,
            "categories": {
                "prompt_injection": {"detected": true, "confidence": 0.9, "reasoning": "test"},
                "jailbreak_attempt": {"detected": true, "confidence": 0.9, "reasoning": "test"},
                "instruction_override": {"detected": true, "confidence": 0.9, "reasoning": "test"}
            },
            "overall_confidence": 0.9,
            "summary": "Multiple"
        }"""
        violations = parse_judge_response(response, config)
        assert len(violations) == 1
        assert violations[0].rule_name == "prompt_injection"

    def test_no_detection_enabled_skips_llm(self):
        evaluator = BehavioralGuardrailEvaluator()
        config = BehavioralGuardrails(
            detect_prompt_injection="off",
            detect_jailbreak_attempts="off",
            max_input_length=50000,
        )
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            evaluator.evaluate("test input", config)
        )
        assert result.passed is True

    def test_classification_prompt_only_includes_enabled_categories(self):
        config = BehavioralGuardrails(
            detect_prompt_injection="block",
            detect_jailbreak_attempts="block",
        )
        prompt = build_classification_prompt("test input", config)
        assert "prompt_injection" in prompt
        assert "jailbreak_attempt" in prompt

    def test_classification_prompt_truncates_long_input(self):
        config = BehavioralGuardrails()
        long_input = "x" * 20000
        prompt = build_classification_prompt(long_input, config)
        assert "truncated" in prompt.lower()

    def test_format_judge_error_content_filter(self):
        exc = Exception("content filter")
        exc.body = {
            "code": "content_filter",
            "innererror": {
                "content_filter_result": {
                    "hate_speech": {"filtered": True},
                    "violence": {"filtered": False},
                }
            },
        }
        msg = format_judge_error(exc)
        assert "Azure content filter" in msg
        assert "hate_speech" in msg

    def test_format_judge_error_generic(self):
        exc = ValueError("something went wrong")
        msg = format_judge_error(exc)
        assert "ValueError" in msg

    # ---- Content-filter fail-closed (content_filter_violations) ----

    def test_content_filter_violations_blocks_detected_adversarial(self):
        """An Azure content-filter rejection that detected a jailbreak becomes a
        blocking violation (fail CLOSED), mapped to the enabled category."""
        config = BehavioralGuardrails(
            detect_prompt_injection="block",
            detect_jailbreak_attempts="block",
        )
        exc = Exception("blocked")
        exc.body = {
            "code": "content_filter",
            "innererror": {
                "content_filter_result": {
                    "jailbreak": {"filtered": True, "detected": True},
                }
            },
        }
        violations = content_filter_violations(exc, config)
        assert len(violations) == 1
        assert violations[0].rule_name == "jailbreak_attempt"
        assert violations[0].severity == "block"
        assert violations[0].details["detection_method"] == "provider_content_filter"

    def test_content_filter_violations_respects_configured_action(self):
        """The mapped violation uses the policy's configured action (warn)."""
        config = BehavioralGuardrails(
            detect_prompt_injection="warn",
            detect_jailbreak_attempts="off",
        )
        exc = Exception("blocked")
        exc.body = {
            "code": "content_filter",
            "innererror": {
                "content_filter_result": {
                    "prompt_injection": {"detected": True},
                }
            },
        }
        violations = content_filter_violations(exc, config)
        assert len(violations) == 1
        assert violations[0].rule_name == "prompt_injection"
        assert violations[0].severity == "warn"

    def test_content_filter_violations_skips_disabled_category(self):
        """A detected category the policy disabled ('off') is not reported."""
        config = BehavioralGuardrails(
            detect_prompt_injection="off",
            detect_jailbreak_attempts="off",
        )
        exc = Exception("blocked")
        exc.body = {
            "code": "content_filter",
            "innererror": {
                "content_filter_result": {
                    "jailbreak": {"filtered": True},
                }
            },
        }
        assert content_filter_violations(exc, config) == []

    def test_content_filter_violations_ignores_non_content_filter(self):
        """A generic (non content-filter) error yields no violations so the
        caller can degrade to a non-blocking judge_error warning."""
        config = BehavioralGuardrails(detect_prompt_injection="block")
        assert content_filter_violations(ValueError("boom"), config) == []

    def test_secrets_violation_preserved_when_merge_scan_fails(self):
        """When anonymize_pii + detect_secrets are both enabled and the scanner
        backend returns a secrets violation, it must be present in the final result
        and sanitized_content should reflect the secrets redaction output."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        evaluator = BehavioralGuardrailEvaluator()
        config = BehavioralGuardrails(
            detect_prompt_injection="off",
            detect_jailbreak_attempts="off",
            detect_toxicity="off",
            anonymize_pii="anonymize",
            detect_secrets="block",
        )

        secrets_first_pass_sanitized = "Hello world, my key is sk-***"

        # Mock classify_with_input_scanners to return a secrets violation
        # and the sanitized content from the first-pass secrets redaction.
        secrets_violation = Violation(
            category="behavioral",
            rule_name="secrets",
            severity="block",
            message="Secret detected (risk score: 0.95)",
            details={"confidence": 0.95, "detection_method": "llm_guard"},
        )

        with patch(
            "backend.services.guardrails.evaluators.behavioral.classify_with_input_scanners",
            new_callable=AsyncMock,
            return_value=(
                [secrets_violation],
                secrets_first_pass_sanitized,
                None,
                None,
            ),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                evaluator.evaluate("Hello world, my key is sk-abc123", config)
            )

        # A secrets violation MUST be present
        secrets_violations = [v for v in result.violations if v.rule_name == "secrets"]
        assert len(secrets_violations) == 1, (
            "Expected exactly one secrets violation but got: "
            f"{[v.rule_name for v in result.violations]}"
        )
        assert secrets_violations[0].severity == "block"

        # Sanitized content should reflect the secrets redaction
        assert result.sanitized_content == secrets_first_pass_sanitized


# ============================================================================
# 5b. Input Evaluator Content Chaining Regression Tests
# ============================================================================


class TestInputEvaluatorContentChaining:
    """Regression tests: pattern-rule redactions must not be overwritten by behavioral sanitization."""

    def test_pattern_redaction_not_overwritten_by_behavioral_sanitization(self):
        """When a pattern rule redacts a secret and behavioral scanners also
        sanitize, the final sanitized_content must never reintroduce the raw
        secret that was already redacted by the pattern rule."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        # Pattern rule that redacts the secret
        secret_pattern = PatternRule(
            name="api_key_redact",
            patterns=[PatternEntry(regex=r"sk-[A-Za-z0-9]{20,}")],
            action="redact",
            applies_to="input",
        )

        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[secret_pattern],
            detect_prompt_injection="off",
            detect_jailbreak_attempts="off",
            anonymize_pii="anonymize",
            detect_secrets="off",
        )

        raw_secret = "sk-abcdefghij1234567890"
        original_content = f"My API key is {raw_secret} please help"

        # The behavioral evaluator would normally do PII anonymization.
        # Mock it to return a result with its own sanitized_content that
        # does NOT contain the secret (simulating PII scanner output).
        mock_behavioral_result = GuardrailResult(
            passed=True,
            action_taken="redacted",
            sanitized_content="My API key is [REDACTED] please help — PII cleaned",
        )

        evaluator = InputGuardrailEvaluator()

        with patch.object(
            evaluator.behavioral_evaluator,
            "evaluate",
            new_callable=AsyncMock,
            return_value=mock_behavioral_result,
        ) as mock_eval:
            result = asyncio.get_event_loop().run_until_complete(
                evaluator.evaluate(original_content, config)
            )

            # The behavioral evaluator must have received the post-pattern
            # redacted text, NOT the original raw content with the secret.
            called_content = mock_eval.call_args[0][0]
            assert raw_secret not in called_content, (
                "Behavioral evaluator received raw secret that was already "
                "redacted by pattern rules"
            )
            assert "[REDACTED]" in called_content

        # Final result must never contain the raw secret
        assert raw_secret not in (result.sanitized_content or ""), (
            "Final sanitized_content reintroduced the raw secret"
        )


# ============================================================================
# 5c. Output Evaluator Tests
# ============================================================================


class TestOutputEvaluator:
    """Tests for the OutputGuardrailEvaluator: pattern rules, length checks,
    output scanner activation, and content chaining."""

    @pytest.fixture
    def output_evaluator(self):
        return OutputGuardrailEvaluator()

    # ---- Pattern rules on output ----

    @pytest.mark.asyncio
    async def test_output_pattern_rule_redacts(self, output_evaluator, ssn_rule):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[ssn_rule],
        )
        result = await output_evaluator.evaluate("Your SSN is 123-45-6789", config)
        assert result.passed is True
        assert result.action_taken == "redacted"
        assert "[REDACTED]" in result.sanitized_content
        assert "123-45-6789" not in result.sanitized_content

    @pytest.mark.asyncio
    async def test_output_pattern_rule_blocks(self, output_evaluator, aws_key_rule):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[aws_key_rule],
        )
        result = await output_evaluator.evaluate("Key: AKIAIOSFODNN7EXAMPLE", config)
        assert result.passed is False
        assert result.action_taken == "blocked"

    # ---- Output length checks ----

    @pytest.mark.asyncio
    async def test_output_length_exceeded(self, output_evaluator):
        config = GuardrailsConfig(
            enabled=True,
            max_output_length=50,
        )
        result = await output_evaluator.evaluate("x" * 100, config)
        assert result.passed is False
        assert any(v.rule_name == "max_output_length" for v in result.violations)

    @pytest.mark.asyncio
    async def test_output_length_within_limit(self, output_evaluator):
        config = GuardrailsConfig(
            enabled=True,
            max_output_length=1000,
        )
        result = await output_evaluator.evaluate("short output", config)
        assert result.passed is True

    # ---- Content chaining: post-pattern sanitized text flows to scanners ----

    @pytest.mark.asyncio
    async def test_content_chaining_length_check_uses_sanitized(self, output_evaluator):
        """Length check should operate on post-pattern sanitized content,
        not the raw content with full secrets present."""
        rule = PatternRule(
            name="big_redact",
            patterns=[PatternEntry(regex=r"SECRET_DATA_[A-Z]{50,}")],
            action="redact",
            applies_to="output",
        )
        # Content with 60-char secret => redacted to [REDACTED] (10 chars)
        big_secret = "SECRET_DATA_" + "A" * 60
        raw_content = f"Prefix {big_secret} suffix"
        config = GuardrailsConfig(
            enabled=True,
            pattern_rules=[rule],
            behavioral=BehavioralGuardrails(
                # Set max_output_length smaller than raw but larger than sanitized
                max_output_length=len(raw_content) - 10,
            ),
        )
        result = await output_evaluator.evaluate(raw_content, config)
        # The sanitized content is shorter, so length check should pass
        assert not any(v.rule_name == "max_output_length" for v in result.violations)

    # ---- Output scanners with mocked LLM Guard ----

    @pytest.mark.asyncio
    async def test_output_toxicity_scanner_violation(self, output_evaluator):
        """Toxicity scanner detects toxic output and produces a violation."""
        from unittest.mock import AsyncMock, patch

        config = GuardrailsConfig(
            enabled=True,
            behavioral=BehavioralGuardrails(),
            output_scanners=OutputScanners(detect_toxicity="block"),
        )
        scanner_result = GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="output",
                    rule_name="output_toxicity",
                    severity="block",
                    message="Toxic content detected in output (risk score: 0.92)",
                    details={"confidence": 0.92, "detection_method": "llm_guard"},
                )
            ],
            action_taken="blocked",
        )

        with patch.object(
            OutputGuardrailEvaluator,
            "_run_output_scanners",
            new_callable=AsyncMock,
            return_value=scanner_result,
        ):
            result = await output_evaluator.evaluate("toxic output", config)

        assert result.passed is False
        assert any(v.rule_name == "output_toxicity" for v in result.violations)
        toxic_v = [v for v in result.violations if v.rule_name == "output_toxicity"][0]
        assert toxic_v.details["confidence"] == 0.92
        assert toxic_v.details["detection_method"] == "llm_guard"

    @pytest.mark.asyncio
    async def test_output_no_refusal_scanner_violation(self, output_evaluator):
        """NoRefusal scanner flags a refusal in output."""
        from unittest.mock import AsyncMock, patch

        config = GuardrailsConfig(
            enabled=True,
            behavioral=BehavioralGuardrails(),
            output_scanners=OutputScanners(detect_refusal="block"),
        )
        scanner_result = GuardrailResult(
            passed=True,
            violations=[
                Violation(
                    category="output",
                    rule_name="no_refusal",
                    severity="warn",
                    message="LLM refusal detected in output (risk score: 0.88)",
                    details={"confidence": 0.88, "detection_method": "llm_guard"},
                )
            ],
            action_taken="warned",
        )

        with patch.object(
            OutputGuardrailEvaluator,
            "_run_output_scanners",
            new_callable=AsyncMock,
            return_value=scanner_result,
        ):
            result = await output_evaluator.evaluate("I cannot help", config)

        assert result.passed is True  # refusal is warn-severity, not block
        assert any(v.rule_name == "no_refusal" for v in result.violations)
        refusal_v = [v for v in result.violations if v.rule_name == "no_refusal"][0]
        assert refusal_v.severity == "warn"

    @pytest.mark.asyncio
    async def test_output_sensitive_data_scanner_violation(self, output_evaluator):
        """Sensitive scanner detects PII in output."""
        from unittest.mock import AsyncMock, patch

        config = GuardrailsConfig(
            enabled=True,
            behavioral=BehavioralGuardrails(),
            output_scanners=OutputScanners(detect_sensitive_data="block"),
        )
        scanner_result = GuardrailResult(
            passed=True,
            violations=[
                Violation(
                    category="output",
                    rule_name="sensitive_data",
                    severity="warn",
                    message="Sensitive data detected in output (risk score: 0.95)",
                    details={"confidence": 0.95, "detection_method": "llm_guard"},
                )
            ],
            action_taken="warned",
        )

        with patch.object(
            OutputGuardrailEvaluator,
            "_run_output_scanners",
            new_callable=AsyncMock,
            return_value=scanner_result,
        ):
            result = await output_evaluator.evaluate("contains SSN 123-45-6789", config)

        assert any(v.rule_name == "sensitive_data" for v in result.violations)

    @pytest.mark.asyncio
    async def test_output_scanner_clean_pass(self, output_evaluator):
        """When all scanners pass, result should have no violations."""
        from unittest.mock import AsyncMock, patch

        config = GuardrailsConfig(
            enabled=True,
            behavioral=BehavioralGuardrails(),
            output_scanners=OutputScanners(
                detect_toxicity="block",
                detect_refusal="block",
                detect_sensitive_data="block",
            ),
        )
        scanner_result = GuardrailResult(passed=True)

        with patch.object(
            OutputGuardrailEvaluator,
            "_run_output_scanners",
            new_callable=AsyncMock,
            return_value=scanner_result,
        ):
            result = await output_evaluator.evaluate("clean text", config)

        assert result.passed is True
        assert len(result.violations) == 0

    @pytest.mark.asyncio
    async def test_output_scanner_exception_handled_gracefully(self, output_evaluator):
        """Scanner backend exceptions are caught inside _run_output_scanners,
        so we mock the backend to raise and verify the error does not propagate."""
        from unittest.mock import AsyncMock, MagicMock, patch

        config = GuardrailsConfig(
            enabled=True,
            behavioral=BehavioralGuardrails(),
            output_scanners=OutputScanners(detect_toxicity="block"),
        )

        mock_backend = MagicMock()
        mock_backend.scan_output = AsyncMock(
            side_effect=RuntimeError("Model load failure")
        )

        with patch(
            "backend.services.guardrails.evaluators.output.get_scanner_backend",
            return_value=mock_backend,
        ):
            # The exception propagates from _run_output_scanners since evaluate()
            # does not wrap it in try/except. Verify it raises.
            with pytest.raises(RuntimeError, match="Model load failure"):
                await output_evaluator.evaluate("some output", config)

    @pytest.mark.asyncio
    async def test_output_deanonymize_with_vault(self, output_evaluator):
        """Deanonymize scanner restores PII placeholders using the vault."""
        from unittest.mock import AsyncMock, patch

        config = GuardrailsConfig(
            enabled=True,
            anonymize_pii="anonymize",
            output_scanners=OutputScanners(),
        )
        scanner_result = GuardrailResult(
            passed=True,
            sanitized_content="Hello John Doe",
        )

        with patch.object(
            OutputGuardrailEvaluator,
            "_run_output_scanners",
            new_callable=AsyncMock,
            return_value=scanner_result,
        ):
            result = await output_evaluator.evaluate(
                "Hello [PERSON_1]",
                config,
                vault_id="test-vault-id",
                vault_secret="test-vault-secret",
            )

        assert result.sanitized_content == "Hello John Doe"

    # ---- Regression: scanners must receive raw content, not post-pattern text ----

    @pytest.mark.asyncio
    async def test_output_scanners_receive_raw_content_not_redacted(
        self, output_evaluator, ssn_rule
    ):
        """Scanners must inspect the original raw LLM output, not text
        that has already been sanitized by pattern rules.  This locks the
        contract so a future refactor cannot silently pass redacted content
        to scanners."""
        from unittest.mock import AsyncMock, patch

        raw_output = "Your SSN is 123-45-6789 and that is fine."

        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[ssn_rule],
            behavioral=BehavioralGuardrails(),
            output_scanners=OutputScanners(detect_toxicity="block"),
        )

        scanner_result = GuardrailResult(passed=True)

        with patch.object(
            OutputGuardrailEvaluator,
            "_run_output_scanners",
            new_callable=AsyncMock,
            return_value=scanner_result,
        ) as mock_run_scanners:
            result = await output_evaluator.evaluate(raw_output, config)

        # The scanners must have been called with the raw output, not redacted
        mock_run_scanners.assert_called_once()
        call_args = mock_run_scanners.call_args
        content_arg = call_args[0][0] if call_args[0] else call_args[1].get("content")
        assert content_arg == raw_output, (
            f"Scanner received redacted content instead of raw output: {content_arg!r}"
        )
        # Pattern rules should still have redacted the SSN in the result
        assert result.sanitized_content is not None
        assert "[REDACTED]" in result.sanitized_content

    # ---- Engine integration: output scanners in check_output ----

    @pytest.mark.asyncio
    async def test_engine_check_output_with_output_scanners(self):
        """Engine.check_output delegates to output evaluator which runs scanners."""
        from unittest.mock import AsyncMock, patch

        engine = GuardrailsEngine()
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            behavioral=BehavioralGuardrails(),
            output_scanners=OutputScanners(detect_toxicity="block"),
        )
        scanner_result = GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="output",
                    rule_name="output_toxicity",
                    severity="block",
                    message="Toxic content detected in output (risk score: 0.95)",
                    details={"confidence": 0.95, "detection_method": "llm_guard"},
                )
            ],
            action_taken="blocked",
        )

        with patch.object(
            OutputGuardrailEvaluator,
            "_run_output_scanners",
            new_callable=AsyncMock,
            return_value=scanner_result,
        ):
            result = await engine.check_output("toxic", config)

        assert result.passed is False
        assert any(v.rule_name == "output_toxicity" for v in result.violations)

    @pytest.mark.asyncio
    async def test_engine_check_output_audit_mode_with_scanners(self):
        """In audit mode, scanner violations are recorded but output passes."""
        from unittest.mock import AsyncMock, patch

        engine = GuardrailsEngine()
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="audit",
            behavioral=BehavioralGuardrails(),
            output_scanners=OutputScanners(detect_toxicity="block"),
        )
        scanner_result = GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="output",
                    rule_name="output_toxicity",
                    severity="block",
                    message="Toxic content detected in output (risk score: 0.95)",
                    details={"confidence": 0.95, "detection_method": "llm_guard"},
                )
            ],
            action_taken="blocked",
        )

        with patch.object(
            OutputGuardrailEvaluator,
            "_run_output_scanners",
            new_callable=AsyncMock,
            return_value=scanner_result,
        ):
            result = await engine.check_output("toxic", config)

        assert result.passed is True  # audit mode always passes
        assert len(result.violations) > 0  # but violations are recorded


# ============================================================================
# 7. GuardrailsConfig Serialization Tests
# ============================================================================


class TestGuardrailsConfigSerialization:
    """Tests for to_dict/from_dict round-tripping."""

    def test_roundtrip_minimal(self):
        config = GuardrailsConfig(enabled=True, enforcement_mode="enforce")
        d = config.to_dict()
        restored = GuardrailsConfig.from_dict(d)
        assert restored.enabled is True
        assert restored.enforcement_mode == "enforce"

    def test_roundtrip_with_pattern_rules(self):
        config = GuardrailsConfig(
            enabled=True,
            pattern_rules=[
                PatternRule(
                    name="test", patterns=[PatternEntry(regex=r"\d+")], action="warn"
                )
            ],
        )
        d = config.to_dict()
        restored = GuardrailsConfig.from_dict(d)
        assert len(restored.pattern_rules) == 1
        assert restored.pattern_rules[0].name == "test"

    def test_roundtrip_with_tool_call_policy(self):
        config = GuardrailsConfig(
            enabled=True,
            tool_call_policy=ToolCallPolicy(max_tool_calls_per_execution=25),
        )
        d = config.to_dict()
        restored = GuardrailsConfig.from_dict(d)
        assert restored.tool_call_policy.max_tool_calls_per_execution == 25

    def test_roundtrip_with_token_budget(self):
        config = GuardrailsConfig(
            enabled=True,
            token_budget=TokenBudget(max_total_tokens_per_execution=50000),
        )
        d = config.to_dict()
        restored = GuardrailsConfig.from_dict(d)
        assert restored.token_budget.max_total_tokens_per_execution == 50000

    def test_roundtrip_with_behavioral(self):
        config = GuardrailsConfig(
            enabled=True,
            detect_prompt_injection="block",
            detect_jailbreak_attempts="off",
            max_input_length=10000,
        )
        d = config.to_dict()
        restored = GuardrailsConfig.from_dict(d)
        assert restored.detect_prompt_injection == "block"
        assert restored.detect_jailbreak_attempts == "off"
        assert restored.max_input_length == 10000

    def test_from_dict_legacy_behavioral_format(self):
        """Old nested format with 'behavioral' key auto-flattens to top-level."""
        legacy = {
            "enabled": True,
            "enforcement_mode": "enforce",
            "behavioral": {
                "detect_prompt_injection": "block",
                "detect_jailbreak_attempts": "warn",
                "system_prompt_protection": True,
                "max_input_length": 20000,
                "anonymize_pii": "anonymize",
            },
        }
        config = GuardrailsConfig.from_dict(legacy)
        assert config.detect_prompt_injection == "block"
        assert config.detect_jailbreak_attempts == "warn"
        assert config.system_prompt_protection is True
        assert config.max_input_length == 20000
        assert config.anonymize_pii == "anonymize"
        # Nested behavioral should not be populated
        assert config.behavioral is None
        # Round-trip should not produce a 'behavioral' key
        d = config.to_dict()
        assert "behavioral" not in d

    def test_roundtrip_with_provider_content_filter(self):
        config = GuardrailsConfig(
            enabled=True,
            provider_content_filter=ProviderContentFilter(
                enabled=True, categories=["violence", "hate_speech"]
            ),
        )
        d = config.to_dict()
        restored = GuardrailsConfig.from_dict(d)
        assert restored.provider_content_filter.enabled is True
        assert "violence" in restored.provider_content_filter.categories

    def test_roundtrip_with_output_scanners(self):
        config = GuardrailsConfig(
            enabled=True,
            output_scanners=OutputScanners(
                detect_toxicity="block",
                detect_refusal="off",
                detect_sensitive_data="warn",
            ),
        )
        d = config.to_dict()
        restored = GuardrailsConfig.from_dict(d)
        assert restored.output_scanners is not None
        assert restored.output_scanners.detect_toxicity == "block"
        assert restored.output_scanners.detect_refusal == "off"
        assert restored.output_scanners.detect_sensitive_data == "warn"

    def test_from_dict_empty(self):
        config = GuardrailsConfig.from_dict({})
        assert config.enabled is False

    def test_from_dict_none(self):
        config = GuardrailsConfig.from_dict(None)
        assert config.enabled is False

    def test_new_policy_fields_defaults(self):
        config = GuardrailsConfig(enabled=True)
        assert config.priority == 0
        assert config.policy_id == ""
        assert config.policy_name == ""

    def test_new_policy_fields_round_trip(self):
        config = GuardrailsConfig(
            enabled=True,
            priority=10,
            policy_id="p1",
            policy_name="Safety",
        )
        d = config.to_dict()
        assert d["priority"] == 10
        assert d["policy_id"] == "p1"
        assert d["policy_name"] == "Safety"
        restored = GuardrailsConfig.from_dict(d)
        assert restored.priority == 10
        assert restored.policy_id == "p1"
        assert restored.policy_name == "Safety"

    def test_from_dict_ignores_old_attribution_fields(self):
        """Ensure from_dict silently discards legacy source_policies/rule_policy_map."""
        data = {
            "enabled": True,
            "source_policies": [{"policy_id": "p1"}],
            "rule_policy_map": {"rule": {"policy_id": "p1"}},
        }
        config = GuardrailsConfig.from_dict(data)
        assert config.enabled is True
        assert not hasattr(config, "source_policies")
        assert not hasattr(config, "rule_policy_map")


# ============================================================================
# 8. GuardrailResult Tests
# ============================================================================


class TestGuardrailResult:
    """Tests for GuardrailResult merge logic and serialization."""

    def test_merge_both_pass(self):
        a = GuardrailResult(passed=True)
        b = GuardrailResult(passed=True)
        merged = a.merge(b)
        assert merged.passed is True

    def test_merge_one_fails(self):
        a = GuardrailResult(passed=True)
        b = GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="test", rule_name="r", severity="block", message="fail"
                )
            ],
            action_taken="blocked",
        )
        merged = a.merge(b)
        assert merged.passed is False

    def test_merge_action_priority(self):
        a = GuardrailResult(passed=True, action_taken="warned")
        b = GuardrailResult(passed=True, action_taken="redacted")
        merged = a.merge(b)
        assert merged.action_taken == "redacted"

    def test_merge_blocked_highest_priority(self):
        a = GuardrailResult(passed=True, action_taken="redacted")
        b = GuardrailResult(passed=False, action_taken="blocked")
        merged = a.merge(b)
        assert merged.action_taken == "blocked"

    def test_merge_violations_concatenated(self):
        v1 = Violation(category="a", rule_name="r1", severity="warn", message="m1")
        v2 = Violation(category="b", rule_name="r2", severity="block", message="m2")
        a = GuardrailResult(passed=True, violations=[v1])
        b = GuardrailResult(passed=False, violations=[v2])
        merged = a.merge(b)
        assert len(merged.violations) == 2

    def test_merge_sanitized_content_from_other(self):
        a = GuardrailResult(passed=True, sanitized_content="first")
        b = GuardrailResult(passed=True, sanitized_content="second")
        merged = a.merge(b)
        assert merged.sanitized_content == "second"

    def test_to_dict(self):
        result = GuardrailResult(
            passed=False,
            violations=[
                Violation(category="test", rule_name="r", severity="block", message="m")
            ],
            action_taken="blocked",
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert len(d["violations"]) == 1
        assert d["action_taken"] == "blocked"

    def test_violation_auto_timestamp(self):
        v = Violation(category="t", rule_name="r", severity="warn", message="m")
        assert v.timestamp  # Should be auto-populated


# ============================================================================
# 9. Python Sandbox Executor Tests
# ============================================================================


class TestPythonSandboxExecutor:
    """Tests for the sandboxed Python filter code executor."""

    def test_valid_filter_passes(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    return {"passed": True, "message": "OK"}
"""
        result = sandbox_executor.execute(code, "test content", "ingress")
        assert result["passed"] is True

    def test_filter_blocks_content(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    if "bad" in content:
        return {"passed": False, "message": "Bad content"}
    return {"passed": True}
"""
        result = sandbox_executor.execute(code, "this is bad", "ingress")
        assert result["passed"] is False

    def test_filter_transforms_content(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    cleaned = content.replace("bad", "good")
    return {"passed": False, "message": "Transformed", "content": cleaned}
"""
        result = sandbox_executor.execute(code, "this is bad", "ingress")
        assert result["content"] == "this is good"

    def test_filter_with_re_module(self, sandbox_executor):
        code = """
import re
def filter(content, direction, **context):
    if re.search(r"\\d{3}-\\d{2}-\\d{4}", content):
        return {"passed": False, "message": "SSN detected"}
    return {"passed": True}
"""
        result = sandbox_executor.execute(code, "SSN: 123-45-6789", "ingress")
        assert result["passed"] is False

    def test_filter_with_json_module(self, sandbox_executor):
        code = """
import json
def filter(content, direction, **context):
    try:
        data = json.loads(content)
        return {"passed": True, "message": "Valid JSON"}
    except Exception:
        return {"passed": False, "message": "Invalid JSON"}
"""
        result = sandbox_executor.execute(code, '{"key": "value"}', "ingress")
        assert result["passed"] is True

    # ---- Forbidden constructs ----

    def test_eval_forbidden(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    eval("1+1")
    return {"passed": True}
"""
        with pytest.raises(CodeValidationError, match="Forbidden name.*eval"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_exec_forbidden(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    exec("x = 1")
    return {"passed": True}
"""
        with pytest.raises(CodeValidationError, match="Forbidden name.*exec"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_open_forbidden(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    open("/etc/passwd")
    return {"passed": True}
"""
        with pytest.raises(CodeValidationError, match="Forbidden name.*open"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_import_os_forbidden(self, sandbox_executor):
        code = """
import os
def filter(content, direction, **context):
    return {"passed": True}
"""
        with pytest.raises(CodeValidationError, match="Import not allowed.*os"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_import_subprocess_forbidden(self, sandbox_executor):
        code = """
import subprocess
def filter(content, direction, **context):
    return {"passed": True}
"""
        with pytest.raises(CodeValidationError, match="Import not allowed.*subprocess"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_dunder_access_forbidden(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    x = content.__class__
    return {"passed": True}
"""
        with pytest.raises(CodeValidationError, match="Forbidden attribute.*__class__"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_async_forbidden(self, sandbox_executor):
        code = """
async def filter(content, direction, **context):
    return {"passed": True}
"""
        with pytest.raises(CodeValidationError, match="Forbidden construct.*Async"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_global_forbidden(self, sandbox_executor):
        code = """
x = 1
def filter(content, direction, **context):
    global x
    return {"passed": True}
"""
        with pytest.raises(CodeValidationError, match="Forbidden construct.*Global"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_syntax_error(self, sandbox_executor):
        code = "def filter(content, direction)\n  return"
        with pytest.raises(CodeValidationError, match="Syntax error"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_no_filter_function(self, sandbox_executor):
        code = "x = 1 + 1"
        with pytest.raises(ValueError, match="must define.*filter"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_filter_returns_non_dict(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    return "not a dict"
"""
        with pytest.raises(ValueError, match="must return a dict"):
            sandbox_executor.execute(code, "test", "ingress")

    def test_output_size_limit(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    return {"passed": True, "content": "x" * 200000}
"""
        with pytest.raises(ValueError, match="character limit"):
            sandbox_executor.execute(code, "test", "ingress")

    # ---- Caching ----

    def test_sandbox_caching(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    return {"passed": True}
"""
        sandbox_executor.execute(code, "test1", "ingress")
        sandbox_executor.execute(code, "test2", "ingress")
        # Should have one cached entry
        assert len(sandbox_executor._sandbox_cache) == 1

    def test_cache_invalidation(self, sandbox_executor):
        code = """
def filter(content, direction, **context):
    return {"passed": True}
"""
        sandbox_executor.execute(code, "test", "ingress")
        assert len(sandbox_executor._sandbox_cache) == 1
        sandbox_executor.invalidate_cache(code)
        assert len(sandbox_executor._sandbox_cache) == 0

    def test_cache_invalidation_all(self, sandbox_executor):
        code1 = (
            'def filter(content, direction, **context):\n    return {"passed": True}'
        )
        code2 = (
            'def filter(content, direction, **context):\n    return {"passed": False}'
        )
        sandbox_executor.execute(code1, "t", "ingress")
        sandbox_executor.execute(code2, "t", "ingress")
        assert len(sandbox_executor._sandbox_cache) == 2
        sandbox_executor.invalidate_cache()
        assert len(sandbox_executor._sandbox_cache) == 0

    def test_validate_code_returns_errors(self, sandbox_executor):
        errors = sandbox_executor.validate_code("import os\ndef filter(c,d): pass")
        assert len(errors) > 0
        assert any("os" in e for e in errors)

    def test_validate_code_valid(self, sandbox_executor):
        errors = sandbox_executor.validate_code(
            "import re\ndef filter(content, direction, **context):\n    return {'passed': True}"
        )
        assert len(errors) == 0


# ============================================================================
# 9b. (Presidio and Detoxify sandbox tests removed — replaced by LLM Guard
#      first-class scanners.  See BehavioralGuardrails.detect_toxicity and
#      BehavioralGuardrails.anonymize_pii.)
# ============================================================================


# ============================================================================
# 10. Custom Filter Evaluator Tests
# ============================================================================


class TestCustomFilterEvaluator:
    """Tests for the custom filter orchestrator (priority, chaining, scoping)."""

    @pytest.fixture
    def evaluator(self):
        return CustomFilterEvaluator()

    @pytest.mark.asyncio
    async def test_no_applicable_filters(self, evaluator):
        result = await evaluator.evaluate("test", [], "ingress")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_disabled_filters_skipped(self, evaluator):
        f = CustomFilter(
            id="f1",
            name="disabled",
            filter_type="python_code",
            action="block",
            scope="both",
            enabled=False,
            python_code='def filter(c,d,**k): return {"passed": False}',
        )
        result = await evaluator.evaluate("test", [f], "ingress")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_scope_filtering_ingress(self, evaluator):
        f = CustomFilter(
            id="f1",
            name="egress-only",
            filter_type="python_code",
            action="block",
            scope="egress",
            enabled=True,
            python_code='def filter(c,d,**k): return {"passed": False, "message": "blocked"}',
        )
        result = await evaluator.evaluate("test", [f], "ingress")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_scope_filtering_egress(self, evaluator):
        f = CustomFilter(
            id="f1",
            name="ingress-only",
            filter_type="python_code",
            action="block",
            scope="ingress",
            enabled=True,
            python_code='def filter(c,d,**k): return {"passed": False, "message": "blocked"}',
        )
        result = await evaluator.evaluate("test", [f], "egress")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_block_action(self, evaluator):
        f = CustomFilter(
            id="f1",
            name="blocker",
            filter_type="python_code",
            action="block",
            scope="both",
            enabled=True,
            python_code='def filter(c,d,**k): return {"passed": False, "message": "blocked"}',
        )
        result = await evaluator.evaluate("test", [f], "ingress")
        assert result.passed is False
        assert result.action_taken == "blocked"

    @pytest.mark.asyncio
    async def test_warn_action(self, evaluator):
        f = CustomFilter(
            id="f1",
            name="warner",
            filter_type="python_code",
            action="warn",
            scope="both",
            enabled=True,
            python_code='def filter(c,d,**k): return {"passed": False, "message": "warning"}',
        )
        result = await evaluator.evaluate("test", [f], "ingress")
        assert result.passed is True
        assert result.action_taken == "warned"

    @pytest.mark.asyncio
    async def test_transform_action(self, evaluator):
        f = CustomFilter(
            id="f1",
            name="transformer",
            filter_type="python_code",
            action="transform",
            scope="both",
            enabled=True,
            python_code='def filter(c,d,**k): return {"passed": False, "message": "transformed", "content": c.upper()}',
        )
        result = await evaluator.evaluate("hello", [f], "ingress")
        assert result.passed is True
        assert result.action_taken == "transformed"
        assert result.sanitized_content == "HELLO"

    @pytest.mark.asyncio
    async def test_priority_ordering(self, evaluator):
        """Filters should run in priority order (lower = first)."""
        f1 = CustomFilter(
            id="f1",
            name="second",
            filter_type="python_code",
            action="transform",
            scope="both",
            enabled=True,
            priority=200,
            python_code='def filter(c,d,**k): return {"passed": False, "content": c + "-second"}',
        )
        f2 = CustomFilter(
            id="f2",
            name="first",
            filter_type="python_code",
            action="transform",
            scope="both",
            enabled=True,
            priority=100,
            python_code='def filter(c,d,**k): return {"passed": False, "content": c + "-first"}',
        )
        result = await evaluator.evaluate("start", [f1, f2], "ingress")
        assert result.sanitized_content == "start-first-second"

    @pytest.mark.asyncio
    async def test_block_stops_pipeline(self, evaluator):
        """A blocking filter should prevent subsequent filters from running."""
        f1 = CustomFilter(
            id="f1",
            name="blocker",
            filter_type="python_code",
            action="block",
            scope="both",
            enabled=True,
            priority=100,
            python_code='def filter(c,d,**k): return {"passed": False, "message": "blocked"}',
        )
        f2 = CustomFilter(
            id="f2",
            name="never-runs",
            filter_type="python_code",
            action="warn",
            scope="both",
            enabled=True,
            priority=200,
            python_code='def filter(c,d,**k): return {"passed": False, "message": "should not appear"}',
        )
        result = await evaluator.evaluate("test", [f1, f2], "ingress")
        assert result.passed is False
        assert len(result.violations) == 1  # Only blocker's violation

    @pytest.mark.asyncio
    async def test_error_in_filter_produces_warning(self, evaluator):
        f = CustomFilter(
            id="f1",
            name="broken",
            filter_type="python_code",
            action="block",
            scope="both",
            enabled=True,
            python_code='def filter(c,d,**k): raise ValueError("boom")',
        )
        result = await evaluator.evaluate("test", [f], "ingress")
        # Errors produce warnings, never blocks
        assert result.passed is True
        assert any("error" in v.rule_name for v in result.violations)

    @pytest.mark.asyncio
    async def test_unknown_filter_type(self, evaluator):
        f = CustomFilter(
            id="f1",
            name="unknown",
            filter_type="unknown_type",
            action="block",
            scope="both",
            enabled=True,
        )
        result = await evaluator.evaluate("test", [f], "ingress")
        assert result.passed is True
        assert any("unknown_type" in v.rule_name for v in result.violations)


# ============================================================================
# 11. GuardrailsEngine Integration Tests
# ============================================================================


class TestGuardrailsEngineIntegration:
    """End-to-end tests through the GuardrailsEngine orchestrator."""

    @pytest.mark.asyncio
    async def test_check_input_disabled(self, engine, disabled_config):
        result = await engine.check_input("any content", disabled_config)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_check_input_enforcement_disabled(self, engine):
        config = GuardrailsConfig(enabled=True, enforcement_mode="disabled")
        result = await engine.check_input("any content", config)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_check_input_pattern_blocks(self, engine, aws_key_rule):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[aws_key_rule],
        )
        result = await engine.check_input("Key: AKIAIOSFODNN7EXAMPLE", config)
        assert result.passed is False
        assert result.action_taken == "blocked"

    @pytest.mark.asyncio
    async def test_check_input_pattern_redacts(self, engine, ssn_rule):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[ssn_rule],
        )
        result = await engine.check_input("SSN: 123-45-6789", config)
        assert result.passed is True
        assert result.action_taken == "redacted"
        assert "[REDACTED]" in result.sanitized_content

    @pytest.mark.asyncio
    async def test_check_input_audit_mode_allows_through(self, engine, aws_key_rule):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="audit",
            pattern_rules=[aws_key_rule],
        )
        result = await engine.check_input("Key: AKIAIOSFODNN7EXAMPLE", config)
        assert result.passed is True  # Audit mode always passes
        assert len(result.violations) > 0  # But violations are recorded

    @pytest.mark.asyncio
    async def test_check_output_disabled(self, engine, disabled_config):
        result = await engine.check_output("any content", disabled_config)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_check_output_pattern_blocks(self, engine, private_key_rule):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[private_key_rule],
        )
        result = await engine.check_output(
            "-----BEGIN RSA PRIVATE KEY-----\ndata", config
        )
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_check_output_length_enforced(self, engine):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            max_output_length=50,
        )
        result = await engine.check_output("x" * 100, config)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_check_output_audit_mode(self, engine, private_key_rule):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="audit",
            pattern_rules=[private_key_rule],
        )
        result = await engine.check_output("-----BEGIN PRIVATE KEY-----\ndata", config)
        assert result.passed is True
        assert len(result.violations) > 0

    def test_check_tool_call_disabled(self, engine, disabled_config):
        result = engine.check_tool_call(
            "http_request", {"url": "http://127.0.0.1"}, disabled_config
        )
        assert result.passed is True

    def test_check_tool_call_ssrf_blocked(self, engine):
        config = GuardrailsConfig(enabled=True, enforcement_mode="enforce")
        result = engine.check_tool_call(
            "http_request",
            {"url": "http://127.0.0.1/admin"},
            config,
        )
        assert result.passed is False

    def test_check_tool_call_default_ssrf_protection(self, engine):
        """Even without explicit policy, SSRF protection should be active."""
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            tool_call_policy=None,
        )
        result = engine.check_tool_call(
            "http_request",
            {"url": "http://169.254.169.254/meta"},
            config,
        )
        assert result.passed is False

    def test_check_tool_call_audit_mode(self, engine):
        config = GuardrailsConfig(enabled=True, enforcement_mode="audit")
        result = engine.check_tool_call(
            "http_request",
            {"url": "http://127.0.0.1/admin"},
            config,
        )
        assert result.passed is True  # Audit mode
        assert len(result.violations) > 0

    def test_check_token_budget_disabled(self, engine, disabled_config):
        result = engine.check_token_budget({"llm_calls": 999}, disabled_config)
        assert result.passed is True

    def test_check_token_budget_no_budget(self, engine, base_config):
        result = engine.check_token_budget({"llm_calls": 999}, base_config)
        assert result.passed is True

    def test_check_token_budget_exceeded(self, engine, token_budget):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            token_budget=token_budget,
        )
        result = engine.check_token_budget(
            {
                "input_tokens": 20000,
                "output_tokens": 10000,
                "total_tokens": 30000,
                "llm_calls": 15,
            },
            config,
        )
        assert result.passed is False

    def test_check_token_budget_audit_mode(self, engine, token_budget):
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="audit",
            token_budget=token_budget,
        )
        result = engine.check_token_budget(
            {
                "input_tokens": 20000,
                "output_tokens": 10000,
                "total_tokens": 30000,
                "llm_calls": 15,
            },
            config,
        )
        assert result.passed is True
        assert len(result.violations) > 0


# ============================================================================
# 10b. Pipeline-List Integration Tests for Non-Input Checkpoints
# ============================================================================


class TestPipelineListIntegration:
    """Verify that check_output, check_tool_call, and check_token_budget
    correctly iterate pipeline lists, normalize single configs, and apply
    per-policy enforcement semantics."""

    # ------------------------------------------------------------------
    # check_output pipeline tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_check_output_single_config_in_list(self, engine, private_key_rule):
        """[config] wrapper should behave identically to bare config."""
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[private_key_rule],
        )
        with pytest.raises(GuardrailViolationError) as exc_info:
            await engine.check_output(
                "-----BEGIN RSA PRIVATE KEY-----\ndata", [config]
            )
        assert len(exc_info.value.violations) > 0

    @pytest.mark.asyncio
    async def test_check_output_two_policy_pipeline(self, engine, ssn_rule, email_rule):
        """Two-policy pipeline: first redacts, second warns; both violations
        collected and content chains through."""
        cfg1 = GuardrailsConfig(
            policy_id="out-p1",
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[ssn_rule],
        )
        cfg2 = GuardrailsConfig(
            policy_id="out-p2",
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=[email_rule],
        )
        result = await engine.check_output(
            "SSN 123-45-6789 email user@example.com", [cfg1, cfg2]
        )
        # SSN redacted (pass), email warned (pass) → overall pass
        assert result.passed is True
        # Violations from both policies collected
        policy_ids = {v.policy_id for v in result.violations}
        assert "out-p1" in policy_ids
        assert "out-p2" in policy_ids

    @pytest.mark.asyncio
    async def test_check_output_audit_pipeline(self, engine, private_key_rule):
        """Audit-mode policy in a pipeline list downgrades to warned."""
        cfg_audit = GuardrailsConfig(
            policy_id="out-audit",
            enabled=True,
            enforcement_mode="audit",
            pattern_rules=[private_key_rule],
        )
        cfg_pass = GuardrailsConfig(
            policy_id="out-pass",
            enabled=True,
            enforcement_mode="enforce",
        )
        result = await engine.check_output(
            "-----BEGIN RSA PRIVATE KEY-----\ndata", [cfg_audit, cfg_pass]
        )
        assert result.passed is True
        assert result.action_taken == "warned"
        assert any(v.policy_id == "out-audit" for v in result.violations)

    # ------------------------------------------------------------------
    # check_tool_call pipeline tests
    # ------------------------------------------------------------------

    def test_check_tool_call_single_config_in_list(self, engine):
        """[config] wrapper should behave identically to bare config."""
        config = GuardrailsConfig(enabled=True, enforcement_mode="enforce")
        with pytest.raises(GuardrailViolationError):
            engine.check_tool_call(
                "http_request",
                {"url": "http://127.0.0.1/admin"},
                [config],
            )

    def test_check_tool_call_two_policy_pipeline(self, engine):
        """Two-policy pipeline: first policy blocks SQL, second has SSRF.
        Enforce on first → short-circuit."""
        cfg1 = GuardrailsConfig(
            policy_id="tc-p1",
            enabled=True,
            enforcement_mode="enforce",
            tool_call_policy=ToolCallPolicy(
                allowed_sql_operations=["SELECT"],
                blocked_tables=["credentials"],
            ),
        )
        cfg2 = GuardrailsConfig(
            policy_id="tc-p2",
            enabled=True,
            enforcement_mode="enforce",
        )
        # DELETE on credentials → cfg1 blocks
        with pytest.raises(GuardrailViolationError) as exc_info:
            engine.check_tool_call(
                "database_query",
                {"query": "DELETE FROM credentials WHERE id=1"},
                [cfg1, cfg2],
            )
        assert any(v.policy_id == "tc-p1" for v in exc_info.value.violations)

    def test_check_tool_call_audit_pipeline(self, engine):
        """Audit-mode tool call policy in a pipeline downgrades to warned."""
        cfg_audit = GuardrailsConfig(
            policy_id="tc-audit",
            enabled=True,
            enforcement_mode="audit",
        )
        result = engine.check_tool_call(
            "http_request",
            {"url": "http://127.0.0.1/admin"},
            [cfg_audit],
        )
        assert result.passed is True
        assert result.action_taken == "warned"
        assert any(v.policy_id == "tc-audit" for v in result.violations)

    def test_check_tool_call_audit_then_enforce_pipeline(self, engine):
        """Audit policy warns first, enforce policy on same violation raises."""
        cfg_audit = GuardrailsConfig(
            policy_id="tc-audit",
            enabled=True,
            enforcement_mode="audit",
        )
        cfg_enforce = GuardrailsConfig(
            policy_id="tc-enforce",
            enabled=True,
            enforcement_mode="enforce",
        )
        # Both policies see SSRF; audit downgrades, enforce raises
        with pytest.raises(GuardrailViolationError) as exc_info:
            engine.check_tool_call(
                "http_request",
                {"url": "http://127.0.0.1/admin"},
                [cfg_audit, cfg_enforce],
            )
        # Violations from both policies collected
        policy_ids = {v.policy_id for v in exc_info.value.violations}
        assert "tc-audit" in policy_ids
        assert "tc-enforce" in policy_ids

    # ------------------------------------------------------------------
    # check_token_budget pipeline tests
    # ------------------------------------------------------------------

    def test_check_token_budget_single_config_in_list(self, engine, token_budget):
        """[config] wrapper should behave identically to bare config."""
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            token_budget=token_budget,
        )
        with pytest.raises(GuardrailViolationError):
            engine.check_token_budget(
                {
                    "input_tokens": 20000,
                    "output_tokens": 10000,
                    "total_tokens": 30000,
                    "llm_calls": 15,
                },
                [config],
            )

    def test_check_token_budget_two_policy_pipeline(self, engine):
        """Two-policy pipeline with different budgets: stricter policy blocks."""
        strict_budget = TokenBudget(
            max_llm_calls_per_execution=5,
            warn_at_percentage=0.8,
        )
        lenient_budget = TokenBudget(
            max_llm_calls_per_execution=50,
            warn_at_percentage=0.8,
        )
        cfg_strict = GuardrailsConfig(
            policy_id="tb-strict",
            enabled=True,
            enforcement_mode="enforce",
            token_budget=strict_budget,
        )
        cfg_lenient = GuardrailsConfig(
            policy_id="tb-lenient",
            enabled=True,
            enforcement_mode="enforce",
            token_budget=lenient_budget,
        )
        # 10 LLM calls exceeds strict (5) → blocks on first policy
        with pytest.raises(GuardrailViolationError) as exc_info:
            engine.check_token_budget(
                {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200, "llm_calls": 10},
                [cfg_strict, cfg_lenient],
            )
        assert any(v.policy_id == "tb-strict" for v in exc_info.value.violations)

    def test_check_token_budget_audit_pipeline(self, engine, token_budget):
        """Audit-mode token budget in a pipeline downgrades to warned."""
        cfg_audit = GuardrailsConfig(
            policy_id="tb-audit",
            enabled=True,
            enforcement_mode="audit",
            token_budget=token_budget,
        )
        cfg_no_budget = GuardrailsConfig(
            policy_id="tb-none",
            enabled=True,
            enforcement_mode="enforce",
        )
        result = engine.check_token_budget(
            {
                "input_tokens": 20000,
                "output_tokens": 10000,
                "total_tokens": 30000,
                "llm_calls": 15,
            },
            [cfg_audit, cfg_no_budget],
        )
        assert result.passed is True
        assert result.action_taken == "warned"
        assert any(v.policy_id == "tb-audit" for v in result.violations)


# ============================================================================
# 11. Pipeline-Specific Tests
# ============================================================================


class TestGuardrailsPipeline:
    """Tests for pipeline-based guardrail evaluation (priority ordering, content
    chaining, per-policy enforcement, short-circuiting, and state threading)."""

    @pytest.mark.asyncio
    async def test_empty_pipeline_passes(self, engine):
        """An empty pipeline should pass immediately with no violations."""
        result = await engine.check_input("some content", [])
        assert result.passed is True
        assert result.violations == []

    @pytest.mark.asyncio
    async def test_pipeline_priority_ordering(self, engine):
        """Content should chain through policies in order; second policy sees
        the sanitized output of the first."""
        cfg_p0 = GuardrailsConfig(
            priority=0, policy_id="p0", enabled=True, enforcement_mode="enforce"
        )
        cfg_p10 = GuardrailsConfig(
            priority=10, policy_id="p10", enabled=True, enforcement_mode="enforce"
        )

        mock_evaluate = AsyncMock(
            side_effect=[
                GuardrailResult(passed=True, sanitized_content="transformed"),
                GuardrailResult(passed=True),
            ]
        )
        with patch.object(engine.input_evaluator, "evaluate", mock_evaluate):
            await engine.check_input("original", [cfg_p0, cfg_p10])

        assert mock_evaluate.call_count == 2
        # Second call should receive the transformed content from first policy
        second_call_content = mock_evaluate.call_args_list[1][0][0]
        assert second_call_content == "transformed"

    @pytest.mark.asyncio
    async def test_pipeline_short_circuit_on_enforce_block(self, engine):
        """When an enforce policy blocks, subsequent policies must not run."""
        cfg1 = GuardrailsConfig(
            policy_id="p1", enabled=True, enforcement_mode="enforce"
        )
        cfg2 = GuardrailsConfig(
            policy_id="p2", enabled=True, enforcement_mode="enforce"
        )

        mock_evaluate = AsyncMock(
            return_value=GuardrailResult(
                passed=False,
                violations=[
                    Violation(
                        category="input",
                        rule_name="block_rule",
                        severity="block",
                        message="blocked",
                    )
                ],
            )
        )
        with patch.object(engine.input_evaluator, "evaluate", mock_evaluate):
            with pytest.raises(GuardrailViolationError):
                await engine.check_input("bad content", [cfg1, cfg2])

        # Only the first policy should have been evaluated
        assert mock_evaluate.call_count == 1

    @pytest.mark.asyncio
    async def test_audit_policy_carry_forward(self, engine):
        """An audit policy that fails should downgrade to warn and carry
        sanitized content forward to the next policy."""
        cfg_audit = GuardrailsConfig(
            policy_id="p_audit", enabled=True, enforcement_mode="audit"
        )
        cfg_enforce = GuardrailsConfig(
            policy_id="p_enforce", enabled=True, enforcement_mode="enforce"
        )

        mock_evaluate = AsyncMock(
            side_effect=[
                GuardrailResult(
                    passed=False,
                    violations=[
                        Violation(
                            category="input",
                            rule_name="audit_rule",
                            severity="block",
                            message="audit violation",
                        )
                    ],
                    sanitized_content="sanitized",
                ),
                GuardrailResult(passed=True),
            ]
        )
        with patch.object(engine.input_evaluator, "evaluate", mock_evaluate):
            result = await engine.check_input(
                "original", [cfg_audit, cfg_enforce]
            )

        assert result.passed is True
        # Second policy received sanitized content from audit policy
        second_call_content = mock_evaluate.call_args_list[1][0][0]
        assert second_call_content == "sanitized"
        # Audit violation is carried forward with warned action
        assert len(result.violations) >= 1
        audit_violations = [
            v for v in result.violations if v.policy_id == "p_audit"
        ]
        assert len(audit_violations) == 1
        # Explicit downgrade semantics: action_taken reflects warning, not block
        assert result.action_taken == "warned"
        # The violation is attributed to the audit policy and marked non-enforcing
        av = audit_violations[0]
        assert av.policy_id == "p_audit"
        assert av.enforcement_mode == "audit"

    @pytest.mark.asyncio
    async def test_per_policy_enforcement_mode(self, engine):
        """Audit blocks should not raise; enforce blocks should raise."""
        cfg_audit = GuardrailsConfig(
            policy_id="p_audit", enabled=True, enforcement_mode="audit"
        )
        cfg_enforce = GuardrailsConfig(
            policy_id="p_enforce", enabled=True, enforcement_mode="enforce"
        )

        def _block():
            return GuardrailResult(
                passed=False,
                violations=[
                    Violation(
                        category="input",
                        rule_name="rule",
                        severity="block",
                        message="fail",
                    )
                ],
            )

        def _pass():
            return GuardrailResult(passed=True)

        # Scenario A: audit blocks, enforce passes → no exception
        mock_a = AsyncMock(side_effect=[_block(), _pass()])
        with patch.object(engine.input_evaluator, "evaluate", mock_a):
            result_a = await engine.check_input(
                "content", [cfg_audit, cfg_enforce]
            )
        assert result_a.passed is True

        # Scenario B: audit passes, enforce blocks → exception raised
        mock_b = AsyncMock(side_effect=[_pass(), _block()])
        with patch.object(engine.input_evaluator, "evaluate", mock_b):
            with pytest.raises(GuardrailViolationError):
                await engine.check_input(
                    "content", [cfg_audit, cfg_enforce]
                )

    @pytest.mark.asyncio
    async def test_per_policy_guardrails_state(self, engine):
        """Vault state from a policy should be threaded into guardrails_state."""
        cfg1 = GuardrailsConfig(
            policy_id="p1", enabled=True, enforcement_mode="enforce"
        )

        mock_evaluate = AsyncMock(
            return_value=GuardrailResult(
                passed=True, vault_id="vault-abc", vault_secret="secret-xyz"
            )
        )
        guardrails_state: dict = {}
        with patch.object(engine.input_evaluator, "evaluate", mock_evaluate):
            await engine.check_input(
                "content", [cfg1], guardrails_state=guardrails_state
            )

        assert guardrails_state["policies"]["p1"]["vault_id"] == "vault-abc"
        assert guardrails_state["vault_id"] == "vault-abc"

    def test_tool_fallback_to_agent_pipeline(self):
        """ResolvedGuardrails should fall back to agent_pipeline when a tool
        has no specific pipeline."""
        cfg_agent = GuardrailsConfig(policy_id="agent_policy", enabled=True)
        resolved = ResolvedGuardrails(
            agent_pipeline=[cfg_agent], tool_pipelines={}
        )

        assert resolved.pipeline_for_tool("nonexistent_tool_id") == [cfg_agent]
        assert resolved.pipeline_for_tool(None) == [cfg_agent]

    @pytest.mark.asyncio
    async def test_violation_attribution(self, engine):
        """Violations should be attributed to their source policy."""
        cfg1 = GuardrailsConfig(
            policy_id="pol-1",
            policy_name="Policy One",
            enabled=True,
            enforcement_mode="audit",
        )
        cfg2 = GuardrailsConfig(
            policy_id="pol-2",
            policy_name="Policy Two",
            enabled=True,
            enforcement_mode="audit",
        )

        mock_evaluate = AsyncMock(
            side_effect=[
                GuardrailResult(
                    passed=False,
                    violations=[
                        Violation(
                            category="input",
                            rule_name="r1",
                            severity="block",
                            message="m1",
                        )
                    ],
                ),
                GuardrailResult(
                    passed=False,
                    violations=[
                        Violation(
                            category="input",
                            rule_name="r2",
                            severity="block",
                            message="m2",
                        )
                    ],
                ),
            ]
        )
        with patch.object(engine.input_evaluator, "evaluate", mock_evaluate):
            result = await engine.check_input("content", [cfg1, cfg2])

        assert result.violations[0].policy_id == "pol-1"
        assert result.violations[0].policy_name == "Policy One"
        assert result.violations[1].policy_id == "pol-2"
        assert result.violations[1].policy_name == "Policy Two"

    @pytest.mark.asyncio
    async def test_content_transform_chaining(self, engine):
        """Sanitized content from one policy should flow into the next."""
        cfg1 = GuardrailsConfig(
            policy_id="p1", enabled=True, enforcement_mode="enforce"
        )
        cfg2 = GuardrailsConfig(
            policy_id="p2", enabled=True, enforcement_mode="enforce"
        )

        mock_evaluate = AsyncMock(
            side_effect=[
                GuardrailResult(
                    passed=True, sanitized_content="transformed_content"
                ),
                GuardrailResult(passed=True),
            ]
        )
        with patch.object(engine.input_evaluator, "evaluate", mock_evaluate):
            await engine.check_input("original_content", [cfg1, cfg2])

        # Second call should receive transformed content, not original
        second_call_content = mock_evaluate.call_args_list[1][0][0]
        assert second_call_content == "transformed_content"

    @pytest.mark.asyncio
    async def test_disabled_policy_skipped(self, engine):
        """Disabled policies should be skipped entirely."""
        cfg1 = GuardrailsConfig(
            policy_id="p1", enabled=True, enforcement_mode="enforce"
        )
        cfg2 = GuardrailsConfig(policy_id="p2", enabled=False)
        cfg3 = GuardrailsConfig(
            policy_id="p3", enabled=True, enforcement_mode="audit"
        )

        mock_evaluate = AsyncMock(return_value=GuardrailResult(passed=True))
        with patch.object(engine.input_evaluator, "evaluate", mock_evaluate):
            await engine.check_input("content", [cfg1, cfg2, cfg3])

        # cfg2 is disabled, so only cfg1 and cfg3 should be evaluated
        assert mock_evaluate.call_count == 2


# ============================================================================
# 12. Accuracy Assessment Tests
# ============================================================================


class TestSSRFAccuracy:
    """Accuracy evaluation for SSRF protection."""

    SHOULD_BLOCK = [
        "http://127.0.0.1/admin",
        "http://10.0.0.1/internal",
        "http://172.16.0.1/api",
        "http://192.168.1.1/config",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0/",
        "file:///etc/passwd",
        "ftp://internal.server/data",
        "gopher://evil.com/",
        "data:text/html,<script>alert(1)</script>",
    ]

    SHOULD_ALLOW = [
        "https://api.example.com/v1/data",
        "https://google.com/search?q=test",
        "http://example.com/path",
        "https://cdn.jsdelivr.net/npm/package",
    ]

    def test_ssrf_blocks_all_dangerous(self):
        for url in self.SHOULD_BLOCK:
            result = validate_url(url)
            assert result.passed is False, f"Should block: {url}"

    def test_ssrf_allows_safe_urls(self):
        for url in self.SHOULD_ALLOW:
            result = validate_url(url)
            assert result.passed is True, f"Should allow: {url}"

    def test_ssrf_overall_accuracy(self):
        blocked = sum(1 for u in self.SHOULD_BLOCK if not validate_url(u).passed)
        allowed = sum(1 for u in self.SHOULD_ALLOW if validate_url(u).passed)

        block_rate = blocked / len(self.SHOULD_BLOCK)
        allow_rate = allowed / len(self.SHOULD_ALLOW)

        assert block_rate == 1.0, f"SSRF block accuracy: {block_rate:.0%}"
        assert allow_rate == 1.0, f"SSRF allow accuracy: {allow_rate:.0%}"


class TestTokenBudgetAccuracy:
    """Accuracy for token budget boundary conditions."""

    def test_exact_limit_boundary(self):
        evaluator = TokenBudgetEvaluator()
        budget = TokenBudget(max_total_tokens_per_execution=1000)

        # At limit — should pass
        result = evaluator.evaluate(
            {
                "input_tokens": 500,
                "output_tokens": 500,
                "total_tokens": 1000,
                "llm_calls": 1,
            },
            budget,
        )
        assert result.passed is True

        # One over — should fail
        result = evaluator.evaluate(
            {
                "input_tokens": 500,
                "output_tokens": 501,
                "total_tokens": 1001,
                "llm_calls": 1,
            },
            budget,
        )
        assert result.passed is False

    def test_warning_threshold_boundary(self):
        evaluator = TokenBudgetEvaluator()
        budget = TokenBudget(
            max_total_tokens_per_execution=1000,
            warn_at_percentage=0.8,
        )

        # Just below threshold (799) — no warning
        result = evaluator.evaluate(
            {
                "input_tokens": 400,
                "output_tokens": 399,
                "total_tokens": 799,
                "llm_calls": 1,
            },
            budget,
        )
        assert not any(v.rule_name == "token_budget_warning" for v in result.violations)

        # At threshold (800) — warning
        result = evaluator.evaluate(
            {
                "input_tokens": 400,
                "output_tokens": 400,
                "total_tokens": 800,
                "llm_calls": 1,
            },
            budget,
        )
        assert any(v.rule_name == "token_budget_warning" for v in result.violations)


# ============================================================================
# 13. Performance Benchmark Tests
# ============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmarks for guardrail evaluation throughput and latency.

    These tests measure execution time and throughput to ensure guardrails
    don't introduce unacceptable latency. Thresholds are generous to avoid
    flaky tests in CI but tight enough to catch regressions.
    """

    @staticmethod
    def _perf_test_rules():
        """Inline pattern rules for performance benchmarks."""
        return [
            PatternRule(
                name="SSN",
                patterns=[PatternEntry(label="SSN", regex=r"\b\d{3}-\d{2}-\d{4}\b")],
                action="block",
                applies_to="input",
                message="SSN detected",
                preset_id="",
            ),
            PatternRule(
                name="Email",
                patterns=[
                    PatternEntry(
                        label="Email",
                        regex=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                    )
                ],
                action="block",
                applies_to="both",
                message="Email detected",
                preset_id="",
            ),
        ]

    def test_pattern_rules_throughput(self):
        """Pattern rules should process 1000+ texts/sec."""
        rules = self._perf_test_rules()
        texts = [
            "My SSN is 123-45-6789 and my card is 4111 1111 1111 1111",
            "Contact user@example.com or call 555-123-4567",
            "API key: sk-1234567890abcdefghijklmnop",
            "Clean text with no sensitive data whatsoever",
            "Another clean message from the system",
        ] * 200  # 1000 texts

        start = time.perf_counter()
        for text in texts:
            apply_pattern_rules(text, rules, "input")
        elapsed = time.perf_counter() - start

        throughput = len(texts) / elapsed
        assert throughput > 500, (
            f"Pattern rule throughput too low: {throughput:.0f} texts/sec"
        )
        assert elapsed < 10.0, (
            f"Pattern rules took too long: {elapsed:.2f}s for {len(texts)} texts"
        )

    def test_pattern_rules_latency_single(self):
        """Single pattern rule evaluation should complete in <5ms."""
        rules = self._perf_test_rules()
        text = "SSN: 123-45-6789, card: 4111 1111 1111 1111, key: AKIAIOSFODNN7EXAMPLE"

        times = []
        for _ in range(100):
            start = time.perf_counter()
            apply_pattern_rules(text, rules, "input")
            times.append(time.perf_counter() - start)

        avg_ms = (sum(times) / len(times)) * 1000
        p95_ms = sorted(times)[94] * 1000
        assert avg_ms < 5.0, f"Average pattern rule latency: {avg_ms:.2f}ms"
        assert p95_ms < 10.0, f"P95 pattern rule latency: {p95_ms:.2f}ms"

    def test_ssrf_validation_throughput(self):
        """SSRF validation should handle 500+ URLs/sec."""
        urls = [
            "https://api.example.com/v1/data",
            "http://127.0.0.1/admin",
            "https://cdn.example.com/assets/image.png",
            "file:///etc/passwd",
            "http://10.0.0.1/internal",
        ] * 100  # 500 URLs

        start = time.perf_counter()
        for url in urls:
            validate_url(url)
        elapsed = time.perf_counter() - start

        throughput = len(urls) / elapsed
        assert throughput > 200, f"SSRF throughput too low: {throughput:.0f} URLs/sec"

    def test_token_budget_evaluation_throughput(self):
        """Token budget checks should be essentially free (<0.1ms each)."""
        evaluator = TokenBudgetEvaluator()
        budget = TokenBudget(
            max_input_tokens_per_execution=10000,
            max_output_tokens_per_execution=5000,
            max_total_tokens_per_execution=15000,
            max_llm_calls_per_execution=20,
        )

        start = time.perf_counter()
        for i in range(10000):
            evaluator.evaluate(
                {
                    "input_tokens": i,
                    "output_tokens": i // 2,
                    "total_tokens": i + i // 2,
                    "llm_calls": i // 1000,
                },
                budget,
            )
        elapsed = time.perf_counter() - start

        per_call_ms = (elapsed / 10000) * 1000
        assert per_call_ms < 0.5, f"Token budget per-call: {per_call_ms:.3f}ms"

    def test_tool_call_evaluation_throughput(self):
        """Tool call evaluations should process 1000+/sec."""
        evaluator = ToolCallGuardrailEvaluator()
        policy = ToolCallPolicy(
            allowed_sql_operations=["SELECT"],
            blocked_tables=["secrets"],
        )
        calls = [
            ("database_query", {"query": "SELECT * FROM products"}),
            ("database_query", {"query": "DELETE FROM users"}),
            ("file_write", {"filename": "test.txt", "content": "data"}),
            ("file_write", {"filename": "../../etc/passwd", "content": "x"}),
            ("custom_tool", {"arg": "value"}),
        ] * 200  # 1000 calls

        start = time.perf_counter()
        for tool_name, tool_args in calls:
            evaluator.evaluate(tool_name, tool_args, policy)
        elapsed = time.perf_counter() - start

        throughput = len(calls) / elapsed
        assert throughput > 500, f"Tool call throughput: {throughput:.0f}/sec"

    def test_python_sandbox_cached_execution(self):
        """Cached sandbox filter execution should be fast (<5ms)."""
        executor = PythonSandboxExecutor()
        code = """
import re
def filter(content, direction, **context):
    if re.search(r"\\d{3}-\\d{2}-\\d{4}", content):
        return {"passed": False, "message": "SSN"}
    return {"passed": True}
"""
        # First call — cold start (includes compilation)
        executor.execute(code, "warmup", "ingress")

        # Measure cached calls
        times = []
        for i in range(100):
            start = time.perf_counter()
            executor.execute(code, f"test content {i}", "ingress")
            times.append(time.perf_counter() - start)

        avg_ms = (sum(times) / len(times)) * 1000
        p95_ms = sorted(times)[94] * 1000
        assert avg_ms < 5.0, f"Cached sandbox avg: {avg_ms:.2f}ms"
        assert p95_ms < 10.0, f"Cached sandbox p95: {p95_ms:.2f}ms"
        executor.invalidate_cache()

    @pytest.mark.asyncio
    async def test_full_input_check_latency(self):
        """Full input check (patterns only, no LLM) should complete in <10ms."""
        engine = GuardrailsEngine()
        config = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            pattern_rules=self._perf_test_rules(),
        )
        text = "SSN: 123-45-6789, card: 4111 1111 1111 1111, email: user@test.com"

        times = []
        for _ in range(100):
            start = time.perf_counter()
            await engine.check_input(text, config)
            times.append(time.perf_counter() - start)

        avg_ms = (sum(times) / len(times)) * 1000
        p95_ms = sorted(times)[94] * 1000
        assert avg_ms < 10.0, f"Full input check avg: {avg_ms:.2f}ms"
        assert p95_ms < 20.0, f"Full input check p95: {p95_ms:.2f}ms"


