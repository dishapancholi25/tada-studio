"""Datasource service module for managing database connections and queries."""

from .service import DataSourceService


# Create singleton instance
_datasource_service = None


def get_datasource_service() -> DataSourceService:
    """Get or create the singleton datasource service instance.

    Returns:
        DataSourceService instance
    """
    global _datasource_service
    if _datasource_service is None:
        _datasource_service = DataSourceService()
    return _datasource_service


__all__ = [
    "DataSourceService",
    "get_datasource_service",
]
