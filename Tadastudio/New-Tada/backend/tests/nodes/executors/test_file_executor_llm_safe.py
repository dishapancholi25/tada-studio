from types import SimpleNamespace

from backend.services.file_content_references import (
    clear_file_content_references,
    get_file_content_reference_metadata,
    register_file_content_reference,
    resolve_file_content_references,
)
from backend.services.nodes.executors.file import FileNodeExecutor


def test_llm_safe_raw_binary_output_uses_reference_and_preserves_raw_content():
    clear_file_content_references()
    executor = FileNodeExecutor()
    node = SimpleNamespace(name="File read 1", uniq_id="file-node-1")
    state = {
        "execution_id": "exec-1",
        "db_execution_id": "db-1",
        "execution_order": 0,
    }
    raw_content = "JVBERi0xLjYKbase64"
    node_output = {
        "content": "[Binary file: payslip.pdf, size: 12 bytes, base64 encoded]",
        "raw_content": raw_content,
        "metadata": {
            "filename": "payslip.pdf",
            "file_size_mb": 0.01,
            "file_type": ".pdf",
            "content_type": "base64",
        },
        "extraction_method": "raw",
        "llm_safe_output_enabled": True,
    }

    update = executor._build_state_update(node, node_output, state)

    assert raw_content not in update["messages"][0].content
    assert raw_content not in update["node_output"]["raw"]
    assert update["node_output"]["fields"]["raw_content"] == raw_content
    assert update["file_raw_content"] == raw_content
    assert update["file_content_is_llm_safe"] is True
    assert resolve_file_content_references(
        update["file_content_ref"],
        strict=True,
    ) == raw_content


def test_file_content_reference_resolves_exact_bare_key():
    clear_file_content_references()
    raw_content = "JVBERi0xLjYKbase64"
    token = register_file_content_reference(
        raw_content,
        metadata={"filename": "salary_certificate.pdf"},
    )
    bare_key = token.replace("{{file_content_ref:", "").replace("}}", "")

    assert resolve_file_content_references(bare_key, strict=True) == raw_content
    assert get_file_content_reference_metadata(bare_key) == {
        "filename": "salary_certificate.pdf"
    }


def test_http_parameter_resolution_resolves_bare_file_ref_and_uses_stored_filename():
    clear_file_content_references()
    raw_content = "JVBERi0xLjYKbase64"
    token = register_file_content_reference(
        raw_content,
        metadata={"filename": "salary_certificate.pdf"},
    )
    bare_key = token.replace("{{file_content_ref:", "").replace("}}", "")

    from backend.tools.http_request.handlers import resolve_runtime_parameter_references

    resolved = resolve_runtime_parameter_references(
        {
            "base64": bare_key,
            "fileName": "test",
            "caseId": "test",
        }
    )

    assert resolved["base64"] == raw_content
    assert resolved["fileName"] == "salarycertificate.pdf"
    assert resolved["caseId"] == "test"


def test_bare_32_hex_value_is_not_treated_as_missing_reference():
    """A 32-hex-char value (e.g. a clientid) must not be mistaken for a stale ref."""
    clear_file_content_references()
    clientid = "f788b425400c66cc010f59c247535cde"

    # In strict mode, a 32-hex string that is not a stored reference must pass
    # through unchanged rather than raising "File content reference is no longer
    # available."
    assert resolve_file_content_references(clientid, strict=True) == clientid


def test_http_parameter_resolution_passes_through_bare_32_hex_clientid():
    clear_file_content_references()

    from backend.tools.http_request.handlers import resolve_runtime_parameter_references

    resolved = resolve_runtime_parameter_references(
        {
            "clientid": "f788b425400c66cc010f59c247535cde",
            "cis_number": "015790091",
            "lookback_days": "20",
        }
    )

    assert resolved == {
        "clientid": "f788b425400c66cc010f59c247535cde",
        "cis_number": "015790091",
        "lookback_days": "20",
    }


def test_missing_explicit_token_still_raises_in_strict_mode():
    clear_file_content_references()
    stale_token = "{{file_content_ref:" + "a" * 32 + "}}"

    import pytest

    with pytest.raises(KeyError):
        resolve_file_content_references(stale_token, strict=True)


def test_exact_file_ref_delegation_task_is_enriched_with_tool_instructions():
    clear_file_content_references()
    token = register_file_content_reference(
        "JVBERi0xLjYKbase64",
        metadata={"filename": "salary_certificate.pdf"},
    )

    from backend.services.delegation.factories.sync_factory import (
        _prepare_file_reference_task_description,
    )

    task_description = _prepare_file_reference_task_description(token)

    assert token in task_description
    assert "Filename: salary_certificate.pdf" in task_description
    assert "pass the File/base64 payload value exactly" in task_description
