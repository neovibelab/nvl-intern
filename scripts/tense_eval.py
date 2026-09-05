# -*- coding: utf-8 -*-
"""시제 기준 대조 - 레이더가 이미 찍어 둔 행을 정답지로 놓고 옛 문구와 새 문구를 같은 조건에서 잰다.

    python scripts/tense_eval.py            # 라벨된 무리 전부, 두 문구 각 1회
    python scripts/tense_eval.py --runs 2

**레이더 판정을 가리고 묻는다.** 실제 파이프라인은 레이더 판정을 보여주지만(다르면 이유를 적는 설계),
그러면 그 라벨이 정답을 흘려 기준 자체를 잴 수 없다.
"""
import argparse
import collections
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, radar, steps  # noqa: E402

OLD_BLOCK = """- 시제 하나: vibe(아직 산업이 받아들이지 않았지만 조짐이 보이고 반복될 종류) / signal(지금 벌어지는 중, 누구나 찾을 수 있다) / background(끝났거나 한 번 있는 일)
  기준 독자는 한국 엔터 실무자다. 해외에서 signal인 것이 한국에는 vibe일 수 있다."""
BLIND = {"radar_tense": None, "factor": None, "stage": None}
OUT = pathlib.Path(__file__).resolve().parent.parent / "reports" / "tense"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--hours", type=int, default=168)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    cs = radar.cluster(radar.fetch_live(args.hours))
    labeled = [c for c in cs if c["radar_tense"] in ("soon", "now", "done", "brief")
               and any((x.get("url") or "").startswith("http") for x in c["items"])]
    print(f"정답지 {len(labeled)}무리: " + str(collections.Counter(c['radar_tense'] for c in labeled).most_common()))

    new_block = steps.TENSE_BLOCK
    recs = []
    for c in labeled:
        want = config.TENSE_FROM_RADAR.get(c["radar_tense"])
        text = radar.describe(c)
        row = {"key": c["key"][:8], "title": c["items"][0]["title"][:60], "radar": c["radar_tense"], "want": want}
        for name, block in (("old", OLD_BLOCK), ("new", new_block)):
            got = []
            for _ in range(args.runs):
                steps.TENSE_BLOCK = block
                try:
                    j = steps.judge(text, BLIND, "")
                    got.append(j["tense"] + ("" if j["tense"] != "vibe" else "*" if str(j.get("vibe_evidence") or "").strip() else "?"))
                except Exception as e:  # noqa: BLE001
                    got.append(f"ERR:{type(e).__name__}")
            row[name] = got
        steps.TENSE_BLOCK = new_block
        recs.append(row)
        print(f"  {row['radar']:5s}→{str(want):10s} old={row['old']} new={row['new']} · {row['title'][:44]}")
        io.open(OUT / "runs.json", "w", encoding="utf-8", newline="\n").write(json.dumps(recs, ensure_ascii=False, indent=1))

    def hit(name):
        return sum(1 for r in recs for g in r[name] if g.rstrip("*?") == r["want"])
    total = sum(len(r["old"]) for r in recs)
    print(f"\n정답 일치 - 옛 문구 {hit('old')}/{total} · 새 문구 {hit('new')}/{total}")
    for name in ("old", "new"):
        print(f"  {name} 분포: " + str(collections.Counter(g.rstrip('*?') for r in recs for g in r[name]).most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
