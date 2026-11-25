"""하부 이상탐지/불량탐지 모델을 교체 가능하게 하는 provider 인터페이스.

실제 모델을 붙일 때는 이 Protocol을 구현한 클래스를 만들고
app.tools.get_provider()가 해당 클래스를 반환하도록 바꾼다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Detection:
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2 (픽셀)
    score: float


@runtime_checkable
class AnomalyProvider(Protocol):
    """오차 맵(error map)을 생성하는 이상탐지 파이프라인."""

    model_version: str
    mapping_version: str
    fixed_threshold: float  # threshold_mode="fixed"에서 사용

    def error_map(self, product_id: str, camera_id: str):
        """H x W float 배열 (0~1 정규화된 이상 점수 맵)."""
        ...


@runtime_checkable
class DefectProvider(Protocol):
    """불량 박스/점수를 직접 반환하는 불량탐지 파이프라인."""

    model_version: str
    mapping_version: str

    def detect(self, product_id: str, camera_id: str) -> list[Detection]:
        ...
