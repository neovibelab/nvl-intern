# -*- coding: utf-8 -*-
"""⑦ 발행·기록 - content/ 마크다운, data/stats.json, data/predictions.json, data/log/, 자기 규칙 후보."""
import io
import json
import re
from datetime import timedelta

from . import config, steps

AI_LABEL_KO = "이 글은 엔터문화연구소의 AI 인턴 1호가 사람 개입 없이 썼습니다."
AI_LABEL_EN = "Written by AI Intern 01 at Neo Vibe Lab with no human in the loop."


def _urls(lang: str) -> dict:
    q = "?lang=en" if lang == "en" else ""
    root = config.SITE_URL + ("/en" if lang == "en" else "")
    return {"about": config.ABOUT_URL + q, "grid": f"{root}/grid", "growth": f"{root}/growth"}


def frame_block(lang: str, day: int) -> str:
    """매회 머리에 붙는 실험 프레임. 뉴스 요약이나 에세이로 읽히지 않게 하는 장치(2026-09-05 대표 지시)."""
    u = _urls(lang)
    if lang == "ko":
        return (f"**엔터문화연구소의 AI 실험** · AI 인턴 1호가 사람 개입 없이 소재를 고르고 판정하고 쓰고 발행합니다. "
                f"D+{day} · [이게 무엇인가]({u['about']}) · [격자]({u['grid']}) · [성장]({u['growth']})")
    return (f"**A Neo Vibe Lab AI experiment** · AI Intern 01 picks the event, makes the call, writes and publishes with no human in the loop. "
            f"Day {day} · [What this is]({u['about']}) · [Grid]({u['grid']}) · [Growth]({u['growth']})")


def sources_block(lang: str, summary: str, items: list[dict]) -> str:
    """오늘의 소재 - 사건·기사 요약 + 원문 인링크."""
    head = "**오늘의 소재**" if lang == "ko" else "**Today's source**"
    lines = []
    for x in items:
        if not x.get("url"):
            continue
        outlet = (x.get("source") or x.get("region") or "").strip()
        title = ((x.get("title_en") if lang == "en" else None) or x.get("title") or "").strip().replace("]", "］").replace("[", "［")
        date = (x.get("published_date") or "")[:10]
        lines.append(f"- [{(outlet + ' · ') if outlet else ''}{title}]({x['url']})" + (f" · {date}" if date else ""))
    first = f"{head} · {summary.strip()}" if summary.strip() else head
    return first + ("\n\n" + "\n".join(lines) if lines else "")


def grid_table(lang: str, j: dict) -> str:
    """21칸 격자. ● 도착 칸, ○ 출발 칸(다를 때만)."""
    st_labels = [s if lang == "ko" else config.STAGES_EN[s] for s in config.STAGES]
    rows = ["| | " + " | ".join(st_labels) + " |", "|---|:-:|:-:|:-:|"]
    for f in config.FACTORS:
        cells = []
        for s in config.STAGES:
            if f == j["factor"] and s == j["to_stage"]:
                cells.append("●")
            elif f == j["factor"] and s == j["from_stage"]:
                cells.append("○")
            else:
                cells.append("·")
        rows.append(f"| {f if lang == 'ko' else config.FACTORS_EN[f]} | " + " | ".join(cells) + " |")
    legend = ("<sub>● 도착 · ○ 출발 · 7요인 × 3단계 = 21칸. 인턴이 매일 한 칸을 찍는다.</sub>" if lang == "ko"
              else "<sub>● arrives · ○ departs · 7 factors × 3 stages = 21 cells. The intern marks one every day.</sub>")
    return "\n".join(rows) + "\n\n" + legend


def slugify(title_en: str, date: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (title_en or "piece").lower()).strip("-")[:50]
    return f"{date}-{s or 'piece'}"


def _load(p, default):
    try:
        return json.loads(io.open(p, encoding="utf-8").read())
    except Exception:
        return default


def _dump(p, obj):
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(obj, ensure_ascii=False, indent=2))


