import sys
import math

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QRadialGradient,
    QBrush,
    QFont,
    QFontMetrics,
    QIcon,
    QPixmap,
    QPainterPath,
)
from PyQt6.QtCore import QTimer, Qt, QPointF, QRectF, QSize
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray


falando = False
intensidade_global = 0.1


def falar_on(vol: float = 1.0):
    global falando, intensidade_global
    falando = True
    intensidade_global = max(0.2, min(1.0, vol))


def falar_off():
    global falando, intensidade_global
    falando = False
    intensidade_global = 0.1


C_GOLD = QColor(255, 200, 60)
C_ORANGE_HOT = QColor(255, 80, 0, 200)
C_RING_OUTER = QColor(255, 180, 0, 55)
C_SCAN_LINE = QColor(255, 220, 80, 18)
C_BG_TINT = QColor(255, 140, 20, 12)


SVG_MIC_ON = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ffcc00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
  <line x1="12" y1="19" x2="12" y2="23"/>
  <line x1="8" y1="23" x2="16" y2="23"/>
</svg>
"""

SVG_MIC_OFF = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ff4d4d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="1" y1="1" x2="23" y2="23" stroke="#ff4d4d"/>
  <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V5a3 3 0 0 0-5.94-.6"/>
  <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/>
  <line x1="12" y1="19" x2="12" y2="23"/>
  <line x1="8" y1="23" x2="16" y2="23"/>
</svg>
"""

SVG_PANEL = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ffcc00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="7" height="7"/>
  <rect x="14" y="3" width="7" height="7"/>
  <rect x="14" y="14" width="7" height="7"/>
  <rect x="3" y="14" width="7" height="7"/>
</svg>
"""

SVG_POWER = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ff4d4d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>
  <line x1="12" y1="2" x2="12" y2="12"/>
</svg>
"""


