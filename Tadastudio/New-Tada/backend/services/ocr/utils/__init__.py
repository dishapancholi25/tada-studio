"""Utility modules for OCR services."""

from .encoding import encode_image
from .file_handling import get_file_extension, load_file_bytes, validate_file_size
from .result_builder import build_error_response, build_success_response


__all__ = [
    "encode_image",
    "load_file_bytes",
    "validate_file_size",
    "get_file_extension",
    "build_success_response",
    "build_error_response",
]
