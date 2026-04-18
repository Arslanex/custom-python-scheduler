from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
@dataclass(frozen=True)
class CronSpec:
    minute: frozenset[int] | None
    hour: frozenset[int] | None
    dom: frozenset[int] | None
    month: frozenset[int] | None
    dow: frozenset[int] | None


def _parse_field(raw: str, lo: int, hi: int) -> frozenset[int] | None:
    s = raw.strip()
    if s == "*":
        return None
    if s.startswith("*/"):
        step = int(s[2:])
        if step <= 0:
            raise ValueError(f"geçersiz adım: {raw!r}")
        return frozenset(range(lo, hi + 1, step))
    if "," in s:
        acc: set[int] = set()
        for part in s.split(","):
            acc |= _parse_atom(part.strip(), lo, hi)
        return frozenset(acc)
    return frozenset(_parse_atom(s, lo, hi))


def _parse_atom(s: str, lo: int, hi: int) -> set[int]:
    if "-" in s:
        a, b = s.split("-", 1)
        ia, ib = int(a), int(b)
        if ia > ib or not (lo <= ia <= hi) or not (lo <= ib <= hi):
            raise ValueError(f"geçersiz aralık: {s!r}")
        return set(range(ia, ib + 1))
    v = int(s)
    if not (lo <= v <= hi):
        raise ValueError(f"geçersiz değer: {s!r}")
    return {v}


def _normalize_dow(fs: frozenset[int] | None) -> frozenset[int] | None:
    if fs is None:
        return None
    out = set(fs)
    if 7 in out:
        out.discard(7)
        out.add(0)
    return frozenset(out)


def parse_cron(expr: str) -> CronSpec:
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            "cron: tam 5 alan gerekli: "
            "'dakika saat gün ay haftanın_günü' (ör. '0 9 * * 1')"
        )
    m, h, dom, mon, dow = parts
    return CronSpec(
        minute=_parse_field(m, 0, 59),
        hour=_parse_field(h, 0, 23),
        dom=_parse_field(dom, 1, 31),
        month=_parse_field(mon, 1, 12),
        dow=_normalize_dow(_parse_field(dow, 0, 7)),
    )


def _cron_weekday(dt: datetime) -> int:
    """Pzt=1 … Paz=0 (cron ile uyumlu)."""
    return (dt.weekday() + 1) % 7


def matches(dt: datetime, spec: CronSpec) -> bool:
    """Gün ve haftanın günü birlikte verildiğinde AND kullanılır (basit model)."""
    if spec.minute is not None and dt.minute not in spec.minute:
        return False
    if spec.hour is not None and dt.hour not in spec.hour:
        return False
    if spec.month is not None and dt.month not in spec.month:
        return False
    if spec.dom is not None and dt.day not in spec.dom:
        return False
    if spec.dow is not None and _cron_weekday(dt) not in spec.dow:
        return False
    return True


def next_fire(expr: str, after: datetime) -> datetime:
    """`after` anından sonraki ilk uygun dakika (saniye/mikrosaniye yok sayılır)."""
    spec = parse_cron(expr)
    t = after.replace(second=0, microsecond=0)
    if t <= after:
        t += timedelta(minutes=1)
    # ~2 yıl dakika üst sınırı
    for _ in range(60 * 24 * 800):
        if matches(t, spec):
            return t
        t += timedelta(minutes=1)
    raise ValueError("cron: uygun zaman bulunamadı")
