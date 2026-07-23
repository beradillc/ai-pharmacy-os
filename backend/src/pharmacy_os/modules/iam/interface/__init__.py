"""IAM interface: HTTP routers and their composition."""

from pharmacy_os.modules.iam.interface.register import build_repositories, register

__all__ = ["build_repositories", "register"]
