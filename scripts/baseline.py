# -*- coding: utf-8 -*-
"""사람 기준선 - 인턴의 글을 대표가 쓴 글과 blind로 붙인다 (2026-09-10 신설).

**왜 필요한가.** 지금까지의 측정은 전부 「어제의 나」 기준이라 상대 좌표뿐이다.
승률이 올라도 그게 어느 높이인지 모른다. 실험의 질문은 「인턴이 경력 있는 리서처·칼럼니스트로
자랄 수 있나」이고, 그 답은 **사람이 쓴 글과 붙여야** 나온다. 0%에서 시작해 올라가는 곡선이
이 실험의 절대 좌표다.

**공정하게 붙이는 법.**
- 소재가 가까운 편끼리 붙인다(제목·리드의 고유명사 겹침).
- 사람 글은 6,000자, 인턴 글은 1,400자다. 그대로 붙이면 분량이 판정을 가른다.
  **양쪽에서 같은 길이의 산문만** 뽑는다 - 소제목·인용 블록·이미지를 걷어낸 본문 앞부분.
- 제목은 제목끼리 붙인다. 사람 글 제목의 이모지·「[밤레터 #01]」 같은 표식은 지운다.
- 판정자는 어느 쪽이 사람인지 모른다. 순서도 매번 섞는다.

**한계를 적어 둔다.** 문체로 눈치챌 여지는 남는다(대표는 평서문 직진, 인턴은 합니다체).
가릴 방법이 없으므로 지우지 않고 적어 둔다. 승률을 소수점으로 읽지 않는다.

**대표 원고는 이 저장소에 들어오지 않는다.** 옆 저장소에서 읽기만 하고, 남기는 것은
제목·날짜·승패·판정 이유뿐이다. 원고가 없는 환경(Actions)에서는 조용히 건너뛴다.
"""
import argparse
import datetime as dt
import io
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from intern import config, duel, publish, radar  # noqa: E402

ARCHIVE = pathlib.Path(os.environ.get("NVL_ARCHIVE") or
                       config.ROOT.parent / "claude-NeoVibeLab" / "ecri-newsletter" / "md-archive")
KINDS = ("리서치", "칼럼")          # 인턴이 쓰는 것과 같은 종류만. 대담·공지는 붙일 대상이 아니다
SINCE = "2025"                      # 지금 문체로 쓴 것만
DROP = re.compile(r"^\s*(#{1,6}\s|>|!\[|\||\[.*\]\(.*\)\s*$|---|\*\*\*)")
NOISE = re.compile(r"구독|공유하기|뉴스레터를 받아|무료 구독|후원|광고 문의|커피|이미지 출처")


def _fm(text: str) -> tuple[dict, str]:
    """맨 앞 frontmatter를 성기게 읽는다. 필요한 건 title·date·category뿐이다."""
    if not text.startswith("---"):
        return {}, text
    head, _, body = text[3:].partition("\n---")
    fm = {}
    for line in head.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm, body


def clean_title(t: str) -> str:
    """이모지·머리표식·회차 번호를 지운다. 남기면 어느 쪽이 사람인지 제목만 보고 안다."""
    t = re.sub(r"^\s*#+\s*", "", t or "")
    t = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", t)
    t = re.sub(r"^\s*\[[^\]]{0,40}\]\s*", "", t)
    return re.sub(r"\s+", " ", t).strip()


def prose(md: str, limit: int) -> str:
    """소제목·인용·이미지를 걷어내고 산문만 앞에서부터 limit자. 양쪽에 같은 자를 댄다."""
    out, n = [], 0
    for para in md.split("\n\n"):
        p = " ".join(l.strip() for l in para.splitlines() if not DROP.match(l)).strip()
        if len(p) < 40 or NOISE.search(p):
            continue
        out.append(p)
        n += len(p)
        if n >= limit:
            break
    return "\n\n".join(out)[:limit + 200]


def human_pool() -> list[dict]:
    if not ARCHIVE.exists():
        print(f"  [baseline] 대표 원고 폴더가 없다({ARCHIVE}) - 건너뛴다")
        return []
    pool = []
    for p in sorted(ARCHIVE.glob("2*.md")):
        if p.name[:4] < SINCE:
            continue
        fm, body = _fm(io.open(p, encoding="utf-8", errors="replace").read())
        if fm.get("category") not in KINDS:
            continue
        text = prose(body, 4000)
        if len(text) < 1200:
            continue
        pool.append({"title": clean_title(fm.get("title", p.stem)), "date": fm.get("date", p.name[:8]),
                     "file": p.name, "text": text})
    return pool


