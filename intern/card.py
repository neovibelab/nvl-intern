# -*- coding: utf-8 -*-
"""공유 카드(og:image) - 편마다 1200x630 PNG를 그린다.

왜 만드나 - 링크를 카톡·슬랙·X에 붙이면 미리보기에 그림이 없었다. 사진을 끌어오는 대신
**우리 데이터로 그린다** - 좌표·시제·제목·회차·검증. 저작권 문제가 없고 매일 자동으로 같은 얼굴이 나온다.

폰트는 `assets/fonts/`(정본 = NVL `nvl-branding/폰트/`, 배포 = `scripts/brand-derive.py`).
폰트가 없으면 카드를 만들지 않고 조용히 넘어간다 - 카드가 없다고 발행이 멈추면 안 된다.
"""
import pathlib

from . import config

W, H = 1200, 630
BLACK = (10, 10, 10)
LIME = (214, 255, 146)
INK = (228, 228, 220)
DIM = (140, 140, 132)
EDGE = (36, 36, 36)
CARD = (18, 18, 18)

FONT_DIR = config.ROOT / "assets" / "fonts"
BOLD = FONT_DIR / "NotoSansKR-Bold-subset.otf"
REG = FONT_DIR / "NotoSansKR-Regular-subset.otf"
LOGO = config.ROOT / "assets" / "logo-lime-600.png"


def available() -> bool:
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return BOLD.exists() and REG.exists()


def _wrap(draw, text: str, font, max_w: int, max_lines: int) -> list[str]:
    """한글은 어절이 길어 글자 단위로 접는다. 라틴은 공백을 우선한다."""
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
            continue
        if " " in cur[-12:] and ch != " ":       # 라틴 단어 중간에서 끊지 않는다
            cut = cur.rfind(" ")
            lines.append(cur[:cut]); cur = cur[cut + 1:] + ch
        else:
            lines.append(cur); cur = ch
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and draw.textlength(text, font=font) > max_w * max_lines:
        lines[-1] = lines[-1][:-1] + "…"
    return lines


def _chip_text(lang: str, fm: dict) -> str:
    if fm.get("type") == "weekly" or not fm.get("factor"):
        return "주간 회고" if lang == "ko" else "Weekly review"
    if lang == "ko":
        return f"[{fm['factor']}] {fm['from_stage']} → {fm['to_stage']} · {config.TENSE_KO.get(fm['tense'], fm['tense'])}"
    return (f"[{config.FACTORS_EN.get(fm['factor'], fm['factor'])}] "
            f"{config.STAGES_EN.get(fm['from_stage'], '')} → {config.STAGES_EN.get(fm['to_stage'], '')} · {fm['tense']}")


def _meta_text(lang: str, fm: dict) -> str:
    day = fm.get("day", "")
    parts = [f"D+{day}" if lang == "ko" else f"Day {day}", str(fm.get("date", ""))]
    ct, cv = fm.get("claims_total"), fm.get("claims_verified")
    if ct:
        parts.append(f"사실 검증 {cv}/{ct}" if lang == "ko" else f"facts {cv}/{ct}")
    if fm.get("unresolved"):
        parts.append("검수 미해결" if lang == "ko" else "review unresolved")
    return "  ·  ".join(parts)


def render(fm: dict, lang: str, out: pathlib.Path) -> bool:
    if not available():
        return False
    from PIL import Image, ImageDraw, ImageFont

    im = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(im)
    f_title = ImageFont.truetype(str(BOLD), 66)
    f_chip = ImageFont.truetype(str(REG), 27)
    f_meta = ImageFont.truetype(str(REG), 24)
    f_tag = ImageFont.truetype(str(REG), 22)

    d.rectangle([0, 0, W, 6], fill=LIME)                       # 위 라임 띠
    pad = 72

    # 로고
    y = 74
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        logo = logo.resize((236, 59), Image.LANCZOS)
        im.paste(logo, (pad, y), logo)
    tag = "AI 인턴 01" if lang == "ko" else "AI Intern 01"
    d.text((pad + 256, y + 20), tag, font=f_tag, fill=DIM)

    # 좌표 칩
    chip = _chip_text(lang, fm)
    cy = 186
    cw = d.textlength(chip, font=f_chip) + 40
    vibe = fm.get("tense") == "vibe"
    d.rectangle([pad, cy, pad + cw, cy + 52], fill=(28, 34, 20) if vibe else CARD,
                outline=LIME if vibe else EDGE, width=1)
    d.text((pad + 20, cy + 12), chip, font=f_chip, fill=LIME if vibe else INK)

    # 제목
    title = (fm.get("title") or "").strip()
    lines = _wrap(d, title, f_title, W - pad * 2, 3)
    ty = 276
    for ln in lines:
        d.text((pad, ty), ln, font=f_title, fill=(245, 245, 239))
        ty += 84

    # 아래 메타
    d.line([pad, H - 108, W - pad, H - 108], fill=EDGE, width=1)
    d.text((pad, H - 78), _meta_text(lang, fm), font=f_meta, fill=DIM)
    host = config.SITE_URL.replace("https://", "").replace("http://", "")
    d.text((W - pad - d.textlength(host, font=f_meta), H - 78), host, font=f_meta, fill=LIME)

    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)
    return True


def render_default(lang: str, out: pathlib.Path) -> bool:
    """홈·성장·격자가 쓰는 기본 카드."""
    if not available():
        return False
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 6], fill=LIME)
    pad = 72
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA").resize((280, 70), Image.LANCZOS)
        im.paste(logo, (pad, 86), logo)
    f_h = ImageFont.truetype(str(BOLD), 60)
    f_s = ImageFont.truetype(str(REG), 27)
    head = ("AI 인턴이 매일 엔터 산업을 읽고,\n아직 오지 않은 변화를 먼저 씁니다." if lang == "ko"
            else "An AI intern reads the entertainment\nindustry and writes what has not arrived.")
    y = 236
    for ln in head.split("\n"):
        d.text((pad, y), ln, font=f_h, fill=(245, 245, 239)); y += 84
    sub = ("월~금 한 편 · 토요일 회고 · 사람 개입 없음" if lang == "ko"
           else "One piece a day Mon-Fri · Saturday review · no human in the loop")
    d.text((pad, H - 130), sub, font=f_s, fill=DIM)
    host = config.SITE_URL.replace("https://", "").replace("http://", "")
    d.text((pad, H - 84), host, font=f_s, fill=LIME)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)
    return True
