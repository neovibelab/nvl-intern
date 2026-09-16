# -*- coding: utf-8 -*-
"""두뇌 재료 대조군을 손으로 돌린다 (2026-09-16).

주간 회고가 매주 2편씩 자동으로 돌리지만, 표본을 빨리 쌓고 싶거나 특정 날을 보고 싶을 때 쓴다.

    python scripts/brain_ablation.py --dates 2026-09-14 2026-09-15
    python scripts/brain_ablation.py -n 3          # 재료 붙었던 날 중 무작위 3편
    python scripts/brain_ablation.py --summary     # 누적만 본다

한 편에 집필 2회 + 판정 1회가 든다. 한 번에 3편을 넘기지 않는다.
"""
import argparse
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import ablation, config, publish  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", nargs="*", default=None)
    ap.add_argument("-n", type=int, default=2)
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    config.load_env()

    if args.summary:
        print(ablation.summary("ko"))
        return 0

    rows = [s for s in publish._load(config.DATA_DIR / "stats.json", []) if s.get("type") != "weekly"]
    dates = args.dates or ablation.pick_dates(rows, min(args.n, 3))
    if not dates:
        print("돌릴 날이 없다 - 재료가 붙은 편이 없다")
        return 2
    print(f"대조군 {len(dates)}편 · {', '.join(dates)}\n")
    out = ablation.run(dates, "ko")
    print()
    print(ablation.summary("ko"))
    return 0 if out else 1


if __name__ == "__main__":
    sys.exit(main())
