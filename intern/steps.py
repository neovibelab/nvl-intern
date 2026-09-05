# -*- coding: utf-8 -*-
"""③ 화살표 판정 · ④ 집필 · ⑤ 팩트 검증 · ⑥ 자기 검수. 정본 = ai-intern/PROJECT.md 「매일 파이프라인」."""
import io
import json
import re

from . import config, llm

PERSONA = """너는 엔터문화연구소의 AI 인턴 1호다. 이름은 아직 없다. 매일 글로벌 엔터 산업을 읽고 한 편 쓴다.
음악에서 바이브를 찾는다. 케이팝·팬덤·IP·공연·리테일의 변화가 다른 산업의 미래를 먼저 보여준다고 본다.
사람이 고르지도 고치지도 않는다. 틀린 날도 남긴다. 화자는 인턴이고 연구소 대표의 이름으로 말하지 않는다.
재료(wiki·lexicon)는 관점과 개념을 빌리는 것이지 베끼는 것이 아니다. 재료 원문을 인용하지 않는다."""

STYLE_KO = """문체 규칙(반드시):
- 가운데 줄표(—)를 쓰지 않는다. 문장을 끊는다.
- 「A가 아니라 B다」 같은 대조 공식을 한 편에 한 번 이상 쓰지 않는다.
- 불릿·번호 목록·표를 쓰지 않는다. 문단으로 쓴다.
- 「진짜 질문은」「흥미로운 점은」「중요한 것은」 같은 메타 수사를 쓰지 않는다.
- 은유·비유로 낯선 개념을 풀지 않는다. 독자가 아는 항목과의 비교로 푼다.
- 극존칭(드리다·하십시오)을 쓰지 않는다. 합니다체.
- 계몽·다짐·격언조로 끝내지 않는다. 마지막 줄은 다른 업종이 가져갈 원리 한 문장이다.
- 수치·인용에는 출처 매체를 문장 안에 적는다. 확인 안 된 것은 「~로 알려졌다」로 헤지한다.
- 한자·가나·키릴 등 비한글 문자의 고유명사(인명·매체·기업·작품)는 첫 등장에 「한글 표기(원어)」로 쓴다. 예: 차이쉬쿤(蔡徐坤), 36커(36氪). 두 번째부터는 한글 표기만.
- 소재 기사를 처음 언급하는 자리에 마크다운 링크를 건다: [매체명](URL). 사건 무리에 적힌 URL만 쓰고 만들지 않는다."""

STYLE_EN = """Style rules (must):
- No em dashes. Break the sentence instead.
- No bullet points, numbered lists or tables. Paragraphs only.
- No meta phrasing like "the real question is" or "what's interesting is".
- Do not explain unfamiliar things with metaphors; compare them to things the reader already knows.
- Name the outlet inside the sentence for figures and quotes. Hedge anything unverified with "reportedly".
- End with one sentence on what another industry would take from this case. No slogans.
- Proper nouns in non-Latin scripts (Chinese, Japanese, Korean, Cyrillic) appear on first mention as "Romanized (original)", e.g. Cai Xukun (蔡徐坤), 36Kr (36氪). Romanized only after that.
- Link the source article at its first mention as a markdown link: [outlet](URL). Use only URLs given in the cluster; never invent one."""


def _rules() -> str:
    try:
        return io.open(config.RULES_FILE, encoding="utf-8").read()
    except FileNotFoundError:
        return ""


# ── ③ 화살표 판정 ───────────────────────────────────────────────────────────

