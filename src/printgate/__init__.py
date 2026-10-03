"""printgate: checks for 3D-print models and G-code before they reach a printer.

This module is the public surface; anything it does not export is internal.
"""
from .contract import Finding, Image, Report, Severity
from .gcode import preflight
from .profile import Profile

__all__ = ["Finding", "Image", "Profile", "Report", "Severity", "preflight"]
