from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QColor


TEMAS_CORE = {
    "MIDNIGHT_MINIMAL": {
        "bg": "#020202",
        "bg_grad": "radial-gradient(1200px 700px at 20% 10%, rgba(255,255,255,.06) 0%, rgba(0,0,0,0) 55%), radial-gradient(900px 520px at 85% 20%, rgba(255,92,92,.09) 0%, rgba(0,0,0,0) 60%), linear-gradient(180deg, #020202 0%, #000000 100%)",
        "card": "#070707",
        "surface": "#050505",
        "border": "#1a1a1a",
        "accent": "#f3f3f3",
        "secondary": "#9a9a9a",
        "terciaria": "#2a2a2a",
        "danger": "#ff5c5c",
        "text_pri": "#f5f5f5",
        "text_sec": "#a8a8a8",
    },
    "OBSIDIAN_GOLD": {
        "bg": "#05050a",
        "bg_grad": "radial-gradient(900px 520px at 18% 12%, rgba(255,180,0,.14) 0%, rgba(0,0,0,0) 55%), radial-gradient(880px 520px at 84% 18%, rgba(255,90,0,.10) 0%, rgba(0,0,0,0) 60%), linear-gradient(180deg, #05050a 0%, #010103 100%)",
        "card": "#0a0a12",
        "surface": "#07070e",
        "border": "#231a10",
        "accent": "#ffb400",
        "secondary": "#ff6a00",
        "terciaria": "#4a240a",
        "danger": "#ff3344",
        "text_pri": "#fff1da",
        "text_sec": "#b99672",
    },
    "NOIR_CYAN": {
        "bg": "#03060a",
        "bg_grad": "radial-gradient(900px 520px at 20% 12%, rgba(0,212,255,.13) 0%, rgba(0,0,0,0) 58%), radial-gradient(900px 520px at 86% 16%, rgba(153,68,255,.10) 0%, rgba(0,0,0,0) 62%), linear-gradient(180deg, #03060a 0%, #010205 100%)",
        "card": "#07101a",
        "surface": "#050b12",
        "border": "#0f2338",
        "accent": "#00d4ff",
        "secondary": "#9944ff",
        "terciaria": "#1a2c44",
        "danger": "#ff4455",
        "text_pri": "#eaf6ff",
        "text_sec": "#8ab0c8",
    },
    "VOID_PURPLE": {
        "bg": "#05020a",
        "bg_grad": "radial-gradient(920px 540px at 18% 14%, rgba(170,68,255,.14) 0%, rgba(0,0,0,0) 58%), radial-gradient(900px 520px at 86% 20%, rgba(255,0,170,.09) 0%, rgba(0,0,0,0) 62%), linear-gradient(180deg, #05020a 0%, #010103 100%)",
        "card": "#0a0512",
        "surface": "#07040e",
        "border": "#1a0d33",
        "accent": "#aa44ff",
        "secondary": "#ff00aa",
        "terciaria": "#2d0f55",
        "danger": "#ff2244",
        "text_pri": "#f3e7ff",
        "text_sec": "#a48ac8",
    },
    "FROST_SIGNAL": {
        "bg": "#020610",
        "bg_grad": "radial-gradient(920px 540px at 20% 12%, rgba(0,170,255,.12) 0%, rgba(0,0,0,0) 60%), radial-gradient(900px 520px at 86% 18%, rgba(0,255,210,.08) 0%, rgba(0,0,0,0) 62%), linear-gradient(180deg, #020610 0%, #010309 100%)",
        "card": "#051022",
        "surface": "#040c1a",
        "border": "#0c2a4a",
        "accent": "#00aaff",
        "secondary": "#00ffd2",
        "terciaria": "#063055",
        "danger": "#ff3344",
        "text_pri": "#dff3ff",
        "text_sec": "#7aa6c2",
    },
    "EMBER_CORE": {
        "bg": "#070206",
        "bg_grad": "radial-gradient(900px 520px at 18% 12%, rgba(255,112,64,.16) 0%, rgba(0,0,0,0) 58%), radial-gradient(900px 520px at 86% 18%, rgba(224,32,48,.10) 0%, rgba(0,0,0,0) 62%), linear-gradient(180deg, #070206 0%, #020102 100%)",
        "card": "#12050a",
        "surface": "#0c0407",
        "border": "#3a1018",
        "accent": "#ff7040",
        "secondary": "#e02030",
        "terciaria": "#4a0d12",
        "danger": "#ff1040",
        "text_pri": "#ffe0dc",
        "text_sec": "#b48585",
    },
    "LARANJA_MESA": {
        "bg": "#080402",
        "bg_grad": "radial-gradient(1000px 600px at 15% 8%, rgba(255,120,0,.20) 0%, rgba(0,0,0,0) 55%), radial-gradient(880px 520px at 88% 22%, rgba(255,60,0,.12) 0%, rgba(0,0,0,0) 60%), linear-gradient(180deg, #0a0502 0%, #000000 100%)",
        "card": "#100804",
        "surface": "#0a0603",
        "border": "#3a1a08",
        "accent": "#ff8c1a",
        "secondary": "#ff5500",
        "terciaria": "#5a2a0a",
        "danger": "#ff3030",
        "text_pri": "#fff0e0",
        "text_sec": "#b89070",
    },
    "ULTRON_ERA": {
        "bg": "#04060c",
        "bg_grad": "radial-gradient(920px 540px at 20% 10%, rgba(255,180,0,.14) 0%, rgba(0,0,0,0) 58%), radial-gradient(900px 520px at 86% 18%, rgba(255,106,0,.10) 0%, rgba(0,0,0,0) 62%), linear-gradient(180deg, #04060c 0%, #010103 100%)",
        "card": "#0a0f18",
        "surface": "#080c14",
        "border": "#1a1510",
        "accent": "#ffb400",
        "secondary": "#ff6a00",
        "terciaria": "#8b2500",
        "danger": "#ff3344",
        "text_pri": "#ffe8cc",
        "text_sec": "#b89870",
    },
    "ARC_FORGE": {
        "bg": "#030508",
        "card": "#0c1018",
        "surface": "#070a10",
        "border": "#2a1a08",
        "accent": "#ffa500",
        "secondary": "#ff4500",
        "terciaria": "#663200",
        "danger": "#ff2222",
        "text_pri": "#fff0dd",
        "text_sec": "#a08060",
    },
    "VISION_CORE": {
        "bg": "#050810",
        "card": "#0a1220",
        "surface": "#081018",
        "border": "#142238",
        "accent": "#ffc84a",
        "secondary": "#ff9030",
        "terciaria": "#402018",
        "danger": "#ff4455",
        "text_pri": "#fff6e8",
        "text_sec": "#908878",
    },
    "CRIMSON_HUD": {
        "bg": "#0a0406",
        "card": "#14080c",
        "surface": "#10060a",
        "border": "#3a1018",
        "accent": "#ff7040",
        "secondary": "#e02030",
        "terciaria": "#501010",
        "danger": "#ff1040",
        "text_pri": "#ffe0dc",
        "text_sec": "#a07070",
    },
    "PHANTOM": {
        "bg": "#030a05",
        "card": "#060e08",
        "surface": "#060e08",
        "border": "#0d2210",
        "accent": "#00ff88",
        "secondary": "#00aa55",
        "terciaria": "#004422",
        "danger": "#ff0044",
        "text_pri": "#ccffdd",
        "text_sec": "#336644",
    },
    "ABYSSAL": {
        "bg": "#00050f",
        "card": "#000810",
        "surface": "#000810",
        "border": "#001535",
        "accent": "#00aaff",
        "secondary": "#0055cc",
        "terciaria": "#002244",
        "danger": "#ff2244",
        "text_pri": "#cceeff",
        "text_sec": "#224466",
    },
    "VIOLETA": {
        "bg": "#06000f",
        "card": "#090012",
        "surface": "#090012",
        "border": "#1a0033",
        "accent": "#aa44ff",
        "secondary": "#7722cc",
        "terciaria": "#440077",
        "danger": "#ff2244",
        "text_pri": "#eeddff",
        "text_sec": "#553366",
    },
    "CYBER_NEON": {
        "bg": "#020205",
        "card": "#05050f",
        "surface": "#07071a",
        "border": "#101035",
        "accent": "#00d4ff",
        "secondary": "#9944ff",
        "terciaria": "#ff00aa",
        "danger": "#ff2255",
        "text_pri": "#e0e0ff",
        "text_sec": "#6060aa",
    },
}


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = (h or "#000000").strip()
    if len(h) == 7 and h[0] == "#":
        return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    return 0, 255, 136


