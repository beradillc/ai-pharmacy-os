"""Kernel: cross-cutting capabilities with no business logic.

The core package must never import ``pharmacy_os.modules`` (enforced by
import-linter). It provides config, DI, the event bus, DB/UoW, security,
audit, the AI gateway port and the plugin loader.
"""
