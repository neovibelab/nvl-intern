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


def review_block(lang: str, meta: dict) -> str:
    """검수 기록. 인턴은 발행 전 별도 검수자에게 글을 넘기고, 상한 안에 통과 못 하면 고치지 않고 낸다. 실패를 숨기지 않는 것이 규칙이라 매회 보인다."""
    rounds = int(meta.get("review_rounds") or 0)
    unresolved = bool(meta.get("unresolved"))
    if lang == "ko":
        head = "**발행 전 검사** · 인턴은 발행 전에 자기 글을 별도 검수자(같은 모델, 다른 지시)에게 넘깁니다. 뻔한가 · 왜 오늘 이 사건인가 · 독자가 가져갈 것이 있나 · 반례를 다뤘나 · 근거가 있나, 다섯 가지를 봅니다. 두 번 안에 통과하지 못하면 고치지 않고 그대로 냅니다. 실패를 숨기지 않는 것이 이 실험의 규칙입니다."
        if not unresolved:
            return f"> {head}\n>\n> 이번 글: {rounds}회차에 통과."
        issues = ((meta.get("last_issues") or [])[:3])
        return f"> {head}\n>\n> 이번 글: {rounds}회 모두 통과하지 못했습니다. 마지막 지적을 그대로 둡니다.\n>\n" + "\n".join(f"> - {i}" for i in issues)
    head = "**Review log** · Before publishing, the intern hands the piece to a separate reviewer (same model, different instructions) that asks five things: is it obvious, why this event today, what a reader takes away, does it face the counterargument, is there evidence. If it fails twice, the piece goes out unchanged. Not hiding failure is a rule of this experiment."
    if not unresolved:
        return f"> {head}\n>\n> This piece: passed on round {rounds}."
    issues = ((meta.get("last_issues_en") or meta.get("last_issues") or [])[:3])
    return f"> {head}\n>\n> This piece: failed all {rounds} rounds. The last notes stay as written.\n>\n" + "\n".join(f"> - {i}" for i in issues)


def sources_block(lang: str, summary: str, items: list[dict]) -> tuple[str, str]:
    """오늘의 소재를 **둘로 나눠** 돌려준다 - (요약 한 문단, 원문 링크 목록).

    요약은 제목 바로 밑에 있어야 무슨 사건인지 알고 본문에 들어간다. **링크 목록은 근거라서 뒤에 간다**
    (2026-09-16 대표 지적 - 본문에 닿기 전에 6줄을 지나야 했다).
    """
    head = "**무슨 일이 있었나**" if lang == "ko" else "**What happened**"
    lines = []
    for x in items:
        if not x.get("url"):
            continue
        outlet = (x.get("source") or x.get("region") or "").strip()
        title = ((x.get("title_en") if lang == "en" else None) or x.get("title") or "").strip().replace("]", "］").replace("[", "［")
        date = (x.get("published_date") or "")[:10]
        lines.append(f"- [{(outlet + ' · ') if outlet else ''}{title}]({x['url']})" + (f" · {date}" if date else ""))
    first = f"{head} · {summary.strip()}" if summary.strip() else ""
    link_head = "**원문**" if lang == "ko" else "**Sources**"
    links = (link_head + "\n\n" + "\n".join(lines)) if lines else ""
    return first, links


def no_em_dash(t: str) -> str:
    """가운데 줄표는 전 출력 금지(루트 지침). 모델이 제목·조짐 같은 짧은 필드에 넣는다 - 기계로 친다."""
    return t.replace(" — ", " - ").replace("—", "-").replace(" – ", " - ").replace("–", "-")


def vibe_line(lang: str, j: dict) -> str:
    """바이브 판정의 근거. 「곧」은 순수 추측이 아니라 관측된 조짐이어야 한다(정본 규칙).

    영문판에는 영문 조짐만 싣는다. 없으면 줄을 통째로 뺀다 - 영문 글에 한국어 문장을
    끼워 넣는 쪽이 빠뜨리는 쪽보다 나쁘다(2026-09-09 실측: 영문 페이지에 한국어가 그대로 나갔다).
    """
    ev = str(j.get("vibe_evidence_en" if lang == "en" else "vibe_evidence") or "").strip()
    if j.get("tense") != "vibe" or not ev:
        return ""
    return (f"**조짐** · {ev}" if lang == "ko" else f"**What is showing** · {ev}")