def qcolor_hex(h: str, a: int = 255) -> QColor:
    r, g, b = hex_rgb(h)
    c = QColor(r, g, b)
    c.setAlpha(a)
    return c


@dataclass(frozen=True)
class ThemeKit:
    ring_outer: QColor
    scan_line: QColor
    bg_tint: QColor
    glow_hot: QColor
    glow_mid: QColor
    tentacle: QColor
    tentacle_hot: QColor
    particle: QColor
    arc: QColor
    title: QColor
    subtitle: QColor
    core_white: QColor
    core_mid: QColor
    core_outer: QColor
    core_hot: QColor
    accent: QColor
    secondary: QColor
    danger: QColor


def kit_pintura(nome_tema: str) -> ThemeKit:
    raw = TEMAS_CORE.get(nome_tema) or TEMAS_CORE["PHANTOM"]
    ac = qcolor_hex(raw["accent"])
    sec = qcolor_hex(raw["secondary"])
    dg = qcolor_hex(raw["danger"])
    tp = qcolor_hex(raw["text_pri"])
    ts = qcolor_hex(raw["text_sec"])
    ar, ag, ab = ac.red(), ac.green(), ac.blue()
    sr, sg, sb = sec.red(), sec.green(), sec.blue()
    ring = QColor(ar, ag, ab, 55)
    scan = QColor(ts.red(), ts.green(), ts.blue(), 18)
    bg_t = QColor(ar, ag, ab, 12)
    glow_hot = QColor(ar, ag, ab, 90)
    glow_mid = QColor(max(0, ar - 40), max(0, ag - 20), ab, 30)
    tent = QColor(ar, ag, ab, 200)
    tent_h = QColor(min(255, ar + 60), min(255, ag + 40), min(255, ab + 20), 220)
    part = QColor(min(255, ar + 80), min(255, ag + 60), min(255, ab + 40), 200)
    arc_c = QColor(sr, sg, sb, 160)
    sub = QColor(tp.red(), tp.green(), tp.blue(), int(tp.alpha() * 0.65))
    cw = QColor(255, 255, 255, 255)
    cm = QColor(min(255, ar + 120), min(255, ag + 100), min(255, ab + 80), 250)
    cout = QColor(ar, ag, ab, 160)
    chot = QColor(dg.red(), dg.green(), dg.blue(), 0)
    return ThemeKit(
        ring_outer=ring,
        scan_line=scan,
        bg_tint=bg_t,
        glow_hot=glow_hot,
        glow_mid=glow_mid,
        tentacle=tent,
        tentacle_hot=tent_h,
        particle=part,
        arc=arc_c,
        title=tp,
        subtitle=sub,
        core_white=cw,
        core_mid=cm,
        core_outer=cout,
        core_hot=chot,
        accent=ac,
        secondary=sec,
        danger=dg,
    )


