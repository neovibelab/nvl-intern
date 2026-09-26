# -*- coding: utf-8 -*-
"""이슈 스레드 - 흩어진 편을 하나의 판으로 잇는다 (2026-09-26 신설).

**왜 필요한가.** 인턴은 지난 편을 **시간 순으로 직전 두 편**만 읽었다(`learn.recent_block`).
같은 이슈를 찾아 읽지 않았다. 그런데 첫 16편 중 7편(44%)이 「AI 음악의 권리·정산」 한 판이었다 -
09-07부터 09-24까지 일곱 번 돌아왔는데 **매번 처음 보는 사건처럼 썼다.**
대표가 세운 목표 둘째 - 「하나의 이슈에 연결된 여러 맥락을 파악하고 거기서 인사이트를 전한다」 -
는 재료가 쌓여 있는데 인턴이 그걸 볼 통로가 없어서 막혀 있었다.

**무엇을 하나.**
- 편마다 이슈 하나를 단다. 인턴이 소재를 고를 때 같이 정한다(`steps.select`).
- 글을 쓸 때 **같은 이슈의 이전 편**을 읽는다. 직전 두 편 읽기(문체·지적 학습)는 그대로 둔다 - 목적이 다르다.
- 이슈에 아직 종합하지 않은 편이 `RIPE`개 쌓인 뒤 그 이슈가 다시 오면 **그날 편을 종합 편으로 쓴다.**
  하루 한 편 리듬은 그대로다. 일요일 휴재 약속을 건드리지 않으려고 따로 발송하지 않는다.

**이슈 입도는 넓게 잡지 않는다.** 「음악 권리」처럼 크게 묶으면 서로 무관한 편이 한 스레드에 들어가
독자가 이어 읽을 이유가 사라진다. 「AI 음악의 권리·정산」 정도 - 같은 당사자와 같은 쟁점이 반복되는 단위.
첫 한 달은 세션이 태그를 검수한다(2026-09-26 대표 확정).

**되돌림 조건** - 종합 편이 개별 편 요약을 블라인드 대결에서 과반 이기지 못하면(표본 6)
잇는 판단이 글을 낫게 하지 못한 것이다. 그때는 종합 모드를 끄고 스레드 읽기만 남긴다.
"""
import io
import re

from . import config, publish

PATH = config.DATA_DIR / "issues.json"
RIPE = 3          # 아직 종합하지 않은 편이 이만큼 쌓인 뒤 같은 이슈가 오면 그날을 종합 편으로 쓴다


def load() -> dict:
    d = publish._load(PATH, {})
    d.setdefault("issues", {})
    d.setdefault("pieces", {})
    return d


def save(d: dict) -> None:
    publish._dump(PATH, d)


def new_id(label_en: str, d: dict) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (label_en or "issue").lower()).strip("-")[:40] or "issue"
    iid, k = base, 2
    while iid in d["issues"]:
        iid, k = f"{base}-{k}", k + 1
    return iid


def assign(d: dict, slug: str, date: str, iid: str | None, label_ko: str = "", label_en: str = "") -> str:
    """편에 이슈를 단다.

    - iid가 이미 있는 이슈면 거기 붙인다.
    - iid가 **주어졌는데 아직 없으면 그 id로 새로 연다.** 라벨에서 다시 만들지 않는다 -
      처음에 여기서 라벨로 id를 다시 만들었더니 같은 이슈를 넘겨도 편마다 새 이슈가 생겼다(2026-09-26 실측).
    - iid가 없으면 라벨에서 id를 만든다.
    """
    if iid:
        iid = re.sub(r"[^a-z0-9-]+", "-", iid.lower()).strip("-")[:48] or None
    if not iid:
        iid = new_id(label_en or label_ko, d)
    if iid not in d["issues"]:
        d["issues"][iid] = {"label_ko": label_ko or label_en or iid, "label_en": label_en or label_ko or iid,
                            "created": date, "synth": []}
    d["pieces"][slug] = iid
    return iid


def _stats() -> list[dict]:
    return [s for s in publish._load(config.DATA_DIR / "stats.json", [])
            if s.get("type") != "weekly" and s.get("region")]


def members(d: dict, iid: str, before: str | None = None) -> list[dict]:
    """그 이슈에 달린 편들. 날짜 순. before가 있으면 그 날짜 **전**만."""
    slugs = {s for s, i in d["pieces"].items() if i == iid}
    rows = [s for s in _stats() if s["slug"] in slugs and (before is None or s["date"] < before)]
    return sorted(rows, key=lambda s: s["date"])


def last_synth_date(d: dict, iid: str) -> str:
    syn = (d["issues"].get(iid) or {}).get("synth") or []
    return max((x.get("date", "") for x in syn), default="")


def unsynth(d: dict, iid: str, before: str | None = None) -> list[dict]:
    """마지막 종합 편 이후에 쌓인 편."""
    cut = last_synth_date(d, iid)
    return [s for s in members(d, iid, before) if s["date"] > cut]