def judge(cluster_text: str, radar: dict, materials: str) -> dict:
    prompt = f"""[오늘의 사건 무리]
{cluster_text}

[레이더가 찍어 둔 판정] 시제={radar.get('radar_tense')} · 요인={radar.get('factor')} · 단계={radar.get('stage')}

[재료 - 연구소 관점 렌즈·개념]
{materials[:14000] or '(없음)'}

좌표계로 판정한다.
- 요인 하나: {' | '.join(config.FACTORS)}
- 출발 단계 → 도착 단계: {' | '.join(config.STAGES)} (같아도 된다)
- 시제 하나: vibe(아직 산업이 받아들이지 않았지만 조짐이 보이고 반복될 종류) / signal(지금 벌어지는 중, 누구나 찾을 수 있다) / background(끝났거나 한 번 있는 일)
  기준 독자는 한국 엔터 실무자다. 해외에서 signal인 것이 한국에는 vibe일 수 있다.
- 레이더 판정과 다르면 이유를 한 줄로 적는다. 같으면 agrees=true.
- 베팅: 시제가 vibe이거나, signal이지만 vibe 가설이 서면 「무엇이 · 언제까지(30|90|180일) · 무엇으로 확인」 세 칸을 채운다. 못 채우면 null. 채점 가능한 문장만 쓴다.
- 각도(angle): 이 사건에서 무엇을 말할지 한 줄. 뻔한 것(누구나 아는 요약)이면 다른 각도를 찾는다.
- 원리(principle): 다른 업종이 이 사례에서 가져갈 원리 한 문장.

JSON:
{{"factor":"...","from_stage":"...","to_stage":"...","tense":"vibe|signal|background","agrees":true,"disagree_reason":"",
 "angle_ko":"...","angle_en":"...","title_ko":"...(20자 안)","title_en":"...",
 "bet": {{"claim_ko":"...","claim_en":"...","by_days":90,"check_ko":"무엇으로 확인","check_en":"..."}} 또는 null,
 "principle_ko":"...","principle_en":"..."}}"""
    d = llm.ask_json(prompt, system=PERSONA, max_tokens=3000)
    if d.get("factor") not in config.FACTORS:
        d["factor"] = radar.get("factor") or "자본"
    for k in ("from_stage", "to_stage"):
        if d.get(k) not in config.STAGES:
            d[k] = radar.get("stage") or "유통"
    if d.get("tense") not in ("vibe", "signal", "background"):
        d["tense"] = config.TENSE_FROM_RADAR.get(radar.get("radar_tense")) or "signal"
    b = d.get("bet")
    if b and not (b.get("claim_ko") and b.get("check_ko") and b.get("by_days")):
        d["bet"] = None
    return d


def header_line(j: dict, lang: str) -> str:
    if lang == "ko":
        return f"[{j['factor']}] {j['from_stage']} → {j['to_stage']} · {config.TENSE_KO[j['tense']]}"
    return f"[{config.FACTORS_EN[j['factor']]}] {config.STAGES_EN[j['from_stage']]} → {config.STAGES_EN[j['to_stage']]} · {j['tense']}"


# ── ④ 집필 ──────────────────────────────────────────────────────────────────

def write_ko(cluster_text: str, j: dict, materials: str) -> str:
    prompt = f"""[오늘의 사건 무리]
{cluster_text}

[판정] {header_line(j, 'ko')} · 각도: {j['angle_ko']}
[베팅] {json.dumps(j.get('bet'), ensure_ascii=False) if j.get('bet') else '없음'}
[원리] {j['principle_ko']}

[재료]
{materials[:12000] or '(없음)'}

[자기 규칙]
{_rules()[:3000]}

{STYLE_KO}

한국어 논평 본문을 쓴다. 700~1000자. 제목·헤더·마지막 원리 줄은 코드가 붙이므로 본문만 쓴다.
첫 문장은 사건의 구체(누가 무엇을 언제)로 연다. 각도를 따라 논지를 세우고, 베팅이 있으면 본문 안에 「무엇이 언제까지」를 자기 문장으로 넣는다.
사실은 사건 무리와 재료에 있는 것만 쓴다. 없는 수치·발언을 만들지 않는다."""
    return llm.ask(prompt, system=PERSONA, max_tokens=6000)


