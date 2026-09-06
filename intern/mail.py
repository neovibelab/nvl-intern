# -*- coding: utf-8 -*-
"""Buttondown 발송. 언어는 metadata.lang 필터. 실측 2026-09-04: 무료 플랜에서 API 발송·metadata 필터 작동."""
import json
import os
import urllib.error
import urllib.request

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
    st, resp = _call("POST", "/emails", payload, live=send)
    ok = st in (200, 201)
    print(f"  [mail] {lang} {'발송' if send else '초안'} → HTTP {st}" + ("" if ok else f" {str(resp)[:120]}"))
    return {"lang": lang, "status": st, "id": resp.get("id") if isinstance(resp, dict) else None, "sent": send and ok}
