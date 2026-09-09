# -*- coding: utf-8 -*-
"""형식·접근성 측정 - 「읽을 만한가·친절한가」를 사람 판정 없이 재는 자 (2026-09-10 신설).

**왜 필요한가.** 먼저 있던 축이 전부 내용 축이었다(사실·판정·논지·격자·예측).
형식은 재지 않으니 나아지는지 나빠지는지 아무도 모른다. **재는 자가 없으면 학습도 없다** -
인턴에게 고치는 법을 알려주는 대신 **자기 숫자를 보여주고** 규칙을 스스로 세우게 한다.

**무엇을 재나.** 사람이 안 봐도 기계가 셀 수 있는 것만 넣는다.
- `title_check` - 제목이 **알려주나·읽고 싶나·약속을 지키나**. 세는 게 아니라 별도 맥락의
  판정자가 본다(2026-09-10 정정). 고유명사 포함(`title_noun`)은 상관지표라 기록만 한다.
- `lead_concrete` - 첫 문단에 고유명사와 수치·날짜가 함께 있나(누가 무엇을 언제).
- `ai_tell` - 대조 공식·메타 수사·가운데 줄표. 0이 정상이고 늘면 AI 티가 돌아온 것이다.
- `hedge_10k` - 만자당 「알려졌다」류. 근거를 못 댄 자리의 대리 지표다.
- `sent_med`·`long80` - 문장 길이. 길수록 읽기 어렵다.
"""
import re

from . import radar

CONTRAST = [r"[가-힣]{2,}이 아니라 ", r"[가-힣]{2,}가 아니라 ", r"[가-힣]{2,}이 아닌 ",
            r"[가-힣]{2,}가 아닌 ", r"[가-힣]{2,}보다는 "]
META = [r"진짜 (질문|문제)은", r"흥미로운 (점|지점)은", r"중요한 것은", r"핵심은", r"주목할 (점|만한)"]
HEDGE = [r"알려졌", r"로 보입니다", r"인 듯", r"가능성이 (있|높)"]
NUM = r"\d{2,}|\d+%|\d+억|\d+조|\d+만|\d+년|\d+월"


def source_nouns(items: list[dict], body: str = "") -> list[str]:
    """소재 기사 제목에서 고유명사 후보를 뽑는다. 레이더의 사건 묶기와 같은 규칙을 쓴다."""
    text = " ".join((x.get("title") or "") + " " + (x.get("source") or "") for x in items or [])
    out = set(radar._tokens(text))
    # 라틴 이름은 이어진 대문자 덩어리로 잡는다("Music Business Worldwide"를 세 조각으로 쪼개지 않는다)
    runs = re.findall(r"[A-Z][A-Za-z0-9&'.-]*(?:\s+[A-Z][A-Za-z0-9&'.-]*)*", (text + " " + (body or "")))
    out |= {r.strip() for r in runs if len(r.strip()) >= 3}
    cand = sorted({t for t in out if len(t) >= 2}, key=len, reverse=True)
    # 더 긴 이름에 포함된 조각은 뺀다
    keep = []
    for t in cand:
        if not any(t != k and t in k for k in keep):
            keep.append(t)
    return keep


def measure(title: str, body: str, items: list[dict] | None = None) -> dict:
    """한 편의 형식 지표. 본문은 프레임·소재 카드·격자를 뺀 순수 본문을 넣는다."""
    nouns = source_nouns(items or [], body)
    lead = body.strip().split("\n\n")[0] if body.strip() else ""
    sents = [s.strip() for s in re.split(r"(?<=다)\.\s|[.!?]\s|\n\n", body) if len(s.strip()) > 5]
    lens = [len(s) for s in sents] or [0]
    chars = max(1, len(re.sub(r"\s", "", body)))
    n = lambda pats: sum(len(re.findall(p, body)) for p in pats)  # noqa: E731
    return {
        "title_noun": bool(nouns) and any(x in title for x in nouns),
        "title_len": len(title),
        "lead_concrete": bool(re.search(NUM, lead)) and (not nouns or any(x in lead for x in nouns)),
        "ai_tell": n(CONTRAST) + n(META) + body.count("—"),
        "contrast": n(CONTRAST),
        "hedge_10k": round(n(HEDGE) / chars * 10000, 1),
        "sent_med": int(sorted(lens)[len(lens) // 2]),
        "long80": round(sum(1 for x in lens if x >= 80) / len(lens) * 100, 1),
    }


def score(f: dict) -> int:
    """0~100. 성장 페이지가 한 숫자로 보여주기 위한 것이고, 축별 원값이 정본이다.

    **제목은 세는 게 아니라 판정한다** (2026-09-10 정정). 고유명사 포함 여부는 상관지표라
    점수에서 뺐다 - 기준은 「알려주나·읽고 싶나·약속을 지키나」다. 판정이 없으면 그 40점은 비운다.
    """
    pts = 0
    t = f.get("title_check") or {}
    if t:
        pts += int(t.get("clarity", 0)) * 10          # 알려주나 0~20
        pts += int(t.get("pull", 0)) * 7              # 읽고 싶나 0~14
        pts += 6 if t.get("kept_promise") else 0      # 약속
    pts += 20 if f.get("lead_concrete") else 0
    pts += max(0, 20 - int(f.get("ai_tell", 0)) * 7)
    pts += max(0, 10 - int(f.get("hedge_10k", 0) / 2))
    med = f.get("sent_med", 0)
    pts += 10 if 25 <= med <= 60 else (5 if med <= 75 else 0)
    return min(100, pts)
