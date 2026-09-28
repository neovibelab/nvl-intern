# -*- coding: utf-8 -*-
"""Buttondown 발송. 언어는 metadata.lang 필터. 실측 2026-09-04: 무료 플랜에서 API 발송·metadata 필터 작동."""
import json
import os
import re
import urllib.error
import urllib.request

import datetime as dt

from . import config

API = "https://api.buttondown.com/v1"


def _call(method: str, path: str, body: dict | None = None, live: bool = False) -> tuple[int, dict | str]:
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", "Token " + os.environ["BUTTONDOWN_API_KEY"])
    req.add_header("Content-Type", "application/json")
    if live:
        req.add_header("X-Buttondown-Live-Dangerously", "true")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=30) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:400]


# 독자 도착 시각(KST). **언어마다 다르다**(2026-09-16 대표 제안) - 같은 시각은 한쪽을
# 반드시 죽은 시간에 꽂는다. 22:00 KST = 09:00 ET · 14:00 런던 · 15:00 베를린.
# **한국어는 다 쓴 직후 바로 보낸다**(2026-09-28 대표 지시). 그전엔 다음 날 08:00 예약이었는데
# GitHub 예약 실행이 매일 두 시간쯤 밀려(실제 시작 10:25~10:55 KST) 쓴 글이 하루를 묵었다.
# 영어는 그날 22:00 - 영어권 아침에 맞춘 16일 판단은 그대로 둔다.
SEND_HOUR = {"en": 22}

# 버튼다운 계정의 이메일 템플릿. **계정 설정과 같은 값이어야 한다** - 여기서 바꾸지 않는다.
# modern을 쓴다. 2026-09-27에 classic을 시험하고 같은 날 되돌렸다 - classic은 머리의 영어 안내 문구와
# 영어 날짜가 빠지는 대신 바닥의 영어(발행 번호·구독 관리·Powered by)를 본문 크기로 두 문단 찍고,
# 제목이 20px로 작아지고 카드·상자가 사라졌다. 영어 문구 자체를 바꾸는 길(한국어 로케일·CSS·커스텀 템플릿)은
# 무료 요금제에 없다(API로 확인 - css__not_allowed). modern에서는 머리가 제목을 찍으므로 본문 제목을 뺀다.
TEMPLATE = "modern"


def next_slot(lang: str = "ko", now: dt.datetime | None = None) -> dt.datetime | None:
    """발송 예약 시각. **None이면 즉시 발송**이다.

    한국어는 늘 None(즉시). 영어는 **같은 날** 22:00이고, 그 시각이 이미 지났으면 즉시 보낸다.
    두 언어가 같은 날에 묶이고 영어가 한국어보다 먼저 나가지 않는다.
    (2026-09-14~09-27에는 한국어도 다음 날 08:00 예약이었다 - 위 SEND_HOUR 주석)
    """
    hour = SEND_HOUR.get(lang)
    if hour is None:
        return None
    now = now or dt.datetime.now(config.KST)
    slot = dt.datetime.combine(now.date(), dt.time(hour), tzinfo=config.KST)
    return slot if slot > now + dt.timedelta(minutes=5) else None


GRID_TABLE = re.compile(r"\n\|\s*\|[^\n]*\n\|[-:| ]+\|\n(?:\|[^\n]*\n)+\n?<sub>[^<]*</sub>\n?")


def strip_grid(body: str, lang: str) -> str:
    """21칸 표를 한 줄로 바꾼다. 표가 없으면 그대로 돌려준다.

    **범례에 적힌 칸 이름을 살려서 옮긴다**(2026-09-17). 표를 빼면서 「어느 칸인지」까지
    같이 빠지면 메일 독자는 격자 이야기만 듣고 결과를 못 듣는다.
    """
    m = re.search(r"<sub>((?:오늘 찍은 칸|Today's cell)[^<]*?)·\s*7[^<]*</sub>", body)
    cell = m.group(1).strip(" ·") if m else ""
    grid = f"{config.SITE_URL}/grid" if lang == "ko" else f"{config.SITE_URL}/en/grid"
    if lang == "ko":
        line = (f"<sub>{cell} · [격자 21칸에서 보기]({grid})</sub>" if cell
                else f"<sub>오늘 찍은 칸은 [격자 21칸]({grid})에서 봅니다.</sub>")
    else:
        line = (f"<sub>{cell} · [see it on the 21-cell grid]({grid})</sub>" if cell
                else f"<sub>Today's cell is on the [21-cell grid]({grid}).</sub>")
    out, n = GRID_TABLE.subn("\n" + line + "\n", body, count=1)
    if not n:
        print("  [mail] 격자 표를 못 찾았다 - 본문 그대로 보낸다")
    return out


def drop_title(body: str) -> str:
    """본문의 첫 `# 제목` 한 줄을 뺀다. 메일에서만 쓴다(2026-09-27 대표 지적).

    버튼다운 템플릿이 머리에 제목(subject)을 이미 크게 찍는다. 본문 제목까지 두면 같은 제목을
    두 번 읽는다. 사이트는 머리가 따로 없어 본문 제목이 유일한 제목이므로 발행본은 건드리지 않는다.
    """
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            return "\n".join(lines[:i] + lines[j:])
    return body