def window(text: str, key: set, size: int, mode: str) -> str:
    """사람 글에서 어느 대목을 뗄 것인가. **이게 판정을 가른다.**

    첫 창(`lead`)을 떼면 6,000자짜리 글의 도입부와 인턴의 완결된 1,400자를 붙이는 꼴이라
    인턴에게 유리하다(2026-09-10 실측: 그 규칙으로 본문 3/3이 나왔다). 기본값은 `match` -
    인턴이 다룬 소재와 가장 많이 겹치는 대목, 곧 **사람이 그 주제로 논지를 펴는 자리**를 뗀다.
    """
    paras = [x for x in text.split("\n\n") if len(x) >= 40]
    if mode == "lead" or not paras:
        return text[:size]
    best, score = text[:size], -1
    for i in range(len(paras)):
        chunk, n = [], 0
        for para in paras[i:]:
            chunk.append(para)
            n += len(para)
            if n >= size:
                break
        if n < size * 0.7 and i:
            break
        c = "\n\n".join(chunk)
        v = len(key & radar._tokens(c))
        if v > score:
            best, score = c, v
    return best


def pick(target: dict, pool: list[dict], used: set) -> dict | None:
    """소재가 가장 가까운 편을 고른다. 겹치는 게 없으면 붙이지 않는다 - 엉뚱한 짝은 측정이 아니다."""
    key = radar._tokens(target["title"] + " " + target["text"][:600])
    best, score = None, 0
    for h in pool:
        if h["file"] in used:
            continue
        v = len(key & radar._tokens(h["title"] + " " + h["text"][:600]))
        if v > score:
            best, score = h, v
    return best if score >= 2 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3, help="붙일 인턴 편 수(최근 것부터)")
    ap.add_argument("--lang", default="ko")
    ap.add_argument("--chars", type=int, default=1400, help="양쪽에서 뽑을 산문 길이")
    ap.add_argument("--window", default="match", choices=("match", "lead"),
                    help="사람 글에서 뗄 대목 - 소재가 겹치는 자리(match) 또는 도입부(lead)")
    args = ap.parse_args()
    config.load_env()

    pool = human_pool()
    if not pool:
        return 0
    print(f"== 사람 기준선 · 대표 원고 {len(pool)}편(2025~ 리서치·칼럼)")

    stats = [s for s in publish._load(config.DATA_DIR / "stats.json", []) if s.get("type") != "weekly"]
    done = publish._load(config.DATA_DIR / "baseline.json", [])
    seen = {(d["intern"], d["axis"], d.get("window", "lead")) for d in done}
    used = {d["human_file"] for d in done}
    rows, new = stats[-args.n:], []
    for s in rows:
        if (s["slug"], "제목", args.window) in seen:
            print(f"  [baseline] {s['slug'][:30]} 이미 붙였다 - 건너뜀")
            continue
        try:
            md = io.open(config.CONTENT_DIR / args.lang / f"{s['slug']}.md", encoding="utf-8").read()
        except FileNotFoundError:
            continue
        mine = {"title": s["title_ko"], "text": prose(duel._plain(md.split("---\n", 2)[-1]), 4000)}
        h = pick(mine, pool, used)
        if not h:
            print(f"  [baseline] {s['slug'][:30]} 짝을 못 찾았다(소재 겹침 부족)")
            continue
        used.add(h["file"])
        cut = min(args.chars, len(mine["text"]), len(h["text"]))
        rt = duel.compare(mine["title"], h["title"], duel.TITLE_Q, args.lang)
        hw = window(h["text"], radar._tokens(mine["title"] + " " + mine["text"][:600]), cut, args.window)
        rb = duel.compare(mine["text"][:cut], hw[:cut], duel.BODY_Q, args.lang)
        print(f"  {s['slug'][:30]} vs 「{h['title'][:32]}」 ({cut}자씩)")
        for axis, r in (("제목", rt), ("본문", rb)):
            w = {"a": "intern", "b": "human", "tie": "tie"}[r["winner"]]
            print(f"    {axis} {w} · {r['why'][:90]}")
            new.append({"date": dt.date.today().isoformat(), "intern": s["slug"], "human_title": h["title"],
                        "human_date": h["date"], "human_file": h["file"], "axis": axis,
                        "winner": w, "why": r["why"], "chars": cut, "window": args.window,
                        "lang": args.lang})
    if new:
        publish._dump(config.DATA_DIR / "baseline.json", done + new)
    allr = done + new
    for axis in ("제목", "본문", None):
        rs = [d for d in allr if (axis is None or d["axis"] == axis) and d["winner"] != "tie"
              and d.get("window", "lead") == args.window]
        if rs:
            print(f"  {axis or '합계'} 인턴 승 {sum(1 for d in rs if d['winner'] == 'intern')}/{len(rs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