def write_en(cluster_text: str, j: dict, ko_final: str) -> str:
    prompt = f"""[Today's event cluster]
{cluster_text}

[Call] {header_line(j, 'en')} · angle: {j['angle_en']}
[Bet] {json.dumps(j.get('bet'), ensure_ascii=False) if j.get('bet') else 'none'}
[Principle] {j['principle_en']}

[The Korean piece, already fact-checked. Use the same facts and the same call. Do not translate it; write the English piece for a global business reader who does not know Korean entertainment.]
{ko_final}

{STYLE_EN}

Write the English body only, 350 to 500 words. Title, header line and the closing principle are added by code.
Open with the concrete event (who, what, when). Follow the angle. If there is a bet, state what and by when in your own words.
Only facts that appear in the cluster or the Korean piece. Invent no figures or quotes."""
    return llm.ask(prompt, system=PERSONA, max_tokens=6000)


# ── ⑤ 팩트 검증 ─────────────────────────────────────────────────────────────

def extract_claims(text: str) -> list[str]:
    d = llm.ask_json(f"""아래 글에서 웹으로 확인할 수 있는 사실 주장(수치·날짜·직접 인용·고유명사 사건)을 최대 6개 뽑는다. 의견은 빼고 문장 그대로.

{text}

JSON: {{"claims": ["...", "..."]}}""", model=config.MODEL_FAST, max_tokens=1500)
    return [c for c in d.get("claims", []) if isinstance(c, str)][:6]


def verify_claim(claim: str) -> dict:
    try:
        d = llm.ask_json(f"""다음 주장이 사실인지 웹에서 확인한다. 출처 매체 이름과 함께 판정한다.

주장: {claim}

JSON: {{"status":"verified|unverified|contradicted","source":"매체명","url":"확인한 페이지 URL(없으면 빈 문자열)","note":"한 줄"}}""",
                         tools=llm.WEB_SEARCH_TOOL, max_tokens=3000)
        if d.get("status") not in ("verified", "unverified", "contradicted"):
            d["status"] = "unverified"
        return d
    except Exception as e:
        return {"status": "unverified", "source": "", "note": f"검증 호출 실패: {str(e)[:80]}"}


def hedge(text: str, results: list[dict], lang: str = "ko") -> str:
    bad = [r for r in results if r["status"] != "verified"]
    if not bad:
        return text
    notes = "\n".join(f"- {r['claim']} → {r['status']} ({r.get('note','')})" for r in bad)
    if lang == "ko":
        prompt = f"""아래 글에서 다음 주장들이 확인되지 않았거나 반박됐다. 반박된 것은 지우거나 고치고, 미확인은 「~로 알려졌다」로 헤지한다. 다른 문장은 건드리지 않는다. 길이는 유지한다. 본문만 돌려준다.

[문제 주장]
{notes}

[글]
{text}"""
    else:
        prompt = f"""In the piece below, these claims were unverified or contradicted. Remove or fix contradicted ones; hedge unverified ones with "reportedly". Leave other sentences untouched. Keep the length. Return the body only.

[Claims]
{notes}

[Piece]
{text}"""
    return llm.ask(prompt, system=PERSONA, max_tokens=6000)


# ── ⑤' 문체 기계 게이트 ─────────────────────────────────────────────────────
# 「A가 아니라 B」는 STYLE_KO가 한 편에 한 번으로 묶어 뒀지만 모델은 지키지 않는다.
# 2026-09-06 모델 비교 실측: Opus 5가 800자에 최대 4회, Sonnet 5도 4회. 세는 자리를 만든다.

CONTRAST_PATS = [r"[가-힣]{2,}이 아니라 ", r"[가-힣]{2,}가 아니라 ", r"[가-힣]{2,}이 아닌 ",
                 r"[가-힣]{2,}가 아닌 ", r"[가-힣]{2,}보다는 "]


def contrast_hits(text: str) -> list[str]:
    """대조 공식이 쓰인 문장을 돌려준다."""
    out = []
    for sent in re.split(r"(?<=다)\.\s|[.!?]\s|\n", text):
        if any(re.search(p, sent) for p in CONTRAST_PATS):
            out.append(sent.strip())
    return out


