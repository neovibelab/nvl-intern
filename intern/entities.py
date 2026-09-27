# -*- coding: utf-8 -*-
"""이 글의 사전 - 낯선 이름과 개념을 몇 줄로 푼다 (2026-09-27 신설).

**왜 필요한가.** 09-27 편의 소재가 Partisan이었는데 대표가 「Partisan 같은 회사가 무슨 회사인지
모르는 일이 많다」고 짚었다. 인턴이 다루는 회사·단체·사람·아티스트 대부분이 그렇다.
기준 독자의 **설명 층**(`steps.READER_KO`)은 음악산업 전문가가 아니다. 본문이 그 설명을 다 떠안으면
글이 소개문으로 무거워지고, 안 하면 설명 층이 첫 문단에서 떨어진다.

**무엇을 하나.**
- 본문을 다 쓴 뒤 설명 층이 모를 이름·개념을 **최대 다섯** 고른다. 누구나 아는 이름(BTS·Spotify)은 뺀다.
- 처음 보는 항목만 웹에서 확인해 한두 문장으로 푼다. **확인이 안 되면 싣지 않는다** - 틀린 풀이가 없는 풀이보다 나쁘다.
- 풀이는 대장(`data/entities.json`)에 쌓고 다음부터 다시 쓴다. 이름은 반복해서 나오므로 편이 쌓일수록 검색이 준다.
- 「이 글에서는 무엇인가」 한 구절만 편마다 새로 쓴다. 풀이는 사실이고 자리는 이 편의 것이다.

**어디에 보이나.** 새 머리 블록을 만들지 않는다 - 「무슨 일이 있었나」 상자 **안에** 목록으로 붙는다.
머리 블록 상한(넷)을 지키려는 것이고, 사건을 읽는 자리에서 모르는 이름을 바로 풀어야 쓸모가 있다.
사이트에는 대장 전체가 `/who` 한 장으로 선다.

**두뇌와의 연결** (같은 날 개정). 이 대장은 두뇌에 직접 쓰지 않는다(봇 자동 푸시 금지). 두뇌에는 렉시콘과 나란한
고유명사 사전(`raw/names/`)이 있고, 이 대장은 그 **후보 공급원**이다 - 연구소 `scripts/names-candidates.py`가 읽고
쓰는 일은 세션이 한다. 개념은 `scripts/lexicon_gaps.py`가 렉시콘에 없는 것만 결번 후보로 뽑는다.

**되돌림 조건** - 독자 신호에서 사전이 읽히지 않거나(발행 20편 동안 사전 항목 링크 클릭·언급 0),
확인 실패로 빠지는 항목이 절반을 넘으면 접는다.
"""
import re

from . import config, llm, publish

NL = chr(10)
PATH = config.DATA_DIR / "entities.json"
MAX = 5
KINDS = ("person", "artist", "company", "org", "concept")
KIND_KO = {"person": "사람", "artist": "아티스트", "company": "회사", "org": "단체", "concept": "개념"}
KIND_EN = {"person": "People", "artist": "Artists", "company": "Companies", "org": "Organizations", "concept": "Concepts"}


def load() -> dict:
    d = publish._load(PATH, {})
    d.setdefault("entries", {})
    return d


def save(d: dict) -> None:
    publish._dump(PATH, d)


def key_of(name: str) -> str:
    return re.sub(r"[^0-9a-z가-힣一-龥ぁ-ゖァ-ヶ]+", "-", (name or "").lower()).strip("-")[:60]


PICK = """아래는 오늘 발행할 글이다. 이 글을 읽을 **설명 층 독자**가 모를 만한 이름과 개념을 고른다.

[설명 층 독자] 엔터·문화에 관심은 있지만 음악산업 실무자는 아니다. 레이블·유통사·저작권 단체·투자사 이름,
업계 계약 용어는 모른다고 본다. 반대로 BTS·블랙핑크·하이브·Spotify·유튜브·넷플릭스·애플처럼
뉴스를 보는 사람이면 아는 이름은 고르지 않는다.

[고르는 규칙]
- **본문에 실제로 나오는 것만.** 원문 기사에만 있고 본문에 없는 이름은 고르지 않는다.
- 최대 {MAX}개. 글을 이해하는 데 걸리는 순서대로. 없으면 빈 목록이 맞다.
- kind: person(업계 인물) · artist(아티스트·그룹) · company(회사·레이블·플랫폼) · org(협회·단체·기관) · concept(업계 용어·제도).
- name_ko: 한국어 본문에 적힌 그대로. name_en: 영어 본문에 적힌 그대로(없으면 표준 영문 이름).
- role_ko: **이 글에서** 무엇인지 한 구절, 합니다체로 끝낸다(「이 글에서 지분을 사들인 쪽입니다」). 풀이를 되풀이하지 않는다.
- role_en: same in English, one short clause.
- 아래 [이미 풀어 둔 항목]에 있는 것이면 key를 그 key로 적는다. 새 항목이면 key를 빈 문자열로 둔다.

[이미 풀어 둔 항목]
{known}

[한국어 본문]
{ko}

[영어 본문]
{en}

JSON: {{"items":[{{"key":"","kind":"company","name_ko":"...","name_en":"...","role_ko":"...","role_en":"..."}}]}}"""

