"""Deterministic mock provider. seed 고정, 같은 입력에는 항상 같은 출력.

- MockAnomalyProvider: 합성 오차 맵 (배경 노이즈 + 가우시안 blob)
- MockDefectProvider: 합성 bbox/점수 목록
"""
from __future__ import annotations

import hashlib

import numpy as np

from ..rois import MAPPING_VERSION
from .base import Detection


def stable_seed(*parts: str) -> int:
    """프로세스 간 deterministic한 시드 (Python 내장 hash()는 salt가 있어 쓰지 않음)."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


class MockAnomalyProvider:
    model_version = "mock-anomaly-v1"
    mapping_version = MAPPING_VERSION
    fixed_threshold = 0.85

    def __init__(self, seed: int = 42, image_size: tuple[int, int] = (480, 640)):
        self.seed = seed
        self.image_size = image_size  # (H, W)

    def _rng(self, product_id: str, camera_id: str):
        return np.random.default_rng(
            stable_seed(str(self.seed), self.model_version, product_id, camera_id)
        )

    def error_map(self, product_id: str, camera_id: str) -> np.ndarray:
        h, w = self.image_size
        rng = self._rng(product_id, camera_id)
        total = np.clip(rng.normal(0.20, 0.05, size=(h, w)), 0.0, 1.0)
        yy, xx = np.mgrid[0:h, 0:w]
        n_blobs = 2 + int(rng.integers(0, 3))  # 2~4개
        for _ in range(n_blobs):
            cx = float(rng.uniform(0, w))
            cy = float(rng.uniform(0, h))
            sigma = float(rng.uniform(8, 36))
            amp = float(rng.uniform(0.5, 1.0))
            blob = amp * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * sigma * sigma)))
            total = total + blob
        return np.clip(total, 0.0, 1.0).astype(np.float32)


class MockDefectProvider:
    model_version = "mock-defect-v1"
    mapping_version = MAPPING_VERSION

    def __init__(self, seed: int = 42, image_size: tuple[int, int] = (480, 640), max_boxes: int = 4):
        self.seed = seed
        self.image_size = image_size
        self.max_boxes = max_boxes

    def detect(self, product_id: str, camera_id: str) -> list[Detection]:
        h, w = self.image_size
        rng = np.random.default_rng(
            stable_seed(str(self.seed), self.model_version, product_id, camera_id)
        )
        n = 1 + int(rng.integers(0, self.max_boxes))
        out: list[Detection] = []
        for _ in range(n):
            bw = int(rng.integers(14, 80))
            bh = int(rng.integers(14, 80))
            x1 = int(rng.integers(0, w - bw))
            y1 = int(rng.integers(0, h - bh))
            score = round(float(rng.uniform(0.30, 0.99)), 4)
            out.append(Detection(bbox=(x1, y1, x1 + bw, y1 + bh), score=score))
        return out


def get_provider(source: str):
    if source == "anomaly":
        return MockAnomalyProvider()
    if source == "defect":
        return MockDefectProvider()
    raise ValueError(f"unknown source: {source}")
