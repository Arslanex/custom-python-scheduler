"""
Senaryo: ana döngü yok; işi elle trigger ile bir kez çalıştırma.

Çalıştırma:
    PYTHONPATH=. python examples/manual_trigger.py
"""

import time

from src import Job, Scheduler


def main() -> None:
    def once() -> str:
        return "done"

    sched = Scheduler()
    sched.add(Job(name="once", func=once, interval=3600.0))

    sched.trigger("once")
    time.sleep(0.3)

    last = sched.history(name="once", limit=1)[0]
    print("durum:", last.status.value, "süre:", round(last.duration, 4), "s")


if __name__ == "__main__":
    main()
