# -*- coding: utf-8 -*-
"""정적 사이트 생성 - dist/. 오늘의 글 · 언어별 목록 · 성장 대시보드 · 격자 허브. 외부 라이브러리 없음."""
import html
import io
import json
import re
import shutil

from . import config, publish

CSS = """:root{--lime:#D6FF92;--lime-dim:rgba(214,255,146,.10);--black:#0A0A0A;--card:#121212;--edge:#242424;--ink:#E4E4DC;--dim:#8C8C84;--line:rgba(255,255,255,.07);--white:#F5F5EF}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--black);color:var(--ink);font-family:'Noto Sans KR',system-ui,sans-serif;-webkit-font-smoothing:antialiased;line-height:1.6}
a{color:var(--white)}.mono{font-family:'DM Mono',ui-monospace,monospace}

/* 상단 */
nav{position:sticky;top:0;z-index:10;background:rgba(10,10,10,.93);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:20px;padding:0 24px;height:52px;overflow-x:auto;white-space:nowrap;scrollbar-width:none}
nav::-webkit-scrollbar{display:none}
nav .brand{display:flex;align-items:center;gap:8px;color:var(--white);font-weight:700;font-size:13px;text-decoration:none;flex:none}
nav .brand::before{content:"";width:7px;height:7px;background:var(--lime);border-radius:50%;flex:none}
nav .sp{flex:1;min-width:12px}
nav a.l{color:var(--dim);text-decoration:none;font-size:12px;font-family:'DM Mono','Noto Sans KR',monospace;letter-spacing:.03em;flex:none;line-height:52px;border-bottom:2px solid transparent}
nav a.l:hover{color:var(--lime)}nav a.l.on{color:var(--white);border-bottom-color:var(--lime)}
.wrap{max-width:720px;margin:0 auto;padding:44px 24px 90px}
.label{color:var(--lime);font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase}

/* 글 머리 */
.chip{display:inline-flex;align-items:center;gap:9px;font-family:'DM Mono',monospace;font-size:12.5px;padding:5px 12px;border:1px solid var(--edge);color:var(--dim)}
.chip b{font-weight:500;color:var(--white)}
.chip .tn{color:var(--lime)}
.chip.vibe{border-color:rgba(214,255,146,.4);background:var(--lime-dim)}
h1{font-size:clamp(27px,4.2vw,40px);font-weight:900;letter-spacing:-.025em;line-height:1.22;margin:16px 0 14px;color:var(--white)}
.meta{color:var(--dim);font-size:11.5px;font-family:'DM Mono','Noto Sans KR',monospace;display:flex;flex-wrap:wrap;gap:6px 16px;padding-bottom:20px;border-bottom:1px solid var(--line);margin-bottom:26px}
.meta .warn{color:var(--lime)}

/* 본문 */
.body p{font-size:17px;line-height:1.95;margin:0 0 20px;color:var(--ink)}
.body strong{color:var(--white);font-weight:700}
.body a{color:var(--white);text-decoration:underline;text-decoration-color:rgba(214,255,146,.45);text-underline-offset:3px}
.body a:hover{color:var(--lime)}
.body sub{color:var(--dim);font-size:11.5px;line-height:1.75;display:block;margin-top:8px}
.tw+p,.tw+.tw{margin-top:0}

/* 실험 프레임 - 조용하게 */
p.frame{font-size:11.5px;color:var(--dim);font-family:'DM Mono','Noto Sans KR',monospace;line-height:1.85;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:10px 0;margin:0 0 26px}
p.frame strong{color:var(--lime);font-weight:500}
p.frame a{text-decoration:none;color:var(--ink)}p.frame a:hover{color:var(--lime)}

/* 오늘의 소재 */
p.src{background:var(--card);border:1px solid var(--edge);padding:15px 18px 13px;margin:0;font-size:14.5px;line-height:1.85;color:var(--ink)}
p.src.joined{border-bottom:none;padding-bottom:10px}
p.src strong{display:block;color:var(--lime);font-family:'DM Mono',monospace;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;margin-bottom:7px;font-weight:500}
ul.src-list{background:var(--card);border:1px solid var(--edge);border-top:none;margin:0 0 26px;padding:0 18px 13px;list-style:none}
ul.src-list li{font-size:12.5px;color:var(--dim);font-family:'DM Mono','Noto Sans KR',monospace;line-height:1.75;padding-left:15px;position:relative}
ul.src-list li::before{content:"";position:absolute;left:1px;top:9px;width:5px;height:5px;background:var(--lime)}
ul.src-list a{color:var(--ink);text-decoration:none}ul.src-list a:hover{color:var(--lime)}

/* 조짐·베팅·원리 */
p.evidence,p.bet{font-size:14px;line-height:1.8;color:var(--ink);background:var(--card);border-left:2px solid var(--edge);padding:12px 16px;margin:0 0 20px}
p.evidence{border-left-color:var(--lime)}
p.evidence strong,p.bet strong{display:block;margin-bottom:6px;color:var(--lime);font-family:'DM Mono',monospace;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;font-weight:500}
p.principle{font-size:17px;line-height:1.8;color:var(--white);border-left:2px solid var(--lime);padding:2px 0 2px 18px;margin:30px 0 22px;font-weight:500}
p.principle strong{display:block;color:var(--lime);font-family:'DM Mono',monospace;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;margin-bottom:7px;font-weight:500}

/* 검수 기록 */
.body blockquote{border:1px solid var(--edge);background:var(--card);padding:14px 17px;margin:26px 0;font-size:12.5px;line-height:1.8;color:var(--dim)}
.body blockquote p{font-size:12.5px;line-height:1.8;color:var(--dim);margin:0 0 9px}
.body blockquote p:last-child{margin:0}
.body blockquote strong{color:var(--lime);font-family:'DM Mono',monospace;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;font-weight:500}
.body blockquote ul{margin:9px 0 0 16px;font-size:12px;line-height:1.75}
.body blockquote li{margin-bottom:6px}

/* 표 */
.tw{overflow-x:auto;margin:0 0 26px;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--lime);font-family:'DM Mono','Noto Sans KR',monospace;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;text-align:left;padding:9px 10px 9px 0;border-bottom:1px solid var(--edge);font-weight:500;white-space:nowrap}
td{padding:9px 10px 9px 0;border-bottom:1px solid var(--line);color:var(--dim);white-space:nowrap}
td:first-child{color:var(--ink)}
td.ttl{white-space:normal;min-width:220px;line-height:1.6;padding-right:16px}
td a{color:var(--ink);text-decoration:none}td a:hover{color:var(--lime)}
table.mini{max-width:302px;font-size:11px;margin:2px 0 4px;border:1px solid var(--line)}
table.mini th,table.mini td{text-align:center;padding:5px 2px;white-space:nowrap;border-bottom:1px solid var(--line);width:56px}
table.mini tr:last-child td{border-bottom:none}
table.mini th{font-size:9.5px;letter-spacing:.06em;padding:6px 2px}
table.mini th:first-child,table.mini td:first-child{text-align:left;width:auto;color:var(--dim);font-family:'DM Mono','Noto Sans KR',monospace;font-size:10.5px;padding:5px 8px}
table.mini td.on{color:var(--lime);font-size:13px;line-height:1;background:rgba(214,255,146,.13)}
table.mini td.from{color:var(--white);background:rgba(255,255,255,.04)}
table.mini td.z{color:#2B2B2B}

/* 홈 */
.hero{padding:8px 0 34px;border-bottom:1px solid var(--line);margin-bottom:30px}
.hero h1{font-size:clamp(25px,3.6vw,34px);line-height:1.42;letter-spacing:-.02em;margin:14px 0 16px;font-weight:900}
.hero-sub{font-size:14.5px;line-height:1.85;color:var(--dim);max-width:560px;margin-bottom:20px}
.hero-run{display:flex;flex-wrap:wrap;gap:8px 10px;margin-bottom:22px}
.hero-run span{font-family:'DM Mono','Noto Sans KR',monospace;font-size:11px;color:var(--dim);border:1px solid var(--edge);padding:4px 10px}
.hero-cta{display:flex;gap:10px;flex-wrap:wrap}
.btn{display:inline-block;font-family:'DM Mono','Noto Sans KR',monospace;font-size:12px;letter-spacing:.04em;padding:11px 20px;background:var(--lime);color:var(--black);text-decoration:none;font-weight:500}
.btn:hover{background:var(--white)}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--edge)}
.btn.ghost:hover{border-color:var(--lime);color:var(--lime)}
.today-card{display:block;background:var(--card);border:1px solid var(--edge);padding:20px 20px 18px;text-decoration:none;transition:border-color .15s}
.today-card:hover{border-color:rgba(214,255,146,.45)}
.today-card .k{display:block;color:var(--lime);font-family:'DM Mono',monospace;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:12px}
.today-card .chip{margin-bottom:12px}
.today-card .t{display:block;font-size:24px;font-weight:900;color:var(--white);letter-spacing:-.02em;line-height:1.3;margin-bottom:10px}
.today-card:hover .t{color:var(--lime)}
.today-card .s{display:block;font-size:14px;line-height:1.8;color:var(--dim);margin-bottom:14px}
.today-card .go{font-family:'DM Mono',monospace;font-size:12px;color:var(--lime)}
.more{margin:-16px 0 0;text-align:right}
.more a{font-family:'DM Mono','Noto Sans KR',monospace;font-size:11.5px;color:var(--dim);text-decoration:none}
.more a:hover{color:var(--lime)}

/* 지난 글 */
.list{margin-top:10px}
.list a{display:flex;gap:18px;align-items:baseline;padding:16px 0;border-bottom:1px solid var(--line);text-decoration:none}
.list a:hover .t{color:var(--lime)}
.list .c{flex:1;min-width:0;display:flex;flex-direction:column}
.list .t{font-size:17px;font-weight:700;color:var(--white);line-height:1.4;margin-bottom:5px}
.list .m{color:var(--dim);font-size:11.5px;font-family:'DM Mono','Noto Sans KR',monospace}
.list .m .t2{color:var(--lime)}
.list .d{color:var(--dim);font-size:11px;font-family:'DM Mono',monospace;flex:none;white-space:nowrap}

/* 성장 요약 */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:1px;background:var(--edge);border:1px solid var(--edge);margin:18px 0 30px}
.stats div{background:var(--black);padding:16px 14px}
.stats b{display:block;font-size:26px;font-weight:900;color:var(--lime);letter-spacing:-.02em;line-height:1.1;margin-bottom:6px}
.stats span{font-size:11px;color:var(--dim);font-family:'DM Mono','Noto Sans KR',monospace;letter-spacing:.04em}

/* 격자 페이지 */
.grid{display:grid;grid-template-columns:104px repeat(3,1fr);gap:1px;background:var(--edge);border:1px solid var(--edge);margin:18px 0}
.grid>div{background:var(--black);padding:11px 10px;min-height:54px;font-size:12px;display:flex;align-items:center;flex-wrap:wrap;gap:6px}
.grid .h{color:var(--lime);font-family:'DM Mono','Noto Sans KR',monospace;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;align-items:flex-end}
.grid .f{font-weight:700;color:var(--ink);font-size:12.5px}
.grid a{text-decoration:none;color:var(--lime);font-family:'DM Mono',monospace;font-size:11.5px;border:1px solid rgba(214,255,146,.3);padding:2px 7px}
.grid a:hover{background:var(--lime);color:var(--black)}
.grid .z{color:#1C1C1C}

/* 독자 신호 */
.fb{margin:36px 0 12px;border:1px solid var(--edge);background:var(--card);padding:17px 18px}
.fb .q{font-size:13.5px;color:var(--white);margin-bottom:11px;font-weight:700}
.fb .q span{color:var(--dim);font-size:11.5px;margin-left:9px;font-weight:400}
.fb .btns{display:flex;flex-wrap:wrap;gap:8px}
.fb button{font-family:'DM Mono','Noto Sans KR',monospace;font-size:12px;padding:8px 13px;background:transparent;color:var(--ink);border:1px solid var(--edge);cursor:pointer;transition:all .15s}
.fb button:hover{border-color:var(--lime);color:var(--lime)}
.fb button.on{background:var(--lime);color:var(--black);border-color:var(--lime)}
.fb button b{font-weight:500;color:var(--dim);margin-left:7px}.fb button.on b{color:var(--black)}
.fb textarea{width:100%;margin-top:11px;background:var(--black);color:var(--ink);border:1px solid var(--edge);padding:11px;font-family:inherit;font-size:13px;min-height:64px;line-height:1.7}
.fb textarea:focus{outline:none;border-color:var(--lime)}
.fb .row{display:flex;gap:11px;align-items:center;margin-top:9px;flex-wrap:wrap}
.fb .note{font-size:11px;color:var(--dim);line-height:1.65}
.fb[hidden]{display:none}

/* 꼬리 */
.foot{margin-top:64px;padding-top:22px;border-top:1px solid var(--line);color:var(--dim);font-size:11.5px;line-height:1.9;font-family:'DM Mono','Noto Sans KR',monospace}
.foot a{color:var(--ink);text-decoration:none}.foot a:hover{color:var(--lime)}

nav .short{display:none}
@media(max-width:600px){
nav{gap:14px;padding:0 18px}
nav .brand{font-size:0}
nav .full{display:none}nav .short{display:inline}
nav a.l[data-k="home"]{display:none}
.wrap{padding:32px 18px 70px}
h1{margin:13px 0 12px}
.body p{font-size:16px;line-height:1.9}
p.principle{font-size:16px}
.grid{grid-template-columns:76px repeat(3,1fr)}
.grid>div{padding:9px 7px;min-height:46px}
.list a{gap:12px}
.list .t{font-size:16px}
.hero{padding-top:0}
.today-card .t{font-size:20px}
.hero-cta .btn{flex:1;text-align:center}
}"""

