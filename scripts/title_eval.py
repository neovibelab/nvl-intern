# -*- coding: utf-8 -*-
"""제목 판정 눈금이 실제로 갈리는가 (2026-09-11).

**왜 재나.** 옛 문구(「알려주나 · 흥미로운가 · 읽고 싶게 하나」)는 ②와 ③이 같은 말이라
6편 전부 「읽고 싶나 1/2」이 나왔다. **분산 0은 정보 0이다.** 눈금에 정의를 박은 뒤
같은 판정자가 실제로 0·1·2를 갈라 쓰는지 본다.

**표본은 제목 21개다.** 시제 평가의 21무리는 기사 묶음이라 제목이 없다 - 같은 규모를 맞추되
대상은 인턴 6편 + 대표 발행본 15편으로 잡는다. 사람 제목이 섞여야 눈금 위쪽이 쓰이는지 보인다.
**판정자는 어느 쪽이 사람 것인지 모른다.**

    python scripts/title_eval.py
"""
import collections
import io
import os
import json
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, duel, publish, steps  # noqa: E402

ARCHIVE = config.ROOT.parent / "claude-NeoVibeLab" / "ecri-newsletter" / "md-archive"
OUT = config.ROOT / "reports" / "tense"
TAG = os.environ.get("TITLE_EVAL_TAG", "")


def human_titles(n: int) -> list[dict]:
    rows = []
    for p in sorted(ARCHIVE.glob("2026*.md")):
        t = io.open(p, encoding="utf-8", errors="replace").read()
        if not t.startswith("---"):
            continue
        head, _, body = t[3:].partition("\n---")
        fm = dict(x.split(":", 1) for x in head.splitlines() if ":" in x)
        if fm.get("category", "").strip() not in ("리서치", "칼럼"):
            continue
        title = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]|^\s*\[[^\]]{0,40}\]\s*", "",
                       fm.get("title", "").strip().strip('"')).strip()
        prose = "\n\n".join(x for x in body.split("\n\n")
                            if len(x.strip()) > 60 and not x.strip().startswith(("#", ">", "![")))[:2600]
        if title and len(prose) > 800:
            rows.append({"who": "사람", "title": title, "body": prose})
    random.seed(20260911)
    random.shuffle(rows)
    return rows[:n]


def main() -> int:
    config.load_env()
    stats = [s for s in publish._load(config.DATA_DIR / "stats.json", []) if s.get("type") != "weekly"]
    rows = []
    for s in stats:
        md = io.open(config.CONTENT_DIR / "ko" / f"{s['slug']}.md", encoding="utf-8").read()
        rows.append({"who": "인턴", "title": s["title_ko"], "body": duel._plain(md.split("---\n", 2)[-1]),
                     "old": (s.get("form") or {}).get("title_check") or {}})
    rows += human_titles(21 - len(rows))
    print(f"== 제목 {len(rows)}개 (인턴 {sum(1 for r in rows if r['who'] == '인턴')} · "
          f"사람 {sum(1 for r in rows if r['who'] == '사람')})")

    recs = []
    for i, r in enumerate(rows, 1):
        got = steps.title_check(r["title"], r["body"], "ko")
        recs.append({"who": r["who"], "title": r["title"], "new": got, "old": r.get("old") or {}})
        old = r.get("old") or {}
        was = f" (옛 눈금 {old.get('clarity')}·{old.get('pull')})" if old else ""
        print(f"  [{i}/{len(rows)}] {r['who']} {got.get('clarity')}·{got.get('pull')}{was} · {r['title'][:38]}")
        io.open(OUT / f"titlecheck{TAG}.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(recs, ensure_ascii=False, indent=1))

    print()
    for axis in ("clarity", "pull"):
        c = collections.Counter(x["new"].get(axis) for x in recs if x["new"])
        name = "알려주나" if axis == "clarity" else "읽고싶나"
        print(f"[새 눈금] {name} 분포 {sorted(c.items())} · 평균 "
              f"{sum(k * v for k, v in c.items() if k is not None) / max(1, sum(c.values())):.2f}")
    old = [x for x in recs if x["old"]]
    if old:
        for axis in ("clarity", "pull"):
            c = collections.Counter(x["old"].get(axis) for x in old)
            n = collections.Counter(x["new"].get(axis) for x in old)
            name = "알려주나" if axis == "clarity" else "읽고싶나"
            print(f"[인턴 6편] {name} 옛 {sorted(c.items())} → 새 {sorted(n.items())}")
    for who in ("인턴", "사람"):
        rs = [x for x in recs if x["who"] == who and x["new"]]
        if rs:
            print(f"[{who}] 평균 알려주나 {sum(x['new']['clarity'] for x in rs) / len(rs):.2f} · "
                  f"읽고싶나 {sum(x['new']['pull'] for x in rs) / len(rs):.2f} · "
                  f"약속 어김 {sum(1 for x in rs if not x['new'].get('kept_promise'))}/{len(rs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
