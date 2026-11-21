"""Live-Fenster für den simulierten mBot2: Welt von oben, Hindernisse, Bodenmarken, mBot2, Fahrweg.

    python mbot_sim_start.py PROGRAMM.py --gui            # über den Starter
    python mbot_sim_start.py PROGRAMM.py --gui --pose     # dazu die vom Programm berechnete Pose
    python mbot_sim_start.py PROGRAMM.py --gui --plot   # dazu Verläufe: Ultraschall, Drehwinkel, Räder
    python mbot_sim_start.py PROGRAMM.py --video fahrt.mp4 --bild fahrt.png   # Lauf aufzeichnen
    welt.fenster(fahrt)                                   # im eigenen Programm (fahrt läuft im Hintergrund)

Gezeichnet wird die wahre Pose (durchgezogen) und, wenn eine Funktion `pose` angegeben ist, die Pose,
die das Programm selbst berechnet (gestrichelt): So sieht man, wie die Koppelnavigation wegläuft.
Das Programm rechnet ab der Startmarke; liegt sie nicht im Ursprung der Welt (Szene mit `start`),
wird seine Pose entsprechend verschoben gezeichnet.

Bedienung im Fenster: Die Tasten a, b, m und die Pfeiltasten gelten als Tasten des CyberPi (auf
jedem System). Den mBot2 mit der linken Maustaste ziehen schiebt ihn von Hand in Fahrtrichtung, mit
gedrückter Umschalttaste dreht es ihn um die Mitte der Radachse; die Räder rollen dabei ab, Encoder
und Gyroskop messen mit (Testbetrieb, Labor 2). Ein Klick neben den mBot2 stößt ihn an: Klick links von ihm dreht ihn um 10° nach
rechts, Klick rechts um 10° nach links; das Gyroskop misst den Stoß, die Encoder nicht. Taste d
schaltet zwischen dunkler (Standard) und heller Darstellung um. Mausrad: zoomen um die Mausposition,
rechte (oder mittlere) Maustaste gedrückt halten: Ansicht verschieben; danach läuft der Ausschnitt nicht
mehr automatisch mit, bis Taste z ihn wieder freigibt.

Das Fenster läuft im Hauptthread (matplotlib verlangt das), das mBot2-Programm in einem eigenen
Thread. Das Fenster liest etwa 15-mal je Sekunde einen Schnappschuss der Welt und bremst die
Regelung nicht. Fenster schließen oder Ctrl+C: Programm beenden, Motoren aus.
"""
import logging
import math
import threading
import time
import traceback

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from _mbot_welt import TASTE_DAUER, UMRISS, US_BEREICH, US_KEGEL

BILDRATE = 15                                  # Bilder je Sekunde (auch im Video)
BILDRATE_BLIT = 30                             # im Fenster ohne Video (blitten_an): nur das Bewegte, daher schneller
SPITZE = [(0.10, 0.0), (0.05, 0.03), (0.05, -0.03)]                         # Richtung, im Umriss
RAND = 0.25                                    # m Platz um Welt und Fahrweg
STOSS = 10.0                                   # Grad je Mausklick
STOSS_ABSTAND = 0.4                            # m: weiter entfernte Klicks zählen nicht
TASTEN = {"a": "a", "b": "b", "m": "middle", "enter": "middle",
          "up": "up", "down": "down", "left": "left", "right": "right"}
NICHT_INTERAKTIV = ("agg", "pdf", "ps", "svg", "cairo", "template")
THEMA_TASTE = "d"                              # im Fenster: zwischen dunkel und hell umschalten
ANSICHT_TASTE = "z"                            # im Fenster: zurück zur automatisch mitlaufenden Ansicht
ZOOM_SCHRITT = 1.25                            # Faktor je Rastung des Mausrads
SCHRIFT, SCHRIFT_HINWEIS, LED_GROESSE = 9.5, 8.5, 11   # rechte Spalte bei voller Größe (pt)
SCHRIFT_MIN = 0.55                             # kleinster Maßstab, wenn das Fenster sehr klein ist
THEMEN = {
    "dunkel": dict(hintergrund="#1e1f22", flaeche="#25272b", text="#d8d8d8", text_schwach="#8a8f96",
                   gitter="#3a3d42", gitter_kurven="#34373c", rahmen="#5a5f66",
                   hindernis="#5f646b", hindernis_rand="#9aa0a6", band="#80858c", rad="#e6e6e6",
                   quad_an="#f2f2f2", quad_aus="#25272b", quad_rand="#c0c0c0",
                   bot="#4da3ff", bot_flaeche=(0.30, 0.64, 1.0, 0.25), berechnet="#ff6b6b", ziel="#5fd35f",
                   us="#ffb347", kollision="#ff6b6b", wahr="#bbbbbb", rechts="#c792ea",
                   anzeige="#0e0f11", anzeige_rand="#5a5f66", led_rand="#8a8f96"),
    "hell": dict(hintergrund="white", flaeche="white", text="black", text_schwach="0.4",
                 gitter="0.88", gitter_kurven="0.9", rahmen="black",
                 hindernis="0.6", hindernis_rand="0.35", band="0.45", rad="0.1",
                 quad_an="0.1", quad_aus="white", quad_rand="0.2",
                 bot="tab:blue", bot_flaeche=(0.12, 0.47, 0.71, 0.25), berechnet="tab:red", ziel="tab:green",
                 us="tab:orange", kollision="tab:red", wahr="0.3", rechts="tab:purple",
                 anzeige="0.12", anzeige_rand="0.4", led_rand="0.4"),
}
logging.getLogger("matplotlib.axes._base").setLevel(logging.ERROR)   # „Ignoring fixed y limits …“ bei aspect=equal


