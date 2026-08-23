"""Exceções tipadas do adapter de fixtures privadas."""

from __future__ import annotations


class PrivateFixturesError(Exception):
    """Erro base do adapter de fixtures privadas."""


class TaskMarkerError(PrivateFixturesError):
    """Marcador private_fixtures ausente/inválido no front matter."""


class ConfigError(PrivateFixturesError):
    """Configuração XDG ou root privado inválidos."""


class InventoryError(PrivateFixturesError):
    """Inventário público inválido ou inconsistente."""


class MaterializeError(PrivateFixturesError):
    """Falha ao materializar cópias privadas no worktree."""
