"""What every check produces and every adapter and reporter speaks. Imports nothing else here."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable


class Severity(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    check: str          # stable id, e.g. "first-layer"; reporters and CI scripts key on it
    severity: Severity
    message: str
    data: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        """The check id, qualified by the printer when the finding came from slicing for one."""
        return f"{self.data['printer']}/{self.check}" if "printer" in self.data else self.check


@dataclass(frozen=True)
class Image:
    name: str
    caption: str
    path: Path


@dataclass
class Report:
    """One subject (a G-code file or a model) and everything learned about it."""
    subject: str
    findings: list[Finding] = field(default_factory=list)
    metrics: dict[str, float | str] = field(default_factory=dict)
    baseline: dict[str, float | str] | None = None
    images: list[Image] = field(default_factory=list)
    attachments: dict[str, str] = field(default_factory=dict)   # title -> preformatted text
    links: dict[str, Path] = field(default_factory=dict)        # title -> file beside the images
    parameters: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(f.severity is Severity.BLOCK for f in self.findings)


# Ports. Adapters implement these; nothing in the core depends on an adapter.

@runtime_checkable
class MeshAnalyzer(Protocol):
    def analyze(self, stl: Path) -> dict[str, float | str]: ...


@runtime_checkable
class Slicer(Protocol):
    # Constructed as Slicer(slicer_config, center) from a configured printer.
    def slice(self, stl: Path, gcode: Path) -> Path: ...


@runtime_checkable
class Differ(Protocol):
    def diff(self, old: Path, new: Path) -> str: ...


@runtime_checkable
class Reporter(Protocol):
    def render(self, reports: list[Report]) -> str: ...
