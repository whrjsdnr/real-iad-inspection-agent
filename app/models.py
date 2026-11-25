"""검사 데이터 스키마 (SQLite 기본)."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Attempt(Base):
    __tablename__ = "inspection_attempts"

    attempt_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(String, index=True)
    item: Mapped[str] = mapped_column(String, index=True)
    started_at: Mapped[str] = mapped_column(String)  # ISO8601
    status: Mapped[str] = mapped_column(String)  # completed | capture_missing | capture_blurred | inference_error
    model_version: Mapped[str] = mapped_column(String)
    mapping_version: Mapped[str] = mapped_column(String)
    # 추가(가가적 마이그레이션, migrate.py): 퓨전 판정/검수 상태/GT/처리 시각
    verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    review_status: Mapped[str | None] = mapped_column(String, nullable=True)
    truth_label: Mapped[str | None] = mapped_column(String, nullable=True)
    processed_at: Mapped[str | None] = mapped_column(String, nullable=True)


class View(Base):
    __tablename__ = "inspection_views"

    view_id: Mapped[str] = mapped_column(String, primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String, index=True)
    product_id: Mapped[str] = mapped_column(String, index=True)
    item: Mapped[str] = mapped_column(String, index=True)
    camera_id: Mapped[str] = mapped_column(String)  # C1~C5
    image_uri: Mapped[str] = mapped_column(String)
    error_map_uri: Mapped[str] = mapped_column(String)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="ok")
    model_version: Mapped[str] = mapped_column(String)
    mapping_version: Mapped[str] = mapped_column(String)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_item_part", "item", "part_id"),
        Index("ix_findings_product", "product_id", "part_id", "camera_id"),
    )

    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    view_id: Mapped[str] = mapped_column(String, index=True)
    product_id: Mapped[str] = mapped_column(String, index=True)
    item: Mapped[str] = mapped_column(String, index=True)
    camera_id: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)  # anomaly | defect
    bbox_x1: Mapped[int] = mapped_column(Integer)
    bbox_y1: Mapped[int] = mapped_column(Integer)
    bbox_x2: Mapped[int] = mapped_column(Integer)
    bbox_y2: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    part_id: Mapped[str] = mapped_column(String)
    model_version: Mapped[str] = mapped_column(String)
    mapping_version: Mapped[str] = mapped_column(String)
    # 추가(가가적 마이그레이션): 근거 종류(rtdetr_box/hvq_score/hvq_map), 맵 경로, 부가 메타
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    map_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    meta_json: Mapped[str | None] = mapped_column(String, nullable=True)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    role: Mapped[str] = mapped_column(String, default="reviewer")  # reviewer | operator | admin
    created_at: Mapped[str] = mapped_column(String)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_item_part", "item", "part_id", "review_state"),)

    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(String, index=True)
    item: Mapped[str] = mapped_column(String, index=True)
    part_id: Mapped[str] = mapped_column(String)
    camera_id: Mapped[str] = mapped_column(String)
    truth_label: Mapped[str] = mapped_column(String)  # defect | normal
    review_state: Mapped[str] = mapped_column(String)  # pending | confirmed
    reviewer: Mapped[str] = mapped_column(String)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[str] = mapped_column(String)  # ISO8601
    # 추가(가가적 마이그레이션): 검수 확정 분류 FP/FN, 검수자 수정 라벨
    fp_fn: Mapped[str | None] = mapped_column(String, nullable=True)
    corrected_label: Mapped[str | None] = mapped_column(String, nullable=True)
    # 동시 검수 지원: 검수자 FK, 갱신 시각, 낙관적 잠금 버전
    reviewer_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.user_id"), nullable=True)
    updated_at: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class MetricsSnapshot(Base):
    __tablename__ = "metrics_snapshots"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric: Mapped[str] = mapped_column(String)
    definition_version: Mapped[str] = mapped_column(String)
    numerator: Mapped[int | None] = mapped_column(Integer, nullable=True)
    denominator: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    item: Mapped[str | None] = mapped_column(String, nullable=True)
    part_id: Mapped[str | None] = mapped_column(String, nullable=True)
    camera_id: Mapped[str | None] = mapped_column(String, nullable=True)
    date_from: Mapped[str | None] = mapped_column(String, nullable=True)
    date_to: Mapped[str | None] = mapped_column(String, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    mapping_version: Mapped[str | None] = mapped_column(String, nullable=True)
    computed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    source_scope: Mapped[str | None] = mapped_column(String, nullable=True)
    baseline_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    split_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    review_status: Mapped[str | None] = mapped_column(String, nullable=True)