T = {
    "ko": dict(today="오늘", growth="성장", grid="격자", about="이 실험이 무엇인가", other="EN", other_href="/en/",
               brand="엔터 바이브 리서치", weekly="주간 회고", about_short="소개", home="홈",
               hero="AI 인턴이 매일 엔터 산업을 읽고,<br>아직 오지 않은 변화를 먼저 씁니다.",
               hero_sub="월요일부터 금요일까지 하루 한 편, 토요일에 그 주를 스스로 돌아봅니다. 소재도 관점도 사람이 고르지 않고, 틀린 날도 그대로 둡니다.",
               latest="오늘의 글", read="읽기", all_pieces="지난 글 전체", sub_cta="구독하기", running="일째 · ",
               pieces_word="편 발행", grid_word="격자 21칸", growth_link="지표 전부 보기",
               list="지난 글", subscribe="구독", empty="아직 글이 없습니다.", label="엔터 바이브 리서치 · AI 인턴 1호",
               about_line="AI 인턴 1호가 매일 엔터 산업을 읽고 씁니다. 사람이 고르지도 고치지도 않습니다. 이 실험이 무엇인지는",
               here="여기", human="AI가 매일 읽고 정리합니다. 관점은 사람이 씁니다.", human_link="엔터문화연구소 뉴스레터",
               growth_title="성장 지표", cols=["날", "날짜", "제목", "좌표", "시제", "레이더와", "검증", "검수", "베팅"],
               grid_title="격자 21칸 · 인턴이 쓴 자리", empty_cell="", bets="베팅 대장", bet_cols=["날짜", "명제", "기한", "확인", "상태"]),
    "en": dict(today="Today", growth="Growth", grid="Grid", about="What this is", other="KO", other_href="/",
               brand="Entertainment Vibe Research", weekly="Weekly review", about_short="About", home="Home",
               hero="An AI intern reads the entertainment industry<br>and writes what has not arrived yet.",
               hero_sub="One piece a day Monday to Friday, and a review of its own week on Saturday. No human picks the topic or edits the text, and the days it gets things wrong stay up.",
               latest="Today", read="Read", all_pieces="All pieces", sub_cta="Subscribe", running=" days in · ",
               pieces_word=" pieces", grid_word="21 cells", growth_link="See all metrics",
               list="Earlier pieces", subscribe="Subscribe", empty="No pieces yet.", label="Entertainment Vibe Research · AI Intern 01",
               about_line="AI Intern 01 reads and writes about the entertainment industry every day. No human picks or edits. What this experiment is:",
               here="here", human="AI reads and sorts every day. The point of view is written by a human.", human_link="Neo Vibe Lab newsletter",
               growth_title="Growth metrics", cols=["Day", "Date", "Title", "Grid", "Tense", "vs radar", "Verified", "Review", "Bet"],
               grid_title="21 cells · where the intern has written", empty_cell="", bets="Bets", bet_cols=["Date", "Claim", "By", "Check", "Status"]),
}