def grid_table(lang: str, j: dict) -> str:
    """21칸 격자. **찍힌 칸 하나만** 표시한다(2026-09-17).

    출발 칸(○)을 빼는 이유는 **시스템의 나머지가 이미 도착 하나로만 세기 때문**이다 -
    격자 페이지도 「N/21 격자 칸」 지표도 `to_stage`로만 집계한다. 표만 두 칸을 찍어
    정본(「인턴이 매일 한 칸을 찍는다」)과 어긋나 있었다. 출발→도착은 좌표 줄이 말한다.
    """
    st_labels = [s if lang == "ko" else config.STAGES_EN[s] for s in config.STAGES]
    rows = ["| | " + " | ".join(st_labels) + " |", "|---|:-:|:-:|:-:|"]
    for f in config.FACTORS:
        cells = []
        for s in config.STAGES:
            if f == j["factor"] and s == j["to_stage"]:
                cells.append("●")
            else:
                cells.append("·")
        rows.append(f"| {f if lang == 'ko' else config.FACTORS_EN[f]} | " + " | ".join(cells) + " |")
    # 범례가 **어느 칸인지 말로 한다**(2026-09-17 대표 지적). 본문을 한참 내려온 자리라
    # 위의 좌표 줄은 이미 기억에서 빠졌고, 행과 열을 눈으로 따라가게 두면 지도가 제 일을 못 한다.
    # 지역과 시제는 넣지 않는다 - 지도가 담고 있는 축이 아니다.
    if lang == "ko":
        legend = f"<sub>오늘 찍은 칸 · {j['to_stage']} 단계의 {j['factor']} · 7요인 × 3단계 = 21칸</sub>"
    else:
        fe = config.FACTORS_EN.get(j["factor"], j["factor"])
        se = config.STAGES_EN.get(j["to_stage"], j["to_stage"])
        legend = f"<sub>Today's cell · {fe} at the {se} stage · 7 factors × 3 stages = 21 cells</sub>"
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
        "region": j.get("region", "글로벌"),
        "radar_tense": meta.get("radar_tense"), "agrees": j.get("agrees"),
        "tense_why": j.get("tense_why", ""), "vibe_evidence": j.get("vibe_evidence", ""),
        "title_source": (meta.get("title_source") or {}).get(lang, ""),
        "vibe_evidence_en": j.get("vibe_evidence_en", ""),
        "bet": bet, "claims_total": meta.get("claims_total"), "claims_verified": meta.get("claims_verified"),
        "review_rounds": meta.get("review_rounds"), "unresolved": meta.get("unresolved"),
        "sources": meta.get("sources", []), "source_items": meta.get("source_items", []),
        "source_summary": (meta.get("source_summary") or {}).get(lang, ""),
        "wiki": meta.get("wiki", []), "lexicon": meta.get("lexicon", []),
    }
    unresolved_line = "\n\n" + review_block(lang, meta)
    bet_line = ""
    if bet:
        if lang == "ko":
            bet_line = f"\n\n**예측** · {bet['claim_ko']} · {bet['by_days']}일 안 · 확인: {bet['check_ko']}"
        else:
            bet_line = f"\n\n**Prediction** · {bet['claim_en']} · within {bet['by_days']} days · check: {bet['check_en']}"
    else:
        bet_line = "\n\n**예측** · 오늘은 없음" if lang == "ko" else "\n\n**Prediction** · none today"
    u = _urls(lang)
    tail = (f"{label} 판정·검증·검사 기록은 [성장 페이지]({u['growth']})에 남고, 예측은 기한이 지나면 스스로 채점합니다. "
            f"관점은 사람이 씁니다: [엔터문화연구소 뉴스레터]({config.NEWSLETTER_URL})." if lang == "ko" else
            f"{label} The call, fact checks and review notes stay on the [growth page]({u['growth']}); bets are self-scored when due. "
            f"The point of view is written by a human: the [Neo Vibe Lab newsletter]({config.NEWSLETTER_URL}).")
    src_sum, src_links = sources_block(lang, fm["source_summary"], fm["source_items"])
    nm = (meta.get("name_map") or {}).get(lang) or {}
    fm["name_map"] = nm
    # 지역을 좌표 줄에 붙인다(2026-09-16). 사이트 칩에만 있어서 메일 독자는 「한국 얘기인가」를 몰랐다.
    # 좌표를 사람 말로 (2026-09-17 대표 지적 - 「무슨 말인지 모르겠다」).
    # 코드 스팬 `[정책] 유통 → 유통 · 시그널`은 이름표도 이음말도 없었고 같은 단계를 두 번 썼다.
    coord = "`" + steps.coord_say(dict(j, region=fm.get("region") or ""), lang) + "`"
    hr = "\n\n---\n\n"
    doc = (f"{frame_block(lang, meta['day'])}" + hr
            + f"{coord}\n\n# {title}\n\n"
            + (f"{src_sum}\n\n" if src_sum else "")
            + (f"{vibe_line(lang, j)}\n\n" if vibe_line(lang, j) else "")
            + hr.lstrip("\n")
            + f"{body.strip()}{bet_line}\n\n"
            + f"**{'가져갈 것' if lang == 'ko' else 'Takeaway'}** · {principle}" + hr
            + (f"{src_links}\n\n" if src_links else "")
            + f"{grid_table(lang, j)}"
            + f"{unresolved_line}\n\n"
            + f"<sub>{tail}</sub>\n")
    doc = no_em_dash(steps.apply_names(doc, nm, lang))
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
        "region": j.get("region", "글로벌"),
        "radar_tense": meta.get("radar_tense"), "agrees": j.get("agrees"),
        "claims_total": meta.get("claims_total", 0), "claims_verified": meta.get("claims_verified", 0),
        "review_rounds": meta.get("review_rounds", 0), "unresolved": bool(meta.get("unresolved")),
        "bet": bool(j.get("bet")), "wiki_used": len(meta.get("wiki", [])), "lexicon_used": len(meta.get("lexicon", [])),
        "form": meta.get("form", {}),
        # 문체는 재고 기록하지 않고 버려지고 있었다(2026-09-16 실측). 회전마다 화면에만 찍혔다.
        # 회고(`weekly._style_line`)와 지난 편 되읽기(`learn._scores`)가 둘 다 이 칸을 읽으므로
        # 여기서 빠지면 **인턴이 자기 문체를 한 번도 못 본다.**
        "style": meta.get("style", {}),
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
    """검수 지적을 규칙 후보로 **쌓기만** 한다. 승격은 주간 회고가 뜻으로 묶은 뒤에 한다
    (`weekly.harvest` - 2026-09-10 개편). 표본 1로 규칙을 만들지 않는다."""
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
    # 문자열 일치 승격은 2026-09-10 폐기 - 같은 지적이 같은 문장으로 두 번 나오지 않아 6일간 0건이었다.
    # 승격은 주간 회고가 뜻으로 묶은 뒤에 한다(weekly.harvest). 여기는 원자료만 쌓는다.
    promote: list[str] = []
    if promote:
        rules = io.open(config.RULES_FILE, encoding="utf-8").read() if config.RULES_FILE.exists() else ""
        lines = [l for l in rules.splitlines() if l.startswith("- ")]
        for k in promote:
            if len(lines) >= 30:
                lines.pop(0)
            lines.append(f"- ({date}) {k}")
            cands[k]["promoted"] = True
        head = rules.split("\n- ")[0].rstrip() if rules else "# 자기 규칙"
        io.open(config.RULES_FILE, "w", encoding="utf-8", newline="\n").write(head + "\n\n" + "\n".join(lines) + "\n")
        _dump(p, cands)
