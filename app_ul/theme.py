from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QColor


TEMAS_CORE = {
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
