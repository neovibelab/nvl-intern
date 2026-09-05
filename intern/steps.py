# -*- coding: utf-8 -*-
"""③ 화살표 판정 · ④ 집필 · ⑤ 팩트 검증 · ⑥ 자기 검수. 정본 = ai-intern/PROJECT.md 「매일 파이프라인」."""
import io
import json

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
- 수치·인용에는 출처 매체를 문장 안에 적는다. 확인 안 된 것은 「~로 알려졌다」로 헤지한다."""

STYLE_EN = """Style rules (must):
- No em dashes. Break the sentence instead.
- No bullet points, numbered lists or tables. Paragraphs only.
- No meta phrasing like "the real question is" or "what's interesting is".
- Do not explain unfamiliar things with metaphors; compare them to things the reader already knows.
- Name the outlet inside the sentence for figures and quotes. Hedge anything unverified with "reportedly".
- End with one sentence on what another industry would take from this case. No slogans."""


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

JSON: {{"status":"verified|unverified|contradicted","source":"매체명 또는 URL","note":"한 줄"}}""",
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
