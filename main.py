#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kreuz-Solitär - vollständige Kivy-Version.
Läuft unter Windows, Pydroid 3 und als Android-APK.
"""
import json
import math
import os
import time

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rectangle, Triangle
from kivy.utils import get_color_from_hex, platform

DATEI = "solitaer_partien.json"
BG, BG2 = "#2c3e50", "#34495e"

if platform != "android":
    Window.size = (360, 640)
Window.clearcolor = get_color_from_hex(BG)

# ---------------------------------------------------------------- Icons
def _icon_down(c, x, y, s):
    Triangle(points=[x, y + s, x + s, y + s, x + s / 2.0, y])

def _icon_right(c, x, y, s):
    Triangle(points=[x, y, x, y + s, x + s, y + s / 2.0])

def _icon_left(c, x, y, s):
    Triangle(points=[x + s, y, x + s, y + s, x, y + s / 2.0])

def _icon_rot(c, x, y, s):
    cx, cy, r = x + s / 2.0, y + s / 2.0, s * 0.42
    Line(circle=(cx, cy, r, 30, 300), width=2)
    a = math.radians(300)
    px, py = cx + r * math.cos(a), cy + r * math.sin(a)
    dx, dy = -math.sin(a), math.cos(a)
    nx, ny = math.cos(a), math.sin(a)
    h, w = s * 0.30, s * 0.16
    Triangle(points=[px + dx * h, py + dy * h,
                     px + nx * w, py + ny * w,
                     px - nx * w, py - ny * w])

def _icon_swap(c, x, y, s):
    y1, y2 = y + s * 0.70, y + s * 0.30
    Line(points=[x + s * 0.10, y1, x + s * 0.80, y1], width=2)
    Triangle(points=[x + s * 0.80, y1 - s * 0.16, x + s * 0.80, y1 + s * 0.16, x + s, y1])
    Line(points=[x + s * 0.20, y2, x + s * 0.90, y2], width=2)
    Triangle(points=[x + s * 0.20, y2 - s * 0.16, x + s * 0.20, y2 + s * 0.16, x, y2])

ICONS = {"down": _icon_down, "right": _icon_right, "left": _icon_left,
         "rot": _icon_rot, "swap": _icon_swap}

class IconBtn(Widget):
    def __init__(self, icon, text, hexfarbe, action, **kw):
        super().__init__(**kw)
        self.icon = icon
        self.hexfarbe = hexfarbe
        self.action = action
        self.active = True
        self._pressed = False
        self.fs_basis = dp(11)
        self.lab = Label(text=text, bold=True, font_size=dp(11), color=(1, 1, 1, 1),
                         halign="center", valign="middle")
        self.add_widget(self.lab)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def set_text(self, t):
        self.lab.text = t
        self._draw()

    def set_active(self, wert):
        if self.active != wert:
            self.active = wert
            self._draw()

    def _draw(self, *a):
        pad = dp(16)
        w = max(10, self.width - pad)
        self.lab.pos = (self.x + pad, self.y)
        self.lab.size = (w, self.height)
        fs = self.fs_basis
        for i in range(0, 4):
            if len(self.lab.text) * fs * 0.68 <= w:
                break
            fs = self.fs_basis - dp(1) * i
        self.lab.font_size = fs
        self.lab.text_size = (w, self.height)
        self.lab.color = (1, 1, 1, 1) if self.active else (0.75, 0.78, 0.80, 1)
        basis = get_color_from_hex(self.hexfarbe)
        if not self.active:
            basis = get_color_from_hex("#5d6d7e")
        elif self._pressed:
            basis = [v * 0.8 for v in basis[:3]] + [1]
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*basis)
            Rectangle(pos=self.pos, size=self.size)
            Color(*((1, 1, 1, 1) if self.active else (0.75, 0.78, 0.80, 1)))
            isz = dp(12)
            ICONS[self.icon](self.canvas.before, self.x + dp(3),
                             self.y + (self.height - isz) / 2.0, isz)

    def on_touch_down(self, t):
        if self.active and self.collide_point(*t.pos):
            self._pressed = True
            self._draw()
            return True
        return super().on_touch_down(t)

    def on_touch_up(self, t):
        if self._pressed:
            self._pressed = False
            innen = self.collide_point(*t.pos)
            self._draw()
            if innen and self.active:
                self.action()
            return True
        return super().on_touch_up(t)

# ---------------------------------------------------------------- Brett
N = None
_FLAT = [N, N, 1, 1, 1, N, N, N, N, 1, 1, 1, N, N, 1, 1, 1, 1, 1, 1, 1,
         1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, N, N, 1, 1, 1, N, N,
         N, N, 1, 1, 1, N, N]
BRETT = [_FLAT[i:i + 7] for i in range(0, 49, 7)]
RICHTUNGEN = ((0, 2), (0, -2), (2, 0), (-2, 0))

def neues_brett():
    return [row[:] for row in BRETT]

def auf_brett(y, x):
    return 0 <= y < 7 and 0 <= x < 7 and BRETT[y][x] is not None

def ziele(brett, y, x):
    if not auf_brett(y, x) or brett[y][x] != 1:
        return []
    out = []
    for dy, dx in RICHTUNGEN:
        ty, tx = y + dy, x + dx
        if auf_brett(ty, tx) and brett[y + dy // 2][x + dx // 2] == 1 and brett[ty][tx] == 0:
            out.append((ty, tx))
    return out

def hat_zuege(brett):
    return any(ziele(brett, y, x) for y in range(7) for x in range(7))

def anzahl(brett):
    return sum(1 for r in brett for c in r if c == 1)

def zug_anwenden(brett, z):
    sy, sx, ty, tx = z
    brett[sy][sx], brett[(sy + ty) // 2][(sx + tx) // 2], brett[ty][tx] = 0, 0, 1

def zug_zuruecknehmen(brett, z):
    sy, sx, ty, tx = z
    brett[sy][sx], brett[(sy + ty) // 2][(sx + tx) // 2], brett[ty][tx] = 1, 1, 0

def spiele_ab(zuege):
    b = neues_brett()
    for i, z in enumerate(zuege, 1):
        z = tuple(z)
        if len(z) != 4 or not all(isinstance(v, int) for v in z):
            raise ValueError("Zug %d: falsches Format" % i)
        if (z[2], z[3]) not in ziele(b, z[0], z[1]):
            raise ValueError("Zug %d ist regelwidrig" % i)
        zug_anwenden(b, z)
    return b

ARM_FUER_ARM = [(1,3,3,3),(2,1,2,3),(0,2,2,2),(0,4,0,2),(2,3,2,1),(2,0,2,2),(2,4,0,4),(2,6,2,4),(3,2,1,2),(0,2,2,2),(3,0,3,2),(3,2,1,2),(3,4,1,4),(0,4,2,4),(3,6,3,4),(3,4,1,4),(5,2,3,2),(4,0,4,2),(4,2,2,2),(1,2,3,2),(3,2,3,4),(4,4,2,4),(1,4,3,4),(4,6,4,4),(4,3,4,5),(6,4,4,4),(3,4,5,4),(6,2,6,4),(6,4,4,4),(4,5,4,3),(5,3,3,3)]
KREUZ_FLANKEN = [(3,1,3,3),(1,2,3,2),(1,4,1,2),(0,2,2,2),(0,4,0,2),(3,2,1,2),(0,2,2,2),(3,3,1,3),(2,1,2,3),(1,3,3,3),(2,5,2,3),(5,2,3,2),(4,0,4,2),(2,0,4,0),(3,2,5,2),(4,4,4,2),(2,3,4,3),(4,3,4,1),(4,0,4,2),(4,6,4,4),(2,6,4,6),(6,3,4,3),(4,3,4,1),(6,2,4,2),(4,1,4,3),(4,3,4,5),(6,4,4,4),(3,4,5,4),(4,6,4,4),(5,4,3,4),(3,5,3,3)]
CHAOS_WEG = [(1,3,3,3),(2,1,2,3),(0,2,2,2),(0,4,0,2),(2,3,2,1),(2,0,2,2),(2,4,0,4),(2,6,2,4),(3,2,1,2),(0,2,2,2),(3,0,3,2),(3,2,1,2),(3,4,3,2),(3,6,3,4),(3,4,1,4),(0,4,2,4),(4,2,2,2),(1,2,3,2),(4,0,4,2),(4,3,4,1),(5,4,3,4),(4,6,4,4),(6,2,4,2),(3,2,5,2),(6,4,6,2),(6,2,4,2),(4,1,4,3),(4,3,4,5),(2,4,4,4),(4,5,4,3),(5,3,3,3)]
KARO_LOESUNG = [(5,3,3,3),(4,5,4,3),(6,4,4,4),(6,2,6,4),(3,4,5,4),(6,4,4,4),(1,4,3,4),(2,6,2,4),(4,6,2,6),(2,3,2,5),(2,6,2,4),(2,1,2,3),(0,2,2,2),(0,4,0,2),(3,2,1,2),(0,2,2,2),(5,2,3,2),(4,0,4,2),(2,0,4,0),(4,3,4,1),(4,0,4,2),(2,3,2,1),(2,1,4,1),(4,1,4,3),(4,3,4,5),(4,5,2,5),(2,5,2,3),(3,3,3,1),(1,3,3,3),(3,4,3,2),(3,1,3,3)]
FEST = [("A", "A: Arm-für-Arm", ARM_FUER_ARM), ("B", "B: Kreuz-Flanken", KREUZ_FLANKEN),
        ("C", "C: Chaos-Weg", CHAOS_WEG), ("D", "D: Karo-Lösung", KARO_LOESUNG)]

class Speicher:
    def __init__(self):
        self.pfad = None
        self.warnung = ""
        self._pfad_suchen()

    @staticmethod
    def _kandidaten():
        try:
            basis = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            basis = os.getcwd()
        liste = [basis, "/storage/emulated/0/python_scripte", os.getcwd(), os.path.expanduser("~")]
        out = []
        for d in liste:
            if d and d not in out and os.path.isdir(d):
                out.append(d)
        return out

    @staticmethod
    def _beschreibbar(ordner):
        probe = os.path.join(ordner, DATEI + ".probe")
        try:
            with open(probe, "wb") as f:
                f.write(b"x")
            os.remove(probe)
            return True
        except OSError:
            return False

    def _pfad_suchen(self):
        kand = self._kandidaten()
        for d in kand:
            if os.path.isfile(os.path.join(d, DATEI)) and self._beschreibbar(d):
                self.pfad = os.path.join(d, DATEI)
                return
        for d in kand:
            if self._beschreibbar(d):
                self.pfad = os.path.join(d, DATEI)
                return
        self.warnung = "Kein beschreibbarer Ordner - Partien werden nicht gespeichert."

    def laden(self):
        leer = {"version": 1, "zuletzt": None, "partien": []}
        if not self.pfad or not os.path.isfile(self.pfad):
            return leer
        try:
            with open(self.pfad, encoding="utf-8") as f:
                roh = json.load(f)
            partien, verworfen = [], 0
            for p in roh.get("partien", []):
                try:
                    zuege = [tuple(int(v) for v in z) for z in p["zuege"]]
                    b = spiele_ab(zuege)
                    partien.append({
                        "id": str(p["id"]), "name": str(p.get("name", p["id"])),
                        "erstellt": str(p.get("erstellt", "")),
                        "zuege": [list(z) for z in zuege],
                        "fertig": not hat_zuege(b), "rest": anzahl(b),
                        "mitte": anzahl(b) == 1 and b[3][3] == 1,
                    })
                except Exception:
                    verworfen += 1
            if verworfen:
                self._sichern("%d ungültige Partie(n) verworfen, Original gesichert: " % verworfen)
            return {"version": 1, "zuletzt": roh.get("zuletzt"), "partien": partien}
        except Exception as e:
            if not self._sichern("Speicherdatei unlesbar (%s), gesichert: " % type(e).__name__):
                self.warnung = "Speicherdatei unlesbar: %s" % e
            return leer

    def _sichern(self, prefix):
        ziel = self.pfad[:-len(".json")] + ".defekt.json"
        try:
            with open(self.pfad, "rb") as f, open(ziel, "wb") as g:
                g.write(f.read())
            self.warnung = prefix + os.path.basename(ziel)
            return True
        except OSError:
            return False

    def speichern(self, daten):
        if not self.pfad:
            return False
        zeilen = ",\n".join(json.dumps(p, ensure_ascii=False, separators=(",", ":"))
                            for p in daten["partien"])
        text = '{"version":1,"zuletzt":%s,"partien":[\n%s\n]}\n' % (
            json.dumps(daten.get("zuletzt")), zeilen)
        roh = text.encode("utf-8")
        tmp = self.pfad + ".tmp"
        try:
            with open(tmp, "wb") as f:
                f.write(roh)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(tmp, self.pfad)
        except OSError:
            try:
                with open(self.pfad, "wb") as f:
                    f.write(roh)
            except OSError as e:
                self.warnung = "Speichern fehlgeschlagen: %s" % e
                return False
        return True

def flach(btn, hexfarbe):
    btn.background_normal = ""
    btn.background_down = ""
    btn.background_color = get_color_from_hex(hexfarbe)

def wrap(lab):
    lab.bind(size=lambda l, v: setattr(l, "text_size", (v[0] - dp(12), None)))

class FarbFrame(BoxLayout):
    def __init__(self, hexfarbe, **kw):
        super().__init__(**kw)
        self._c = get_color_from_hex(hexfarbe)
        self.bind(pos=self._mal, size=self._mal)

    def _mal(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._c)
            Rectangle(pos=self.pos, size=self.size)

class ListeZeile(Button):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.is_double_tap:
            self.app.flyout_oeffnen()
            return True
        return super().on_touch_down(touch)

class BrettWidget(Widget):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        if self.width < 20 or self.height < 20:
            return
        cs = min(self.width, self.height) / 7.5
        ox = self.x + (self.width - cs * 7) / 2
        oy = self.y + (self.height - cs * 7) / 2
        self.app._geo = (ox, oy, cs)
        if self.app.modus == "spielen":
            von, nach = self.app.sel, set(self.app.ziel_felder)
        elif self.app.idx < len(self.app.moves):
            sy, sx, ty, tx = self.app.moves[self.app.idx]
            von, nach = (sy, sx), {(ty, tx)}
        else:
            von, nach = None, set()
        with self.canvas:
            for y in range(7):
                for x in range(7):
                    if BRETT[y][x] is None:
                        continue
                    x1 = ox + x * cs
                    y1 = oy + (6 - y) * cs
                    x2, y2 = x1 + cs * 0.9, y1 + cs * 0.9
                    out, w = "#7f8c8d", 1
                    if (y, x) == von:
                        out, w = "#e74c3c", 3
                    elif (y, x) in nach:
                        out, w = "#2ecc71", 3
                    Color(*get_color_from_hex("#5c3a21"))
                    Ellipse(pos=(x1, y1), size=(x2 - x1, y2 - y1))
                    Color(*get_color_from_hex(out))
                    Line(circle=((x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 2), width=w)
                    if self.app.board[y][x] == 1:
                        pk = (y, x) == von
                        pad = cs * 0.15
                        Color(*get_color_from_hex("#f1c40f" if pk else "#ecf0f1"))
                        Ellipse(pos=(x1 + pad, y1 + pad),
                                size=(x2 - x1 - 2 * pad, y2 - y1 - 2 * pad))
                        Color(*get_color_from_hex("#f39c12" if pk else "#bdc3c7"))
                        Line(circle=((x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 2 - pad), width=2)

    def feld_unter(self, touch):
        ox, oy, cs = self.app._geo
        if cs <= 0:
            return None, None
        if not (ox <= touch.x < ox + cs * 7 and oy <= touch.y < oy + cs * 7):
            return None, None
        x = int((touch.x - ox) // cs)
        y = 6 - int((touch.y - oy) // cs)
        return (y, x) if auf_brett(y, x) else (None, None)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or self.app.modus != "spielen":
            return super().on_touch_down(touch)
        y, x = self.feld_unter(touch)
        if y is None:
            return super().on_touch_down(touch)
        self.app.on_klick(y, x)
        return True

class SolitaerKivyApp(App):
    title = "Kreuz-Solitär"

    def build(self):
        self.speicher = Speicher()
        self.daten = self.speicher.laden()
        self.modus = "zuschauen"
        self.spiel = None
        self.moves = []
        self.idx = 0
        self.board = neues_brett()
        self.gedreht = False
        self.sel = None
        self.ziel_felder = []
        self.flyout_offen = False
        self.eintraege = []
        self.zeilen = []
        self.auswahl = None
        self._loesch_wartet = None
        self._geo = (0, 0, 1)
        root = BoxLayout(orientation="vertical", padding=dp(5), spacing=dp(4))
        self.info = FarbFrame(BG2, orientation="vertical", size_hint_y=None, height=dp(62))
        self.phase_label = Label(text="Kreuz-Solitär", bold=True, font_size=dp(13),
                                 color=get_color_from_hex("#1abc9c"),
                                 halign="center", valign="middle")
        self.desc_label = Label(text="", font_size=dp(11),
                                color=get_color_from_hex("#ecf0f1"),
                                halign="center", valign="middle")
        wrap(self.phase_label)
        wrap(self.desc_label)
        self.info.add_widget(self.phase_label)
        self.info.add_widget(self.desc_label)
        ctrl = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        self.btn_list = IconBtn("down", "Partien", "#7f8c8d",
                                self.flyout_umschalten, size_hint_x=0.26)
        self.btn_modus = Button(text="Zuschauen", bold=True, font_size=dp(11),
                                size_hint_x=0.26)
        flach(self.btn_modus, "#16a085")
        self.btn_mirror = IconBtn("swap", "Spiegeln", "#2980b9",
                                  self.mirror_solution, size_hint_x=0.30)
        self.btn_rot = IconBtn("rot", "90°", "#8e44ad",
                               self.rotate_solution, size_hint_x=0.18)
        ctrl.add_widget(self.btn_list)
        ctrl.add_widget(self.btn_modus)
        ctrl.add_widget(Widget(size_hint_x=None, width=dp(8)))
        ctrl.add_widget(self.btn_mirror)
        ctrl.add_widget(self.btn_rot)
        self.mitte = BoxLayout()
        self.brett_w = BrettWidget(self)
        self.flyout = FarbFrame(BG2, orientation="vertical", spacing=dp(2))
        self.flyout.add_widget(Label(text="Partien", bold=True, font_size=dp(13),
                                     color=get_color_from_hex("#1abc9c"),
                                     size_hint_y=None, height=dp(26)))
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(12),
                                 scroll_type=["bars", "content"],
                                 bar_color=get_color_from_hex("#2980b9"),
                                 bar_inactive_color=get_color_from_hex("#7f8c8d"))
        self.zeilen_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(1))
        self.zeilen_grid.bind(minimum_height=self.zeilen_grid.setter("height"))
        self.scroll.add_widget(self.zeilen_grid)
        self.flyout.add_widget(self.scroll)
        knoepfe = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(4))
        self.btn_oeffnen = Button(text="Öffnen", bold=True, font_size=dp(11))
        flach(self.btn_oeffnen, "#27ae60")
        self.btn_loeschen = Button(text="Löschen", bold=True, font_size=dp(11))
        flach(self.btn_loeschen, "#c0392b")
        self.btn_schliessen = Button(text="Schließen", bold=True, font_size=dp(11))
        flach(self.btn_schliessen, "#7f8c8d")
        for b in (self.btn_oeffnen, self.btn_loeschen, self.btn_schliessen):
            knoepfe.add_widget(b)
        self.flyout.add_widget(knoepfe)
        self.pfad_label = Label(text="", font_size=dp(9),
                                color=get_color_from_hex("#bdc3c7"),
                                halign="left", valign="middle",
                                size_hint_y=None, height=dp(24))
        wrap(self.pfad_label)
        self.flyout.add_widget(self.pfad_label)
        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.btn_prev = IconBtn("left", "Zurück", "#7f8c8d", self.prev_move)
        self.btn_prev.fs_basis = dp(12)
        self.btn_reset = Button(text="Reset", bold=True, font_size=dp(12))
        flach(self.btn_reset, "#c0392b")
        self.btn_next = IconBtn("right", "Weiter", "#27ae60", self.next_move)
        self.btn_next.fs_basis = dp(12)
        for b in (self.btn_prev, self.btn_reset, self.btn_next):
            btns.add_widget(b)
        root.add_widget(self.info)
        root.add_widget(ctrl)
        root.add_widget(self.mitte)
        root.add_widget(btns)
        self.btn_modus.bind(on_release=lambda *a: self.wechsle_modus())
        self.btn_reset.bind(on_release=lambda *a: self.reset_game())
        self.btn_oeffnen.bind(on_release=lambda *a: self.flyout_oeffnen())
        self.btn_loeschen.bind(on_release=lambda *a: self.flyout_loeschen())
        self.btn_schliessen.bind(on_release=lambda *a: self.flyout_schliessen())
        self.mitte.add_widget(self.brett_w)
        self.starte()
        return root

    def starte(self):
        letzte = self.finde_eigene(self.daten.get("zuletzt"))
        if letzte and not letzte["fertig"] and letzte["zuege"]:
            self.oeffne_eigene(letzte, spielen=True, text="Letzte Partie fortgesetzt.")
        else:
            self.oeffne_fest(FEST[0])
        if self.speicher.warnung:
            self.desc_label.text = self.speicher.warnung

    def finde_eigene(self, pid):
        return next((p for p in self.daten["partien"] if p["id"] == pid), None)

    def oeffne_fest(self, eintrag, text=None):
        key, name, zuege = eintrag
        self.spiel = {"fest": True, "id": key, "name": name}
        self.moves = [tuple(z) for z in zuege]
        self.idx = 0
        self.board = neues_brett()
        self.gedreht = False
        self.modus = "zuschauen"
        self.sel, self.ziel_felder = None, []
        self.aktualisiere(text)

    def oeffne_eigene(self, p, spielen, text=None):
        self.spiel = p
        self.moves = [tuple(z) for z in p["zuege"]]
        self.gedreht = False
        self.sel, self.ziel_felder = None, []
        if spielen:
            self.modus = "spielen"
            self.idx = len(self.moves)
            self.board = spiele_ab(self.moves)
        else:
            self.modus = "zuschauen"
            self.idx = 0
            self.board = neues_brett()
            text = text or "Abspielen mit Weiter."
        self.aktualisiere(text)

    def neues_spiel(self, zuege=(), quelle=None):
        jetzt = time.localtime()
        basis = time.strftime("%Y%m%d-%H%M%S", jetzt)
        ids = {p["id"] for p in self.daten["partien"]}
        pid, n = basis, 1
        while pid in ids:
            n += 1
            pid = "%s-%d" % (basis, n)
        name = time.strftime("%d.%m. %H:%M", jetzt) + (" ab %s" % quelle if quelle else "")
        return {"id": pid, "name": name, "erstellt": time.strftime("%Y-%m-%d %H:%M:%S", jetzt),
                "zuege": [list(z) for z in zuege], "fertig": False, "rest": 0, "mitte": False}

    def wechsle_modus(self):
        self.flyout_schliessen()
        if self.modus == "spielen":
            self.modus = "zuschauen"
            self.sel, self.ziel_felder = None, []
            self.aktualisiere("Zuschauen. Die Partie bleibt gespeichert.")
        else:
            self.starte_spielen()

    def starte_spielen(self):
        k = self.idx
        kann = hat_zuege(self.board)
        if not self.spiel.get("fest") and not self.gedreht and k == len(self.moves) and kann:
            text = "Weiter in dieser Partie."
        elif k > 0 and kann:
            quelle = "%s:%d" % (self.spiel["id"] if self.spiel.get("fest") else self.spiel["name"], k)
            self.moves = list(self.moves[:k])
            self.spiel = self.neues_spiel(self.moves, quelle)
            text = "Neue Partie ab Zug %d. Du spielst weiter." % k
        else:
            self.spiel = self.neues_spiel()
            self.moves, self.idx, self.board = [], 0, neues_brett()
            text = "Neue Partie. Stein antippen, dann Ziel."
        self.modus = "spielen"
        self.gedreht = False
        self.sel, self.ziel_felder = None, []
        self.aktualisiere(text)

    def aktualisiere(self, text=None):
        n = len(self.moves)
        spielen = self.modus == "spielen"
        if spielen:
            self.phase_label.text = "Spielen · %s" % self.spiel["name"]
            standard = "Zug %d · %d Steine. Stein antippen, dann Ziel." % (self.idx, anzahl(self.board))
        else:
            self.phase_label.text = "%s · Schritt %d/%d" % (self.spiel["name"], self.idx, n)
            if self.idx > 0:
                sy, sx, ty, tx = self.moves[self.idx - 1]
                standard = "Zug: (%d,%d) -> (%d,%d)" % (sy + 1, sx + 1, ty + 1, tx + 1)
                if self.idx >= n:
                    r = anzahl(self.board)
                    standard += " · Ende: " + ("ein Stein in der Mitte" if r == 1 and self.board[3][3] == 1
                                               else "%d Stein(e)" % r)
            else:
                standard = "Bereit zum Start."
        self.desc_label.text = text or standard
        self.desc_label.color = get_color_from_hex("#ecf0f1")
        self.btn_modus.text = "Spielen" if spielen else "Zuschauen"
        flach(self.btn_modus, "#e67e22" if spielen else "#16a085")
        self.btn_reset.text = "Neu" if spielen else "Reset"
        self.btn_rot.set_active(not spielen)
        self.btn_mirror.set_active(not spielen)
        self.btn_prev.set_active(self.idx > 0)
        self.btn_next.set_active((not spielen) and self.idx < n)
        self.brett_w._draw()

    def next_move(self):
        self.flyout_schliessen()
        if self.modus != "zuschauen" or self.idx >= len(self.moves):
            return
        zug_anwenden(self.board, self.moves[self.idx])
        self.idx += 1
        self.aktualisiere()

    def prev_move(self):
        self.flyout_schliessen()
        if self.idx == 0:
            return
        if self.modus == "spielen":
            z = self.moves.pop()
            zug_zuruecknehmen(self.board, z)
            self.idx = len(self.moves)
            self.sel, self.ziel_felder = None, []
            self.aktualisiere("Zug zurückgenommen.")
            self.speichere_spiel()
        else:
            self.idx -= 1
            zug_zuruecknehmen(self.board, self.moves[self.idx])
            self.aktualisiere()

    def reset_game(self):
        self.flyout_schliessen()
        if self.modus == "spielen":
            hatte = bool(self.moves)
            self.spiel = self.neues_spiel()
            self.moves, self.idx, self.board = [], 0, neues_brett()
            self.sel, self.ziel_felder = None, []
            self.aktualisiere("Neue Partie." + (" Die vorige bleibt in der Liste." if hatte else ""))
        else:
            self.board, self.idx = neues_brett(), 0
            self.aktualisiere("Spiel zurückgesetzt.")

    def rotate_solution(self):
        self.flyout_schliessen()
        self.moves = [(sx, 6 - sy, tx, 6 - ty) for sy, sx, ty, tx in self.moves]
        self.gedreht = True
        self.board, self.idx = neues_brett(), 0
        self.aktualisiere("Um 90° gedreht.")

    def mirror_solution(self):
        self.flyout_schliessen()
        self.moves = [(sy, 6 - sx, ty, 6 - tx) for sy, sx, ty, tx in self.moves]
        self.gedreht = True
        self.board, self.idx = neues_brett(), 0
        self.aktualisiere("Gespiegelt.")

    def on_klick(self, y, x):
        if self.modus != "spielen" or self.flyout_offen:
            return
        if self.sel is not None and (y, x) in self.ziel_felder:
            self.spiele_zug((self.sel[0], self.sel[1], y, x))
            return
        text = None
        if auf_brett(y, x) and (y, x) != self.sel and self.board[y][x] == 1:
            z = ziele(self.board, y, x)
            if z:
                self.sel, self.ziel_felder = (y, x), z
            else:
                self.sel, self.ziel_felder = None, []
                text = "Dieser Stein kann nicht springen."
        else:
            self.sel, self.ziel_felder = None, []
        self.aktualisiere(text)

    def spiele_zug(self, z):
        zug_anwenden(self.board, z)
        self.moves.append(z)
        self.idx = len(self.moves)
        self.sel, self.ziel_felder = None, []
        self.aktualisiere()
        self.speichere_spiel()
        if not hat_zuege(self.board):
            self.spiel_ende()

    def spiel_ende(self):
        r = anzahl(self.board)
        if r == 1 and self.board[3][3] == 1:
            text = "Perfekt! Ein einziger Stein liegt exakt in der Mitte."
        elif r == 1:
            text = "Nur noch ein Stein, aber nicht in der Mitte."
        else:
            text = "Keine Züge mehr möglich. %d Steine übrig." % r
        self.desc_label.text = text
        self.desc_label.color = get_color_from_hex("#f1c40f")

    def speichere_spiel(self):
        s = self.spiel
        s["zuege"] = [list(z) for z in self.moves]
        s["fertig"] = not hat_zuege(self.board)
        s["rest"] = anzahl(self.board)
        s["mitte"] = s["rest"] == 1 and self.board[3][3] == 1
        vorhanden = [i for i, p in enumerate(self.daten["partien"]) if p["id"] == s["id"]]
        if not self.moves:
            for i in reversed(vorhanden):
                del self.daten["partien"][i]
            if self.daten.get("zuletzt") == s["id"]:
                self.daten["zuletzt"] = None
        else:
            if vorhanden:
                self.daten["partien"][vorhanden[0]] = s
            else:
                self.daten["partien"].append(s)
            self.daten["zuletzt"] = s["id"]
        if not self.speicher.speichern(self.daten) and self.speicher.warnung:
            self.desc_label.text = self.speicher.warnung

    def flyout_umschalten(self):
        if self.flyout_offen:
            self.flyout_schliessen()
        else:
            self.mitte.clear_widgets()
            self.mitte.add_widget(self.flyout)
            self.flyout_offen = True
            self.liste_fuellen()

    def flyout_schliessen(self):
        if not self.flyout_offen:
            return
        self._loesch_zuruecksetzen()
        self.mitte.clear_widgets()
        self.mitte.add_widget(self.brett_w)
        self.flyout_offen = False
        self.brett_w._draw()

    def liste_fuellen(self):
        self.eintraege = []
        self.zeilen = []
        self.zeilen_grid.clear_widgets()
        for key, name, zuege in FEST:
            self._zeile("[fest]  %s · %d Züge" % (name, len(zuege)), ("fest", key))
        for p in reversed(self.daten["partien"]):
            if not p["fertig"]:
                status = "läuft"
            elif p["mitte"]:
                status = "1 Stein in der Mitte"
            else:
                status = "%d Stein%s" % (p["rest"], "" if p["rest"] == 1 else "e")
            self._zeile("[eigen] %s · %d Züge · %s" % (p["name"], len(p["zuege"]), status),
                        ("eigen", p["id"]))
        aktuell = ("fest" if self.spiel.get("fest") else "eigen", self.spiel["id"])
        self.auswahl = aktuell if aktuell in self.eintraege else None
        self._zeilen_farben()
        self._loesch_zuruecksetzen()

    def _zeile(self, text, eintrag):
        z = ListeZeile(text=text, font_size=dp(12), halign="left", valign="middle",
                       size_hint_y=None, height=dp(36), color=(0, 0, 0, 1))
        z.app = self
        z.bind(on_release=lambda b, e=eintrag: self._auswahl_setzen(e))
        self.zeilen_grid.add_widget(z)
        self.eintraege.append(eintrag)
        self.zeilen.append((z, eintrag))

    def _zeilen_farben(self):
        for z, e in self.zeilen:
            sel = e == self.auswahl
            flach(z, "#2980b9" if sel else "#ecf0f1")
            z.color = (1, 1, 1, 1) if sel else (0, 0, 0, 1)

    def _auswahl_setzen(self, eintrag):
        self.auswahl = eintrag
        self._zeilen_farben()
        if not (self._loesch_wartet and eintrag[1] == self._loesch_wartet):
            self._loesch_zuruecksetzen()

    def flyout_oeffnen(self):
        a = self.auswahl
        if not a:
            return
        typ, key = a
        self.flyout_schliessen()
        if typ == "fest":
            self.oeffne_fest(next(e for e in FEST if e[0] == key))
        else:
            p = self.finde_eigene(key)
            if p:
                self.oeffne_eigene(p, spielen=not p["fertig"])

    def flyout_loeschen(self):
        a = self.auswahl
        if not a:
            self.hinweis("Erst eine Partie auswählen.")
            return
        typ, key = a
        if typ == "fest":
            self._loesch_wartet = None
            self.btn_loeschen.text = "Löschen"
            self.hinweis("Feste Beispiele können nicht gelöscht werden.")
            return
        p = self.finde_eigene(key)
        if not p:
            return
        if self._loesch_wartet != key:
            self._loesch_wartet = key
            self.btn_loeschen.text = "Sicher?"
            self.hinweis("Partie '%s' löschen? Zum Bestätigen nochmal Löschen tippen." % p["name"])
            return
        self.daten["partien"] = [q for q in self.daten["partien"] if q["id"] != key]
        if self.daten.get("zuletzt") == key:
            self.daten["zuletzt"] = None
        self.speicher.speichern(self.daten)
        if not self.spiel.get("fest") and self.spiel["id"] == key:
            self.oeffne_fest(FEST[0])
        self.liste_fuellen()
        self.hinweis("Partie '%s' gelöscht." % p["name"])

    def hinweis(self, text):
        self.pfad_label.text = text
        self.pfad_label.color = get_color_from_hex("#f1c40f")

    def _loesch_zuruecksetzen(self):
        self._loesch_wartet = None
        self.btn_loeschen.text = "Löschen"
        self.pfad_label.text = "Speicher: " + (self.speicher.pfad or "nicht verfügbar")
        self.pfad_label.color = get_color_from_hex("#bdc3c7")

if __name__ == "__main__":
    SolitaerKivyApp().run()