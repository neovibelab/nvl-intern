# -*- coding: utf-8 -*-
"""정적 사이트 생성 - dist/. 오늘의 글 · 언어별 목록 · 성장 대시보드 · 격자 허브. 외부 라이브러리 없음."""
import html
import io
import json
import re
import shutil

from . import config, publish

CSS = """:root{--lime:#D6FF92;--black:#0A0A0A;--dark:#111;--gray:#888;--gray-dark:#333;--line:rgba(255,255,255,.08);--white:#F0F0EA}
*{box-sizing:border-box;margin:0;padding:0}body{background:var(--black);color:var(--white);font-family:'Noto Sans KR',Outfit,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--white)}.mono{font-family:'DM Mono',ui-monospace,monospace}
nav{position:sticky;top:0;background:rgba(10,10,10,.9);backdrop-filter:blur(10px);border-bottom:1px solid var(--line);padding:14px 24px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
nav .brand{color:var(--lime);font-weight:800;letter-spacing:.08em;text-transform:uppercase;text-decoration:none;font-size:13px}
nav a.l{color:var(--gray);text-decoration:none;font-size:12px;font-family:'DM Mono',monospace;letter-spacing:.04em}nav a.l:hover{color:var(--lime)}
nav .sp{flex:1}.wrap{max-width:760px;margin:0 auto;padding:40px 24px 80px}
.label{color:var(--lime);font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase}
h1{font-size:clamp(26px,4vw,40px);font-weight:900;letter-spacing:-.02em;line-height:1.2;margin:10px 0 18px}
.hdr{display:inline-block;font-family:'DM Mono',monospace;font-size:13px;color:var(--lime);background:var(--dark);border:1px solid var(--gray-dark);padding:4px 10px;margin-bottom:8px}
.meta{color:var(--gray);font-size:12px;font-family:'DM Mono',monospace;margin-bottom:26px}
.body p{font-size:16.5px;line-height:1.95;color:#d9d9d2;margin-bottom:18px}.body strong{color:var(--white)}
.body blockquote{border-left:2px solid var(--lime);padding:12px 18px;color:var(--gray);margin:18px 0;background:rgba(214,255,146,.05);font-size:13.5px;line-height:1.75}
.body blockquote p{font-size:13.5px;line-height:1.75;color:var(--gray);margin:0 0 8px}.body blockquote p:last-child{margin:0}.body blockquote strong{color:var(--lime)}
.body blockquote ul{margin:0 0 8px 18px;font-size:13.5px}
.body sub{color:var(--gray);font-size:12px}
.list a{display:block;padding:18px 0;border-bottom:1px solid var(--line);text-decoration:none}
.list .t{font-size:18px;font-weight:700;margin:6px 0}.list .m{color:var(--gray);font-size:12px;font-family:'DM Mono',monospace}
table{width:100%;border-collapse:collapse;font-size:13px;margin:16px 0}th{color:var(--lime);font-family:'DM Mono',monospace;font-size:11px;text-align:left;padding:8px;border-bottom:1px solid var(--gray-dark);font-weight:500}
td{padding:8px;border-bottom:1px solid var(--line);color:var(--gray)}td:first-child{color:var(--white)}
.grid{display:grid;grid-template-columns:110px repeat(3,1fr);gap:1px;background:var(--gray-dark);border:1px solid var(--gray-dark);margin:18px 0}
.grid>div{background:var(--black);padding:10px;min-height:52px;font-size:12px}.grid .h{color:var(--lime);font-family:'DM Mono',monospace;font-size:11px}
.grid .f{font-weight:700}.grid a{text-decoration:none;color:var(--lime)}.grid .z{color:var(--gray-dark)}
.body p.frame{font-size:12.5px;color:var(--gray);border:1px solid var(--gray-dark);background:var(--dark);padding:10px 14px;line-height:1.7}
.body p.frame strong{color:var(--lime)}.body ul{margin:0 0 18px 18px;color:var(--gray);font-size:14px;line-height:1.8}.body ul a{color:var(--white)}
.body table.mini{max-width:420px;font-size:12px}.body table.mini th,.body table.mini td{text-align:center;padding:5px 6px}.body table.mini td:first-child,.body table.mini th:first-child{text-align:left}
.body table.mini td.on{color:var(--lime);font-size:16px}.body table.mini td.from{color:var(--white)}
.fb{margin:34px 0 10px;border:1px solid var(--gray-dark);background:var(--dark);padding:16px 18px}
.fb .q{font-size:13px;color:var(--white);margin-bottom:10px}.fb .q span{color:var(--gray);font-size:12px;margin-left:8px}
.fb .btns{display:flex;flex-wrap:wrap;gap:8px}.fb button{font-family:'DM Mono','Noto Sans KR',monospace;font-size:12px;padding:7px 12px;background:transparent;color:var(--white);border:1px solid var(--gray-dark);cursor:pointer}
.fb button:hover{border-color:var(--lime);color:var(--lime)}.fb button.on{background:var(--lime);color:var(--black);border-color:var(--lime)}.fb button b{font-weight:500;color:var(--gray);margin-left:6px}.fb button.on b{color:var(--black)}
.fb textarea{width:100%;margin-top:10px;background:var(--black);color:var(--white);border:1px solid var(--gray-dark);padding:10px;font-family:inherit;font-size:13px;min-height:64px}
.fb .row{display:flex;gap:10px;align-items:center;margin-top:8px}.fb .note{font-size:11.5px;color:var(--gray);line-height:1.6}.fb[hidden]{display:none}
.foot{margin-top:60px;padding-top:20px;border-top:1px solid var(--line);color:var(--gray);font-size:12px;line-height:1.8}
.foot a{color:var(--white)}.about{background:var(--dark);border:1px solid var(--gray-dark);padding:16px 18px;font-size:13.5px;color:var(--gray);line-height:1.7;margin-bottom:28px}
@media(max-width:600px){.grid{grid-template-columns:80px repeat(3,1fr)}}"""

