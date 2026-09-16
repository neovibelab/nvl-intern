# -*- coding: utf-8 -*-
"""Buttondown 발송. 언어는 metadata.lang 필터. 실측 2026-09-04: 무료 플랜에서 API 발송·metadata 필터 작동."""
import json
import os
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
# 반드시 죽은 시간에 꽂는다. 08:00 KST는 영어권에서 전날 밤 11시(ET)다.
# 22:00 KST = 09:00 ET · 14:00 런던 · 15:00 베를린.
SEND_HOUR = {"ko": 8, "en": 22}


def next_slot(lang: str = "ko", now: dt.datetime | None = None) -> dt.datetime | None:
    """다음 발송 시각. **이미 지났으면 None**을 돌려 즉시 발송으로 떨어뜨린다.

    회전은 오전 10시 무렵에 끝나므로 보통 **다음 날**이 잡힌다. 속보를 쫓지 않기로 했으므로
    (2026-09-14) 하루 묵는 것이 비용이 아니다.

    **기준일은 한국어 슬롯이 잡히는 날이고 영어는 그날 밤이다.** 두 언어가 같은 날에 묶이고
    영어가 한국어보다 먼저 나가지 않는다.
    """
    now = now or dt.datetime.now(config.KST)
    day = now.date() if now.hour < SEND_HOUR["ko"] else (now + dt.timedelta(days=1)).date()
    slot = dt.datetime.combine(day, dt.time(SEND_HOUR.get(lang, 8)), tzinfo=config.KST)
    return slot if slot > now + dt.timedelta(minutes=5) else None


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
    url = f"{config.SITE_URL}/{'' if lang == 'ko' else 'en/'}{slug}"
    if lang == "ko":
        fb = ("**이 글은 어땠습니까** · [맞는 말이다](%s?fb=agree) · [뻔하다](%s?fb=obvious) · [근거가 약하다](%s?fb=weak) · [관점이 어긋난다](%s?fb=off)"
              "\n\n누른 것은 매주 묶여 인턴의 규칙 후보가 됩니다. 지적을 문장으로 남기려면 웹 페이지 아래 칸에, 또는 이 메일에 답장하면 됩니다." % (url, url, url, url))
        footer = "\n\n---\n\n" + fb + "\n\n[웹에서 읽기](%s)" % url
    else:
        fb = ("**How was this piece** · [Fair point](%s?fb=agree) · [Obvious](%s?fb=obvious) · [Weak evidence](%s?fb=weak) · [Wrong lens](%s?fb=off)"
              "\n\nVotes are batched weekly into the intern's rule candidates. To leave a note, use the box on the web page or reply to this email." % (url, url, url, url))
        footer = "\n\n---\n\n" + fb + "\n\n[Read on the web](%s)" % url
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
    payload = {"subject": subject, "body": body_md + footer, "status": "about_to_send" if send else "draft",
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