def qss_botao_accent(tema: dict) -> str:
    r, g, b = hex_rgb(tema["accent"])
    return (
        f"QPushButton {{ background-color: transparent;"
        f" border: 1.5px solid rgba({r}, {g}, {b}, 140); border-radius: 34px;"
        f" min-width: 68px; max-width: 68px; min-height: 68px; max-height: 68px; }}"
        f"QPushButton:hover {{ background-color: rgba({r}, {g}, {b}, 32);"
        f" border: 1.5px solid rgba({r}, {g}, {b}, 210); }}"
        f"QPushButton:pressed {{ background-color: rgba({r}, {g}, {b}, 55); }}"
    )


def qss_botao_danger(tema: dict) -> str:
    r, g, b = hex_rgb(tema["danger"])
    return (
        f"QPushButton {{ background-color: transparent;"
        f" border: 1.5px solid rgba({r}, {g}, {b}, 130); border-radius: 34px;"
        f" min-width: 68px; max-width: 68px; min-height: 68px; max-height: 68px; }}"
        f"QPushButton:hover {{ background-color: rgba({r}, {g}, {b}, 30);"
        f" border: 1.5px solid rgba({r}, {g}, {b}, 210); }}"
        f"QPushButton:pressed {{ background-color: rgba({r}, {g}, {b}, 55); }}"
    )


def qss_botao_muted(tema: dict) -> str:
    r, g, b = hex_rgb(tema["danger"])
    return (
        f"QPushButton {{ background-color: transparent;"
        f" border: 1.5px solid rgba({r}, {g}, {b}, 165); border-radius: 34px;"
        f" min-width: 68px; max-width: 68px; min-height: 68px; max-height: 68px; }}"
        f"QPushButton:hover {{ background-color: rgba({r}, {g}, {b}, 38);"
        f" border: 1.5px solid rgba({r}, {g}, {b}, 230); }}"
    )


def lista_temas() -> tuple[str, ...]:
    return tuple(TEMAS_CORE.keys())