# 문단 머리말 → 블록 종류. 한 편의 고정 구조를 눈으로 구분되게 한다(2026-09-09 UI 개편).
BLOCK_KINDS = [
    ("frame", ("**엔터문화연구소의 AI 실험**", "**A Neo Vibe Lab AI experiment**")),
    ("src", ("**오늘의 소재**", "**Today's source**")),
    ("evidence", ("**조짐**", "**What is showing**")),
    ("bet", ("**베팅**", "**Bet**")),
    ("principle", ("**원리**", "**Principle**")),
]


def _kind(b: str) -> str:
    for name, heads in BLOCK_KINDS:
        if any(b.startswith(h) for h in heads):
            return name
    return ""


def md_to_html(md: str) -> str:
    out, prev = [], ""
    for block in re.split(r"\n\s*\n", md.strip()):
        b = block.strip()
        if not b:
            continue
        if b.startswith("# "):
            continue  # 제목은 따로
        if b.startswith("`") and b.endswith("`") and "\n" not in b:
            continue  # 헤더 줄은 따로
        if b.startswith("> "):
            out.append(_quote(b)); prev = "quote"; continue
        if b.startswith("<sub>"):
            out.append(_inline_keep_tags(b)); prev = "sub"; continue
        if b.startswith("| "):
            out.append('<div class="tw">' + _table(b) + "</div>"); prev = "table"; continue
        if b.startswith("- "):
            cls = ' class="src-list"' if prev == "src" else ""
            out.append(f"<ul{cls}>" + "".join(f"<li>{_inline(l[2:])}</li>" for l in b.splitlines() if l.startswith("- ")) + "</ul>")
            prev = "list"; continue
        k = _kind(b)
        if k:
            frag = _inline(b)
            if k != "frame":  # 라벨이 한 줄을 차지하므로 바로 뒤 구분자는 군더더기가 된다
                frag = frag.replace("</strong> · ", "</strong>", 1)
            out.append(f'<p class="{k}">{frag}</p>'); prev = k; continue
        out.append(f"<p>{_inline(b)}</p>"); prev = "p"
    res = "\n".join(out)
    # 소재 문단 뒤에 출처 목록이 붙으면 한 덩어리로 보이게 아래 테두리를 뗀다
    return res.replace('<p class="src">', '<p class="src joined">') if 'class="src-list"' in res else res


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
    def cell(c: str) -> str:
        v = c.strip()
        if v == "●":
            return "<td class='on'>●</td>"
        if v == "○":
            return "<td class='from'>○</td>"
        if v == "·":
            return "<td class='z'>·</td>"
        return f"<td>{_inline(v)}</td>"
    body = "".join("<tr>" + "".join(cell(c) for c in r) + "</tr>" for r in rows[1:])
    return f"<table class='{'mini' if mini else ''}'><tr>{h}</tr>{body}</table>"