T = {
    "ko": dict(today="오늘", growth="성장", grid="격자", about="이 실험이 무엇인가", other="EN", other_href="/en/",
               list="지난 글", subscribe="구독", empty="아직 글이 없습니다.", label="엔터 바이브 리서치 · AI 인턴 1호",
               about_line="AI 인턴 1호가 매일 엔터 산업을 읽고 씁니다. 사람이 고르지도 고치지도 않습니다. 이 실험이 무엇인지는",
               here="여기", human="AI가 매일 읽고 정리합니다. 관점은 사람이 씁니다.", human_link="엔터문화연구소 뉴스레터",
               growth_title="성장 지표", cols=["날", "날짜", "제목", "좌표", "시제", "레이더와", "검증", "검수", "베팅"],
               grid_title="격자 21칸 · 인턴이 쓴 자리", empty_cell="", bets="베팅 대장", bet_cols=["날짜", "명제", "기한", "확인", "상태"]),
    "en": dict(today="Today", growth="Growth", grid="Grid", about="What this is", other="KO", other_href="/",
               list="Earlier pieces", subscribe="Subscribe", empty="No pieces yet.", label="Entertainment Vibe Research · AI Intern 01",
               about_line="AI Intern 01 reads and writes about the entertainment industry every day. No human picks or edits. What this experiment is:",
               here="here", human="AI reads and sorts every day. The point of view is written by a human.", human_link="Neo Vibe Lab newsletter",
               growth_title="Growth metrics", cols=["Day", "Date", "Title", "Grid", "Tense", "vs radar", "Verified", "Review", "Bet"],
               grid_title="21 cells · where the intern has written", empty_cell="", bets="Bets", bet_cols=["Date", "Claim", "By", "Check", "Status"]),
}


def md_to_html(md: str) -> str:
    out = []
    for block in re.split(r"\n\s*\n", md.strip()):
        b = block.strip()
        if not b:
            continue
        if b.startswith("# "):
            continue  # 제목은 따로
        if b.startswith("`") and b.endswith("`") and "\n" not in b:
            continue  # 헤더 줄은 따로
        if b.startswith("> "):
            out.append(_quote(b)); continue
        if b.startswith("<sub>"):
            out.append(_inline_keep_tags(b)); continue
        if b.startswith("| "):
            out.append(_table(b)); continue
        if b.startswith("- "):
            out.append("<ul>" + "".join(f"<li>{_inline(l[2:])}</li>" for l in b.splitlines() if l.startswith("- ")) + "</ul>"); continue
        if b.startswith("**엔터문화연구소의 AI 실험**") or b.startswith("**A Neo Vibe Lab AI experiment**"):
            out.append(f'<p class="frame">{_inline(b)}</p>'); continue
        out.append(f"<p>{_inline(b)}</p>")
    return "\n".join(out)


