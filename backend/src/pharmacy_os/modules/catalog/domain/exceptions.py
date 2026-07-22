"""Catalog domain exceptions (pure — no framework)."""

from __future__ import annotations


class CatalogError(Exception):
    """Base for catalog domain rule violations."""


class DuplicateUnitError(CatalogError):
    """Raised when adding a unit name that already exists on a drug."""


class InvalidIngredientError(CatalogError):
    """Raised when an :class:`ActiveIngredient`/:class:`DrugIngredient` is malformed."""


class DuplicateIngredientError(CatalogError):
    """Raised when adding an ingredient already present on a drug."""
