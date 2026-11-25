# POSTGRES_VALIDATION

{
  "migration": {
    "row_counts": {
      "findings": {
        "source": 50,
        "destination": 50
      },
      "inspection_attempts": {
        "source": 40,
        "destination": 40
      },
      "inspection_views": {
        "source": 198,
        "destination": 198
      },
      "metrics_snapshots": {
        "source": 0,
        "destination": 0
      },
      "users": {
        "source": 0,
        "destination": 0
      },
      "reviews": {
        "source": 121,
        "destination": 121
      }
    },
    "app_read_write_denied": true,
    "app_review_update_allowed": true,
    "optimistic_conflict_detected": true,
    "database": "inspection_recovery_20261123_v2",
    "production_sqlite_modified": false,
    "original_postgres_database_modified": false
  },
  "backup_restore": {
    "dump": "/home/geonug/MV/outputs/agent_integration_20261123_v1/postgres_validation/backups/inspection_20261123T102552_2456465.dump",
    "bytes": 24712,
    "restore_database": "inspection_restore_20261123_v1",
    "row_counts": {
      "alembic_version": {
        "source": 1,
        "restored": 1,
        "matches": true
      },
      "inspection_views": {
        "source": 198,
        "restored": 198,
        "matches": true
      },
      "metrics_snapshots": {
        "source": 0,
        "restored": 0,
        "matches": true
      },
      "reviews": {
        "source": 121,
        "restored": 121,
        "matches": true
      },
      "findings": {
        "source": 50,
        "restored": 50,
        "matches": true
      },
      "users": {
        "source": 0,
        "restored": 0,
        "matches": true
      },
      "inspection_attempts": {
        "source": 40,
        "restored": 40,
        "matches": true
      }
    },
    "all_match": true
  }
}