def _svg_to_icon(svg_bytes: bytes, size: int = 28) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class JarvisUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnBottomHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(1200, 900)
        self._centralizar()

        self.tempo_vivido = 0.0
        self.intensidade_interna = 0.0
        self.is_muted = False
        self._drag_pos = None
        self._painel_aberto = None

        self._build_hud()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        self._timer.start(16)

    def _centralizar(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _build_hud(self):
        self._hud = QFrame(self)
        self._hud.setObjectName("HudBar")
        self._hud.setFixedSize(310, 90)
        self._hud.setStyleSheet("QFrame#HudBar { background: transparent; }")

        layout = QHBoxLayout(self._hud)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        style_gold = """
            QPushButton {
                background-color: rgba(18, 14, 0, 210);
                border: 1.5px solid rgba(255, 200, 0, 100);
                border-radius: 34px;
                min-width: 68px; max-width: 68px;
                min-height: 68px; max-height: 68px;
            }
            QPushButton:hover {
                background-color: rgba(255, 200, 0, 50);
                border: 2px solid rgba(255, 200, 0, 200);
            }
            QPushButton:pressed {
                background-color: rgba(255, 200, 0, 80);
            }
        """

        style_red = """
            QPushButton {
                background-color: rgba(18, 14, 0, 210);
                border: 1.5px solid rgba(255, 77, 77, 120);
                border-radius: 34px;
                min-width: 68px; max-width: 68px;
                min-height: 68px; max-height: 68px;
            }
            QPushButton:hover {
                background-color: rgba(255, 77, 77, 40);
                border: 2px solid rgba(255, 77, 77, 200);
            }
            QPushButton:pressed {
                background-color: rgba(255, 77, 77, 80);
            }
        """

        self.btn_mute = QPushButton()
        self.btn_code = QPushButton()
        self.btn_off = QPushButton()

        self.btn_mute.setIcon(_svg_to_icon(SVG_MIC_ON, 28))
        self.btn_mute.setIconSize(QSize(28, 28))
        self.btn_code.setIcon(_svg_to_icon(SVG_PANEL, 26))
        self.btn_code.setIconSize(QSize(26, 26))
        self.btn_off.setIcon(_svg_to_icon(SVG_POWER, 26))
        self.btn_off.setIconSize(QSize(26, 26))

        self.btn_mute.setStyleSheet(style_gold)
        self.btn_code.setStyleSheet(style_gold)
        self.btn_off.setStyleSheet(style_red)

        self.btn_mute.setToolTip("Mutar / Desmutar microfone")
        self.btn_code.setToolTip("Abrir Painel J.A.R.V.I.S")
        self.btn_off.setToolTip("Encerrar sistema")

        self.btn_mute.clicked.connect(self._toggle_mute)
        self.btn_code.clicked.connect(self._abrir_painel)
        self.btn_off.clicked.connect(QApplication.quit)

        for btn in [self.btn_mute, self.btn_code, self.btn_off]:
            layout.addWidget(btn)

    def _toggle_mute(self):
        self.is_muted = not self.is_muted

        if self.is_muted:
            self.btn_mute.setIcon(_svg_to_icon(SVG_MIC_OFF, 28))
            self.btn_mute.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 77, 77, 30);
                    border: 1.5px solid rgba(255, 77, 77, 150);
                    border-radius: 34px;
                    min-width: 68px; max-width: 68px;
                    min-height: 68px; max-height: 68px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 77, 77, 70);
                    border: 2px solid #ff6060;
                }
            """)
            print("[SISTEMA] Microfone MUTADO")
        else:
            self.btn_mute.setIcon(_svg_to_icon(SVG_MIC_ON, 28))
            self.btn_mute.setStyleSheet("""
                QPushButton {
                    background-color: rgba(18, 14, 0, 210);
                    border: 1.5px solid rgba(255, 200, 0, 100);
                    border-radius: 34px;
                    min-width: 68px; max-width: 68px;
                    min-height: 68px; max-height: 68px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 200, 0, 50);
                    border: 2px solid rgba(255, 200, 0, 200);
                }
            """)
            print("[SISTEMA] Microfone ATIVO")

    def _abrir_painel(self):
        if self._painel_aberto is not None and self._painel_aberto.isVisible():
            self._painel_aberto.raise_()
            self._painel_aberto.activateWindow()
            return
        try:
            from painel import PainelCore

            self._painel_aberto = PainelCore()
            self._painel_aberto.show()
        except Exception as e:
            print(f"[SISTEMA] Falha ao abrir painel: {e}")

    def _update_frame(self):
        global falando, intensidade_global
        alvo = intensidade_global if falando else 0.1
        vel = 0.22 if alvo > self.intensidade_interna else 0.055
        self.intensidade_interna += (alvo - self.intensidade_interna) * vel
        speed = 0.28 + self.intensidade_interna * 1.6
        self.tempo_vivido += 0.05 * speed
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cx = self.width() // 2
        cy = int(self.height() // 2.15)
        iv = self.intensidade_interna
        t = self.tempo_vivido

        ang_base = math.radians((t * 10) % 360)
        r_sol = 88 + iv * 24
        r_anel1 = r_sol * 1.65
        r_anel2 = r_sol * 2.60
        r_anel3 = r_sol * 3.40

        bg = QRadialGradient(cx, cy, r_anel3 * 1.1)
        bg.setColorAt(0, C_BG_TINT)
        bg.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawEllipse(
            int(cx - r_anel3 * 1.1),
            int(cy - r_anel3 * 1.1),
            int(r_anel3 * 2.2),
            int(r_anel3 * 2.2),
        )

        self._draw_scan_lines(painter, cx, cy, r_anel3)
        self._draw_rings(painter, cx, cy, r_anel1, r_anel2, r_anel3, t, iv)

        glow_outer = QRadialGradient(cx, cy, r_sol * 4.0)
        glow_outer.setColorAt(0, QColor(255, 80, 0, int(90 + iv * 60)))
        glow_outer.setColorAt(0.4, QColor(255, 50, 0, int(30 + iv * 20)))
        glow_outer.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow_outer))
        r4 = r_sol * 4
        painter.drawEllipse(int(cx - r4), int(cy - r4), int(r4 * 2), int(r4 * 2))

        if iv > 0.04:
            self._draw_tentacles(painter, cx, cy, r_sol, ang_base, t, iv)

        self._draw_sun(painter, cx, cy, r_sol, iv)
        self._draw_particles(painter, cx, cy, r_sol, r_anel2, ang_base, iv)
        self._draw_arc_ring(painter, cx, cy, r_anel1, t)

        y_texto = cy + r_anel2 + 44
        self._draw_text(painter, cx, y_texto, iv)

        hud_y = int(y_texto + 34)
        self._hud.move(int(cx - self._hud.width() // 2), hud_y)

    def _draw_scan_lines(self, p, cx, cy, r):
        pen = QPen(C_SCAN_LINE, 1.0)
        p.setPen(pen)
        y0, y1 = int(cy - r), int(cy + r)
        for y in range(y0, y1, 14):
            dx = math.sqrt(max(0, r * r - (y - cy) ** 2))
            p.drawLine(int(cx - dx), y, int(cx + dx), y)

    def _draw_rings(self, p, cx, cy, r1, r2, r3, t, iv):
        pen = QPen(C_RING_OUTER, 1.2)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 8])
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(cx, cy)
        p.rotate(math.degrees(t * 0.18))
        p.drawEllipse(QPointF(0, 0), r3, r3)
        p.restore()

        alpha_mid = int(50 + iv * 80)
        p.setPen(QPen(QColor(255, 200, 50, alpha_mid), 1.0))
        p.drawEllipse(QPointF(cx, cy), r2, r2)

        alpha_in = int(80 + iv * 100)
        pen3 = QPen(QColor(255, 220, 80, alpha_in), 1.5)
        pen3.setStyle(Qt.PenStyle.DotLine)
        p.setPen(pen3)
        p.save()
        p.translate(cx, cy)
        p.rotate(-math.degrees(t * 0.35))
        p.drawEllipse(QPointF(0, 0), r1, r1)
        p.restore()

        p.setBrush(QBrush(QColor(255, 200, 60, alpha_mid + 40)))
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(4):
            ang = math.radians(i * 90 + math.degrees(t * 0.22))
            p.drawEllipse(
                QPointF(cx + math.cos(ang) * r2, cy + math.sin(ang) * r2), 4, 4
            )

    def _draw_sun(self, p, cx, cy, r, iv):
        halo = QRadialGradient(cx, cy, r * 1.5)
        halo.setColorAt(0, QColor(255, 180, 40, int(100 + iv * 80)))
        halo.setColorAt(1, QColor(255, 80, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(halo))
        p.drawEllipse(QPointF(cx, cy), r * 1.5, r * 1.5)

        sun = QRadialGradient(cx - r * 0.12, cy - r * 0.12, r)
        sun.setColorAt(0.00, QColor(255, 255, 255, 255))
        sun.setColorAt(0.15, QColor(255, 240, 180, 250))
        sun.setColorAt(0.40, QColor(255, 160, 30, 220))
        sun.setColorAt(0.70, QColor(255, 80, 0, 160))
        sun.setColorAt(1.00, QColor(200, 30, 0, 0))
        p.setBrush(QBrush(sun))
        p.drawEllipse(QPointF(cx, cy), r, r)

        core = QRadialGradient(cx, cy, r * 0.18)
        core.setColorAt(0, QColor(255, 255, 255, 255))
        core.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(core))
        p.drawEllipse(QPointF(cx, cy), r * 0.18, r * 0.18)

    def _draw_tentacles(self, p, cx, cy, r_sol, ang_base, t, iv):
        for i in range(12):
            ang = ang_base + math.radians(i * (360 / 12))
            dist = 180 + math.sin(t * 1.4 + i * 0.9) * 70 + iv * 50 + (i % 3) * 20
            alpha = int(40 + iv * 60 + math.sin(t + i) * 20)
            width = 1.2 + iv * 1.8 - (i % 3) * 0.3
            p.setPen(QPen(QColor(255, 140 + i * 8, 20, max(20, alpha)), width))
            self._draw_tentacle(p, cx, cy, r_sol, ang, i, t, dist)

    def _draw_tentacle(self, p, cx, cy, r_sol, angle, idx, t, dist):
        perp = angle + math.pi / 2.8
        onda = 75 + math.cos(t * 1.1 + idx) * 45
        sx = cx + math.cos(angle) * (r_sol * 0.78)
        sy = cy + math.sin(angle) * (r_sol * 0.78)
        ex = cx + math.cos(angle) * dist
        ey = cy + math.sin(angle) * dist
        c1x = sx + math.cos(angle) * 55 + math.cos(perp) * onda
        c1y = sy + math.sin(angle) * 55 + math.sin(perp) * onda
        c2x = ex - math.cos(angle) * 55 - math.cos(perp) * onda
        c2y = ey - math.sin(angle) * 55 - math.sin(perp) * onda
        path = QPainterPath()
        path.moveTo(QPointF(sx, sy))
        path.cubicTo(QPointF(c1x, c1y), QPointF(c2x, c2y), QPointF(ex, ey))
        p.strokePath(path, p.pen())

    def _draw_particles(self, p, cx, cy, r_sol, r_max, ang_base, iv):
        for num, r_fac, speed_fac, size, base_alpha in [
            (22, 1.25, -1.5, 3, 200),
            (16, 2.00, 1.0, 2, 160),
            (10, 2.80, -0.6, 4, 130),
        ]:
            r_orbit = r_sol * r_fac
            for i in range(num):
                ang = ang_base * speed_fac + math.radians(i * 360 / num)
                px_ = cx + math.cos(ang) * r_orbit
                py_ = cy + math.sin(ang) * r_orbit
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(255, 200, 100, int(base_alpha + iv * 55))))
                p.drawEllipse(QPointF(px_, py_), size, size)

    def _draw_arc_ring(self, p, cx, cy, r, t):
        num_seg = 24
        gap_deg = 4.0
        seg_deg = (360 / num_seg) - gap_deg
        offset = math.degrees(t * 0.55)
        p.setPen(
            QPen(
                QColor(255, 160, 30, 160),
                2.5,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        p.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        for i in range(num_seg):
            start_deg = i * (360 / num_seg) + offset
            p.drawArc(rect, int(start_deg * 16), int(seg_deg * 16))

    def _draw_text(self, p, cx, y, iv):
        alpha = int(130 + iv * 125)

        fnt = QFont("Segoe UI", 19, QFont.Weight.Bold)
        fnt.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 7)
        p.setFont(fnt)
        p.setPen(QPen(QColor(255, 200, 0, alpha)))
        texto = "J.A.R.V.I.S"
        fm = QFontMetrics(fnt)
        larg = fm.horizontalAdvance(texto)
        p.drawText(int(cx - larg // 2), int(y), texto)

        fnt2 = QFont("Segoe UI", 10, QFont.Weight.Bold)
        fnt2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        p.setFont(fnt2)
        p.setPen(QPen(QColor(255, 180, 0, int(alpha * 0.65))))
        sub = "A C T I V E"
        fm2 = QFontMetrics(fnt2)
        larg2 = fm2.horizontalAdvance(sub)
        p.drawText(int(cx - larg2 // 2), int(y + 22), sub)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = JarvisUI()
    janela.show()

    def _sim():
        global falando, intensidade_global
        falando = not falando
        intensidade_global = 0.85 if falando else 0.1
        QTimer.singleShot(2800, _sim)

    QTimer.singleShot(500, _sim)
    sys.exit(app.exec())