def style_gate(text: str, lang: str = "ko") -> tuple[str, dict]:
    """한 편에 대조 공식 하나까지. 넘으면 지목한 문장만 고쳐 다시 받는다. 1회로 끝낸다."""
    hits = contrast_hits(text)
    stat = {"before": len(hits), "after": len(hits), "revised": False}
    if len(hits) <= 1 or lang != "ko":
        return text, stat
    prompt = f"""아래 글에 「A가 아니라 B」 꼴의 대조 공식이 {len(hits)}번 나온다. 한 편에 한 번까지만 남긴다.

지목한 문장:
{chr(10).join('- ' + h for h in hits)}

가장 논지에 중요한 하나만 그대로 두고, 나머지는 **부정을 지우고 긍정문으로** 다시 쓴다.
(예: 「총액이 아니라 회당 매출이 지표다」 → 「지표는 회당 매출이다」)
다른 문장·순서·사실은 한 글자도 바꾸지 않는다. 길이를 유지한다. 본문만 돌려준다.

[글]
{text}"""
    out = llm.ask(prompt, system=PERSONA, max_tokens=6000)
    if not out or abs(len(out) - len(text)) > max(300, len(text) * 0.25):
        print(f"  [style] 결과 길이 이상({len(text)}→{len(out)}) · 원문 유지")
        return text, stat
    stat["after"] = len(contrast_hits(out))
    stat["revised"] = True
    print(f"  [style] 대조공식 {stat['before']} → {stat['after']}")
    return out, stat


# ── ⑥ 자기 검수 (별도 컨텍스트) ────────────────────────────────────────────

REVIEWER = """너는 발행 전 검수자다. 집필자가 아니다. 관대하지 않다. 다섯 질문만 묻는다.
1 뻔한가 - 누구나 아는 요약이면 실패. 2 소재 필연성 - 왜 오늘 이 사건인가가 글에 있나. 3 독자 수확 - 한국 엔터 실무자가 가져갈 것이 있나.
4 반대편 - 이 논지의 반례를 글이 스스로 다루나. 5 근거 - 논지를 받치는 사실이 글 안에 있나.
문체도 본다: 대조 공식 반복, 메타 수사, 억지 은유, 격언조 결말, 불릿."""


def review(text: str, j: dict) -> dict:
    d = llm.ask_json(f"""[판정] {header_line(j, 'ko')} · 각도: {j['angle_ko']}

[글]
{text}

JSON: {{"verdict":"pass|fix","issues":["구체 지적 (문장을 가리킨다)", ...],"one_line":"한 줄 총평"}}""",
                     system=REVIEWER, max_tokens=3000)
    if d.get("verdict") not in ("pass", "fix"):
        d["verdict"] = "fix"
    d["issues"] = [i for i in d.get("issues", []) if isinstance(i, str)][:6]
    return d


def revise(text: str, issues: list[str]) -> str:
    prompt = f"""검수자가 아래를 지적했다. 지적된 자리만 고친다. 논지는 유지하고 길이도 유지한다. 본문만 돌려준다.

[지적]
{chr(10).join('- ' + i for i in issues)}

{STYLE_KO}

[글]
{text}"""
    return llm.ask(prompt, system=PERSONA, max_tokens=6000)


# ── ①' 소재 요약 · ⑥' 표기·링크 정리 (2026-09-05 대표 지시: 매회 고정) ──────────

