# -*- coding: utf-8 -*-
"""AI티를 목록이 아니라 **분포 거리**로 잰다 (2026-09-16 신설).

**왜 목록으로는 안 되나.** 지금 문체 자는 전부 금칙 카운트다(대조 공식·메타 수사·줄표·헤지).
그것들을 0으로 만들어도 글은 여전히 AI가 쓴 것처럼 읽힌다. 차이는 **어느 단어를 썼나**가 아니라
**문장이 얼마나 고르게 생겼나**에 있다. 사람은 들쭉날쭉하게 쓰고 기계는 평평하게 쓴다.

**그래서 사람 코퍼스를 자로 쓴다.** 대표 발행본은 사람이 쓴 것의 분포다. 인턴 글이 그 분포에서
얼마나 떨어져 있는지가 AI티의 조작적 정의가 된다. **무엇이 AI티인지 우리가 정하지 않는다** -
두 코퍼스가 실제로 갈리는 축만 남기고 나머지는 버린다.

**주의 - 설계상 다른 것은 축이 아니다.** 대표는 평서문 직진, 인턴은 합니다체다. 어미·존대 축은
문체 차이가 아니라 포맷 차이라 비교에서 뺀다. 분량도 다르다(1천자 대 6천자)라 밀도로만 본다.

    python scripts/style_gap.py
"""
import collections
import io
import json
import pathlib
import re
import statistics as st
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, duel, publish  # noqa: E402

ARCHIVE = config.ROOT.parent / "claude-NeoVibeLab" / "ecri-newsletter" / "md-archive"
CONJ = r"그러나|하지만|또한|즉|따라서|반면|그리고|그래서|다만|물론"
HEDGE = r"알려졌|로 보입니다|인 듯|가능성이 (있|높)|것으로 보|수 있습니다"
MODIF = r"매우|상당히|특히|크게|분명히|확실히|충분히|명확히"
DROP = re.compile(r"^\s*(#{1,6}\s|>|!\[|\||---|\*\*\*)")


def sentences(t: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=다)\.\s|(?<=요)\.\s|[.!?]\s|\n\n", t) if len(s.strip()) > 5]


def _mattr(words: list[str], w: int = 200) -> float:
    """고정 창 어휘 다양도. 단순 TTR은 글이 짧을수록 높게 나와 길이를 문체로 착각하게 만든다."""
    if len(words) < w:
        return round(len(set(words)) / max(1, len(words)), 3)
    vals = [len(set(words[i:i + w])) / w for i in range(0, len(words) - w, 50)]
    return round(sum(vals) / len(vals), 3)


def measure(text: str) -> dict:
    """모델을 쓰지 않는다. 전부 세는 것이다."""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)          # 링크는 표기라 벗긴다
    sents = sentences(t)
    lens = [len(s) for s in sents] or [1]
    paras = [p for p in t.split("\n\n") if len(p.strip()) > 40]
    plens = [len(p) for p in paras] or [1]
    chars = max(1, len(re.sub(r"\s", "", t)))
    words = re.findall(r"[가-힣A-Za-z]{2,}", t)
    heads = [s.split()[0] for s in sents if s.split()]
    per10k = lambda p: round(len(re.findall(p, t)) / chars * 10000, 1)  # noqa: E731
    return {
        # ── 리듬 - 사람은 들쭉날쭉하다
        "문장길이 변동": round(st.pstdev(lens) / (st.mean(lens) or 1), 3),
        "문단길이 변동": round(st.pstdev(plens) / (st.mean(plens) or 1), 3),
        "문장 중앙": int(st.median(lens)),
        # ── 반복 - 기계는 같은 자리에서 시작한다.
        # **길이에 딸려 오는 축은 창을 고정해서 잰다.** 짧은 글은 그냥 두면 반복이 적고 다양도가 높게 나온다.
        "첫어절 반복": round(1 - len(set(heads[:12])) / max(1, len(heads[:12])), 3),
        "어휘 다양도": _mattr(words),
        # ── 밀도
        "접속부사 만자": per10k(CONJ),
        "헤지 만자": per10k(HEDGE),
        "수식어 만자": per10k(MODIF),
        "「것」 만자": per10k(r"것[이을은는의]?"),
        "쉼표 만자": round(t.count(",") / chars * 10000, 1),
        "숫자 만자": round(len(re.findall(r"\d", t)) / chars * 10000, 1),
    }


