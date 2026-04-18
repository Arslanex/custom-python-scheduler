"""
Senaryo: interval ile tekrarlayan iş + ana döngü (tick).

Çalıştırma (proje kökünden):
    PYTHONPATH=. python examples/interval_and_loop.py
"""

import time

from src import Job, Scheduler


def main() -> None:
    log: list[str] = []

    def tick() -> int:
        log.append("ok")
        return len(log)

    sched = Scheduler(tick=0.25, max_workers=2)
    sched.add(Job(name="heartbeat", func=tick, interval=0.35))

    sched.start()
    try:
        time.sleep(1.2)
    finally:
        sched.stop()

    print("çalıştırma sayısı:", len(log))
    print("son kayıtlar:", [r.name for r in sched.history(limit=10)])


if __name__ == "__main__":
    main()
