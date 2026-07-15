"""
Vendored from Moist-Cat/synack commit 47e69b2f80ccb286c6d399dcfb368a3ce0d326a1.

Local modifications:
- relative imports for in-repo vendoring
- optional OpenTelemetry initialization disabled by default
"""

from .parser import SYNOPParser

__all__ = ["SYNOPParser"]