def day_number(date: str) -> int:
    stats = _load(config.DATA_DIR / "stats.json", [])
    first = config.LAUNCH_DATE or (stats[0]["date"] if stats else date)
    from datetime import date as D
    y, m, d = map(int, first.split("-")); y2, m2, d2 = map(int, date.split("-"))
    return (D(y2, m2, d2) - D(y, m, d)).days + 1


def piece_markdown(lang: str, date: str, slug: str, j: dict, body: str, meta: dict) -> str:
    title = j["title_ko"] if lang == "ko" else j["title_en"]
    header = steps.header_line(j, lang)
    principle = j["principle_ko"] if lang == "ko" else j["principle_en"]
    label = AI_LABEL_KO if lang == "ko" else AI_LABEL_EN
    bet = j.get("bet")
    fm = {
        "title": title, "date": date, "slug": slug, "lang": lang, "day": meta["day"],
        "factor": j["factor"], "from_stage": j["from_stage"], "to_stage": j["to_stage"], "tense": j["tense"],
        "radar_tense": meta.get("radar_tense"), "agrees": j.get("agrees"),
        "bet": bet, "claims_total": meta.get("claims_total"), "claims_verified": meta.get("claims_verified"),
        "review_rounds": meta.get("review_rounds"), "unresolved": meta.get("unresolved"),
        "sources": meta.get("sources", []), "source_items": meta.get("source_items", []),
        "source_summary": (meta.get("source_summary") or {}).get(lang, ""),
        "wiki": meta.get("wiki", []), "lexicon": meta.get("lexicon", []),
    }
    unresolved_line = ""
    if meta.get("unresolved"):
        unresolved_line = ("\n\n> 미해결. 검수를 정해진 횟수 안에 통과하지 못했습니다. 지적을 그대로 둡니다: " if lang == "ko"
                           else "\n\n> Unresolved. This piece failed its own review within the allowed rounds. The notes stay: ") \
                          + " / ".join(((meta.get("last_issues_en") if lang == "en" else None) or meta.get("last_issues", []))[:3])
    bet_line = ""
    if bet:
        if lang == "ko":
            bet_line = f"\n\n**베팅** · {bet['claim_ko']} · {bet['by_days']}일 안 · 확인: {bet['check_ko']}"
        else:
            bet_line = f"\n\n**Bet** · {bet['claim_en']} · within {bet['by_days']} days · check: {bet['check_en']}"
    else:
        bet_line = "\n\n**베팅** · 오늘은 없음" if lang == "ko" else "\n\n**Bet** · none today"
    u = _urls(lang)
    tail = (f"{label} 판정·검증·검수 기록은 [성장 페이지]({u['growth']})에 남고, 베팅은 기한 뒤 스스로 채점합니다. "
            f"관점은 사람이 씁니다: [엔터문화연구소 뉴스레터]({config.NEWSLETTER_URL})." if lang == "ko" else
            f"{label} The call, fact checks and review notes stay on the [growth page]({u['growth']}); bets are self-scored when due. "
            f"The point of view is written by a human: the [Neo Vibe Lab newsletter]({config.NEWSLETTER_URL}).")
    srcs = sources_block(lang, fm["source_summary"], fm["source_items"]) if (fm["source_summary"] or fm["source_items"]) else ""
    nm = (meta.get("name_map") or {}).get(lang) or {}
    fm["name_map"] = nm
    doc = (f"{frame_block(lang, meta['day'])}\n\n"
            f"`{header}`\n\n# {title}\n\n"
            + (f"{srcs}\n\n" if srcs else "")
            + f"{grid_table(lang, j)}\n\n"
            f"{body.strip()}{bet_line}\n\n"
            f"**{'원리' if lang == 'ko' else 'Principle'}** · {principle}{unresolved_line}\n\n"
            f"<sub>{tail}</sub>\n")
    doc = steps.apply_names(doc, nm, lang)
    return f"---\n{json.dumps(fm, ensure_ascii=False, indent=1)}\n---\n\n" + doc


