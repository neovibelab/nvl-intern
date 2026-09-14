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


SEND_HOUR = 8            # 독자 도착 시각(KST). 회전이 언제 끝나든 여기로 모은다.


def next_slot(now: dt.datetime | None = None) -> dt.datetime | None:
    """다음 발송 시각. **이미 지났으면 None**을 돌려 즉시 발송으로 떨어뜨린다.

    회전은 오전 10시 무렵에 끝나므로 보통 **다음 날 08:00**이 잡힌다.
    속보를 쫓지 않기로 했으므로(2026-09-14) 하루 묵는 것이 비용이 아니다.
    """
    now = now or dt.datetime.now(config.KST)
    slot = (now + dt.timedelta(days=1)).replace(hour=SEND_HOUR, minute=0, second=0, microsecond=0)
    if now.hour < SEND_HOUR:                      # 새벽에 돌았으면 같은 날 아침으로
        slot = now.replace(hour=SEND_HOUR, minute=0, second=0, microsecond=0)
    return slot if slot > now + dt.timedelta(minutes=5) else None


def send_piece(lang: str, day: int, title: str, body_md: str, slug: str, send: bool = False) -> dict:
    """구독자는 언어만 고른다. 매일 한 편과 일요일 회고가 같은 리스트로 간다(2026-09-05 대표: 주기 구분 폐지)."""
    weekly = "주차 회고" in title or title.startswith("Week ")
    subject = title if weekly else (f"D+{day} · {title}" if lang == "ko" else f"Day {day} · {title}")
    url = f"{config.SITE_URL}/{'' if lang == 'ko' else 'en/'}{slug}"
    if lang == "ko":
        fb = ("**이 글은 어땠습니까** · [맞는 말이다](%s?fb=agree) · [뻔하다](%s?fb=obvious) · [근거가 약하다](%s?fb=weak) · [관점이 어긋난다](%s?fb=off)"
              "\n\n누른 것은 매주 묶여 인턴의 규칙 후보가 됩니다. 지적을 문장으로 남기려면 웹 페이지 아래 칸에, 또는 이 메일에 답장하면 됩니다." % (url, url, url, url))
        footer = "\n\n---\n\n" + fb + "\n\n[웹에서 읽기](%s)" % url
    else:
        fb = ("**How was this piece** · [Fair point](%s?fb=agree) · [Obvious](%s?fb=obvious) · [Weak evidence](%s?fb=weak) · [Wrong lens](%s?fb=off)"
              "\n\nVotes are batched weekly into the intern's rule candidates. To leave a note, use the box on the web page or reply to this email." % (url, url, url, url))
        footer = "\n\n---\n\n" + fb + "\n\n[Read on the web](%s)" % url
    filters = {"predicate": "and", "groups": [], "filters": [
        {"field": "subscriber.metadata.lang", "operator": "equals", "value": lang},
    ]}
    payload = {"subject": subject, "body": body_md + footer, "status": "about_to_send" if send else "draft",
               "archival_mode": "disabled", "filters": filters}
    when = next_slot() if send else None
    if when:
        payload["status"] = "scheduled"
        payload["publish_date"] = when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    st, resp = _call("POST", "/emails", payload, live=send)
    ok = st in (200, 201)
    how = ("초안" if not send else (f"{when:%m-%d %H:%M} 예약" if when else "즉시 발송"))
    print(f"  [mail] {lang} {how} → HTTP {st}" + ("" if ok else f" {str(resp)[:120]}"))
    return {"lang": lang, "status": st, "id": resp.get("id") if isinstance(resp, dict) else None, "sent": send and ok}