def _quote(b: str) -> str:
    lines = [re.sub(r"^>\s?", "", l) for l in b.splitlines()]
    paras, cur, items = [], [], []
    def flush():
        nonlocal cur, items
        if items:
            paras.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>"); items = []
        if cur:
            paras.append(f"<p>{_inline(' '.join(cur))}</p>"); cur = []
    for l in lines:
        if not l.strip():
            flush()
        elif l.startswith("- "):
            if cur: flush()
            items.append(l[2:])
        else:
            if items: flush()
            cur.append(l)
    flush()
    return "<blockquote>" + "".join(paras) + "</blockquote>"


def _inline_keep_tags(b: str) -> str:
    inner = re.sub(r"^<sub>|</sub>$", "", b.strip())
    return f"<sub>{_inline(inner)}</sub>"


def _table(b: str) -> str:
    rows = [r.strip().strip("|").split("|") for r in b.splitlines() if r.strip().startswith("|")]
    rows = [r for r in rows if not all(re.fullmatch(r"\s*:?-+:?\s*", c) for c in r)]
    if not rows:
        return ""
    mini = rows[0][0].strip() == ""
    h = "".join(f"<th>{_inline(c.strip())}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(
        f"<td class='{'on' if c.strip() == '●' else 'from' if c.strip() == '○' else ''}'>{_inline(c.strip())}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f"<table class='{'mini' if mini else ''}'><tr>{h}</tr>{body}</table>"


def _inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\[(.+?)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return t.replace("\n", "<br>")


def page(lang: str, title: str, body: str, path_prefix: str = "") -> str:
    t = T[lang]
    root = "/" if lang == "ko" else "/en/"
    return f"""<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · {t['label']}</title><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<nav><a class="brand" href="{root}">{t['label']}</a><span class="sp"></span>
<a class="l" href="{root}">{t['today']}</a><a class="l" href="{root}growth">{t['growth']}</a><a class="l" href="{root}grid">{t['grid']}</a>
<a class="l" href="{config.ABOUT_URL}{'?lang=en' if lang == 'en' else ''}">{t['about']}</a><a class="l" href="{config.ABOUT_URL}{'?lang=en' if lang == 'en' else ''}#subscribe">{t['subscribe']}</a><a class="l" href="{t['other_href']}">{t['other']}</a></nav>
<div class="wrap">{body}
<div class="foot">{t['human']} <a href="{config.NEWSLETTER_URL}">{t['human_link']}</a><br>© 2026 엔터문화연구소 (Neo Vibe Lab) · Seoul</div></div></body></html>"""


FB_T = {
    "ko": dict(q="이 글은 어땠습니까", hint="누른 것은 매주 묶여 인턴의 규칙 후보가 됩니다. 관점은 안 건드립니다.",
               btns=[("agree", "맞는 말이다"), ("obvious", "뻔하다"), ("weak", "근거가 약하다"), ("off", "관점이 어긋난다")],
               ph="지적을 한두 문장으로 (선택, 500자)", send="보내기", thanks="기록했습니다. 일요일 회고에 반영됩니다.", done="이미 남겼습니다",
               textnote="자유 지적은 공개되지 않고 인턴에게 직접 들어가지도 않습니다. 별도 모델이 유형과 건수로 정리한 것만 넘어갑니다."),
    "en": dict(q="How was this piece", hint="Votes are batched weekly into the intern's rule candidates. The point of view is left alone.",
               btns=[("agree", "Fair point"), ("obvious", "Obvious"), ("weak", "Weak evidence"), ("off", "Wrong lens")],
               ph="A note in a sentence or two (optional, 500 chars)", send="Send", thanks="Recorded. It goes into Sunday's retrospective.", done="Already recorded",
               textnote="Free-text notes are not shown publicly and never go to the intern directly. A separate model turns them into types and counts."),
}


def feedback_widget(lang: str, slug: str) -> str:
    """독자 버튼 4 + 자유 텍스트. Supabase intern_feedback에 publishable 키로 INSERT. 표가 없으면(마이그레이션 전) 스스로 숨는다."""
    t = FB_T[lang]
    btns = "".join(f'<button type="button" data-k="{k}">{v}<b data-n="{k}"></b></button>' for k, v in t["btns"])
    return f"""<div class="fb" id="fb" data-slug="{html.escape(slug)}" data-lang="{lang}" hidden>
<div class="q">{t['q']}<span>{t['hint']}</span></div>
<div class="btns">{btns}</div>
<textarea id="fb-text" maxlength="500" placeholder="{t['ph']}"></textarea>
<div class="row"><button type="button" id="fb-send">{t['send']}</button><span class="note" id="fb-msg"></span></div>
<div class="note" style="margin-top:8px">{t['textnote']}</div>
</div>
<script>
(function(){{
var API={json.dumps(config.FEEDBACK_API)};
var el=document.getElementById('fb');if(!el)return;
var slug=el.dataset.slug,lang=el.dataset.lang;
var key='fb:'+slug,mine={{}};try{{mine=JSON.parse(localStorage.getItem(key)||'{{}}')}}catch(e){{}}
function save(){{try{{localStorage.setItem(key,JSON.stringify(mine))}}catch(e){{}}}}
function counts(){{fetch(API+'?slug='+encodeURIComponent(slug)).then(function(r){{if(!r.ok)throw 0;return r.json()}}).then(function(d){{el.hidden=false;var c=d.counts||{{}};el.querySelectorAll('b[data-n]').forEach(function(b){{b.textContent=c[b.dataset.n]||''}});el.querySelectorAll('button[data-k]').forEach(function(b){{b.classList.toggle('on',!!mine[b.dataset.k])}})}}).catch(function(){{}})}}
function post(kind,text,via){{return fetch(API,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{slug:slug,lang:lang,kind:kind,text:text||'',via:via||'web'}})}})}}
var msg=document.getElementById('fb-msg');
el.querySelectorAll('button[data-k]').forEach(function(b){{b.addEventListener('click',function(){{var k=b.dataset.k;if(mine[k]){{msg.textContent={json.dumps(t['done'])};return}}post(k,'','web').then(function(r){{if(r.ok){{mine[k]=1;save();msg.textContent={json.dumps(t['thanks'])};counts()}}}})}})}});
document.getElementById('fb-send').addEventListener('click',function(){{var v=document.getElementById('fb-text').value.trim();if(v.length<2)return;post('text',v,'web').then(function(r){{if(r.ok){{document.getElementById('fb-text').value='';mine.text=1;save();msg.textContent={json.dumps(t['thanks'])};counts()}}}})}});
var q=new URLSearchParams(location.search).get('fb');
if(q&&['agree','obvious','weak','off'].indexOf(q)>=0&&!mine[q]){{post(q,'','mail').then(function(r){{if(r.ok){{mine[q]=1;save();msg.textContent={json.dumps(t['thanks'])};counts()}}}})}}
counts();
}})();
</script>"""


def _pieces(lang: str) -> list[tuple[dict, str, str]]:
    out = []
    for p in sorted((config.CONTENT_DIR / lang).glob("*.md"), reverse=True):
        fm, body = publish.parse_piece(p)
        if fm:
            out.append((fm, body, p.stem))
    return out


def render_piece(lang: str, fm: dict, body: str) -> str:
    t = T[lang]
    hdr = re.search(r"`([^`]+)`", body)
    hdr_html = f'<div class="hdr">{html.escape(hdr.group(1))}</div>' if hdr else ""
    day = fm.get("day", "")
    if fm.get("type") == "weekly":
        meta = f"{fm.get('date')} · " + ("주간 회고" if lang == "ko" else "Weekly review")
    else:
        meta = f"D+{day} · {fm.get('date')}" if lang == "ko" else f"Day {day} · {fm.get('date')}"
    inner = md_to_html(body)
    # 독자 신호 위젯은 검수 기록 앞(원리 뒤)에 들어간다
    k = inner.rfind("<blockquote>")
    widget = feedback_widget(lang, fm.get("slug", ""))
    inner = (inner[:k] + widget + inner[k:]) if k >= 0 else inner + widget
    return f"""<p class="label">{t['label']}</p>{hdr_html}<h1>{html.escape(fm.get('title',''))}</h1><p class="meta">{meta}</p>
<div class="body">{inner}</div>"""


def build() -> None:
    keep = config.DIST_DIR / ".vercel"
    saved = None
    if keep.exists():
        saved = config.DIST_DIR.parent / ".vercel-keep"
        shutil.rmtree(saved, ignore_errors=True); shutil.copytree(keep, saved)
    if config.DIST_DIR.exists():
        shutil.rmtree(config.DIST_DIR)
    config.DIST_DIR.mkdir(parents=True, exist_ok=True)
    if saved:
        shutil.copytree(saved, keep); shutil.rmtree(saved, ignore_errors=True)
    stats = [s for s in publish._load(config.DATA_DIR / "stats.json", []) if s.get("type") != "weekly"]
    preds = publish._load(config.DATA_DIR / "predictions.json", [])
    for lang in ("ko", "en"):
        t = T[lang]
        base = config.DIST_DIR / ("" if lang == "ko" else "en")
        base.mkdir(parents=True, exist_ok=True)
        pieces = _pieces(lang)
        about = f'<div class="about">{t["about_line"]} <a href="{config.ABOUT_URL}{"?lang=en" if lang == "en" else ""}">{t["here"]}</a>.</div>'
        # 개별 글
        for fm, body, slug in pieces:
            io.open(base / f"{slug}.html", "w", encoding="utf-8").write(page(lang, fm.get("title", ""), about + render_piece(lang, fm, body)))
        # 오늘의 글 + 목록
        if pieces:
            fm, body, slug = pieces[0]
            def _meta(f):
                if f.get("type") == "weekly":
                    return ("주간 회고" if lang == "ko" else "Weekly review") + f' · {f.get("date")}'
                return (f'D+{f.get("day")} · {f.get("date")} · {html.escape(f.get("factor",""))} '
                        f'{html.escape(f.get("from_stage",""))} → {html.escape(f.get("to_stage",""))} · {f.get("tense")}')
            lst = "".join(f'<a href="{s}"><div class="m">{_meta(f)}</div><div class="t">{html.escape(f.get("title",""))}</div></a>' for f, _, s in pieces[1:])
            main = about + render_piece(lang, fm, body) + (f'<h2 class="label" style="margin-top:50px">{t["list"]}</h2><div class="list">{lst}</div>' if lst else "")
        else:
            main = about + f"<p>{t['empty']}</p>"
        io.open(base / "index.html", "w", encoding="utf-8").write(page(lang, t["today"], main))
        # 성장
        rows = "".join(
            f"<tr><td>{s['day']}</td><td>{s['date']}</td><td><a href='{s['slug']}'>{html.escape(s['title_ko'] if lang == 'ko' else s['title_en'])}</a></td>"
            f"<td>{html.escape(s['factor'])} {html.escape(s['from_stage'])}→{html.escape(s['to_stage'])}</td><td>{s['tense']}</td>"
            f"<td>{'-' if s.get('agrees') is None else '=' if s.get('agrees') else '≠ ' + str(s.get('radar_tense'))}</td><td>{s['claims_verified']}/{s['claims_total']}</td>"
            f"<td>{s['review_rounds']}{' · unresolved' if s['unresolved'] else ''}</td><td>{'●' if s['bet'] else ''}</td></tr>" for s in reversed(stats))
        n = len(stats) or 1
        summary = {
            "verified": sum(s["claims_verified"] for s in stats) / max(1, sum(s["claims_total"] for s in stats)),
            "agree": (sum(1 for s in stats if s.get("agrees")) / max(1, sum(1 for s in stats if s.get("agrees") is not None))),
            "pass1": sum(1 for s in stats if s["review_rounds"] <= 1 and not s["unresolved"]) / n,
            "cells": len({(s["factor"], s["to_stage"]) for s in stats}),
        }
        bets = "".join(f"<tr><td>{p['date']}</td><td>{html.escape(p['claim_ko'] if lang == 'ko' else p['claim_en'])}</td><td>{p['by_date']}</td><td>{html.escape(p['check_ko'] if lang == 'ko' else p['check_en'])}</td><td>{p['status']}</td></tr>" for p in reversed(preds))
        g = (f"<p class='label'>{t['growth_title']}</p><h1>{'다섯 축' if lang == 'ko' else 'Five axes'}</h1>"
             f"<table><tr><th>{'사실' if lang=='ko' else 'Facts'}</th><th>{'판정 일치' if lang=='ko' else 'Judgment agrees'}</th><th>{'논지 1회 통과' if lang=='ko' else 'Argument pass@1'}</th><th>{'격자 칸' if lang=='ko' else 'Grid cells'}</th><th>{'예측' if lang=='ko' else 'Prediction'}</th></tr>"
             f"<tr><td>{summary['verified']:.0%}</td><td>{summary['agree']:.0%}</td><td>{summary['pass1']:.0%}</td><td>{summary['cells']}/21</td><td>{'기한 전' if lang=='ko' else 'pending'}</td></tr></table>"
             f"<table><tr>{''.join(f'<th>{c}</th>' for c in t['cols'])}</tr>{rows}</table>"
             f"<h2 class='label' style='margin-top:40px'>{t['bets']}</h2><table><tr>{''.join(f'<th>{c}</th>' for c in t['bet_cols'])}</tr>{bets or '<tr><td colspan=5>-</td></tr>'}</table>")
        io.open(base / "growth.html", "w", encoding="utf-8").write(page(lang, t["growth"], g))
        # 격자
        cells = {}
        for s in stats:
            cells.setdefault((s["factor"], s["to_stage"]), []).append(s)
        gh = f"<div class='grid'><div class='h'>{'요인 / 단계' if lang=='ko' else 'factor / stage'}</div>" + "".join(f"<div class='h'>{st if lang=='ko' else config.STAGES_EN[st]}</div>" for st in config.STAGES)
        for f in config.FACTORS:
            gh += f"<div class='f'>{f if lang=='ko' else config.FACTORS_EN[f]}</div>"
            for st in config.STAGES:
                ss = cells.get((f, st), [])
                gh += "<div>" + ("".join(f"<a href='{x['slug']}'>D+{x['day']}</a> " for x in ss) if ss else "<span class='z'>·</span>") + "</div>"
        gh += "</div>"
        io.open(base / "grid.html", "w", encoding="utf-8").write(page(lang, t["grid"], f"<p class='label'>{t['grid_title']}</p><h1>{'21칸' if lang=='ko' else '21 cells'}</h1>" + gh))
    # 브랜드 자산 - 메일·아카이브가 이 URL을 쓴다(외부 호스팅 금지)
    src = config.ROOT / "assets"
    if src.exists():
        shutil.copytree(src, config.DIST_DIR / "assets", dirs_exist_ok=True)
    # 데이터 공개
    (config.DIST_DIR / "data").mkdir(exist_ok=True)
    for name in ("stats.json", "predictions.json"):
        src = config.DATA_DIR / name
        if src.exists():
            shutil.copy(src, config.DIST_DIR / "data" / name)
    # dist/에서 그대로 배포한다. outputDirectory를 쓰면 dist/dist를 찾아 cleanUrls가 죽는다(2026-09-06 실측 404).
    io.open(config.DIST_DIR / "vercel.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps({"cleanUrls": True, "trailingSlash": False,
                    # 랜딩의 실험실 카드가 이 기록을 읽어 숫자를 채운다.
                    "headers": [{"source": "/data/(.*)",
                                 "headers": [{"key": "Access-Control-Allow-Origin", "value": "*"}]}]},
                   ensure_ascii=False, indent=2) + "\n")
    io.open(config.DIST_DIR / "robots.txt", "w").write("User-agent: *\nAllow: /\nUser-agent: GPTBot\nDisallow: /\nUser-agent: ClaudeBot\nDisallow: /\nUser-agent: CCBot\nDisallow: /\n")
    print(f"  [site] dist/ 생성 - ko {len(_pieces('ko'))}편 · en {len(_pieces('en'))}편")
