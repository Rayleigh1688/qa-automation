"""Calendar ranges in GMT+8, with inclusive integer millisecond timestamps."""

from datetime import date, datetime, time, timedelta, timezone

GMT8 = timezone(timedelta(hours=8))


def calculate_ranges(reference: date | None = None) -> list[dict]:
    """Use the reference date, or today's date in GMT+8; weeks start Monday."""
    today = reference if reference is not None else datetime.now(GMT8).date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    next_month_start = (month_start + timedelta(days=32)).replace(day=1)
    windows = (
        ("today", "今天", today, today + timedelta(days=1)),
        ("yesterday", "昨天", today - timedelta(days=1), today),
        ("this_week", "本周", week_start, week_start + timedelta(days=7)),
        ("this_month", "本月", month_start, next_month_start),
        ("last_month", "上月", last_month_start, month_start),
    )
    result = []
    for key, label, first, after in windows:
        start = datetime.combine(first, time.min, GMT8)
        following = datetime.combine(after, time.min, GMT8)
        end = following - timedelta(milliseconds=1)
        result.append({
            "key": key,
            "label": label,
            "start_ms": int(start.timestamp()) * 1000,
            "end_ms": int(following.timestamp()) * 1000 - 1,
            "start_time": start.isoformat(sep=" ", timespec="milliseconds")[:-6],
            "end_time": end.isoformat(sep=" ", timespec="milliseconds")[:-6],
        })
    return result
