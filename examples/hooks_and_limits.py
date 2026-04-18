"""
Senaryo: başarı hook'u, geçmiş ve max_runs ile otomatik durdurma.

Çalıştırma:
    PYTHONPATH=. python examples/hooks_and_limits.py
"""

import time

from src import Job, Scheduler


def main() -> None:
    traces: list[str] = []

    def work() -> None:
        pass

    sched = Scheduler(tick=0.08, max_workers=2)
    sched.on_success(lambda r: traces.append(f"ok:{r.name}"))
    sched.add(Job(name="limited", func=work, interval=0.15, max_runs=3))

    sched.start()
    try:
        time.sleep(0.85)
    finally:
        sched.stop()

    job = sched.get("limited")
    assert job is not None
    print("hook kayıtları:", traces)
    print("toplam çalışma:", job.runs, "aktif mi:", job.enabled)


if __name__ == "__main__":
    main()