def _inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\[(.+?)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return t.replace("\n", "<br>")


def page(lang: str, title: str, body: str, here: str = "", latest: str = "") -> str:
    t = T[lang]
    root = "/" if lang == "ko" else "/en/"
    ab = config.ABOUT_URL + ("?lang=en" if lang == "en" else "")

    def l(key: str, href: str, text: str, short: str = "") -> str:
        label = (f'<span class="full">{text}</span><span class="short">{short}</span>') if short else text
        return f'<a class="l{" on" if here == key else ""}" data-k="{key}" href="{href}">{label}</a>'
    links = (l("home", root, t["home"]) + l("today", latest or root, t["today"])
             + l("growth", f"{root}growth", t["growth"]) + l("grid", f"{root}grid", t["grid"])
             + l("", ab, t["about"], t["about_short"]) + l("", ab + "#subscribe", t["subscribe"])
             + l("", t["other_href"], t["other"]))
    return f"""<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · {t['label']}</title>
<meta name="description" content="{html.escape(t['about_line'])}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<nav><a class="brand" href="{root}">{t['brand']}</a><span class="sp"></span>{links}</nav>
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


def _chip(lang: str, fm: dict) -> str:
    """좌표 칩 - 요인·화살표·시제. 시제가 바이브면 칩 자체가 라임으로 켜진다."""
    if fm.get("type") == "weekly" or not fm.get("factor"):
        return ""
    tense = fm.get("tense", "")
    if lang == "ko":
        arrow = f"{fm['from_stage']} → {fm['to_stage']}"
        word = config.TENSE_KO.get(tense, tense)
        factor = fm["factor"]
    else:
        arrow = f"{config.STAGES_EN.get(fm['from_stage'], '')} → {config.STAGES_EN.get(fm['to_stage'], '')}"
        word = tense
        factor = config.FACTORS_EN.get(fm["factor"], fm["factor"])
    on = " vibe" if tense == "vibe" else ""
    return (f'<span class="chip{on}"><b>{html.escape(factor)}</b>{html.escape(arrow)}'
            f'<span class="tn">{html.escape(word)}</span></span>')


def _meta_line(lang: str, fm: dict) -> str:
    """날짜·회차 뒤에 검증·검수를 같이 둔다. 기록이 남는다는 것이 매 편에서 보여야 한다."""
    day = fm.get("day", "")
    if fm.get("type") == "weekly":
        head = f"{fm.get('date')} · " + ("주간 회고" if lang == "ko" else "Weekly review")
        return f'<p class="meta"><span>{head}</span></p>'
    parts = [f"D+{day} · {fm.get('date')}" if lang == "ko" else f"Day {day} · {fm.get('date')}"]
    ct, cv = fm.get("claims_total"), fm.get("claims_verified")
    if ct:
        parts.append((f"사실 검증 {cv}/{ct}" if lang == "ko" else f"facts {cv}/{ct}"))
    rounds = fm.get("review_rounds")
    if rounds:
        w = (f"검수 {rounds}회" if lang == "ko" else f"review {rounds}")
        if fm.get("unresolved"):
            w += (" · 미해결" if lang == "ko" else " · unresolved")
            parts.append(f'<span class="warn">{w}</span>')
        else:
            parts.append(w)
    return '<p class="meta">' + "".join(f"<span>{x}</span>" for x in parts) + "</p>"


def render_piece(lang: str, fm: dict, body: str) -> str:
    inner = md_to_html(body)
    # 독자 신호 위젯은 검수 기록 앞(원리 뒤)에 들어간다
    k = inner.rfind("<blockquote>")
    widget = feedback_widget(lang, fm.get("slug", ""))
    inner = (inner[:k] + widget + inner[k:]) if k >= 0 else inner + widget
    return (f"{_chip(lang, fm)}<h1>{html.escape(fm.get('title', ''))}</h1>{_meta_line(lang, fm)}"
            f'<div class="body">{inner}</div>')


def _summary_cards(lang: str, stats: list, preds: list) -> list:
    n = len(stats) or 1
    verified = sum(s["claims_verified"] for s in stats) / max(1, sum(s["claims_total"] for s in stats))
    agree = sum(1 for s in stats if s.get("agrees")) / max(1, sum(1 for s in stats if s.get("agrees") is not None))
    pass1 = sum(1 for s in stats if s["review_rounds"] <= 1 and not s["unresolved"]) / n
    cells = len({(s["factor"], s["to_stage"]) for s in stats})
    ko = lang == "ko"
    return [
        (f"{verified:.0%}", "사실 검증" if ko else "facts verified"),
        (f"{agree:.0%}", "레이더와 일치" if ko else "agrees with radar"),
        (f"{pass1:.0%}", "검수 1회 통과" if ko else "review pass@1"),
        (f"{cells}/21", "격자 칸" if ko else "grid cells"),
        (f"{len(preds)}", "베팅" if ko else "bets"),
    ]


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
        # 개별 글 - 소개 상자는 두지 않는다. 본문 머리의 실험 프레임이 같은 말을 한다(2026-09-09)
        for fm, body, slug in pieces:
            io.open(base / f"{slug}.html", "w", encoding="utf-8").write(
                page(lang, fm.get("title", ""), render_piece(lang, fm, body), here="today", latest=pieces[0][2]))

        def _row(f: dict, slug: str) -> str:
            if f.get("type") == "weekly":
                meta = f'<span class="t2">{t["weekly"]}</span>'
                right = f.get("date", "")
            else:
                factor = f.get("factor", "") if lang == "ko" else config.FACTORS_EN.get(f.get("factor", ""), "")
                a, b2 = f.get("from_stage", ""), f.get("to_stage", "")
                if lang == "en":
                    a, b2 = config.STAGES_EN.get(a, ""), config.STAGES_EN.get(b2, "")
                word = config.TENSE_KO.get(f.get("tense", ""), f.get("tense", "")) if lang == "ko" else f.get("tense", "")
                meta = f'{html.escape(factor)} {html.escape(a)} → {html.escape(b2)} · <span class="t2">{html.escape(word)}</span>'
                right = (f'D+{f.get("day")} · {f.get("date", "")[5:]}' if lang == "ko"
                         else f'Day {f.get("day")} · {f.get("date", "")[5:]}')
            return (f'<a href="{slug}"><span class="c"><span class="t">{html.escape(f.get("title", ""))}</span>'
                    f'<span class="m">{meta}</span></span><span class="d">{right}</span></a>')

        latest_slug = pieces[0][2] if pieces else ""
        ab = config.ABOUT_URL + ("?lang=en" if lang == "en" else "")
        if pieces:
            fm0 = pieces[0][0]
            summary = (fm0.get("source_summary") or "").strip()
            if len(summary) > 150:
                summary = summary[:150].rstrip() + "…"
            chip = _chip(lang, fm0)
            days = fm0.get("day", 0)
            run = (f"D+{days}" if lang == "ko" else f"Day {days}")
            hero = (f'<section class="hero"><p class="label">{t["brand"]}</p>'
                    f'<h1>{t["hero"]}</h1><p class="hero-sub">{t["hero_sub"]}</p>'
                    f'<p class="hero-run"><span>{run}</span><span>{len(pieces)}{t["pieces_word"]}</span>'
                    f'<span>{len({(x[0].get("factor"), x[0].get("to_stage")) for x in pieces if x[0].get("factor")})}/21 {t["grid_word"]}</span></p>'
                    f'<p class="hero-cta"><a class="btn" href="{ab}#subscribe">{t["sub_cta"]}</a>'
                    f'<a class="btn ghost" href="{ab}">{t["about"]}</a></p></section>')
            card = (f'<a class="today-card" href="{latest_slug}"><span class="k">{t["latest"]}</span>{chip}'
                    f'<span class="t">{html.escape(fm0.get("title", ""))}</span>'
                    + (f'<span class="s">{html.escape(summary)}</span>' if summary else "")
                    + f'<span class="go">{t["read"]} →</span></a>')
            stat_cards = "".join(f"<div><b>{v}</b><span>{k}</span></div>" for v, k in _summary_cards(lang, stats, preds))
            lst = "".join(_row(f, s2) for f, _, s2 in pieces[1:])
            main = (hero + card
                    + f'<div class="stats">{stat_cards}</div>'
                    + f'<p class="more"><a href="{"/" if lang == "ko" else "/en/"}growth">{t["growth_link"]} →</a></p>'
                    + (f'<h2 class="label" style="margin-top:44px">{t["list"]}</h2><div class="list">{lst}</div>' if lst else ""))
        else:
            main = f"<p>{t['empty']}</p>"
        io.open(base / "index.html", "w", encoding="utf-8").write(
            page(lang, t["home"], main, here="home", latest=latest_slug))
        # 성장
        def _row_cells(s):
            if lang == "ko":
                coord = f"{s['factor']} {s['from_stage']}→{s['to_stage']}"
                tense = config.TENSE_KO.get(s["tense"], s["tense"])
                rv = f"{s['review_rounds']}회" + (" · 미해결" if s["unresolved"] else "")
            else:
                coord = (f"{config.FACTORS_EN.get(s['factor'], s['factor'])} "
                         f"{config.STAGES_EN.get(s['from_stage'], '')}→{config.STAGES_EN.get(s['to_stage'], '')}")
                tense = s["tense"]
                rv = f"{s['review_rounds']}" + (" · unresolved" if s["unresolved"] else "")
            radar = "-" if s.get("agrees") is None else ("=" if s.get("agrees") else "≠ " + str(s.get("radar_tense")))
            title = html.escape(s["title_ko"] if lang == "ko" else s["title_en"])
            return (f"<tr><td>{s['day']}</td><td>{s['date'][5:]}</td><td class='ttl'><a href='{s['slug']}'>{title}</a></td>"
                    f"<td>{html.escape(coord)}</td><td>{html.escape(tense)}</td><td>{radar}</td>"
                    f"<td>{s['claims_verified']}/{s['claims_total']}</td><td>{html.escape(rv)}</td>"
                    f"<td>{'●' if s['bet'] else ''}</td></tr>")
        rows = "".join(_row_cells(s) for s in reversed(stats))
        n = len(stats) or 1
        summary = {
            "verified": sum(s["claims_verified"] for s in stats) / max(1, sum(s["claims_total"] for s in stats)),
            "agree": (sum(1 for s in stats if s.get("agrees")) / max(1, sum(1 for s in stats if s.get("agrees") is not None))),
            "pass1": sum(1 for s in stats if s["review_rounds"] <= 1 and not s["unresolved"]) / n,
            "cells": len({(s["factor"], s["to_stage"]) for s in stats}),
        }
        bets = "".join(f"<tr><td>{p['date'][5:]}</td><td class='ttl'>{html.escape(p['claim_ko'] if lang == 'ko' else p['claim_en'])}</td>"
                       f"<td>{p['by_date'][5:]}</td><td class='ttl'>{html.escape(p['check_ko'] if lang == 'ko' else p['check_en'])}</td>"
                       f"<td>{'열림' if (lang == 'ko' and p['status'] == 'open') else p['status']}</td></tr>" for p in reversed(preds))
        cards = _summary_cards(lang, stats, preds)
        g = (f"<p class='label'>{t['growth_title']}</p><h1>{'다섯 축' if lang == 'ko' else 'Five axes'}</h1>"
             + '<div class="stats">' + "".join(f"<div><b>{v}</b><span>{k}</span></div>" for v, k in cards) + "</div>"
             + f"<div class='tw'><table><tr>{''.join(f'<th>{c}</th>' for c in t['cols'])}</tr>{rows}</table></div>"
             f"<h2 class='label' style='margin-top:44px'>{t['bets']}</h2>"
             f"<div class='tw'><table><tr>{''.join(f'<th>{c}</th>' for c in t['bet_cols'])}</tr>{bets or '<tr><td colspan=5>-</td></tr>'}</table></div>")
        io.open(base / "growth.html", "w", encoding="utf-8").write(page(lang, t["growth"], g, here="growth", latest=latest_slug))
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
        filled = len({(s2["factor"], s2["to_stage"]) for s2 in stats})
        note = (f"<p class='meta' style='border:none;margin-top:6px'><span>{filled}/21 " +
                ("칸이 찼습니다. 빈 칸이 곧 소재 공백입니다.</span></p>" if lang == "ko"
                 else "cells filled. An empty cell is a gap in coverage.</span></p>"))
        io.open(base / "grid.html", "w", encoding="utf-8").write(
            page(lang, t["grid"], f"<p class='label'>{t['grid_title']}</p><h1>{'21칸' if lang == 'ko' else '21 cells'}</h1>"
                 + note + '<div class="tw">' + gh + "</div>", here="grid", latest=latest_slug))
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
