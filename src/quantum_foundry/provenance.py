"""Shared provenance tracking for every Result dataclass in the pipeline.

Every solver-stage output carries one of these so the validation report can
always state whether a number came from a stub or a real backend — see
CLAUDE.md's "one rule that matters most."
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class ProvenanceInfo:
    backend_name: str
    is_stub: bool
    tool_version: str | None = None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    git_commit: str | None = None