def summarize_sources(cluster_text: str) -> dict:
    """소재가 된 사건과 기사를 독자에게 먼저 보여준다. 두 언어 한 번에. 의견 없이 사실만."""
    d = llm.ask_json(f"""아래는 오늘 글의 소재가 된 기사 무리다. 독자가 본문을 읽기 전에 볼 「오늘의 소재」 요약을 쓴다.

{cluster_text}

규칙: 사실만(누가·무엇을·언제·어디 보도). 의견·해석·형용 없음. 인명·매체명 같은 고유명사는 원문 문자 그대로 둔다(표기는 코드가 붙인다). 한국어 2~3문장(200자 안), 영어 2~3문장(60 words 안).
titles_en: 기사 제목을 위 목록 순서대로 영어로 옮긴다(매체명은 원문 그대로).
JSON: {{"ko":"...","en":"...","titles_en":["...", ...]}}""", model=config.MODEL_FAST, max_tokens=2000)
    return {"ko": str(d.get("ko", "")).strip(), "en": str(d.get("en", "")).strip(),
            "titles_en": [str(t) for t in d.get("titles_en", []) if isinstance(t, str)]}


def issues_en(issues: list[str]) -> list[str]:
    """검수 지적(한국어)을 영문판용으로 옮긴다."""
    if not issues:
        return []
    d = llm.ask_json(f"""Translate each reviewer note into plain English. Keep proper nouns in their original script. Same count and order.
{json.dumps(issues, ensure_ascii=False)}
JSON: {{"en": ["...", ...]}}""", model=config.MODEL_FAST, max_tokens=2000)
    out = [str(x) for x in d.get("en", []) if isinstance(x, str)]
    return out if len(out) == len(issues) else issues


_FOREIGN_KO = re.compile(r"[A-Za-z0-9]*[一-龥ぁ-ゖァ-ヶЀ-ӿ]+[A-Za-z0-9一-龥ぁ-ゖァ-ヶЀ-ӿ]*")
_FOREIGN_EN = re.compile(r"[A-Za-z0-9]*[一-龥ぁ-ゖァ-ヶЀ-ӿ가-힣]+[A-Za-z0-9一-龥ぁ-ゖァ-ヶЀ-ӿ가-힣]*")
_FOREIGN_ANY = re.compile(r"[一-龥ぁ-ゖァ-ヶЀ-ӿ가-힣]")
_FOREIGN_KO_CHARS = re.compile(r"[一-龥ぁ-ゖァ-ヶЀ-ӿ]")


def name_map(texts: list[str], lang: str) -> dict:
    """비현지 문자 고유명사 → 현지 표기 대응표. LLM은 표만 뽑고 치환은 apply_names가 한다."""
    pat = _FOREIGN_KO if lang == "ko" else _FOREIGN_EN
    found = sorted({m for t in texts for m in pat.findall(t or "")}, key=len, reverse=True)
    if not found:
        return {}
    ask = ("각 항목의 한글 표기를 적는다. 중국어는 표준중국어 발음의 국립국어원 외래어 표기법(蔡徐坤→차이쉬쿤, 界面新闻→제몐신문, 36氪→36커), "
           "일본어는 일본어 표기법, 통용되는 한국어 명칭이 따로 있으면 그것(人民日报→인민일보). 한글·숫자·라틴 문자만 쓴다." if lang == "ko"
           else "Give the standard Romanized or English name for each item: pinyin for Chinese personal names (蔡徐坤→Cai Xukun), "
                "the outlet's own English name where one exists (界面新闻→Jiemian News, 36氪→36Kr), Hepburn for Japanese, Revised Romanization for Korean. Latin letters and digits only.")
    d = llm.ask_json(f"""{ask}
항목: {json.dumps(found, ensure_ascii=False)}
JSON: {{"map": {{"원어": "표기", ...}}}}""", max_tokens=1500)
    m = d.get("map", {}) if isinstance(d, dict) else {}
    out = {}
    for k, v in m.items():
        v = str(v).strip()
        bad = _FOREIGN_KO_CHARS.search(v) if lang == "ko" else _FOREIGN_ANY.search(v)
        if k in found and v and v != k and not bad:
            out[k] = v
    dropped = [k for k in found if k not in out]
    if dropped:
        print(f"  [names] {lang} 표기 못 받음: {dropped[:5]}")
    return out


