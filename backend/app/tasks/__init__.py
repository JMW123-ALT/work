"""Celery task package for the v2 platform."""

from app.tasks.vector_index import vector_index_pending

__all__ = ["vector_index_pending"]
