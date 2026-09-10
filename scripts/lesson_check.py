# -*- coding: utf-8 -*-
"""지난 편 지적이 오늘 다시 나왔나 (2026-09-11 신설).

2026-09-11부터 인턴은 집필 전에 **직전 2편의 본문·검수 지적·숫자**를 받는다(`intern/learn.py`).
그것이 실제로 학습으로 이어졌는지 재는 자리다. 물음은 하나다 - **같은 지적을 두 번 받았나.**

문자열로 대조하지 않는다. 같은 결함이 같은 문장으로 두 번 나오지 않는 것은 09-10에 실측했다
(후보 35개 전부 count 1). **뜻으로 묶어** 어제 유형과 오늘 유형이 겹치는지 본다.

    python scripts/lesson_check.py                 # 오늘 회전을 어제와 대조
    python scripts/lesson_check.py --date 2026-09-12
"""
import argparse
import datetime as dt
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, form, publish, weekly  # noqa: E402


def log(date: str) -> dict:
    try:
        return json.loads(io.open(config.LOG_DIR / f"{date}.json", encoding="utf-8").read())
    except FileNotFoundError:
        return {}


def issues_of(lg: dict) -> list[str]:
    out = []
    for rv in lg.get("reviews", []):
        out.extend(rv.get("issues", []))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=config.today_kst().strftime("%Y-%m-%d"))
    ap.add_argument("--back", type=int, default=2, help="며칠 전까지 대조하나")
    args = ap.parse_args()
    config.load_env()

    today = log(args.date)
    if not today or today.get("rest"):
        print(f"  [{args.date}] 회전 기록이 없다 - 아직 안 돌았거나 휴재일이다")
        return 0

    stats = {s["date"]: s for s in publish._load(config.DATA_DIR / "stats.json", [])}
    s = stats.get(args.date, {})
    print(f"== {args.date} · D+{s.get('day', '?')} 「{s.get('title_ko', '?')}」")

    attached = bool(today.get("recent"))
    print(f"  [지난 편 붙음] {'예' if attached else '아니오 - learn 블록이 안 들어갔다'}")

    f = s.get("form") or {}
    if f:
        t = f.get("title_check") or {}
        print(f"  [숫자] 형식 {form.score(f)}/100 · 제목 알려주나 {t.get('clarity')}/2 · 읽고싶나 {t.get('pull')}/2 · "
              f"AI tell {f.get('ai_tell')} · 헤지 {f.get('hedge_10k')}")
    print(f"  [검수] {len(today.get('reviews', []))}회 · 차단 "
          f"{len((today.get('reviews') or [{}])[-1].get('blocking', []))}")

    y, m, d = map(int, args.date.split("-"))
    prev_dates = []
    for k in range(1, args.back + 3):
        p = (dt.date(y, m, d) - dt.timedelta(days=k)).isoformat()
        if log(p).get("reviews"):
            prev_dates.append(p)
        if len(prev_dates) >= args.back:
            break

    cur, prev = issues_of(today), []
    for p in prev_dates:
        prev.extend(issues_of(log(p)))
    if not cur:
        print("\n  오늘 지적이 없다 - 검수 1회 통과")
    if not prev:
        print("  대조할 지난 편 지적이 없다")
        return 0

    all_issues = prev + cur
    dates = [f"지난편({p})" for p in prev_dates for _ in issues_of(log(p))] + [f"오늘({args.date})"] * len(cur)
    types = weekly.group_issues(all_issues, dates)

    print(f"\n== 뜻으로 묶은 유형 {len(types)}개 · 지난 편 지적 {len(prev)}건 · 오늘 {len(cur)}건")
    repeated = []
    for t in types:
        days = set(t["days"])
        both = any(x.startswith("지난편") for x in days) and any(x.startswith("오늘") for x in days)
        mark = "**반복**" if both else ("오늘만" if any(x.startswith("오늘") for x in days) else "지난편만")
        if both:
            repeated.append(t)
        print(f"  [{mark}] {t['name'][:70]}")

    print()
    if repeated:
        print(f"  판정 - **같은 지적을 다시 받았다 {len(repeated)}건.** 지난 편을 읽힌 것이 아직 효과가 없다.")
    elif cur:
        print("  판정 - 오늘 지적은 전부 새 유형이다. 지난 편 지적은 반복되지 않았다.")
    else:
        print("  판정 - 오늘 지적이 0건이다.")
    print("  **한 편으로 단정하지 않는다** - 소재가 다르면 지적도 달라진다. 주 단위로 본다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
