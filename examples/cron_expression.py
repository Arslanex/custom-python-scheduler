"""
Senaryo: cron ifadesi parse / bir sonraki tetik zamanı ve Job ile gösterim.

Uzun süre bekletmez; dakikalık gerçek tetik için interval_and_loop örneğini kullanın.

Çalıştırma:
    PYTHONPATH=. python examples/cron_expression.py
"""

from datetime import datetime

from src import Job, next_fire, parse_cron


def main() -> None:
    expr = "0 9 * * 1"
    spec = parse_cron(expr)
    print("Cron:", repr(expr))
    print("Specs (None = her değer):", spec)
    now = datetime.now()
    print("Şu andan sonraki ilk eşleşme:", next_fire(expr, now))

    job = Job(
        name="report",
        func=lambda: None,
        interval=3600.0,
        cron="0 15 * * *",
    )
    print("İzleme satırı (örnek):", job.monitoring_row())


if __name__ == "__main__":
    main()
