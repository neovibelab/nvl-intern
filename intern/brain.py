# -*- coding: utf-8 -*-
"""② 재료 인출 - 두뇌(virtual-brain/llm-wiki)를 읽기 전용으로. 원문을 산출물에 노출하지 않는다.

wiki(관점 렌즈) · lexicon(개념) · TOPIC-MAP(그물망). 인턴은 인출해 자기 문장으로 쓴다.
"""
import io
import re

from . import config, llm

WIKI_CAP = 6000
LEX_CAP = 2500


def _read(p, cap=None) -> str:
    try:
        t = io.open(p, encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        return ""
    return t[:cap] if cap else t


def wiki_index() -> list[tuple[str, str]]:
    out = []
    wdir = config.BRAIN_DIR / "wiki"
    if not wdir.exists():
        return out
    for p in sorted(wdir.glob("*.md")):
        if p.name.upper().startswith("INDEX"):
            continue
        t = _read(p, 1500)
        m = re.search(r"^#\s+(.+)$", t, re.M)
        tags = re.search(r"^tags:\s*(.+)$", t, re.M)
        out.append((p.name, (m.group(1).strip() if m else p.stem) + (f"  {tags.group(1).strip()}" if tags else "")))
    return out


def lexicon_sections() -> dict[str, list[str]]:
    out = {}
    ldir = config.BRAIN_DIR / "raw" / "lexicon"
    for p in sorted(ldir.glob("*.md")) if ldir.exists() else []:
        if p.name.upper() in ("INDEX.MD", "README.MD"):
            continue
        heads = re.findall(r"^##\s+(.+)$", _read(p), re.M)
        out[p.name] = heads
    return out


def _lexicon_section(fname: str, head: str) -> str:
    t = _read(config.BRAIN_DIR / "raw" / "lexicon" / fname)
    m = re.search(r"^##\s+" + re.escape(head) + r"\s*$(.*?)(?=^##\s|\Z)", t, re.M | re.S)
    return (m.group(1).strip() if m else "")[:LEX_CAP]


def retrieve(topic: str) -> dict:
    """주제 텍스트에 맞는 wiki 3 · lexicon 4를 fast 모델이 고른다. 없으면 빈 재료로 간다."""
    widx = wiki_index()
    lex = lexicon_sections()
    if not widx and not lex:
        print("  [brain] 두뇌 경로 없음 - 재료 없이 간다:", config.BRAIN_DIR)
        return {"text": "", "wiki": [], "lexicon": []}
    wlist = "\n".join(f"- {n} :: {t}" for n, t in widx)
    llist = "\n".join(f"- {f} :: {', '.join(h[:60] for h in hs[:80])}" for f, hs in lex.items())
    topic_map = _read(config.BRAIN_DIR / "TOPIC-MAP.md", 6000)
    picked = llm.ask_json(
        f"""아래는 한 연구소의 관점 렌즈(wiki) 목록과 개념 사전(lexicon) 절 목록, 그리고 주제 지도다.
오늘의 사건에 논평을 쓰기 위해 읽을 재료를 고른다. wiki는 최대 3개(파일명 그대로), lexicon은 최대 4개(파일명과 절 제목 그대로).
관련 없으면 적게 고른다. 억지로 채우지 않는다.

[오늘의 사건]
{topic}

[wiki 목록]
{wlist}

[lexicon 절 목록]
{llist}

[주제 지도 앞부분]
{topic_map}

JSON: {{"wiki": ["파일명", ...], "lexicon": [{{"file": "industry.md", "head": "절 제목"}}, ...], "why": "한 줄"}}""",
        model=config.MODEL_FAST, max_tokens=800)
    parts, used_w, used_l = [], [], []
    for n in picked.get("wiki", [])[:3]:
        t = _read(config.BRAIN_DIR / "wiki" / n, WIKI_CAP)
        if t:
            used_w.append(n); parts.append(f"### wiki: {n}\n{t}")
    for it in picked.get("lexicon", [])[:4]:
        f, h = it.get("file", ""), it.get("head", "")
        sec = _lexicon_section(f, h)
        if sec:
            used_l.append(f"{f}#{h}"); parts.append(f"### lexicon: {f} / {h}\n{sec}")
    print(f"  [brain] wiki {len(used_w)} · lexicon {len(used_l)} · {picked.get('why','')[:60]}")
    return {"text": "\n\n".join(parts), "wiki": used_w, "lexicon": used_l}
