# -*- coding: utf-8 -*-
"""인턴 문체 기준선 - 「자기 학습이 어투를 바꾸나」를 나중에 실측으로 답하기 위한 자.

    python scripts/style_baseline.py            # 전체
    python scripts/style_baseline.py --since 2026-09-10

**모델 가중치는 안 변한다.** 바뀔 수 있는 것은 셋뿐이다 - ⓐ 자기 규칙(주간 회고가 뜻으로 묶어 승격) ⓑ 두뇌 재료
(관점 렌즈·개념 사전) ⓒ 프롬프트. 그래서 여기서 재는 것도 그 셋이 건드릴 수 있는 축이다.
문장 리듬(길이 분포)은 ⓒ가 바뀌지 않는 한 거의 안 움직인다는 것이 가설이고, 이 표가 그 가설을 친다.
"""
import argparse
import collections
import io
import json
import pathlib
import re
import statistics as st
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "ko"

CONTRAST = [r"[가-힣]{2,}이 아니라 ", r"[가-힣]{2,}가 아니라 ", r"[가-힣]{2,}이 아닌 ",
            r"[가-힣]{2,}가 아닌 ", r"[가-힣]{2,}보다는 "]
HEDGE = [r"알려졌", r"~로 보인다", r"로 보입니다", r"인 듯", r"가능성이 (있|높)"]
META = [r"진짜 (질문|문제)은", r"흥미로운 (점|지점)은", r"중요한 것은", r"핵심은", r"주목할"]
SOURCE = [r"보도했", r"전했", r"집계", r"발표했", r"기고", r"밝혔"]


def body_of(md: str) -> str:
    """프론트매터·프레임·소재·격자·베팅·원리·검수 기록을 뺀 순수 본문."""
    t = md.split("---", 2)[2] if md.startswith("---") else md
    i = t.find("</sub>")                      # 격자 범례 뒤부터가 본문
    t = t[i + 6:] if i >= 0 else t
    for stop in ("**베팅**", "**Bet**"):
        j = t.find(stop)
        if j > 0:
            t = t[:j]
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t).strip()


def measure(text: str) -> dict:
    sents = [s.strip() for s in re.split(r"(?<=다)\.\s|[.!?]\s|\n\n", text) if len(s.strip()) > 5]
    lens = [len(s) for s in sents] or [0]
    chars = len(re.sub(r"\s", "", text))
    per10k = (lambda n: round(n / max(chars, 1) * 10000, 1))
    return {
        "chars": chars,
        "sents": len(sents),
        "sent_med": int(st.median(lens)),
        "sent_p90": int(sorted(lens)[int(len(lens) * 0.9) - 1]) if len(lens) > 2 else max(lens),
        "long80_pct": round(sum(1 for x in lens if x >= 80) / len(lens) * 100, 1),
        "contrast": sum(len(re.findall(p, text)) for p in CONTRAST),
        "hedge_10k": per10k(sum(len(re.findall(p, text)) for p in HEDGE)),
        "meta": sum(len(re.findall(p, text)) for p in META),
        "source_10k": per10k(sum(len(re.findall(p, text)) for p in SOURCE)),
        "em_dash": text.count("—"),
        "question": text.count("?"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = []
    for p in sorted(CONTENT.glob("*.md")):
        md = io.open(p, encoding="utf-8").read()
        try:
            fm = json.loads(md.split("---", 2)[1])
        except Exception:
            continue
        if fm.get("type") == "weekly" or (args.since and fm.get("date", "") < args.since):
            continue
        m = measure(body_of(md))
        m["date"] = fm.get("date"); m["day"] = fm.get("day")
        m["brain"] = len(fm.get("wiki", [])) + len(fm.get("lexicon", []))
        rows.append(m)
    if not rows:
        print("잰 편 없음"); return 1
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1)); return 0

    cols = [("day", "날"), ("date", "날짜"), ("brain", "재료"), ("chars", "자"), ("sent_med", "문장중앙"),
            ("sent_p90", "p90"), ("long80_pct", "80자+%"), ("contrast", "대조"), ("hedge_10k", "헤지/만"),
            ("source_10k", "출처/만"), ("meta", "메타"), ("em_dash", "줄표")]
    print(" ".join(f"{h:>7}" for _, h in cols))
    for r in rows:
        print(" ".join(f"{str(r[k]):>7}" for k, _ in cols))
    print("-" * (8 * len(cols)))
    med = {k: (st.median([r[k] for r in rows]) if isinstance(rows[0][k], (int, float)) else "")
           for k, _ in cols}
    print(" ".join(f"{(str(round(med[k], 1)) if med[k] != '' else '중앙'):>7}" for k, _ in cols))
    with_brain = [r for r in rows if r["brain"]]
    without = [r for r in rows if not r["brain"]]
    print(f"\n재료 붙은 편 {len(with_brain)} · 없는 편 {len(without)}")
    if with_brain and without:
        for k in ("sent_med", "long80_pct", "contrast", "hedge_10k", "source_10k"):
            a = st.median([r[k] for r in with_brain]); b = st.median([r[k] for r in without])
            print(f"  {k:12s} 재료있음 {a:>6} · 없음 {b:>6}")
        print("  ** 표본이 적어 방향만 본다. 회차 산포가 큰 축은 판별에 쓰지 않는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
