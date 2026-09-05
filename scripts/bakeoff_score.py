# -*- coding: utf-8 -*-
"""인턴 모델 비교 채점 - reports/bakeoff/runs.json → SCORES.md.

축은 인턴이 실제로 지켜야 하는 것만 둔다.
- 규격: 본문 700~1000자(공백 제외). 인턴 프롬프트가 요구하는 유일한 분량 규격이다.
- 판정 안정성: 같은 소재 3회에서 좌표(요인·단계)와 시제가 몇 번 일치하나. ③이 실험의 급소다.
- 지침 준수: 가운데 줄표, 불릿·표, 메타 수사, 대조공식(「A가 아니라 B다」류), 극존칭.
- 값·시간.
회차 산포가 모델 간 차이보다 큰 축은 판별 축으로 쓰지 않는다(옆 세션 실측).
"""
import collections
import io
import json
import pathlib
import re
import statistics as st

OUT = pathlib.Path(__file__).resolve().parent.parent / "reports" / "bakeoff"

META = [r"진짜 (질문|문제)은", r"흥미로운 (점|지점)은", r"중요한 것은", r"주목할 (점|만한)", r"핵심은"]
CONTRAST = [r"[가-힣]+이 아니라 [가-힣]", r"[가-힣]+가 아니라 [가-힣]", r"[가-힣]+이 아닌 [가-힣]",
            r"[가-힣]+보다는 [가-힣]+다", r"[^.]{2,20}은 [^.]{2,20}지만"]
HONOR = [r"드립니다", r"하십시오", r"여쭙", r"드리겠습니다"]


def count(pats: list[str], t: str) -> int:
    return sum(len(re.findall(p, t)) for p in pats)


def score_body(b: str) -> dict:
    chars = len(re.sub(r"\s", "", b))
    sents = [s for s in re.split(r"(?<=다)[.]\s|[.!?]\s", b) if len(s.strip()) > 5]
    return {
        "chars": chars,
        "spec": 700 <= chars <= 1000,
        "em_dash": b.count("—") + b.count(" - "),
        "bullets": len(re.findall(r"^\s*[-*·]\s|^\s*\d+[.)]\s|^\|", b, re.M)),
        "meta": count(META, b),
        "contrast": count(CONTRAST, b),
        "honor": count(HONOR, b),
        "sent_med": int(st.median([len(s) for s in sents])) if sents else 0,
        "long80": round(sum(1 for s in sents if len(s) >= 80) / len(sents) * 100, 1) if sents else 0.0,
        "sources_named": len(re.findall(r"(보도|보도했다|전했다|집계|발표|기고|리포트|조사)", b)),
    }


def med_range(xs: list) -> str:
    xs = [x for x in xs if x is not None]
    if not xs:
        return "-"
    m = st.median(xs)
    m = int(m) if float(m).is_integer() else round(m, 2)
    lo, hi = min(xs), max(xs)
    if lo == hi:
        return f"{m}"
    fmt = (lambda v: int(v) if float(v).is_integer() else round(v, 2))
    return f"{m} ({fmt(lo)}~{fmt(hi)})"


def main() -> None:
    recs = json.loads(io.open(OUT / "runs.json", encoding="utf-8").read())
    recs = [r for r in recs if not r.get("error")]
    for r in recs:
        r.update(score_body(r["body"]))
    subs = sorted({r["subject"] for r in recs})
    models = sorted({r["model"] for r in recs})
    lines = ["# 인턴 프롬프트 모델 비교 - 채점", "",
             "회차 3회의 **중앙값**이고 괄호는 최소~최대다. 산포 자체가 결과다. 하네스 = `scripts/bakeoff.py`.", ""]
    for s in subs:
        rs = [r for r in recs if r["subject"] == s]
        title = rs[0]["title"] if rs else s
        lines += [f"## 소재 `{s[:8]}` ({title})", "", "| | " + " | ".join(m.replace("claude-", "") for m in models) + " |",
                  "|---|" + "---:|" * len(models)]
        rows = [
            ("글자수 (규격 700~1000)", lambda x: x["chars"]),
            ("규격 밖 회차", None),
            ("문장 중앙값", lambda x: x["sent_med"]),
            ("80자+ %", lambda x: x["long80"]),
            ("대조공식", lambda x: x["contrast"]),
            ("메타 수사", lambda x: x["meta"]),
            ("가운데 줄표", lambda x: x["em_dash"]),
            ("불릿·표", lambda x: x["bullets"]),
            ("극존칭", lambda x: x["honor"]),
            ("출처 명시", lambda x: x["sources_named"]),
            ("시간(초)", lambda x: x["sec"]),
            ("출력 토큰", lambda x: x["out"]),
            ("편당 $", lambda x: x["cost"]),
        ]
        for name, fn in rows:
            cells = []
            for m in models:
                mr = [r for r in rs if r["model"] == m]
                cells.append(str(sum(1 for r in mr if not r["spec"])) if fn is None else med_range([fn(r) for r in mr]))
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines += ["", "**판정 3회 (요인 · 출발→도착 · 시제)**", "",
                  "| | " + " | ".join(m.replace("claude-", "") for m in models) + " |", "|---|" + "---|" * len(models)]
        for i in (1, 2, 3):
            cells = []
            for m in models:
                mr = [r for r in rs if r["model"] == m and r["run"] == i]
                cells.append(f"{mr[0]['factor']} {mr[0]['from_stage']}→{mr[0]['to_stage']} · {mr[0]['tense']}" if mr else "-")
            lines.append(f"| r{i} | " + " | ".join(cells) + " |")
        cells = []
        for m in models:
            mr = [r for r in rs if r["model"] == m]
            coord = collections.Counter((r["factor"], r["from_stage"], r["to_stage"]) for r in mr)
            tense = collections.Counter(r["tense"] for r in mr)
            cells.append(f"좌표 {coord.most_common(1)[0][1]}/3 · 시제 {tense.most_common(1)[0][1]}/3" if mr else "-")
        lines += ["| **자기 일치** | " + " | ".join(cells) + " |",
                  "| 베팅 | " + " | ".join(f"{sum(1 for r in rs if r['model'] == m and r['bet'])}/3" for m in models) + " |",
                  "| 레이더와 일치 | " + " | ".join(f"{sum(1 for r in rs if r['model'] == m and r['agrees'])}/3" for m in models) + " |", ""]
    lines += ["## 합계", "", "| | " + " | ".join(m.replace("claude-", "") for m in models) + " |", "|---|" + "---:|" * len(models)]
    for name, fn in [("회차", lambda rs: len(rs)), ("규격 밖", lambda rs: sum(1 for r in rs if not r["spec"])),
                     ("편당 $ 중앙값", lambda rs: round(st.median([r["cost"] for r in rs]), 3)),
                     ("편당 초 중앙값", lambda rs: round(st.median([r["sec"] for r in rs]), 1)),
                     ("실비 $", lambda rs: round(sum(r["cost"] for r in rs), 2))]:
        lines.append(f"| {name} | " + " | ".join(str(fn([r for r in recs if r["model"] == m])) for m in models) + " |")
    io.open(OUT / "SCORES.md", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
