"""Custom exceptions for Wiki API.

This module defines a hierarchy of custom exceptions for the Wiki API,
providing structured error handling with appropriate HTTP status codes.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException


class WikiAPIException(HTTPException):
    """Base exception for Wiki API errors."""

    def __init__(
        self, status_code: int, detail: str, headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class WikiPageNotFoundError(WikiAPIException):
    """Raised when a wiki page is not found."""

    def __init__(self, slug: str):
        super().__init__(status_code=404, detail=f"Page not found: {slug}")


class WikiRevisionNotFoundError(WikiAPIException):
    """Raised when a wiki revision is not found."""

    def __init__(self, slug: str, version: int):
        super().__init__(
            status_code=404, detail=f"Revision {version} not found for page '{slug}'"
        )


class WikiPageAlreadyExistsError(WikiAPIException):
    """Raised when a wiki page with the same slug already exists."""

    def __init__(self, slug: str):
        super().__init__(
            status_code=400, detail=f"Page with slug '{slug}' already exists"
        )


class WikiParentNotFoundError(WikiAPIException):
    """Raised when a parent page is not found."""

    def __init__(self, parent_id: str):
        super().__init__(status_code=404, detail=f"Parent page not found: {parent_id}")


class WikiPageHasChildrenError(WikiAPIException):
    """Raised when attempting to delete a page that has children."""

    def __init__(self, children_count: int):
        super().__init__(
            status_code=400,
            detail=f"Cannot delete page with {children_count} child pages. Delete or move children first.",
        )


class WikiSelfParentError(WikiAPIException):
    """Raised when attempting to set a page as its own parent."""

    def __init__(self):
        super().__init__(status_code=400, detail="A page cannot be its own parent")


class WikiCircularParentError(WikiAPIException):
    """Raised when setting a parent would create a circular hierarchy."""

    def __init__(self):
        super().__init__(
            status_code=400, detail="Circular parent relationship detected"
        )


class WikiImageNotFoundError(WikiAPIException):
    """Raised when a wiki image is not found."""

    def __init__(self):
        super().__init__(status_code=404, detail="Image not found")


class WikiImageTooLargeError(WikiAPIException):
    """Raised when an uploaded image exceeds the size limit."""

    def __init__(self):
        super().__init__(status_code=413, detail="Image exceeds 10 MB limit")


class WikiInvalidImageError(WikiAPIException):
    """Raised when an uploaded file is not an image."""

    def __init__(self):
        super().__init__(status_code=400, detail="File must be an image")


class WikiImageProxyDomainError(WikiAPIException):
    """Raised when the image proxy domain is not allowed."""

    def __init__(self):
        super().__init__(status_code=403, detail="Domain not allowed")


class WikiImageProxySchemeError(WikiAPIException):
    """Raised when the image proxy URL has an invalid scheme."""

    def __init__(self):
        super().__init__(status_code=400, detail="Invalid scheme")