def _drehen(punkte, x, y, th):
    c, s = math.cos(th), math.sin(th)
    return [(x + c * px - s * py, y + s * px + c * py) for px, py in punkte]


def _grad(rad):
    return (math.degrees(rad) + 180.0) % 360.0 - 180.0


class _Spur:
    """Fahrweg: ein Punkt, wenn sich der mBot2 um mehr als 2 mm bewegt hat."""

    def __init__(self):
        self.x, self.y = [], []

    def dazu(self, x, y):
        if not self.x or math.hypot(x - self.x[-1], y - self.y[-1]) > 0.002:
            self.x.append(x)
            self.y.append(y)


class _Video:
    """MP4 mit fester Bildrate: Bilder werden nach der Uhr wiederholt oder ausgelassen, damit das
    Video so lange dauert wie der Lauf."""

    def __init__(self, pfad):
        try:
            import imageio_ffmpeg
        except ImportError:
            raise SystemExit("--video braucht das Paket imageio-ffmpeg (pip install imageio-ffmpeg)")
        self.ffmpeg, self.pfad = imageio_ffmpeg, pfad
        self.schreiber, self.n, self.groesse, self.t0 = None, 0, None, time.monotonic()

    def bild(self, fig):
        import numpy as np
        fig.canvas.draw()
        rgb = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
        h, w = rgb.shape[:2]
        if self.schreiber is None:
            self.groesse = (w - w % 2, h - h % 2)     # H.264 braucht gerade Kantenlängen
            self.schreiber = self.ffmpeg.write_frames(self.pfad, self.groesse, fps=BILDRATE, quality=7,
                                                      macro_block_size=1)
            self.schreiber.send(None)
        W, H = self.groesse
        if (w, h) != (W, H):
            # Fenster nach dem ersten Bild größer oder kleiner (Bildschirmskalierung, Maximieren):
            # ganzes Bild auf die Videogröße bringen statt es abzuschneiden, Seitenverhältnis bleibt
            from PIL import Image
            s = min(W / w, H / h)
            neu = Image.fromarray(np.ascontiguousarray(rgb)).resize((max(1, round(w * s)), max(1, round(h * s))),
                                                                  Image.LANCZOS)
            grund = tuple(int(255 * c) for c in fig.get_facecolor()[:3])
            leinwand = Image.new("RGB", (W, H), grund)
            leinwand.paste(neu, ((W - neu.width) // 2, (H - neu.height) // 2))
            rgb = np.asarray(leinwand)
        daten = np.ascontiguousarray(rgb[:H, :W]).tobytes()
        soll = int((time.monotonic() - self.t0) * BILDRATE) + 1
        while self.n < soll:
            self.schreiber.send(daten)
            self.n += 1

    def schliessen(self):
        if self.schreiber is not None:
            self.schreiber.close()
            print(f"Video: {self.pfad} ({self.n / BILDRATE:.1f} s)")


class Fenster:
    def __init__(self, welt, pose=None, titel="mBot2, simuliert", plot=False, thema="dunkel"):
        self.welt, self.pose_fn, self.plot = welt, pose, plot
        self.T = THEMEN[thema]
        self.t0 = time.monotonic()
        self.spur, self.spur_ber = _Spur(), _Spur()
        self.status, self.meldung, self.meldung_bis = "läuft", "", 0.0
        self.grenzen = None
        self.manuell = False                       # Ansicht selbst gezoomt/verschoben: nicht mehr nachführen
        self.skala = 1.0                           # Schriftmaßstab der rechten Spalte (_anordnen)
        self.ziehen = None                         # rechte Maustaste gedrückt: (x, y in Pixel, xlim, ylim)
        self.hand = None                           # mBot2 von Hand: ("schieben" | "drehen", x, y der Maus in m)
        self.hand_maus = None                      # letzte Mausposition beim Ziehen, noch nicht angewendet
        self.blit = False                          # Blitting: blitten_an()
        self.k_grenzen = [None, None, None]        # y-Bereiche der Verlaufskurven (_kurven_grenzen)
        self.k_bis = 0                             # bis hierher hat _kurven_grenzen die Werte gesehen
        self.verlauf = {"t": [], "us": [], "gyro": [], "wahr": [], "l": [], "r": []}

        for k in ("keymap.back", "keymap.forward", "keymap.save", "keymap.xscale", "keymap.yscale"):
            plt.rcParams[k] = []                   # Pfeiltasten und Buchstaben gehören dem CyberPi
        if plot:
            self.fig = plt.figure(figsize=(13, 9))
            gs = self.fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 1.05], height_ratios=[2.3, 1],
                                       wspace=0.35, hspace=0.28)
            ax = self.ax = self.fig.add_subplot(gs[0, 0:3])
            self.info = self.fig.add_subplot(gs[:, 3])
            self._kurven_anlegen([self.fig.add_subplot(gs[1, k]) for k in range(3)])
        else:
            self.fig = plt.figure(figsize=(12, 7))
            gs = self.fig.add_gridspec(1, 2, width_ratios=[3, 1], wspace=0.05)
            ax = self.ax = self.fig.add_subplot(gs[0])
            self.info = self.fig.add_subplot(gs[1])
        self.fig.canvas.manager.set_window_title(titel)
        self.info.axis("off")

        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True, color="0.88")
        ax.set_axisbelow(True)
        ax.set_xlabel("x in m")
        ax.set_ylabel("y in m")
        # Farben setzt thema_setzen() am Ende, hier nur Form und Lage
        self.p_hind = [ax.add_patch(Polygon(poly, closed=True, zorder=2)) for poly in welt.hindernisse]
        self.p_band = []
        for a, b, w in welt.marken:                # Klebeband als Rechteck der Breite w
            l = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
            nx, ny = -(b[1] - a[1]) / l * w / 2, (b[0] - a[0]) / l * w / 2
            self.p_band.append(ax.add_patch(Polygon([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                                                     (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)],
                                                    closed=True, edgecolor="none", zorder=2)))
        self.l_ziel, self.t_ziel = [], []
        for zx, zy, name in welt.ziele:
            self.l_ziel += ax.plot([zx], [zy], marker="x", markersize=10, markeredgewidth=2, zorder=3)
            if name:
                self.t_ziel.append(ax.annotate(name, (zx, zy), xytext=(6, 6), textcoords="offset points",
                                               fontsize=8, zorder=3))
        x0, y0, _ = welt.wahr()
        self.l_start, = ax.plot([x0], [y0], marker="o", markersize=5, zorder=3, label="Start")
        self.l_spur, = ax.plot([], [], "-", linewidth=1.5, zorder=4, label="Fahrweg (wahr)")
        self.p_bot = ax.add_patch(Polygon(UMRISS, closed=True, linewidth=1.5, zorder=5))
        self.p_rich = ax.add_patch(Polygon(SPITZE, closed=True, edgecolor="none", zorder=6))
        self.l_rad, = ax.plot([], [], "-", linewidth=4, solid_capstyle="butt", zorder=6)
        self.l_us, = ax.plot([], [], "-", linewidth=1, zorder=4, label="Ultraschall")
        self.l_quad = ax.scatter([], [], s=14, zorder=7, linewidths=0.6)
        if pose is not None:
            self.l_spur_ber, = ax.plot([], [], "--", linewidth=1.2, zorder=4, label="Fahrweg (berechnet)")
            self.p_ber = ax.add_patch(Polygon(UMRISS, closed=True, facecolor="none",
                                              linestyle="--", linewidth=1.3, zorder=5))
            self.p_rich_ber = ax.add_patch(Polygon(SPITZE, closed=True, facecolor="none",
                                                   linestyle="--", linewidth=1.2, zorder=6))
        self.l_ziel_leg = ax.plot([], [], "x", markeredgewidth=2, label="Ziel")[0] if welt.ziele else None
        self.p_band_leg = ax.add_patch(Polygon([(0, 0)], label="Klebeband")) if welt.marken else None

        self.t_info = self.info.text(0.0, 1.0, "", va="top", ha="left", family="monospace", fontsize=9.5,
                                     transform=self.info.transAxes)
        y_led = 0.465 if not plot else 0.40
        self.t_led = self.info.text(0.0, y_led, "LED", va="center", ha="left", family="monospace", fontsize=9.5,
                                    transform=self.info.transAxes)
        self.p_led, = self.info.plot([0.17], [y_led], "o", markersize=11, markerfacecolor="black",
                                     transform=self.info.transAxes, clip_on=False)
        self.t_anzeige = self.info.text(0.0, y_led - 0.045, "", va="top", ha="left", family="monospace",
                                        fontsize=9.5, transform=self.info.transAxes, color="white",
                                        bbox=dict(boxstyle="round"))
        self.t_hinweis = self.info.text(
            0.0, 0.02, "mBot2, linke Maustaste:\n  auf mBot2 ziehen: schieben\n  dazu Umschalt: drehen\n"
            "  Klick daneben: Stoß 10°\nAnsicht:\n  rechte Maustaste halten: verschieben\n  Mausrad: zoomen\n"
            "  %s: automatisch\n  %s: hell / dunkel\nCyberPi: Tasten a b, Pfeile,\n  m (Joystick Mitte)\n"
            "Fenster schließen: Ende" % (ANSICHT_TASTE, THEMA_TASTE),
            va="bottom", ha="left", fontsize=8.5, transform=self.info.transAxes)
        self.thema_setzen(thema)
        self.fig.canvas.mpl_connect("key_press_event", self._taste)
        self.fig.canvas.mpl_connect("button_press_event", self._klick)
        self.fig.canvas.mpl_connect("button_release_event", self._loslassen)
        self.fig.canvas.mpl_connect("motion_notify_event", self._bewegen)
        self.fig.canvas.mpl_connect("scroll_event", self._rad)

    def thema_setzen(self, thema):
        """Farben für 'dunkel' oder 'hell' setzen; geht auch im laufenden Fenster."""
        self.thema, T = thema, THEMEN[thema]
        self.T = T
        self.fig.set_facecolor(T["hintergrund"])
        achsen = [self.ax] + (list(self.k_achsen) if self.plot else [])
        for a in achsen:
            a.set_facecolor(T["flaeche"])
            a.tick_params(colors=T["text"], which="both")
            a.xaxis.label.set_color(T["text"])
            a.yaxis.label.set_color(T["text"])
            a.title.set_color(T["text"])
            for rand in a.spines.values():
                rand.set_edgecolor(T["rahmen"])
        self.info.set_facecolor(T["hintergrund"])
        self.ax.grid(True, color=T["gitter"])
        for p in self.p_hind:
            p.set_facecolor(T["hindernis"])
            p.set_edgecolor(T["hindernis_rand"])
        for p in self.p_band + ([self.p_band_leg] if self.p_band_leg is not None else []):
            p.set_facecolor(T["band"])
        for l in self.l_ziel + ([self.l_ziel_leg] if self.l_ziel_leg is not None else []):
            l.set_color(T["ziel"])
        for t in self.t_ziel:
            t.set_color(T["ziel"])
        for l in (self.l_start, self.l_spur):
            l.set_color(T["bot"])
        self.p_bot.set_facecolor(T["bot_flaeche"])
        self.p_bot.set_edgecolor(T["bot"])
        self.p_rich.set_facecolor(T["bot"])
        self.l_rad.set_color(T["rad"])
        self.l_us.set_color(T["us"])
        self.l_quad.set_edgecolors(T["quad_rand"])
        if self.pose_fn is not None:
            self.l_spur_ber.set_color(T["berechnet"])
            self.p_ber.set_edgecolor(T["berechnet"])
            self.p_rich_ber.set_edgecolor(T["berechnet"])
        leg = self.ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, fontsize=8,
                             frameon=False)      # über der Welt, damit sie nichts verdeckt; neu, damit die Farben stimmen
        for t in leg.get_texts():
            t.set_color(T["text"])
        for t in (self.t_info, self.t_led):
            t.set_color(T["text"])
        self.t_hinweis.set_color(T["text_schwach"])
        self.p_led.set_markeredgecolor(T["led_rand"])
        self.t_anzeige.get_bbox_patch().set_facecolor(T["anzeige"])
        self.t_anzeige.get_bbox_patch().set_edgecolor(T["anzeige_rand"])
        if self.plot:
            a_us, a_rot, a_rad = self.k_achsen
            self.k_us.set_color(T["us"])
            self.k_gyro.set_color(T["ziel"])
            self.k_wahr.set_color(T["wahr"])
            self.k_l.set_color(T["bot"])
            self.k_r.set_color(T["rechts"])
            for a in self.k_achsen:
                a.grid(True, color=T["gitter_kurven"])
            for a in (a_rot, a_rad):
                leg = a.legend(fontsize=7, loc="upper left", facecolor=T["flaeche"], edgecolor=T["rahmen"])
                for t in leg.get_texts():
                    t.set_color(T["text"])

    def _kurven_anlegen(self, achsen):
        a_us, a_rot, a_rad = self.k_achsen = achsen
        self.k_us, = a_us.plot([], [])
        a_us.set_title("Ultraschall (wahrer Abstand, %d = kein Echo)" % round(100 * US_BEREICH[1]), fontsize=9)
        a_us.set_ylabel("cm")
        self.k_gyro, = a_rot.plot([], [], label="Gyroskop")
        self.k_wahr, = a_rot.plot([], [], linestyle=":", label="wahr")
        a_rot.set_title("Drehwinkel", fontsize=9)
        a_rot.set_ylabel("Grad")
        self.k_l, = a_rad.plot([], [], label="links")
        self.k_r, = a_rad.plot([], [], label="rechts")
        a_rad.set_title("Raddrehzahl", fontsize=9)
        a_rad.set_ylabel("U/min")
        for a in achsen:                           # Farben, Gitter und Legenden: thema_setzen()
            a.set_xlabel("Zeit in s", fontsize=8)
            a.tick_params(labelsize=8)

    # ---------------------------------------------------------------- Bedienung
    def _taste(self, ev):
        if ev.key == THEMA_TASTE:
            self.thema_setzen("hell" if self.thema == "dunkel" else "dunkel")
            return
        if ev.key == ANSICHT_TASTE:
            self.manuell, self._gesetzt = False, False     # beim nächsten Bild wieder den ganzen Ausschnitt
            return
        name = TASTEN.get(ev.key)
        if name:
            with self.welt.lock:
                self.welt.tasten_bis[name] = time.monotonic() + TASTE_DAUER

    def _klick(self, ev):
        """Klick neben den mBot2: Stoß. Nicht, während Zoom oder Verschieben der Werkzeugleiste aktiv ist."""
        leiste = getattr(self.fig.canvas, "toolbar", None)
        if ev.inaxes is self.ax and ev.button in (2, 3):         # mittlere/rechte Taste: Ansicht verschieben
            self.ziehen = (ev.x, ev.y, self.ax.get_xlim(), self.ax.get_ylim())
            return
        if ev.inaxes is not self.ax or ev.button != 1 or (leiste is not None and getattr(leiste, "mode", "")):
            return
        if self.p_bot.contains(ev)[0]:                          # auf dem mBot2: von Hand schieben oder drehen
            art = "drehen" if ev.key == "shift" else "schieben"
            self.hand, self.hand_maus = (art, ev.xdata, ev.ydata), None
            self.meldung, self.meldung_bis = "von Hand " + art, time.monotonic() + 1.0
            return
        x, y, th = self.welt.wahr()
        dx, dy = ev.xdata - x, ev.ydata - y
        if math.hypot(dx, dy) > STOSS_ABSTAND:
            return
        links = math.cos(th) * dy - math.sin(th) * dx > 0       # Klick links vom mBot2
        self.stossen(-STOSS if links else STOSS)

    def _bewegen(self, ev):
        """Linke Maustaste auf dem mBot2: ihn von Hand bewegen. Rechte Maustaste: die Welt verschieben."""
        if self.hand is not None:
            if ev.xdata is not None and ev.inaxes is self.ax:
                self.hand_maus = (ev.xdata, ev.ydata)          # angewendet einmal je Bild (_hand_anwenden)
            return
        if self.ziehen is None or ev.x is None:
            return
        x0, y0, (xa, xb), (ya, yb) = self.ziehen
        bb = self.ax.bbox
        dx = (ev.x - x0) * (xb - xa) / bb.width
        dy = (ev.y - y0) * (yb - ya) / bb.height
        self.ax.set_xlim(xa - dx, xb - dx)
        self.ax.set_ylim(ya - dy, yb - dy)
        self.manuell = True

    def _hand_anwenden(self):
        """Den mBot2 bis zur letzten Mausposition bewegen. Einmal je Bild statt bei jedem Mausereignis:
        sonst stauen sich die Ereignisse, während das Fenster zeichnet, und der mBot2 läuft hinterher."""
        if self.hand is None or self.hand_maus is None:
            return
        art, mx, my = self.hand
        nx, ny = self.hand_maus
        if (nx, ny) == (mx, my):
            return
        x, y, th = self.welt.wahr()
        if art == "schieben":                                  # nur in Fahrtrichtung: Räder rollen, rutschen nicht
            self.welt.schieben(strecke=(nx - mx) * math.cos(th) + (ny - my) * math.sin(th))
        elif math.hypot(nx - x, ny - y) > 0.01:                # um die Mitte der Radachse, der gegriffene Punkt folgt der Maus
            dw = math.atan2(ny - y, nx - x) - math.atan2(my - y, mx - x)
            self.welt.schieben(winkel=math.degrees((dw + math.pi) % (2 * math.pi) - math.pi))
        else:
            return                                             # zu nah an der Drehachse: Winkel unsicher, Bezug behalten
        self.hand = (art, nx, ny)
        self.meldung_bis = time.monotonic() + 1.0

    def _loslassen(self, ev):
        self._hand_anwenden()
        self.ziehen = self.hand = self.hand_maus = None
        leiste = getattr(self.fig.canvas, "toolbar", None)
        if ev.inaxes is self.ax and leiste is not None and getattr(leiste, "mode", ""):
            self.manuell = True                    # mit Lupe oder Kreuz der Werkzeugleiste gezoomt/verschoben

    def _rad(self, ev):
        """Mausrad: um die Mausposition zoomen, nach oben hinein, nach unten heraus."""
        if ev.inaxes is not self.ax or ev.xdata is None:
            return
        f = 1 / ZOOM_SCHRITT if ev.button == "up" else ZOOM_SCHRITT
        (xa, xb), (ya, yb) = self.ax.get_xlim(), self.ax.get_ylim()
        cx, cy = ev.xdata, ev.ydata
        self.ax.set_xlim(cx - (cx - xa) * f, cx + (xb - cx) * f)
        self.ax.set_ylim(cy - (cy - ya) * f, cy + (yb - cy) * f)
        self.manuell = True

    def stossen(self, winkel):
        self.welt.stossen(winkel)
        self.meldung = "Stoß: %+.0f° (%s)" % (winkel, "nach links" if winkel > 0 else "nach rechts")
        self.meldung_bis = time.monotonic() + 2.0

    # ---------------------------------------------------------------- Zeichnen
    def zeichnen(self):
        w = self.welt
        self._hand_anwenden()
        echo = w.echo()                            # ruft weiter(): die Welt läuft auch, während das Programm schläft
        quad = w.auf_linie()
        with w.lock:
            x, y, th = w.pose
            rpm_l, rpm_r = w.rpm["EM1"], -w.rpm["EM2"]
            rot, led = w.rotation["z"], w.led
            labels = [w.labels[k] for k in sorted(w.labels)]
            zeilen = list(w.zeilen[-6:])
            us, quad_geo, b, r, start = w.us_pos, w.quad, w.b, w.r_true, w.start
            kollidiert = w.kollidiert
        t = time.monotonic() - self.t0
        self.spur.dazu(x, y)
        self.l_spur.set_data(self.spur.x, self.spur.y)
        self.p_bot.set_xy(_drehen(UMRISS, x, y, th))
        self.p_bot.set_edgecolor(self.T["kollision"] if kollidiert else self.T["bot"])
        self.p_bot.set_linewidth(3 if kollidiert else 1.5)
        self.p_rich.set_xy(_drehen(SPITZE, x, y, th))
        rad = _drehen([(-r, b / 2), (r, b / 2), (float("nan"), 0), (-r, -b / 2), (r, -b / 2)], x, y, th)
        self.l_rad.set_data(*zip(*rad))

        weit = echo < US_BEREICH[1]
        d = echo if weit else US_BEREICH[1]        # ohne Echo: der ganze Messbereich, blass
        ux, uy = _drehen([us], x, y, th)[0]
        kegel = []
        for k in (-1, 1):
            a = th + math.radians(US_KEGEL * k)
            kegel += [(ux, uy), (ux + d * math.cos(a), uy + d * math.sin(a)), (float("nan"), float("nan"))]
        if weit:
            kegel += [(ux, uy), (ux + d * math.cos(th), uy + d * math.sin(th))]
        self.l_us.set_data(*zip(*kegel))
        self.l_us.set_alpha(1.0 if weit else 0.35)

        punkte = _drehen([(quad_geo[0], q) for q in quad_geo[1]], x, y, th)
        self.l_quad.set_offsets(punkte)
        self.l_quad.set_facecolors([self.T["quad_an"] if an else self.T["quad_aus"] for an in quad])

        zeilen_ber = ""
        if self.pose_fn is not None:
            p = None
            try:
                p = self.pose_fn()
            except Exception:
                pass
            if p is not None:
                xp, yp, thp = (float(v) for v in p)              # im Rahmen der Startmarke
                (xb, yb), thb = _drehen([(xp, yp)], *start)[0], start[2] + thp
                self.spur_ber.dazu(xb, yb)
                self.l_spur_ber.set_data(self.spur_ber.x, self.spur_ber.y)
                self.p_ber.set_xy(_drehen(UMRISS, xb, yb, thb))
                self.p_rich_ber.set_xy(_drehen(SPITZE, xb, yb, thb))
                zeilen_ber = ("\nberechnet\n  x %7.1f cm\n  y %7.1f cm\n  θ %7.1f°\n  Abstand zur wahren\n  Pose %5.1f cm\n"
                              % (100 * xp, 100 * yp, _grad(thp), 100 * math.hypot(xb - x, yb - y)))
            else:
                zeilen_ber = "\nberechnet: keine Pose\n"

        meldung = self.meldung if time.monotonic() < self.meldung_bis else ""
        if kollidiert:
            meldung = "Kollision: Räder drehen durch"
        self.t_info.set_text(
            "t %8.1f s   %s\n%s\nwahr\n  x %7.1f cm\n  y %7.1f cm\n  θ %7.1f°\n%s\nGyro      %7.1f°\n"
            "Räder L %5.0f  R %5.0f U/min\nUltraschall %s\n"
            % (t, self.status, meldung, 100 * x, 100 * y, _grad(th), zeilen_ber, rot, rpm_l, rpm_r,
               "%5.1f cm" % (100 * echo) if weit else "  kein Echo"))
        self.p_led.set_markerfacecolor(tuple(max(0, min(255, c)) / 255 for c in led))
        anzeige = labels + zeilen
        self.t_anzeige.set_text("CyberPi\n" + ("\n".join(anzeige) if anzeige else ""))
        self._anordnen()
        self._ausschnitt([x] + ([self.spur_ber.x[-1]] if self.spur_ber.x else []),
                         [y] + ([self.spur_ber.y[-1]] if self.spur_ber.y else []))

        if self.plot:
            v = self.verlauf
            for k, wert in (("t", t), ("us", 100 * min(echo, US_BEREICH[1])), ("gyro", rot),   # wie der Sensor: 300 ohne Echo
                            ("wahr", math.degrees(th - start[2])), ("l", rpm_l), ("r", rpm_r)):
                v[k].append(wert)
            self.k_us.set_data(v["t"], v["us"])
            self.k_gyro.set_data(v["t"], v["gyro"])
            self.k_wahr.set_data(v["t"], v["wahr"])
            self.k_l.set_data(v["t"], v["l"])
            self.k_r.set_data(v["t"], v["r"])
            if self.hand is None or self.k_grenzen[0] is None:
                self._kurven_grenzen(t)        # beim Ziehen nicht: jedes Wachsen zeichnet alles neu und ruckelt

    def _kurven_grenzen(self, t):
        """Achsen der Verlaufskurven in Stufen erweitern, nie verkleinern: jede Änderung der Achsen
        zeichnet das ganze Fenster neu (teuer), sonst zeichnet das Blitting nur die Kurven."""
        v, g = self.verlauf, self.k_grenzen
        k0, self.k_bis = self.k_bis, len(v["t"])   # alle Werte seit dem letzten Mal (beim Ziehen ausgesetzt)
        if t > self.k_achsen[0].get_xlim()[1] or g[0] is None:
            for a in self.k_achsen:
                a.set_xlim(0, max(10.0, math.ceil(t * 1.5 / 10) * 10))
        u = max(v["us"][k0:])                          # Abstand ab 0, sonst wirkt ein ruhiger Wert wie Rauschen
        if g[0] is None or u > g[0][1]:
            g[0] = (0.0, max(50.0, 1.2 * u))
            self.k_achsen[0].set_ylim(*g[0])
        for i, werte, mindest in ((1, v["gyro"][k0:] + v["wahr"][k0:], 10.0), (2, v["l"][k0:] + v["r"][k0:], 10.0)):
            lo, hi = min(werte), max(werte)
            if g[i] is None:                       # Mindesthöhe: sonst zeigt ein ruhendes Signal Rauschen im µ-Bereich
                m = (lo + hi) / 2
                g[i] = (min(lo, m - mindest / 2), max(hi, m + mindest / 2))
            elif lo < g[i][0] or hi > g[i][1]:
                lo, hi = min(lo, g[i][0]), max(hi, g[i][1])
                rand = 0.5 * (hi - lo)             # gleich viel Luft, damit es nicht bei jedem Bild wächst
                g[i] = (lo - rand if lo < g[i][0] else lo, hi + rand if hi > g[i][1] else hi)
            else:
                continue
            self.k_achsen[i].set_ylim(*g[i])

    def blitten_an(self):
        """Nur die bewegten Teile je Bild neu zeichnen (Blitting): mBot2, Spuren, Ultraschall, Texte.
        Achsen, Gitter, Hindernisse und Hinweise zeichnet matplotlib nur neu, wenn sich dort etwas
        ändert (Ausschnitt, Fenstergröße, Thema, Achsen der Verlaufskurven); sonst schafft das Fenster kaum
        10 Bilder/s, und der mBot2 folgt der Maus nur ruckelnd. Nicht beim Video: dort zählt das ganze Bild."""
        self.dyn = [self.l_spur, self.p_bot, self.p_rich, self.l_rad, self.l_us, self.l_quad,
                    self.t_info, self.p_led, self.t_anzeige]
        if self.pose_fn is not None:
            self.dyn += [self.l_spur_ber, self.p_ber, self.p_rich_ber]
        if self.plot:
            self.dyn += [self.k_us, self.k_gyro, self.k_wahr, self.k_l, self.k_r]
        for a in self.dyn:
            a.set_animated(True)                   # nicht mehr Teil des normalen Zeichnens
        self._grund = None
        self.fig.canvas.mpl_connect("draw_event", self._nach_zeichnen)
        self.blit = True

    def blitten_aus(self):
        for a in getattr(self, "dyn", []):
            a.set_animated(False)
        self.blit = False

    def _nach_zeichnen(self, ev):
        """Nach jedem vollen Zeichnen (auch Zoom, Größe, Werkzeugleiste): Hintergrund merken, Bewegtes darauf."""
        if not hasattr(self.fig.canvas, "copy_from_bbox"):
            return                                 # Fenster schon geschlossen
        self._grund = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        for a in self.dyn:
            a.axes.draw_artist(a)

    def auffrischen(self):
        """Bild auf den Bildschirm: voll, wenn sich im Hintergrund etwas geändert hat, sonst nur das Bewegte."""
        if not self.blit:
            return                                 # plt.pause zeichnet
        c = self.fig.canvas
        if self.fig.stale or self._grund is None:
            c.draw()                               # löst _nach_zeichnen aus
        else:
            c.restore_region(self._grund)
            for a in self.dyn:
                a.axes.draw_artist(a)
            c.blit(self.fig.bbox)

    def _anordnen(self):
        """Rechte Spalte an die Fenstergröße anpassen: Pose-Text oben, darunter LED und CyberPi-Anzeige,
        die Bedienhinweise unten. Überlappen sie oder ragt Text aus dem Fenster, werden die Schriften
        kleiner; ist wieder Platz, wachsen sie bis zur vollen Größe zurück."""
        anzeige = self.t_anzeige.get_text().split("\n")
        schluessel = (round(self.fig.bbox.width), round(self.fig.bbox.height),
                      self.t_info.get_text().count("\n"), len(anzeige), max(len(z) for z in anzeige))
        if schluessel == getattr(self, "_angeordnet", None) and self.skala >= 1.0:
            return                                 # nichts geändert, was die Anordnung betrifft
        self._angeordnet = schluessel
        try:
            r = self.fig.canvas.get_renderer()
        except Exception:
            return
        ib = self.info.get_window_extent(r)
        if ib.height <= 0:
            return
        zu_achse = lambda py: (py - ib.y0) / ib.height            # Pixel -> Achsenbruchteil (senkrecht)
        rechts = self.fig.bbox.x1 - 4
        px_je_pt = self.fig.dpi / 72

        def setzen(s):
            fs, fh = SCHRIFT * s, SCHRIFT_HINWEIS * s
            for t, g in ((self.t_info, fs), (self.t_led, fs), (self.t_anzeige, fs), (self.t_hinweis, fh)):
                if t.get_fontsize() != g:                          # nur bei Änderung: sonst verwirft
                    t.set_fontsize(g)                              # matplotlib jedes Mal den Textspeicher
            if self.p_led.get_markersize() != LED_GROESSE * s:
                self.p_led.set_markersize(LED_GROESSE * s)
            luecke = 0.6 * fs * px_je_pt / ib.height           # etwa eine halbe Zeile, als Achsenbruchteil
            y_led = zu_achse(self.t_info.get_window_extent(r).y0) - luecke - 0.5 * fs * px_je_pt / ib.height
            self.t_led.set_y(y_led)
            led_x = (self.t_led.get_window_extent(r).x1 - ib.x0 + 1.2 * LED_GROESSE * s * px_je_pt) / ib.width
            self.p_led.set_data([led_x], [y_led])
            rahmen = 0.3 * fs * px_je_pt + 2                      # Polster des runden Kastens (boxstyle pad 0.3)
            y_kasten = y_led - (0.5 * fs * px_je_pt + luecke * ib.height + rahmen) / ib.height
            self.t_anzeige.set_y(y_kasten)
            unten = zu_achse(self.t_anzeige.get_window_extent(r).y0 - rahmen)
            oben_hinweis = zu_achse(self.t_hinweis.get_window_extent(r).y1)
            breit = max(t.get_window_extent(r).x1 + (rahmen if t is self.t_anzeige else 0)
                        for t in (self.t_info, self.t_anzeige, self.t_hinweis))
            return unten - oben_hinweis, breit <= rechts

        platz, passt = setzen(self.skala)
        while (platz < 0.01 or not passt) and self.skala > SCHRIFT_MIN:       # zu eng: kleiner
            self.skala = max(SCHRIFT_MIN, self.skala * 0.92)
            platz, passt = setzen(self.skala)
        if self.skala < 1.0 and platz > 0.12 and passt:                        # wieder Platz: langsam größer
            s = min(1.0, self.skala * 1.05)
            platz2, passt2 = setzen(s)
            if platz2 >= 0.01 and passt2:
                self.skala = s
            else:
                setzen(self.skala)

    def _ausschnitt(self, xs, ys):
        """Ausschnitt wächst mit, schrumpft aber nie (sonst springt das Bild). Nach Zoomen oder
        Verschieben bleibt die Ansicht stehen, bis die Taste ANSICHT_TASTE sie wieder freigibt."""
        if self.manuell:
            return
        if self.grenzen is None:
            px, py = list(xs), list(ys)
            for poly in self.welt.hindernisse:
                px += [p[0] for p in poly]
                py += [p[1] for p in poly]
            for a, b, _ in self.welt.marken:
                px += [a[0], b[0]]
                py += [a[1], b[1]]
            px += [z[0] for z in self.welt.ziele]
            py += [z[1] for z in self.welt.ziele]
            mx, my = (min(px) + max(px)) / 2, (min(py) + max(py)) / 2
            hx, hy = max(0.5, (max(px) - min(px)) / 2 + RAND), max(0.5, (max(py) - min(py)) / 2 + RAND)
            self.grenzen = [mx - hx, mx + hx, my - hy, my + hy]
        g, neu = self.grenzen, False
        for x, y in zip(xs, ys):
            if x - RAND < g[0]:
                g[0], neu = x - RAND, True
            if x + RAND > g[1]:
                g[1], neu = x + RAND, True
            if y - RAND < g[2]:
                g[2], neu = y - RAND, True
            if y + RAND > g[3]:
                g[3], neu = y + RAND, True
        if neu or not getattr(self, "_gesetzt", False):
            # selbst auf das Seitenverhältnis der Achsen erweitern, sonst beschneidet aspect="equal"
            # die längere Seite und der mBot2 kann aus dem Bild fallen (kleines oder schmales Fenster)
            x0, x1, y0, y1 = g
            bb = self.ax.bbox
            soll = bb.height / bb.width if bb.width > 0 else 1.0
            if (y1 - y0) < (x1 - x0) * soll:
                m, h = (y0 + y1) / 2, (x1 - x0) * soll / 2
                y0, y1 = m - h, m + h
            else:
                m, h = (x0 + x1) / 2, (y1 - y0) / soll / 2
                x0, x1 = m - h, m + h
            self.ax.set_xlim(x0, x1)
            self.ax.set_ylim(y0, y1)
            self._gesetzt = True