def intern_bodies() -> list[str]:
    rows = [s for s in publish._load(config.DATA_DIR / "stats.json", []) if s.get("type") != "weekly"]
    out = []
    for s in rows:
        p = config.CONTENT_DIR / "ko" / f"{s['slug']}.md"
        if p.exists():
            out.append(duel._plain(io.open(p, encoding="utf-8").read().split("---\n", 2)[-1]))
    return [x for x in out if len(x) > 400]


def human_bodies(limit: int = 60) -> list[str]:
    out = []
    for p in sorted(ARCHIVE.glob("2*.md"), reverse=True):
        if p.name[:4] < "2025":
            continue
        raw = io.open(p, encoding="utf-8", errors="replace").read()
        if not raw.startswith("---"):
            continue
        head, _, body = raw[3:].partition("\n---")
        if "category: 리서치" not in head and "category: 칼럼" not in head:
            continue
        prose = "\n\n".join(x for x in body.split("\n\n")
                            if len(x.strip()) > 60 and not DROP.match(x.strip()))
        if len(prose) > 1500:
            out.append(prose)
        if len(out) >= limit:
            break
    return out


def main() -> int:
    ai, human = intern_bodies(), human_bodies()
    print(f"== 인턴 {len(ai)}편 · 대표 발행본 {len(human)}편 (2025~ 리서치·칼럼)\n")
    A = [measure(x) for x in ai]
    H = [measure(x) for x in human]
    keys = list(A[0])
    print(f"{'축':14s} {'인턴':>8s} {'대표':>8s} {'대표 분포 안':>12s}  판정")
    print("-" * 62)
    gaps = []
    for k in keys:
        a, h = st.median([x[k] for x in A]), st.median([x[k] for x in H])
        col = sorted(x[k] for x in H)
        pct = round(sum(1 for v in col if v < a) / len(col) * 100)
        # 대표 분포의 10~90 퍼센타일 밖이면 갈린 축이다
        verdict = "**갈린다**" if pct <= 10 or pct >= 90 else ("가깝다" if 25 <= pct <= 75 else "약간")
        gaps.append((abs(pct - 50), k, a, h, pct, verdict))
        print(f"{k:14s} {a:8.3f} {h:8.3f} {pct:11d}%  {verdict}")
    print("\n갈린 축부터:")
    for _, k, a, h, pct, v in sorted(gaps, reverse=True)[:5]:
        print(f"  {k} - 인턴 {a} vs 대표 {h} (대표 {len(H)}편 중 {pct}% 지점)")
    out = {"intern_n": len(A), "human_n": len(H),
           "intern": {k: st.median([x[k] for x in A]) for k in keys},
           "human": {k: st.median([x[k] for x in H]) for k in keys}}
    (config.ROOT / "reports").mkdir(exist_ok=True)
    io.open(config.ROOT / "reports" / "style-gap.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    # 라이브 기준선 - 인턴이 매 편 자기 위치를 잴 자다. 갈린 다섯 축의 사람 분포를 통째로 남긴다.
    from intern import style
    base = {"source": "대표 발행본 2025~ 리서치·칼럼", "n": len(human), "made": "2026-09-16",
            "axes": {k: sorted(round(style.measure(x)[k], 3) for x in human) for k in style.AXES}}
    io.open(style.BASELINE, "w", encoding="utf-8", newline=chr(10)).write(
        json.dumps(base, ensure_ascii=False, indent=1))
    print(f"\n기준선 갱신 - {style.BASELINE.name} ({len(human)}편 · 축 {len(style.AXES)}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