def ripe(d: dict, iid: str | None, date: str) -> bool:
    return bool(iid) and iid in d["issues"] and len(unsynth(d, iid, before=date)) >= RIPE


def mark_synth(d: dict, iid: str, slug: str, date: str) -> None:
    d["issues"][iid].setdefault("synth", []).append({"slug": slug, "date": date})


def label(d: dict, iid: str, lang: str = "ko") -> str:
    x = d["issues"].get(iid) or {}
    return x.get("label_ko" if lang == "ko" else "label_en") or x.get("label_ko") or iid


def open_text(d: dict, date: str, limit: int = 14) -> str:
    """선정 프롬프트에 보여줄 이슈 목록. 최근에 움직인 순."""
    rows = []
    for iid, x in d["issues"].items():
        ms = members(d, iid, before=date)
        if not ms:
            continue
        rows.append((ms[-1]["date"], iid, x, ms))
    rows.sort(reverse=True)
    out = []
    for last, iid, x, ms in rows[:limit]:
        pend = len(unsynth(d, iid, before=date))
        out.append(f"- {iid} · {x.get('label_ko')} · {len(ms)}편 · 마지막 {last} · 종합 전 {pend}편"
                   f" · 최근: 「{ms[-1].get('title_ko', '')[:40]}」")
    return "\n".join(out) or "(아직 없다)"


# ── 스레드 읽기 ───────────────────────────────────────────────────────────

def _piece(slug: str, lang: str) -> tuple[dict, str]:
    p = config.CONTENT_DIR / lang / f"{slug}.md"
    if not p.exists():
        return {}, ""
    return publish.parse_piece(p)


def _principle(body: str, lang: str) -> str:
    head = "**가져갈 것** ·" if lang == "ko" else "**Takeaway** ·"
    for ln in body.split("\n"):
        if ln.strip().startswith(head):
            return ln.strip()[len(head):].strip()
    return ""


def _preds() -> dict:
    return {p["slug"]: p for p in publish._load(config.DATA_DIR / "predictions.json", [])}


def _rechecks() -> dict:
    out: dict = {}
    for r in publish._load(config.DATA_DIR / "recheck.json", []):
        out.setdefault(r.get("slug"), []).append(r)
    return out


def thread_block(d: dict, iid: str | None, date: str, lang: str = "ko", cap: int = 6000,
                 full: bool = False) -> str:
    """같은 이슈의 이전 편을 집필 자리에 붙인다.

    기본은 편마다 요약·결론 한 줄씩이다. `full`(종합 편)이면 **이전 판단과 그 뒤 드러난 것**까지 붙인다 -
    종합 편이 「3주 전에 이렇게 봤는데 지금 보니」를 쓰려면 그 재료가 있어야 한다.
    """
    if not iid:
        return ""
    ms = unsynth(d, iid, before=date) if full else members(d, iid, before=date)[-5:]
    if not ms:
        return ""
    from . import learn  # noqa: PLC0415 - 순환 참조 회피
    preds, rch = _preds(), _rechecks()
    ko = lang == "ko"
    lines = []
    for i, s in enumerate(ms):
        fm, body = _piece(s["slug"], lang)
        summ = (fm.get("source_summary") or "").strip()
        prin = _principle(body, lang)
        title = s.get("title_ko" if ko else "title_en", "")
        block = [f"[{s['date']}] 「{title}」 {s.get('factor')} {s.get('from_stage')}→{s.get('to_stage')} · {s.get('tense')}"]
        if summ:
            block.append(("  무슨 일 · " if ko else "  what happened · ") + summ[:420])
        if prin:
            block.append(("  그때 뽑은 것 · " if ko else "  takeaway then · ") + prin[:220])
        if full:
            p = preds.get(s["slug"])
            if p:
                block.append(("  그때 건 예측 · " if ko else "  prediction then · ")
                             + f"{p['claim_ko' if ko else 'claim_en']} (기한 {p['by_date']} · {p['status']})")
            for r in rch.get(s["slug"], [])[:1]:
                if r.get("kind") in ("followup", "correction"):
                    block.append(("  그 뒤 드러난 것 · " if ko else "  since then · ")
                                 + f"[{r['kind']}] {str(r.get('why', ''))[:260]}")
        if full and i >= len(ms) - 2:
            b = learn._body(s["slug"], lang)
            if b:
                block.append("  본문 일부 · " + " ".join(b.split())[:700])
        lines.append("\n".join(block))
    return ("\n\n".join(lines))[:cap]


def thread_links(d: dict, iid: str | None, date: str, lang: str = "ko", n: int = 4) -> list[tuple[str, str, str]]:
    """「이어지는 흐름」에 걸 이전 편 링크. (날짜, 제목, URL)."""
    if not iid:
        return []
    ms = members(d, iid, before=date)[-n:]
    root = config.SITE_URL + ("" if lang == "ko" else "/en")
    return [(s["date"], s.get("title_ko" if lang == "ko" else "title_en", ""), f"{root}/{s['slug']}") for s in ms]
