# -*- coding: utf-8 -*-
"""「애매하면 vibe 쪽으로 올린다」를 뺐을 때 판정이 어떻게 달라지나 (2026-09-10 대표 지시).

**왜 재나.** 축을 지리에서 주변↔주류로 바꿔도 판정 분포가 거의 안 움직였다(94무리 기준 24 vs 23).
움직인 것은 축이 아니라 **동점 처리 지시** 쪽으로 보인다 - 인턴은 레이더가 background로 본 것까지
대부분 vibe로 올린다. 그 지시가 실제로 얼마나 세게 끄는지 같은 표본에서 붙여 본다.

**옳고 그름이 아니라 트레이드오프다.** 지시의 근거는 비대칭 비용이다
(「잘못 올리면 사람이 내리지만 잘못 내리면 놓친다」). 그러니 볼 것은 정답률 하나가 아니라 둘이다.
- **놓침** - 레이더가 vibe로 본 것을 background·signal로 내리는가(민감도)
- **과잉** - 레이더가 background로 본 것을 vibe로 올리는가(특이도)
레이더 라벨도 정답이 아니라 다른 판정자의 의견이다. 일치율을 정답률로 읽지 않는다.

    python scripts/tiebreak_eval.py --n 30
"""
import argparse
import collections
import io
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, radar, steps  # noqa: E402

TIE_LINE = "  **애매하면 vibe 쪽으로 올린다.** 잘못 올리면 사람이 내리지만 잘못 내리면 놓친다."
BLIND = {"radar_tense": None, "factor": None, "stage": None}
OUT = pathlib.Path(__file__).resolve().parent.parent / "reports" / "tense"


def strat(labeled: list[dict], n: int) -> list[dict]:
    """라벨별로 고르게 뽑는다. brief(배경)가 144무리로 압도적이라 그냥 뽑으면 배경만 재게 된다."""
    by = collections.defaultdict(list)
    for c in labeled:
        by[c["radar_tense"]].append(c)
    random.seed(20260910)
    out = []
    per = max(1, n // max(1, len(by)))
    for k, rows in by.items():
        random.shuffle(rows)
        out.extend(rows[:per])
    return out[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--hours", type=int, default=168)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    config.load_env()

    full = steps.TENSE_BLOCK
    assert TIE_LINE in full, "동점 처리 문구를 못 찾았다 - TENSE_BLOCK이 바뀌었나"
    no_tie = full.replace("\n" + TIE_LINE, "")

    cs = radar.cluster(radar.fetch_live(args.hours))
    labeled = [c for c in cs if c["radar_tense"] in ("soon", "now", "done", "brief")
               and any((x.get("url") or "").startswith("http") for x in c["items"])]
    sample = strat(labeled, args.n)
    print(f"표본 {len(sample)}무리 " + str(collections.Counter(c["radar_tense"] for c in sample).most_common()))

    recs = []
    for i, c in enumerate(sample, 1):
        want = config.TENSE_FROM_RADAR.get(c["radar_tense"])
        text = radar.describe(c)
        row = {"key": c["key"][:8], "title": c["items"][0]["title"][:60], "radar": c["radar_tense"], "want": want}
        for name, block in (("tie", full), ("no_tie", no_tie)):
            steps.TENSE_BLOCK = block
            try:
                j = steps.judge(text, BLIND, "")
                row[name] = j["tense"]
                row[name + "_ev"] = bool(str(j.get("vibe_evidence") or "").strip())
                row[name + "_why"] = str(j.get("tense_why") or "")[:120]
            except Exception as e:  # noqa: BLE001
                row[name] = f"ERR:{type(e).__name__}"
        steps.TENSE_BLOCK = full
        recs.append(row)
        print(f"  [{i}/{len(sample)}] 레이더 {row['radar']:5s}→{str(want):10s} "
              f"있음 {row['tie']:10s} 없음 {row['no_tie']:10s} · {row['title'][:38]}")
        io.open(OUT / "tiebreak.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(recs, ensure_ascii=False, indent=1))

    print()
    for name in ("tie", "no_tie"):
        got = [r[name] for r in recs if not str(r[name]).startswith("ERR")]
        agree = sum(1 for r in recs if r[name] == r["want"])
        miss = sum(1 for r in recs if r["want"] == "vibe" and r[name] != "vibe")
        over = sum(1 for r in recs if r["want"] == "background" and r[name] == "vibe")
        nb = sum(1 for r in recs if r["want"] == "background")
        nv = sum(1 for r in recs if r["want"] == "vibe")
        ev = sum(1 for r in recs if r[name] == "vibe" and r.get(name + "_ev"))
        nvibe = sum(1 for g in got if g == "vibe")
        label = "동점→vibe 있음" if name == "tie" else "동점→vibe 없음"
        print(f"[{label}] 레이더와 일치 {agree}/{len(recs)} · vibe 판정 {nvibe}/{len(got)} "
              f"(조짐 댄 것 {ev}) · 놓침 {miss}/{nv} · 배경을 vibe로 {over}/{nb}")
        print("   분포 " + str(collections.Counter(got).most_common()))
    flip = [r for r in recs if r["tie"] != r["no_tie"]]
    print(f"\n두 문구가 갈린 무리 {len(flip)}/{len(recs)}")
    for r in flip[:8]:
        print(f"  {r['radar']:5s} 있음 {r['tie']:10s} / 없음 {r['no_tie']:10s} · {r['title'][:44]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
