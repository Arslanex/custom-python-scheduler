"""
Senaryo: @schedule ile varsayılan scheduler'a iş kaydı + start.

Çalıştırma:
    PYTHONPATH=. python examples/decorator_global_scheduler.py
"""

import time

import src.scheduler as sched_mod
from src import get_scheduler, schedule


def main() -> None:
    sched_mod._default_scheduler = None

    hits = []

    @schedule(interval=0.4)
    def ping():
        hits.append(len(hits) + 1)

    s = get_scheduler()
    s.start()
    try:
        time.sleep(1.2)
    finally:
        s.stop()

    sched_mod._default_scheduler = None
    print("ping tetik sayısı:", len(hits), hits)


if __name__ == "__main__":
    main()