def _nach_vorn(fig):
    """Fenster nach vorn holen und ihm den Tastaturfokus geben (Tk; andere Backends: so gut es geht)."""
    try:
        fenster = fig.canvas.manager.window
        if hasattr(fenster, "lift"):               # TkAgg
            fenster.lift()
            fenster.attributes("-topmost", True)   # unter Windows sonst oft hinter dem Editor
            fenster.after(300, lambda: fenster.attributes("-topmost", False))
            fig.canvas.get_tk_widget().focus_force()
        elif hasattr(fenster, "raise_"):           # Qt
            fenster.raise_()
            fenster.activateWindow()
    except Exception:
        pass


def zeigen(welt, ziel=None, pose=None, titel="mBot2, simuliert", plot=False, video=None, bild=None,
           thema="dunkel"):
    """Fenster öffnen; ziel() läuft in einem eigenen Thread. Kehrt zurück, wenn das Fenster zu ist
    (bei einem Backend ohne Bildschirm, etwa MPLBACKEND=Agg: wenn ziel() fertig ist).
    video: MP4-Datei für den ganzen Lauf, bild: PNG-Datei mit dem letzten Bild.
    thema: 'dunkel' (Standard) oder 'hell', im Fenster mit Taste d umschaltbar. Gibt das Fenster zurück."""
    f = Fenster(welt, pose=pose, titel=titel, plot=plot, thema=thema)
    film = _Video(video) if video else None
    fehler = []

    def lauf():
        try:
            ziel()
        except SystemExit:
            pass                                   # cyberpi.stop_all() oder Fenster geschlossen
        except BaseException as e:                 # sichtbar machen, sonst stirbt der Thread leise
            fehler.append(e)
            traceback.print_exc()

    thread = None
    welt.fenster_offen = True                      # API-Aufrufe geben kurz ab (_mbot_welt.ruf), das Fenster bleibt flüssig
    if ziel is not None:
        thread = threading.Thread(target=lauf, daemon=True, name="mbot2-programm")
        thread.mbot_lauf = welt.lauf               # damit stop_all() und das Schließen es beenden
        thread.start()
    interaktiv = matplotlib.get_backend().lower() not in NICHT_INTERAKTIV
    if interaktiv and film is None and getattr(f.fig.canvas, "supports_blit", False):
        f.blitten_an()
    try:
        while plt.fignum_exists(f.fig.number):
            t_bild = time.monotonic()
            if thread is not None and not thread.is_alive() and f.status == "läuft":
                f.status = "Fehler im Programm" if fehler else "Programm fertig"
                if film is not None:               # das Video endet mit dem Programm
                    f.zeichnen()
                    film.bild(f.fig)
                    film.schliessen()
                    film = None
            f.zeichnen()
            if film is not None:
                film.bild(f.fig)
            if not interaktiv and (thread is None or not thread.is_alive()):
                break
            f.auffrischen()
            warten = max(0.001, 1.0 / (BILDRATE_BLIT if f.blit else BILDRATE) - (time.monotonic() - t_bild))   # Zeichenzeit abziehen
            if f.blit and getattr(f, "_fokus", False):
                f.fig.canvas.start_event_loop(warten)   # plt.pause zeichnete über show() jedes Mal alles neu
            else:
                plt.pause(warten)
            if not getattr(f, "_fokus", False):
                f._fokus = True
                _nach_vorn(f.fig)                  # Tasten sollen ins Fenster gehen, nicht ins Terminal
    except KeyboardInterrupt:
        pass
    if thread is not None and not thread.is_alive() and f.status == "läuft":
        f.status = "Fehler im Programm" if fehler else "Programm fertig"
    if thread is not None and thread.is_alive():   # Fenster zu oder Ctrl+C: Programm beenden, Motoren aus
        welt.alle_stoppen()
        with welt.lock:
            welt.soll = {"EM1": 0.0, "EM2": 0.0}
        thread.join(0.5)
    if film is not None:
        film.schliessen()
    if bild:
        f.blitten_aus()                            # savefig zeichnet nur, was nicht animiert ist
        f.zeichnen()
        f.fig.savefig(bild, dpi=100, facecolor=f.fig.get_facecolor())
        print(f"Bild: {bild}")
    plt.close(f.fig)
    welt.fenster_offen = False
    return f
