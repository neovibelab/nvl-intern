# -*- coding: utf-8 -*-
"""인턴 프롬프트 모델 비교 - 판정(③)과 집필(④)을 실제 호출 경로로 재고, 회차 산포까지 남긴다.

    python scripts/bakeoff.py --count-only          # 비용 추정
    python scripts/bakeoff.py --runs 3              # 두 소재 x 3모델 x 3회
    python scripts/bakeoff.py --runs 1 --models claude-opus-5

옆 세션의 뉴스레터 시험(`NeoVibeLab/scripts/model-bakeoff.py`)과 다른 점 둘.
- thinking·effort를 손대지 않는다. **인턴이 매일 실제로 쓰는 경로**(intern/llm.py)를 그대로 부른다.
- 한 회차가 판정 → 집필로 이어진다. 그 모델의 판정 위에 그 모델이 쓴다. 파이프라인과 같다.
산포가 모델 간 차이보다 큰 축은 판별 축으로 쓰지 않는다(옆 세션 실측).
"""
import argparse
import io
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import brain, config, llm, radar, steps  # noqa: E402

# 입력 $/1M, 출력 $/1M (NVL scripts/model-bakeoff.py와 같은 표)
PRICES = {"claude-fable-5-1": (10.0, 50.0), "claude-opus-5": (5.0, 25.0), "claude-sonnet-5": (2.0, 10.0)}
OUT = pathlib.Path(__file__).resolve().parent.parent / "reports" / "bakeoff"


def subjects(n: int, hours: int) -> list[dict]:
    """오늘 인턴이 실제로 고를 사건 n개. pick_today를 그대로 부르고 고른 것을 빼며 반복한다."""
    rows = radar.fetch_live(hours)
    cs = radar.cluster(rows)
    exclude = set(radar.used_keys())
    picked = []
    while len(picked) < n:
        c = radar.pick_today(cs, exclude)
        if not c:
            break
        picked.append(c)
        exclude.add(c["key"])
    return picked


def one_run(subject: dict, model: str, run_i: int, mats: str) -> dict:
    cluster_text = radar.describe(subject)
    before = dict(llm.USAGE)
    config.MODEL_MAIN = model            # llm.ask가 호출 시점에 읽는다
    t0 = time.time()
    err = None
    try:
        j = steps.judge(cluster_text, subject, mats)
        ko = steps.write_ko(cluster_text, j, mats)
    except Exception as e:                # noqa: BLE001
        print(f"  [{subject['key'][:8]}/{model}#{run_i}] 실패 {type(e).__name__}: {str(e)[:100]}")
        return {"subject": subject["key"], "model": model, "run": run_i, "error": f"{type(e).__name__}: {str(e)[:120]}"}
    sec = round(time.time() - t0, 1)
    d_in = llm.USAGE["input"] - before["input"]
    d_out = llm.USAGE["output"] - before["output"]
    pin, pout = PRICES.get(model, (5.0, 25.0))
    rec = {"subject": subject["key"], "model": model, "run": run_i, "sec": sec, "in": d_in, "out": d_out,
           "cost": round(d_in / 1e6 * pin + d_out / 1e6 * pout, 4),
           "factor": j["factor"], "from_stage": j["from_stage"], "to_stage": j["to_stage"], "tense": j["tense"],
           "agrees": bool(j.get("agrees")), "bet": bool(j.get("bet")),
           "bet_days": (j.get("bet") or {}).get("by_days"), "title": j.get("title_ko", ""),
           "angle": j.get("angle_ko", ""), "principle": j.get("principle_ko", ""),
           "chars": len(re.sub(r"\s", "", ko)), "body": ko, "error": err}
    d = OUT / subject["key"][:8]
    d.mkdir(parents=True, exist_ok=True)
    io.open(d / f"{model}-r{run_i}.md", "w", encoding="utf-8", newline="\n").write(
        f"<!-- {model} r{run_i} · {steps.header_line(j, 'ko')} · {rec['chars']}자 · {sec}초 · ${rec['cost']} -->\n"
        f"# {j['title_ko']}\n\n각도: {j['angle_ko']}\n\n{ko}\n\n원리 · {j['principle_ko']}\n")
    print(f"  [{subject['key'][:8]}/{model}#{run_i}] {steps.header_line(j, 'ko')} · {rec['chars']}자 · {sec}초 · ${rec['cost']}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--models", nargs="*", default=list(PRICES))
    ap.add_argument("--subjects", type=int, default=2)
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--count-only", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    subs = subjects(args.subjects, args.hours)
    if not subs:
        print("소재 없음"); return 1
    for s in subs:
        print(f"소재 {s['key'][:8]} · {s['n']}건 · {s['items'][0]['title'][:60]}")
    if args.count_only:
        n = len(subs) * len(args.models) * args.runs
        print(f"\n회차 {n} (소재 {len(subs)} x 모델 {len(args.models)} x {args.runs})")
        print("회차당 대략 입력 12k · 출력 3k 토큰 기준 추정:")
        for m in args.models:
            pin, pout = PRICES[m]
            print(f"  {m:20s} ${(12000/1e6*pin + 3000/1e6*pout) * len(subs) * args.runs:.2f}")
        return 0

    mats = {}
    for s in subs:                        # 재료는 소재당 한 번만 뽑아 전 모델이 같은 것을 본다
        mats[s["key"]] = brain.retrieve(radar.describe(s))["text"]
        print(f"  [재료] {s['key'][:8]} {len(mats[s['key']])}자")

    recs = []
    for s in subs:
        for m in args.models:
            for i in range(1, args.runs + 1):
                recs.append(one_run(s, m, i, mats[s["key"]]))
                io.open(OUT / "runs.json", "w", encoding="utf-8", newline="\n").write(
                    json.dumps(recs, ensure_ascii=False, indent=1))
    ok = [r for r in recs if not r.get("error")]
    print(f"\n완료 {len(ok)}/{len(recs)} · 실비 ${sum(r['cost'] for r in ok):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
