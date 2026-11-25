"""지표 스냅샷 비동기 재계산 큐 — 동시 검수 중 지표 계산 경합 방지.

- API 서버 시작 시 워커 1개 기동 (serial 처리).
- 검수 확정(submit_review)은 큐에 적재만 하고 즉시 반환.
- 워커 미기동 환경(배치/CLI)에서는 enqueue가 동기 폐백으로 처리한다.
"""

from __future__ import annotations

import logging
import queue
import threading

logger = logging.getLogger("inspection.recompute")

_q: queue.Queue[str | None] = queue.Queue()
_started = False
_lock = threading.Lock()


def _worker() -> None:
    while True:
        item = _q.get()
        if item is None:
            _q.task_done()
            return
        try:
            import metrics  # noqa: PLC0415

            metrics.compute_all(save=True, item=item)
            logger.info("[recompute] snapshots recomputed item=%s", item)
        except Exception:  # noqa: BLE001
            logger.exception("[recompute] failed item=%s", item)
        finally:
            _q.task_done()


def start_worker() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True
    t = threading.Thread(target=_worker, name="metrics-recompute", daemon=True)
    t.start()
    logger.info("[recompute] worker started")


def enqueue_item_metrics(item: str | None) -> str:
    """스냅샷 재계산 적재. 워커가 없으면 동기 실행 폐백."""
    if not _started:
        try:
            import metrics  # noqa: PLC0415

            metrics.compute_all(save=True, item=item)
            return "sync"
        except Exception as e:  # noqa: BLE001
            logger.exception("[recompute] sync fallback failed")
            return f"sync_error: {e}"
    _q.put(item)
    return "queued"
