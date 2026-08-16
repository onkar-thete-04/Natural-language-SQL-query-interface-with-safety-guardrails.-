from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgreementResult:
    agreed: bool
    identical: bool
    row_counts: tuple[int, int]
    divergence_detail: str | None
