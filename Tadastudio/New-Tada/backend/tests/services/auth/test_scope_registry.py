"""Tests for the PAT scope registry.

Covers:
- is_valid_scope: static catalogue entries + named-resource pattern
- is_admin_only_scope: admin ceiling rules
- validate_scopes: list validation with error on unknowns
- get_user_available_scope_definitions: role-based filtering
"""

import pytest

from backend.services.auth.scope_registry import (
    is_admin_only_scope,
    is_valid_scope,
    validate_scopes,
    get_user_available_scope_definitions,
    VALID_SCOPES,
    ADMIN_ONLY_SCOPES,
)


# ---------------------------------------------------------------------------
# is_valid_scope
# ---------------------------------------------------------------------------


class TestIsValidScope:
    def test_wildcard_catalogue_scopes_are_valid(self):
        for scope in VALID_SCOPES:
            assert is_valid_scope(scope), f"Expected {scope!r} to be valid"

    def test_named_workflow_execute_is_valid(self):
        assert is_valid_scope("workflow:my-flow:execute")

    def test_named_workflow_read_is_valid(self):
        assert is_valid_scope("workflow:my-flow:read")

    def test_named_workflow_write_is_valid(self):
        assert is_valid_scope("workflow:my-flow:write")

    def test_named_document_read_is_valid(self):
        assert is_valid_scope("document:my-doc:read")

    def test_named_datasource_write_is_valid(self):
        assert is_valid_scope("datasource:my-ds:write")

    def test_named_memory_read_is_valid(self):
        assert is_valid_scope("memory:agent-1:read")

    def test_named_execution_read_is_valid(self):
        assert is_valid_scope("execution:run-1:read")

    def test_wildcard_name_is_invalid(self):
        # "workflow:*:execute" is valid (in catalogue), but "workflow:*:bogus" is not
        assert not is_valid_scope("workflow:*:bogus")

    def test_unknown_resource_is_invalid(self):
        assert not is_valid_scope("settings:*:read")

    def test_missing_action_part_is_invalid(self):
        assert not is_valid_scope("workflow:my-flow")

    def test_empty_string_is_invalid(self):
        assert not is_valid_scope("")

    def test_extra_colon_segments_invalid(self):
        assert not is_valid_scope("workflow:my:flow:execute")

    def test_asterisk_in_name_is_invalid(self):
        # asterisk in the name part should not match named-resource pattern
        assert not is_valid_scope("workflow:my*flow:execute")

    def test_api_star_is_valid(self):
        assert is_valid_scope("api:*")


# ---------------------------------------------------------------------------
# is_admin_only_scope
# ---------------------------------------------------------------------------


class TestIsAdminOnlyScope:
    def test_api_star_is_admin_only(self):
        assert is_admin_only_scope("api:*")

    def test_workflow_star_write_is_admin_only(self):
        assert is_admin_only_scope("workflow:*:write")

    def test_workflow_named_write_is_admin_only(self):
        assert is_admin_only_scope("workflow:my-flow:write")

    def test_document_read_is_admin_only(self):
        assert is_admin_only_scope("document:*:read")

    def test_document_write_is_admin_only(self):
        assert is_admin_only_scope("document:*:write")

    def test_datasource_read_is_admin_only(self):
        assert is_admin_only_scope("datasource:*:read")

    def test_execution_read_is_admin_only(self):
        assert is_admin_only_scope("execution:*:read")

    def test_memory_read_is_admin_only(self):
        assert is_admin_only_scope("memory:*:read")

    def test_memory_write_is_admin_only(self):
        assert is_admin_only_scope("memory:*:write")

    def test_workflow_star_execute_not_admin_only(self):
        assert not is_admin_only_scope("workflow:*:execute")

    def test_workflow_star_read_not_admin_only(self):
        assert not is_admin_only_scope("workflow:*:read")

    def test_workflow_named_execute_not_admin_only(self):
        assert not is_admin_only_scope("workflow:my-flow:execute")

    def test_workflow_named_read_not_admin_only(self):
        assert not is_admin_only_scope("workflow:my-flow:read")

    def test_all_admin_only_scopes_in_set(self):
        for scope in ADMIN_ONLY_SCOPES:
            assert is_admin_only_scope(scope), f"Expected {scope!r} to be admin-only"


# ---------------------------------------------------------------------------
# validate_scopes
# ---------------------------------------------------------------------------


class TestValidateScopes:
    def test_valid_list_passes_through(self):
        scopes = ["workflow:*:execute", "workflow:*:read"]
        assert validate_scopes(scopes) == scopes

    def test_empty_list_passes(self):
        assert validate_scopes([]) == []

    def test_named_scope_in_list_passes(self):
        scopes = ["workflow:my-flow:execute"]
        assert validate_scopes(scopes) == scopes

    def test_invalid_scope_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown scopes"):
            validate_scopes(["workflow:*:execute", "bogus:scope"])

    def test_error_message_includes_bad_scope(self):
        with pytest.raises(ValueError, match="bogus:scope"):
            validate_scopes(["bogus:scope"])

    def test_all_invalid_raises(self):
        with pytest.raises(ValueError):
            validate_scopes(["bad1", "bad2"])


# ---------------------------------------------------------------------------
# get_user_available_scope_definitions
# ---------------------------------------------------------------------------


class TestGetUserAvailableScopeDefinitions:
    def test_admin_gets_all_scopes(self):
        defs = get_user_available_scope_definitions(is_admin=True, restrict_to_workflow=False)
        scopes = [d["scope"] for d in defs]
        assert "api:*" in scopes
        assert "workflow:*:execute" in scopes
        assert "document:*:read" in scopes

    def test_admin_gets_all_scopes_even_with_restriction(self):
        defs = get_user_available_scope_definitions(is_admin=True, restrict_to_workflow=True)
        scopes = [d["scope"] for d in defs]
        assert "api:*" in scopes
        assert "document:*:read" in scopes

    def test_non_admin_restricted_gets_only_workflow(self):
        defs = get_user_available_scope_definitions(is_admin=False, restrict_to_workflow=True)
        resources = {d["resource"] for d in defs}
        assert resources == {"workflow"}
        scopes = [d["scope"] for d in defs]
        assert "document:*:read" not in scopes
        assert "api:*" not in scopes

    def test_non_admin_unrestricted_gets_non_admin_only(self):
        defs = get_user_available_scope_definitions(is_admin=False, restrict_to_workflow=False)
        for d in defs:
            assert not d["admin_only"], f"Non-admin got admin-only scope: {d['scope']}"

    def test_non_admin_unrestricted_includes_workflow_execute(self):
        defs = get_user_available_scope_definitions(is_admin=False, restrict_to_workflow=False)
        scopes = [d["scope"] for d in defs]
        assert "workflow:*:execute" in scopes

    def test_all_defs_have_required_keys(self):
        defs = get_user_available_scope_definitions(is_admin=True, restrict_to_workflow=False)
        for d in defs:
            for key in ("scope", "label", "description", "resource", "action", "admin_only"):
                assert key in d, f"Missing key {key!r} in {d}"
