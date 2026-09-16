# -*- coding: utf-8 -*-
"""수식어 0은 어디서 나왔나 (2026-09-16).

**규칙에는 없다.** 프롬프트·자기 규칙·검수 어디에도 수식어를 막는 문장이 없다.
그런데 인턴 9편 전부 강조부사 0 · 정도부사 0 · 형용 어미 0이다(대표는 각각 4.3 · 11.9 · 10.7).

셋 중 무엇인지 가른다.
- **A 현행** - 지금 프롬프트 전부
- **B 문체 규칙 없이** - `STYLE_KO`만 뺀다
- **C 맨몸** - 페르소나와 「900자 논평」만. 우리 지시가 거의 없는 상태

C에 수식이 있으면 **우리 지시가 누른 것**이고, C도 0이면 **모델 기본 문체**다.
B와 C가 갈리면 범인은 `STYLE_KO`, 안 갈리면 나머지 지시(사실 제약·분량·출처 요구)의 합이다.

    python scripts/modifier_ablation.py [--date 2026-09-15]
"""
import argparse
import io
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, llm, steps  # noqa: E402

PATS = {
    "강조부사": r"매우|상당히|특히|크게|분명히|확실히|충분히|명확히",
    "정도부사": r"훨씬|더욱|가장|아주|꽤|제법|무척|한층|급격히|빠르게|조금|약간|거의|대부분|일부",
    "형용 어미": r"[가-힣]{1,4}(적인|스러운|로운|다운)\s",
}


def density(t: str) -> dict:
    c = max(1, len(re.sub(r"\s", "", t)))
    return {k: round(len(re.findall(p, t)) / c * 10000, 1) for k, p in PATS.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-15")
    args = ap.parse_args()
    config.load_env()

    lg = json.loads(io.open(config.LOG_DIR / f"{args.date}.json", encoding="utf-8").read())
    cl = lg["cluster"]
    cluster_text = "\n".join(f"- [{x.get('source')}] {x.get('title')}" for x in cl["items"])
    j, live = lg["judgment"], lg.get("draft_ko_final") or ""

    print(f"== 대조군 · {args.date} 소재 「{cl['items'][0]['title'][:40]}」\n")
    rows = [("A 현행(실제 발행본)", live)]

    # B - 문체 규칙만 뺀다
    keep = steps.STYLE_KO
    try:
        steps.STYLE_KO = "(문체 규칙 없음)"
        rows.append(("B 문체 규칙 없이", steps.write_ko(cluster_text, j, "")))
    finally:
        steps.STYLE_KO = keep

    # C - 맨몸. 페르소나와 분량만 준다
    bare = llm.ask(f"""[오늘의 사건]
{cluster_text}

이 사건을 놓고 한국 엔터 실무자를 위한 논평을 한국어로 900자 안팎 쓴다. 본문만 쓴다.""",
                   system=steps.PERSONA, max_tokens=4000)
    rows.append(("C 맨몸(페르소나+분량만)", bare))

    print(f"{'조건':22s} {'강조':>6s} {'정도':>6s} {'형용':>6s}  자수")
    print("-" * 52)
    out = []
    for name, text in rows:
        d = density(text)
        out.append({"arm": name, **d, "chars": len(text)})
        print(f"{name:22s} {d['강조부사']:6.1f} {d['정도부사']:6.1f} {d['형용 어미']:6.1f}  {len(text)}")
    io.open(config.ROOT / "reports" / "modifier-ablation.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps({"date": args.date, "rows": out}, ensure_ascii=False, indent=1))
    print("\n대표 발행본 중앙값 · 강조 4.3 · 정도 11.9 · 형용 10.7")
    return 0


if __name__ == "__main__":
    sys.exit(main())