DESCRIBE = """다음 {kind_ko}을(를) 음악산업 실무자가 아닌 독자에게 풀어 준다. 웹에서 확인한 사실만 쓴다.

이름: {name}
글의 맥락(참고용, 풀이에 옮기지 않는다): {context}

규칙
- ko: 한국어 합니다체 1~2문장, 90자 안. 무엇인지(업종·국적·규모 중 확인된 것)와 알아볼 단서 하나(대표작·소속 아티스트·설립 연도 중 하나).
  사람이면 직함과 소속, 개념이면 뜻과 어디서 쓰는지. 평가·수식어(「유명한」「대표적인」) 없이.
- en: the same in plain English, one or two sentences, under 35 words.
- 확인한 페이지 URL 하나(공식 사이트나 신뢰할 만한 매체)와 그 매체 이름.
- **확인이 안 되거나 동명이인을 가를 수 없으면 status를 unverified로 둔다.** 추측으로 채우지 않는다.

JSON: {{"status":"verified|unverified","ko":"...","en":"...","url":"...","source":"..."}}"""


def _known_text(d: dict) -> str:
    rows = [f"- {k} · {e.get('name_en') or e.get('name_ko')} · {e.get('kind')}" for k, e in d["entries"].items()]
    return NL.join(rows[-300:]) if rows else "(없음)"


def describe(name: str, kind: str, context: str) -> dict | None:
    try:
        r = llm.ask_json(DESCRIBE.format(kind_ko=KIND_KO.get(kind, "항목"), name=name, context=context[:400]),
                         tools=llm.WEB_SEARCH_TOOL, max_tokens=3000, model=config.MODEL_VERIFY)
    except Exception as e:  # noqa: BLE001
        print(f"  [cast] {name} 풀이 호출 실패 {type(e).__name__}")
        return None
    ko, en = str(r.get("ko", "")).strip(), str(r.get("en", "")).strip()
    if r.get("status") != "verified" or not ko or not en:
        print(f"  [cast] {name} 확인 안 됨 · 싣지 않는다")
        return None
    return {"ko": ko, "en": en, "url": str(r.get("url", "")).strip(), "source": str(r.get("source", "")).strip()}


def cast(ko: str, en: str, summary_ko: str, slug: str = "", date: str = "", write: bool = True) -> list[dict]:
    """이 글의 사전. 돌려주는 것 = 편에 붙일 목록. write=False면 대장을 안 건드린다(dry-run)."""
    d = load()
    try:
        r = llm.ask_json(PICK.format(MAX=MAX, known=_known_text(d), ko=ko, en=en), model=config.MODEL_FAST, max_tokens=2000)
    except Exception as e:  # noqa: BLE001
        print(f"  [cast] 고르기 실패 {type(e).__name__} · 사전 없이 간다")
        return []
    out, new, seen = [], 0, set()
    for it in (r.get("items") or [])[:MAX]:
        if not isinstance(it, dict):
            continue
        name_ko, name_en = str(it.get("name_ko", "")).strip(), str(it.get("name_en", "")).strip()
        if not name_ko or name_ko not in ko:        # 본문에 없는 이름은 붙이지 않는다
            continue
        kind = it.get("kind") if it.get("kind") in KINDS else "company"
        k = str(it.get("key") or "").strip()
        if k not in d["entries"]:
            k = key_of(name_en or name_ko)
        if not k or k in seen:
            continue
        seen.add(k)
        e = d["entries"].get(k)
        if not e:
            desc = describe(name_en or name_ko, kind, summary_ko)
            if not desc:
                continue
            e = {"kind": kind, "name_ko": name_ko, "name_en": name_en or name_ko, "first": date, "pieces": [], **desc}
            new += 1
        if slug and slug not in e["pieces"]:
            e["pieces"].append(slug)
        d["entries"][k] = e
        out.append({"key": k, "kind": e["kind"], "name_ko": name_ko, "name_en": name_en or e.get("name_en", ""),
                    "desc_ko": e["ko"], "desc_en": e["en"], "url": e.get("url", ""),
                    "role_ko": str(it.get("role_ko", "")).strip(), "role_en": str(it.get("role_en", "")).strip()})
    if write:
        save(d)
    print(f"  [cast] {len(out)}개" + (f" · 새로 푼 것 {new}" if new else "") + (" · " + ", ".join(x["name_ko"] for x in out) if out else ""))
    return out


def link(items: list[dict], slug: str) -> None:
    """발행이 끝난 뒤 대장의 항목에 이 편을 단다. 슬러그는 제목이 정해진 뒤에야 생긴다."""
    if not items or not slug:
        return
    d = load()
    for x in items:
        e = d["entries"].get(x["key"])
        if e is not None and slug not in e.setdefault("pieces", []):
            e["pieces"].append(slug)
    save(d)


def lines(items: list[dict], lang: str) -> str:
    """「무슨 일이 있었나」 상자 안에 붙는 목록."""
    rows = []
    for x in items or []:
        name = x["name_ko"] if lang == "ko" else x["name_en"]
        desc = x["desc_ko"] if lang == "ko" else x["desc_en"]
        role = x["role_ko"] if lang == "ko" else x["role_en"]
        name = name.replace("]", "］").replace("[", "［")
        rows.append(f"- **{name}** · {desc.rstrip()}" + (f" {role}" if role else ""))
    return NL.join(rows)


def rate() -> tuple[int, int]:
    """대장 크기, 개념 수."""
    es = load()["entries"]
    return len(es), sum(1 for e in es.values() if e.get("kind") == "concept")