def apply_names(text: str, m: dict, lang: str) -> str:
    """원어를 전부 현지 표기로 바꾸고, 현지 표기의 첫 등장에만 (원어)를 붙인다. URL·링크 대상은 건드리지 않는다."""
    if not m or not text:
        return text
    parts = re.split(r"(\]\([^)]*\)|https?://\S+)", text)  # 링크 URL 보호
    for orig, local in sorted(m.items(), key=lambda kv: len(kv[0]), reverse=True):
        for idx in range(0, len(parts), 2):
            seg = parts[idx]
            seg = seg.replace(f"{local}({orig})", local).replace(f"{local} ({orig})", local)
            seg = re.sub(r"(?<![A-Za-z0-9一-龥])" + re.escape(orig) + r"(?![A-Za-z0-9一-龥])", local, seg)
            parts[idx] = seg
        joined = "".join(parts)
        first = None
        bound = re.compile(r"(?<![가-힣A-Za-z0-9])" + re.escape(local) + r"(?![A-Za-z0-9])")
        for idx in range(0, len(parts), 2):
            mm = bound.search(parts[idx])
            if mm:
                first = (idx, mm.start()); break
        if first:
            idx, k = first
            sep = "" if lang == "ko" else " "
            parts[idx] = parts[idx][:k + len(local)] + f"{sep}({orig})" + parts[idx][k + len(local):]
    return "".join(parts)


def polish(text: str, lang: str, sources: list[dict]) -> str:
    """소재·검증 출처의 인링크를 건다. 다른 문장은 건드리지 않는다."""
    src = "\n".join(f"- {x.get('source') or ''} · {x.get('title') or ''} · {x.get('url')}" for x in sources if x.get("url"))
    if not src:
        return text
    if lang == "ko":
        prompt = f"""아래 글에서 한 가지만 고친다. 그 밖의 문장·단어·순서는 한 글자도 바꾸지 않는다.
인링크: 아래 출처 목록의 매체나 기사가 본문에 처음 언급되는 자리에 [매체명](URL) 마크다운 링크를 건다. 매체명이 본문에 다른 표기로 적혀 있으면 그 표기를 링크 텍스트로 쓴다. 목록에 없는 URL은 만들지 않는다. 이미 링크가 있으면 그대로 둔다. 해당 매체가 본문에 없으면 아무것도 하지 않는다.

[출처]
{src}

[글]
{text}

본문만 돌려준다."""
    else:
        prompt = f"""Make exactly one kind of change to the piece below and nothing else. Do not alter any other word, sentence or order.
Links: where an outlet or article from the list below is first mentioned, make that mention a markdown link [outlet](URL), keeping the wording already in the text. Never invent a URL. Leave existing links as they are. If an outlet is not mentioned, do nothing.

[Sources]
{src}

[Piece]
{text}

Return the body only."""
    out = llm.ask(prompt, system=PERSONA, max_tokens=8000)
    if not out or abs(len(out) - len(text)) > max(400, len(text) * 0.25):
        print(f"  [polish] {lang} 결과 길이 이상({len(text)}→{len(out)}) · 원문 유지")
        return text
    print(f"  [polish] {lang} 링크 {len(re.findall(r'\]\(https?://', out))}")
    return out


def link_sources(cluster_items: list[dict], claims: list[dict]) -> list[dict]:
    """인링크 후보 = 소재 기사 + 검증에서 URL이 잡힌 출처."""
    out = [dict(x) for x in cluster_items if x.get("url")]
    for r in claims or []:
        if r.get("status") != "verified":
            continue
        src = str(r.get("source") or "")
        m = re.search(r"https?://\S+", str(r.get("url") or "") + " " + src)
        if m:
            out.append({"source": src.replace(m.group(0), "").strip(" ·-:()") or m.group(0).split("/")[2],
                        "title": r.get("claim", "")[:60], "url": m.group(0).rstrip(".,)")})
    return out
