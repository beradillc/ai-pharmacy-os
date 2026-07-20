"""Catalog domain exceptions (pure — no framework)."""

from __future__ import annotations


class CatalogError(Exception):
    """Base for catalog domain rule violations."""


class DuplicateUnitError(CatalogError):
    """Raised when adding a unit name that already exists on a drug."""
