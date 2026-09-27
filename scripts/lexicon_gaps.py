# -*- coding: utf-8 -*-
"""인턴이 푼 개념 가운데 렉시콘에 없는 것 - 결번 후보 (2026-09-27 신설).

    python scripts/lexicon_gaps.py

인턴의 사전(`data/entities.json`)에서 개념(kind=concept)만 꺼내 두뇌 렉시콘의 표제어(`## `)와 대조한다.
**후보를 뽑기만 한다.** 렉시콘 항목은 학술 spine 출처(저자·연도·쪽)가 있어야 서고, 두뇌에는 봇이 쓰지 않는다.
인턴의 풀이는 웹 한두 줄이라 항목의 재료가 못 된다 - 「사전에 이 자리가 비었다」는 신호로만 쓴다.
채우는 일은 세션이 `ai-coworker/LEXICON-결번.md` 절차로 한다.

여러 편에 나온 개념이 먼저다. 한 편에만 나온 용어는 그 기사의 말일 수 있다.
"""
import pathlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intern import entities  # noqa: E402

LEX = ROOT.parent / "claude-virtual-brain" / "llm-wiki" / "raw" / "lexicon"


def _norm(t: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", (t or "").lower())


def headwords() -> list[str]:
    out = []
    for p in LEX.glob("*.md"):
        if p.name.upper() in ("README.MD", "INDEX.MD"):
            continue
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.startswith("## "):
                # 「라이브 프로모션; 프로모터·티켓팅·공연장」 - 세미콜론·가운뎃점으로 이음말을 쪼갠다
                out += [_norm(x) for x in re.split(r"[;·,/()]", ln[3:]) if _norm(x)]
    return out


def main() -> int:
    if not LEX.exists():
        print(f"렉시콘을 못 찾았다 - {LEX}")
        return 2
    hw = headwords()
    es = entities.load()["entries"]
    cons = [(k, e) for k, e in es.items() if e.get("kind") == "concept"]
    gaps = []
    for k, e in cons:
        names = [_norm(e.get("name_ko")), _norm(e.get("name_en"))]
        # 두 글자 이하(A&R → ar)는 부분 일치를 쓰면 stars에 걸린다 - 그때는 같아야 한다
        hit = any(n and any((n == h) if len(n) < 3 else (n in h or (len(h) >= 3 and h in n)) for h in hw) for n in names)
        if not hit:
            gaps.append((len(e.get("pieces", [])), k, e))
    gaps.sort(key=lambda x: -x[0])
    print(f"렉시콘 표제어 조각 {len(hw)} · 인턴이 푼 개념 {len(cons)} · 렉시콘에 없는 것 {len(gaps)}\n")
    for n, _k, e in gaps:
        print(f"- {e.get('name_ko')} ({e.get('name_en')}) · {n}편 · 첫 등장 {e.get('first') or '-'}")
        print(f"  인턴 풀이: {e.get('ko')}")
        if e.get("url"):
            print(f"  확인한 곳: {e.get('source') or ''} {e['url']}")
    if gaps:
        print("\n두 편 이상 나온 것부터 본다. 표제어로 세울 만하면 LEXICON-결번.md에 올리고 spine 출처를 찾는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
