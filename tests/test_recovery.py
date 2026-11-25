"""Regression checks for interrupted DB helpers and authoritative fusion rules."""
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app import db
import fusion
from migrate import migrate

ROOT = Path(__file__).resolve().parents[1]


def test_default_database_is_repository_database(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    assert db.database_url() == 'sqlite:///' + str(ROOT / 'inspection.db')


def test_legacy_migration_keeps_rows_and_backfills_review_versions(tmp_path):
    path = tmp_path / 'legacy.db'
    engine = create_engine('sqlite:///' + str(path))
    with engine.begin() as con:
        con.execute(text('CREATE TABLE reviews (review_id TEXT PRIMARY KEY)'))
        con.execute(text("INSERT INTO reviews VALUES ('old')"))
    migrate(path)
    migrate(path)
    with engine.connect() as con:
        assert con.execute(text('SELECT review_id,version FROM reviews')).one() == ('old', 1)
    assert {'users', 'metrics_snapshots', 'inspection_attempts'} <= set(inspect(engine).get_table_names())


def test_authoritative_weights_and_uncalibrated_state():
    cfg = fusion.load_config()
    assert cfg['weights'] == {'rtdetr': 0.7, 'hvq': 0.3}
    if cfg['calibration_status'] != 'derived':
        assert fusion.load_derived() is None
        assert cfg['derived'] is None


def test_hold_includes_both_boundaries_and_zero_margin():
    cfg = {'weights': {'rtdetr': .7, 'hvq': .3},
           'score_norm': {'rt': {'min': 0, 'max': 1}, 'hvq': {'min': 0, 'max': 1}},
           'score_definition': {'product_agg': 'mean'}, 'derived': {'th': .5, 'margin': .125}}
    for value in (.375, .5, .625):
        assert fusion.fuse_product_derived([value]*5, [value]*5, cfg)['verdict'] == 'hold'
    assert fusion.fuse_product_derived([1]*5, [1]*5, cfg)['verdict'] == 'defect'
    assert fusion.fuse_product_derived([0]*5, [0]*5, cfg)['verdict'] == 'normal'
    cfg['derived']['margin'] = 0
    assert fusion.fuse_product_derived([.5]*5, [.5]*5, cfg)['verdict'] == 'hold'


def test_validation_does_not_select_arbitrary_products(tmp_path):
    import derive_fusion
    with pytest.raises(ValueError, match='manifest'):
        derive_fusion.select_val_products(tmp_path, tmp_path/'missing.csv')


def test_roi_mapping_is_loaded_by_version():
    from app.rois import map_bbox_to_part
    assert map_bbox_to_part('toothbrush', 'C1', (200, 30, 440, 170), 'roi-lut-v1') == 'bristle'
    assert map_bbox_to_part('toothbrush', 'C1', (200, 30, 440, 170), 'parts-roi-v1') == 'unknown'


def test_review_update_detects_a_concurrent_writer(tmp_path):
    from sqlalchemy.orm import Session
    from sqlalchemy.orm.exc import StaleDataError
    from app.models import Base, Review
    engine = create_engine('sqlite:///' + str(tmp_path/'race.db'))
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Review(review_id='r',product_id='p',item='toy',part_id='surface',
                     camera_id='C1',truth_label='normal',review_state='confirmed',
                     reviewer='one',reviewed_at='2026-11-23T00:00:00',version=1))
        s.commit()
    with Session(engine) as first, Session(engine) as second:
        a, b = first.get(Review, 'r'), second.get(Review, 'r')
        a.reason='first writer'; first.commit()
        b.reason='stale second writer'
        with pytest.raises(StaleDataError): second.commit()