def send_piece(lang: str, day: int, title: str, body_md: str, slug: str, send: bool = False) -> dict:
    """구독자는 언어만 고른다. 매일 한 편과 일요일 회고가 같은 리스트로 간다(2026-09-05 대표: 주기 구분 폐지)."""
    # `archival_mode` - 버튼다운 아카이브에 쌓을지(2026-09-16). 골격 커밋부터 `disabled`였고
    # 판단해서 끈 것이 아니었다. 그 주소가 구독 창구인데 빈 페이지라 죽은 레터로 보였다.
    # 발행 정본은 여전히 intern.neovibelab.com이고 우리 링크는 전부 그쪽을 가리킨다.
    #
    # **한국어만 쌓는다** - 한 리스트라 켜 두면 D+12 다음에 Day 12가 오는 식으로 두 언어가
    # 번갈아 선다. 목록이 어지럽고 어느 언어인지는 제목을 읽어야 안다. 영문 독자에게는
    # 사이트 `/en`이 더 낫다 - 격자·성장 기록까지 거기 있다.
    # 제목에 회차를 붙이지 않는다(2026-09-16 대표 지적). 제목 줄은 **열지 말지를 정하는 자리**이고
    # 앞 대여섯 글자를 우리 쪽 회차 번호가 먹는다. 수신함에서 제목이 잘리면 잘리는 쪽은 늘 뒷부분이다.
    # D+N은 읽기로 마음먹은 뒤에 의미가 생기는 값이라 본문 머리와 사이트에만 둔다.
    subject = title
    # 언어가 비어 있으면 **한국어로 간다**(2026-09-16). 버튼다운 포털·아카이브의 구독 폼에는
    # 언어 칸이 없어서 거기로 들어온 사람은 `lang`이 빈다. 정확히 일치만 보면 그 사람은
    # 구독은 됐는데 메일을 한 통도 못 받는다(대표 계정에서 실제로 났던 사고다).
    # 영어는 고른 사람에게만 간다 - 기본값을 둘로 둘 수는 없다.
    if lang == "ko":
        filters = {"predicate": "or", "groups": [], "filters": [
            {"field": "subscriber.metadata.lang", "operator": "equals", "value": "ko"},
            {"field": "subscriber.metadata.lang", "operator": "is_empty", "value": ""},
        ]}
    else:
        filters = {"predicate": "and", "groups": [], "filters": [
            {"field": "subscriber.metadata.lang", "operator": "equals", "value": "en"},
        ]}
    payload = {"subject": subject, "body": compose_body(lang, body_md, slug), "status": "about_to_send" if send else "draft",
               "archival_mode": "enabled" if lang == "ko" else "disabled", "filters": filters}
    when = next_slot(lang) if send else None
    if when:
        payload["status"] = "scheduled"
        payload["publish_date"] = when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    st, resp = _call("POST", "/emails", payload, live=send)
    ok = st in (200, 201)
    how = ("초안" if not send else (f"{when:%m-%d %H:%M} 예약" if when else "즉시 발송"))
    print(f"  [mail] {lang} {how} → HTTP {st}" + ("" if ok else f" {str(resp)[:120]}"))
    return {"lang": lang, "status": st, "id": resp.get("id") if isinstance(resp, dict) else None, "sent": send and ok}


def compose_body(lang: str, body_md: str, slug: str) -> str:
    """메일 본문 = 발행본(격자 표 → 한 줄, 제목 빼기) + 독자 신호 꼬리.

    발송과 **예약된 메일 고치기**(`python -m intern.mail --update <id> <lang> <slug>`)가 같이 쓴다 -
    따로 만들면 고친 본문이 발송본과 다른 모양이 된다(2026-09-28 영문 예약분 바로잡기에서 분리).
    """
    url = f"{config.SITE_URL}/{'' if lang == 'ko' else 'en/'}{slug}"
    if lang == "ko":
        fb = ("**이 글은 어땠습니까** · [맞는 말이다](%s?fb=agree) · [뻔하다](%s?fb=obvious) · [근거가 약하다](%s?fb=weak) · [관점이 어긋난다](%s?fb=off)"
              "\n\n누른 것은 매주 묶여 인턴의 규칙 후보가 됩니다. 지적을 문장으로 남기려면 웹 페이지 아래 칸에, 또는 이 메일에 답장하면 됩니다." % (url, url, url, url))
        footer = "\n\n---\n\n" + fb + "\n\n[웹에서 읽기](%s)" % url
    else:
        fb = ("**How was this piece** · [Fair point](%s?fb=agree) · [Obvious](%s?fb=obvious) · [Weak evidence](%s?fb=weak) · [Wrong lens](%s?fb=off)"
              "\n\nVotes are batched weekly into the intern's rule candidates. To leave a note, use the box on the web page or reply to this email." % (url, url, url, url))
        footer = "\n\n---\n\n" + fb + "\n\n[Read on the web](%s)" % url
    # 꼬리 문구는 본문 끝의 AI 표시 하나만 둔다. 버튼다운 계정 푸터는 2026-09-27에 비웠다 -
    # 한국어 한 벌이라 영문 메일에도 한국어로 붙었고, 한국어 메일에서는 본문 꼬리와 같은 말을 두 번 했다.
    body = strip_grid(body_md, lang)
    if TEMPLATE == "modern":      # 머리에 제목을 찍는 템플릿일 때만 본문 제목을 뺀다
        body = drop_title(body)
    return body + footer


def update_scheduled(email_id: str, lang: str, slug: str) -> tuple[int, str]:
    """아직 안 나간(예약) 메일의 본문을 지금 발행본으로 바꾼다. 발행본을 바로잡은 뒤에 쓴다."""
    from . import publish  # noqa: PLC0415
    st, cur = _call("GET", f"/emails/{email_id}")
    if st != 200 or not isinstance(cur, dict) or cur.get("status") != "scheduled":
        return st, f"예약 상태가 아니다: {cur.get('status') if isinstance(cur, dict) else cur}"
    _fm, body = publish.parse_piece(config.CONTENT_DIR / lang / f"{slug}.md")
    st, r = _call("PATCH", f"/emails/{email_id}", {"body": compose_body(lang, body.strip(), slug)})
    return st, (r.get("status") if isinstance(r, dict) else str(r)[:200])
