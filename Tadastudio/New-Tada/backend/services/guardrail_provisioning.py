"""Shared guardrail model-provisioning helpers — single source of truth.

Consolidates the logic that used to be duplicated across:
  * backend/scripts/download_all_models.py      (standalone / Docker bake)
  * backend/services/guardrails/backends/local.py               (app self-provisioning)
  * backend/services/guardrails/filters/executors/python_sandbox.py  (sets HF_HOME)

Provides:
  * ``resolve_models_dir()`` / ``default_models_dir()`` — where local-mode
    guardrail models live (``GUARDRAIL_MODELS_DIR`` or the repo-local
    ``models/guardrail`` folder, mirroring the container's /app/models/guardrail).
  * ``ensure_corporate_ca_bundle()`` — make Python/requests trust the corporate
    TLS proxy CA before any HuggingFace download (certifi + the Windows trust
    store on Windows + the repo's committed certs on every OS).
  * ``ensure_spacy_en_core_web_lg()`` — download/load the spaCy English model
    used by the PII scanners (the 13th model).

Kept dependency-light: only the stdlib is imported at module load, and
``certifi`` / ``ssl`` / ``spacy`` are imported inside the functions, so the
standalone download script can import this *before* the heavy ML libraries and
without dragging in the guardrails engine.
"""

from __future__ import annotations

import glob
import logging
import os

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Where the guardrail models live
# ---------------------------------------------------------------------------
def default_models_dir() -> str:
    """Repo-local ``models/guardrail`` folder (mirrors the container's
    /app/models/guardrail). This file is at ``backend/services/`` so the repo
    root is two levels up."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    return os.path.join(repo_root, "models", "guardrail")


def resolve_models_dir() -> str:
    """The ``GUARDRAIL_MODELS_DIR`` override if set, else the repo-local default."""
    return os.environ.get("GUARDRAIL_MODELS_DIR") or default_models_dir()


# ---------------------------------------------------------------------------
# Corporate TLS: trust the proxy CA before any HuggingFace download
# ---------------------------------------------------------------------------
_ca_bundle_ready = False


def _repo_ca_cert_dirs() -> list:
    """Directories holding the committed corporate CA certs (``certs/`` and
    ``backend/certs/``), found by walking up from this file. These make the
    corporate proxy trusted on macOS / Linux, where there is no Windows trust
    store to read. Override the search with ``GUARDRAIL_CA_CERTS_DIR``."""
    dirs: list = []
    seen = set()
    env_dir = os.environ.get("GUARDRAIL_CA_CERTS_DIR")
    candidates = [env_dir] if env_dir else []
    directory = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        candidates.append(os.path.join(directory, "certs"))
        candidates.append(os.path.join(directory, "backend", "certs"))
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    for cand in candidates:
        if not cand:
            continue
        path = os.path.abspath(cand)
        if path not in seen and os.path.isdir(path):
            seen.add(path)
            dirs.append(path)
    return dirs


def _load_repo_ca_pems() -> list:
    """Read committed corporate CA certs into clean PEM ``CERTIFICATE`` blocks.

    Only real X.509 ``CERTIFICATE`` blocks are kept: ``TRUSTED CERTIFICATE`` and
    other non-cert PEM types are skipped, and DER files are validated via
    ``cryptography`` before conversion. This matters because a single bogus block
    makes OpenSSL reject the WHOLE bundle ('[X509] PEM lib'), which would break
    every model download."""
    import re

    cert_re = re.compile(
        rb"-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----", re.DOTALL
    )
    blocks: list = []
    seen = set()

    def _add(pem: str) -> None:
        pem = pem.strip()
        if pem and pem not in seen:
            seen.add(pem)
            blocks.append(pem)

    for directory in _repo_ca_cert_dirs():
        for pattern in ("*.crt", "*.cer", "*.pem"):
            for path in sorted(glob.glob(os.path.join(directory, pattern))):
                try:
                    with open(path, "rb") as handle:
                        raw = handle.read()
                    if b"-----BEGIN CERTIFICATE-----" in raw:
                        for match in cert_re.findall(raw):
                            _add(match.decode("ascii", "ignore"))
                    else:  # DER-encoded cert: validate + convert.
                        from cryptography import x509
                        from cryptography.hazmat.primitives import serialization

                        cert = x509.load_der_x509_certificate(raw)
                        _add(cert.public_bytes(serialization.Encoding.PEM).decode("ascii"))
                except Exception:
                    continue
    return blocks


def ensure_corporate_ca_bundle(cache_dir: str | None = None) -> None:
    """Build a CA bundle (certifi + Windows trust store on Windows + the repo's
    committed corporate certs) and point requests/ssl at it, so model downloads
    succeed behind the corporate TLS proxy. Runs once; safe to call repeatedly.
    No-op if ``REQUESTS_CA_BUNDLE`` already points at a valid file."""
    global _ca_bundle_ready
    if _ca_bundle_ready:
        return
    _ca_bundle_ready = True  # attempt only once, even on failure
    try:
        existing = os.environ.get("REQUESTS_CA_BUNDLE")
        if existing and os.path.exists(existing):
            logger.info("[guardrails] using existing REQUESTS_CA_BUNDLE -> %s", existing)
            return

        pem_blocks: list = []
        if os.name == "nt":
            try:
                import ssl

                for store in ("ROOT", "CA"):
                    try:
                        for cert_bytes, encoding, _trust in ssl.enum_certificates(store):
                            if encoding == "x509_asn":
                                pem_blocks.append(ssl.DER_cert_to_PEM_cert(cert_bytes))
                    except Exception:
                        continue
            except Exception:
                pass
        pem_blocks.extend(_load_repo_ca_pems())
        if not pem_blocks:
            return

        base = ""
        try:
            import certifi

            with open(certifi.where(), "r", encoding="utf-8") as handle:
                base = handle.read()
        except Exception:
            base = ""

        target = cache_dir or resolve_models_dir()
        os.makedirs(target, exist_ok=True)
        bundle = os.path.join(target, "corporate_ca.pem")
        with open(bundle, "w", encoding="utf-8") as handle:
            handle.write(base.rstrip() + "\n" + "\n".join(pem_blocks) + "\n")

        os.environ["REQUESTS_CA_BUNDLE"] = bundle
        os.environ["SSL_CERT_FILE"] = bundle
        os.environ["CURL_CA_BUNDLE"] = bundle
        logger.info(
            "[guardrails] wrote corporate CA bundle -> %s (%d certs)", bundle, len(pem_blocks)
        )
    except Exception as exc:  # never fatal -- plain certifi may already work
        logger.warning("[guardrails] could not build corporate CA bundle: %s", exc)


# ---------------------------------------------------------------------------
# spaCy English model (used by the Presidio-based PII scanners)
# ---------------------------------------------------------------------------
def ensure_spacy_en_core_web_lg() -> None:
    """Ensure the spaCy ``en_core_web_lg`` model is present (download if not).

    This is the 13th local-mode model: it is a pip-installed spaCy package, not
    an entry in the HuggingFace cache, so it must be provisioned separately."""
    import spacy

    try:
        spacy.load("en_core_web_lg")
    except OSError:
        from spacy.cli import download as spacy_download

        spacy_download("en_core_web_lg")
        spacy.load("en_core_web_lg")