def parse_piece(path) -> tuple[dict, str]:
    t = io.open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", t, re.S)
    if not m:
        return {}, t
    try:
        fm = json.loads(m.group(1))
    except Exception:
        fm = {}
    return fm, m.group(2)


def record(date: str, slug: str, j: dict, meta: dict, ko_body: str, en_body: str, trace: dict) -> None:
    config.ensure_dirs()
    io.open(config.CONTENT_DIR / "ko" / f"{slug}.md", "w", encoding="utf-8", newline="\n").write(
        piece_markdown("ko", date, slug, j, ko_body, meta))
    io.open(config.CONTENT_DIR / "en" / f"{slug}.md", "w", encoding="utf-8", newline="\n").write(
        piece_markdown("en", date, slug, j, en_body, meta))
    stats = _load(config.DATA_DIR / "stats.json", [])
    stats = [s for s in stats if s.get("date") != date]
    stats.append({
        "date": date, "day": meta["day"], "slug": slug, "title_ko": j["title_ko"], "title_en": j["title_en"],
        "factor": j["factor"], "from_stage": j["from_stage"], "to_stage": j["to_stage"], "tense": j["tense"],
        "radar_tense": meta.get("radar_tense"), "agrees": j.get("agrees"),
        "claims_total": meta.get("claims_total", 0), "claims_verified": meta.get("claims_verified", 0),
        "review_rounds": meta.get("review_rounds", 0), "unresolved": bool(meta.get("unresolved")),
        "bet": bool(j.get("bet")), "wiki_used": len(meta.get("wiki", [])), "lexicon_used": len(meta.get("lexicon", [])),
        "tokens": trace.get("usage", {}),
    })
    stats.sort(key=lambda s: s["date"])
    _dump(config.DATA_DIR / "stats.json", stats)
    if j.get("bet"):
        preds = _load(config.DATA_DIR / "predictions.json", [])
        y, m, d = map(int, date.split("-"))
        from datetime import date as D
        by = (D(y, m, d) + timedelta(days=int(j["bet"]["by_days"]))).isoformat()
        preds = [p for p in preds if p.get("slug") != slug]
        preds.append({"slug": slug, "date": date, "by_date": by, "claim_ko": j["bet"]["claim_ko"],
                      "claim_en": j["bet"]["claim_en"], "check_ko": j["bet"]["check_ko"], "check_en": j["bet"]["check_en"],
                      "factor": j["factor"], "status": "open"})
        _dump(config.DATA_DIR / "predictions.json", preds)
    _dump(config.LOG_DIR / f"{date}.json", trace)


def rule_candidates(issues: list[str], date: str) -> None:
    """검수 지적을 규칙 후보로 쌓는다. 3회 재현이면 승격(상한 30, 넣으려면 하나 뺀다). 표본 1로 규칙을 만들지 않는다."""
    if not issues:
        return
    p = config.DATA_DIR / "rule_candidates.json"
    cands = _load(p, {})
    for i in issues:
        key = re.sub(r"\s+", " ", i.strip())[:80]
        c = cands.setdefault(key, {"count": 0, "dates": []})
        if date not in c["dates"]:
            c["count"] += 1; c["dates"].append(date)
    _dump(p, cands)
    promote = [k for k, c in cands.items() if c["count"] >= 3 and not c.get("promoted")]
    if promote:
        rules = io.open(config.RULES_FILE, encoding="utf-8").read() if config.RULES_FILE.exists() else ""
        lines = [l for l in rules.splitlines() if l.startswith("- ")]
        for k in promote:
            if len(lines) >= 30:
                lines.pop(0)
            lines.append(f"- ({date}) {k}")
            cands[k]["promoted"] = True
        head = rules.split("\n- ")[0].rstrip() if rules else "# 자기 규칙\n\n검수 지적이 3회 재현되면 여기 올라온다. 상한 30. 넣으려면 하나 뺀다."
        io.open(config.RULES_FILE, "w", encoding="utf-8", newline="\n").write(head + "\n\n" + "\n".join(lines) + "\n")
        _dump(p, cands)
