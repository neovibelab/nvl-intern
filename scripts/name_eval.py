# -*- coding: utf-8 -*-
"""세 번째 시제의 **이름**이 판정을 바꾸는지 (2026-09-10 대표 지시).

「배경」으로 부르던 칸을 「뉴스」로 바꿨다. 이름이 판정을 바꿀 것이라는 가설이 있다 -
배경은 **용도**를 부르는 이름이라 「나중에 맥락으로 쓸 수 있나」를 묻게 되고, 그러면 웬만한 것이
다 해당돼 오히려 안 쓰게 된다. 94무리 실측에서 background 판정은 2건이었다.

`tiebreak.json`이 남긴 **같은 표본**(같은 시드)에 새 이름을 붙여 한 번 더 묻는다.
비교 대상은 그 파일의 `tie`(옛 이름 + 동점 지시 있음)다. 표본과 지시가 같으니 차이는 이름뿐이다.

    python scripts/name_eval.py
"""
import argparse
import collections
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, radar, steps  # noqa: E402

BLIND = {"radar_tense": None, "factor": None, "stage": None}
OUT = pathlib.Path(__file__).resolve().parent.parent / "reports" / "tense"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--arm", default="new_name", help="결과를 적을 열 이름")
    args = ap.parse_args()
    config.load_env()
    assert "news(뉴스)" in steps.TENSE_BLOCK, "새 이름이 프롬프트에 없다"
    # 같은 표본에 현행 프롬프트를 다시 물어 회차를 쌓는다. 열 이름은 arm으로 받는다.

    src = OUT / "namecheck-new_name.json"
    prev = json.loads(io.open(src if src.exists() else OUT / "tiebreak.json", encoding="utf-8").read())
    want_keys = {r["key"] for r in prev}
    cs = radar.cluster(radar.fetch_live(args.hours))
    by_key = {c["key"][:8]: c for c in cs}
    rows = [(r, by_key[r["key"]]) for r in prev if r["key"] in by_key]
    print(f"이전 표본 {len(prev)}무리 중 {len(rows)}무리를 다시 찾았다")

    recs = []
    for i, (old, c) in enumerate(rows, 1):
        try:
            j = steps.judge(radar.describe(c), BLIND, "")
            got, ev = j["tense"], bool(str(j.get("vibe_evidence") or "").strip())
        except Exception as e:  # noqa: BLE001
            got, ev = f"ERR:{type(e).__name__}", False
        recs.append(dict(old, **{args.arm: got, args.arm + "_ev": ev}))
        print(f"  [{i}/{len(rows)}] 레이더 {old['radar']:5s} · 이전 {old['tie']:10s} → 이번 {got:10s} · {old['title'][:36]}")
        io.open(OUT / f"namecheck-{args.arm}.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(recs, ensure_ascii=False, indent=1))

    def norm(x):
        return "news" if x == "background" else x

    print()
    for col, label in (("tie", "옛 이름(배경) + 동점 지시"), ("no_tie", "옛 이름(배경) + 지시 없음"), ("new_name", "새 이름(뉴스) + 동점 지시"), (args.arm, f"이번 회차({args.arm})")):
        got = [norm(r[col]) for r in recs if not str(r[col]).startswith("ERR")]
        agree = sum(1 for r in recs if norm(r[col]) == norm(r["want"]))
        over = sum(1 for r in recs if norm(r["want"]) == "news" and norm(r[col]) == "vibe")
        nb = sum(1 for r in recs if norm(r["want"]) == "news")
        miss = sum(1 for r in recs if r["want"] == "vibe" and norm(r[col]) != "vibe")
        nv = sum(1 for r in recs if r["want"] == "vibe")
        print(f"[{label}] 레이더와 일치 {agree}/{len(recs)} · 분포 {collections.Counter(got).most_common()} "
              f"· 뉴스를 vibe로 {over}/{nb} · 놓침 {miss}/{nv}")
    flip = [r for r in recs if norm(r["new_name"]) != norm(r[args.arm])]
    print(f"\n이름만 바꿨는데 판정이 갈린 무리 {len(flip)}/{len(recs)}")
    for r in flip[:10]:
        print(f"  {r['radar']:5s} 이전 {r['new_name']:10s} → 이번 {r[args.arm]:10s} · {r['title'][:44]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
