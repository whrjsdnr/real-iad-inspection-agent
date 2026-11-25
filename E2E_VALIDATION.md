# E2E_VALIDATION

부품별검증만완료. 실제추론→자동퓨전TH→GUI검수→LLM근거조회전체E2E는미완료(TH/원본분할미확정). fixture/합성결과를실데이터E2E성공으로보고하지않음.


## 실제 데이터 부분 검증

{
  "api": {
    "isolated_database": "inspection_restore_20261123_v1",
    "first_import": {
      "added": 100,
      "skipped": 0,
      "model_version": "uncalibrated-scores:9ad319cd944e030f",
      "automatic_verdicts": false
    },
    "second_import": {
      "added": 0,
      "skipped": 100,
      "model_version": "uncalibrated-scores:9ad319cd944e030f",
      "automatic_verdicts": false
    },
    "case_http": 200,
    "product_id": "audiojack/NG/QS/S0006",
    "all_five_views": true,
    "real_image_bytes": {
      "C1": {
        "http": 200,
        "bytes": 250263,
        "jpeg": true
      },
      "C2": {
        "http": 200,
        "bytes": 223033,
        "jpeg": true
      },
      "C3": {
        "http": 200,
        "bytes": 205542,
        "jpeg": true
      },
      "C4": {
        "http": 200,
        "bytes": 228134,
        "jpeg": true
      },
      "C5": {
        "http": 200,
        "bytes": 199165,
        "jpeg": true
      }
    },
    "review_http": 200,
    "stale_review_http": 409,
    "stale_review_message": {
      "error": {
        "tool": "submit_review",
        "input_summary": "{'product_id': 'audiojack/NG/QS/S0006', 'camera_id': 'C1', 'bbox': [10, 10, 40, 40], 'truth_label': 'defect', 'reviewer': 'DIAGNOSTIC_ONLY', 'reason': 'API test on isolated recovery DB; not a genuine human approval', 'expected_version': 0}",
        "message": "이미 다른 사용자가 검수함 — 버전 충돌 (기대 0 vs 실제 1). 새로고침 후 다시 시도하세요."
      }
    },
    "reference_snapshot_rows": 6,
    "human_approval_claimed": false,
    "production_db_modified": false,
    "browser_verified": false
  },
  "map_api": {
    "C1": {
      "http": 200,
      "bytes": 676661,
      "png": true,
      "scaling": "PER_VIEW_PERCENTILES_VISUALIZATION_ONLY"
    },
    "C2": {
      "http": 200,
      "bytes": 738377,
      "png": true,
      "scaling": "PER_VIEW_PERCENTILES_VISUALIZATION_ONLY"
    },
    "C3": {
      "http": 200,
      "bytes": 736371,
      "png": true,
      "scaling": "PER_VIEW_PERCENTILES_VISUALIZATION_ONLY"
    },
    "C4": {
      "http": 200,
      "bytes": 764432,
      "png": true,
      "scaling": "PER_VIEW_PERCENTILES_VISUALIZATION_ONLY"
    },
    "C5": {
      "http": 200,
      "bytes": 742463,
      "png": true,
      "scaling": "PER_VIEW_PERCENTILES_VISUALIZATION_ONLY"
    }
  }
}

전체 자동퓨전/실브라우저/Qwen 실제루프는 미완료입니다.


## GUI 안정화 최종 추가 검증 — 2026-11-24

Python81pass+4skip / Vitest62pass / lint+TypeScript+build pass. Jobs는경량처리기,에이전트는격리시드DB도구조회로검증. 실제모델추론→검수→Qwen전체E2E로주장하지않음. 실제운영브라우저/최신스크린샷은BLOCKED. 이전스크린샷과신규구현구분. 상세 FINAL_GUI_VALIDATION_REPORT.md, host harness scripts/capture_gui_validation.mjs.
