"""Gemeinsamer Zustand von mbot_sim: ein simulierter mBot2, den cyberpi.py und mbot2.py lesen und steuern.

Modell: zwei Radmotoren mit Anlaufzeit (EM1 = linkes Rad, EM2 = rechtes Rad, spiegelbildlich
eingebaut: positive Drehzahl an EM2 dreht das rechte Rad rückwärts, wie beim mBot2),
Radwinkel in Grad (ganzzahlig, wie die Encoder), wahrer Radradius etwas anders als
konfiguriert, Gyro mit Nullpunktfehler und Rauschen, Akku, Tasten, Anzeige, LED, WLAN.
Wahlweise (REALISTISCH): ungleiche Räder, Schlupf beim Drehen, Drift von get_rotation.
Die Zeit ist die echte Uhr (time.monotonic): der simulierte mBot2 läuft in Echtzeit.
"""
import math
import random
import threading
import time

try:
    import msvcrt             # Tastatur ohne Enter, nur Windows
except ImportError:
    msvcrt = None

TASTE_DAUER = 0.3             # s, so lange gilt ein Tastendruck am PC als gedrückt
TAU = 0.08                   # s, Anlaufzeit der Motoren (wie naman466/mBot2-simulator)
RPM_MAX = 200.0               # Höchstdrehzahl der Encodermotoren (Makeblock: -200..200 U/min)
US_BEREICH = (0.05, 3.00)     # m, Ultraschallsensor 2: Ausgabe 5..300 cm, außerhalb 300
US_FEHLER = 0.05              # ±5 % (Datenblatt) -> 1 sigma ~2,5 %
UMRISS = [(-0.06, -0.065), (0.11, -0.065), (0.11, 0.065), (-0.06, 0.065)]   # m, ungefähr, Radachse im Ursprung
US_KEGEL = 8.0                # Grad, halber Öffnungswinkel (Annahme)

# Typische Fehler eines echten mBot2 für Labor 2 (Koppelnavigation), Annahmen:
# rechtes Rad 1 % größer als das linke, wahrer Radradius 1 % größer als eingetragen, wirksame
# Spurweite beim Drehen 2 % größer (Schlupf), Gyro 0,5 % Maßstabsfehler, keine Drift
REALISTISCH = dict(radius_fehler=0.01, rad_ungleich=0.01, spur_fehler=0.02, gyro_skala=0.995,
                   rotation_drift=0.0)


class Welt:
    def __init__(self, **kw):
        self.lock = threading.RLock()
        self.lauf = 0                 # zählt cyberpi.stop_all(): Skripte (event.py) eines älteren Laufs enden
        self.konfigurieren(**kw)

    def konfigurieren(self, rad_radius=0.0325, spurweite=0.115, radius_fehler=0.01, gyro_bias=0.4,
                      gyro_rauschen=0.15, start=(0.0, 0.0, 0.0), seed=1, akku=87.0, ssid=None, passwort=None,
                      protokoll=False, hindernisse=(), us_position=(0.105, 0.0), marken=(),
                      quad=(0.088, (0.024, 0.008, -0.008, -0.024)), gyro_skala=1.0, tastatur=False,
                      rad_ungleich=0.0, spur_fehler=0.0, rotation_drift=0.0, aufgebockt=False, ziele=(), kollision=False):
        """Alles zurück auf Anfang. ssid/passwort: nur dieses WLAN „gibt es“ (None = jedes).
        tastatur: Tasten der PC-Tastatur im Terminal gelten als Tasten des CyberPi (tastatur_lesen).
        hindernisse: Polygone [(x, y), ...] im Rahmen der wahren Pose (für den Ultraschall).
        marken: Klebebänder am Boden [((x0, y0), (x1, y1), breite), ...] für den Linienfolger;
        quad: (Abstand vor der Radachse, Querlage der Sonden L2, L1, R1, R2) [m].
        rad_ungleich: rechtes Rad um diesen Anteil größer als das linke (Kurve trotz gleicher Encoder).
        spur_fehler: wirksame Spurweite um diesen Anteil größer als spurweite (Schlupf beim Drehen).
        rotation_drift: Drift von get_rotation [Grad/s], auch im Stillstand.
        aufgebockt: Räder drehen frei, der mBot bewegt sich nicht (Pose und Gyro bleiben).
        ziele: Punkte [(x, y, Name), ...], nur zum Ansehen im Fenster (szenen.py).
        kollision: Berührt der Umriss (UMRISS) ein Hindernis, bleibt der mBot stehen; die Räder drehen
        durch (Encoder zählen weiter, der Gyro sieht nichts)."""
        with getattr(self, "lock", threading.RLock()):
            self.rnd = random.Random(seed)
            self.r_true = rad_radius * (1.0 + radius_fehler)
            self.r_rechts = self.r_true * (1.0 + rad_ungleich)
            self.b = spurweite * (1.0 + spur_fehler)
            self.drift = float(rotation_drift)
            self.aufgebockt = bool(aufgebockt)
            self.bias, self.rauschen = gyro_bias, gyro_rauschen
            self.gyro_skala = float(gyro_skala)        # gemessene / wahre Drehrate (Maßstabsfehler des Gyro)
            self.pose = [float(a) for a in start]     # wahre Pose x, y, th (auch aus NumPy-Werten)
            self.start = tuple(self.pose)              # Startmarke: Ursprung der Pose, die das Programm rechnet
            self.kollision, self.kollidiert = bool(kollision), False
            self.ziele = [(float(z[0]), float(z[1]), str(z[2]) if len(z) > 2 else "") for z in ziele]
            self.v = self.w = 0.0
            self.soll = {"EM1": 0.0, "EM2": 0.0}       # U/min am Motor (eigener Drehsinn)
            self.rpm = {"EM1": 0.0, "EM2": 0.0}
            self.winkel = {"EM1": 0.0, "EM2": 0.0}     # Grad am Motor (eigener Drehsinn)
            self.null = {"EM1": 0.0, "EM2": 0.0}       # EM_reset_angle
            self.rotation = {"x": 0.0, "y": 0.0, "z": 0.0}
            self.akku = akku
            self.tasten = set()                        # gedrückte Tasten: "a", "b", "up", ...
            self.tastatur = bool(tastatur)
            self.tasten_bis = {}                       # Taste -> Zeit, bis zu der ein Druck am PC gilt
            self.zeilen = []                           # Konsole des CyberPi
            self.labels = {}                           # display.show_label: index -> Text
            self.led = (0, 0, 0)
            self.netz = (ssid, passwort)
            self.wlan_verbunden = False
            self.wlan_versuche = []                    # (ssid, passwort) jeder connect-Aufruf
            self.aufrufe = []                          # (Name, Argumente) jeder API-Aufruf
            self.protokoll = protokoll                 # Konsole zusätzlich auf stdout
            self.hindernisse = [[(float(q[0]), float(q[1])) for q in p] for p in hindernisse]
            self.us_pos = (float(us_position[0]), float(us_position[1]))
            self.marken = [((float(a[0]), float(a[1])), (float(b[0]), float(b[1])), float(w)) for a, b, w in marken]
            self.quad = (float(quad[0]), tuple(float(q) for q in quad[1]))
            self.t = None

    # ---------------------------------------------------------------- Physik
    def weiter(self):
        with self.lock:
            now = time.monotonic()
            if self.t is None:
                self.t = now
                return
            dt, self.t = now - self.t, now
            while dt > 0:
                h = min(dt, 0.005)
                dt -= h
                a = min(1.0, h / TAU)
                for m in ("EM1", "EM2"):
                    self.rpm[m] += (self.soll[m] - self.rpm[m]) * a
                    self.winkel[m] += self.rpm[m] * 6.0 * h          # U/min -> Grad/s
                k = 2 * math.pi / 60
                vl, vr = self.rpm["EM1"] * k * self.r_true, -self.rpm["EM2"] * k * self.r_rechts   # EM2 spiegelbildlich
                self.v, self.w = (0.0, 0.0) if self.aufgebockt else (0.5 * (vl + vr), (vr - vl) / self.b)
                x, y, th = self.pose
                m_ = th + 0.5 * self.w * h
                neu = [x + self.v * h * math.cos(m_), y + self.v * h * math.sin(m_), th + self.w * h]
                if self.kollision and (self.v or self.w) and self._beruehrt(neu):
                    self.kollidiert = True             # steht an: Räder drehen durch, Pose und Gyro bleiben
                    self.rotation["z"] += self.drift * h
                    continue
                self.kollidiert = False if (self.v or self.w) else self.kollidiert
                self.pose = neu
                self.rotation["z"] += (self.gyro_skala * math.degrees(self.w) + self.drift) * h

    def _beruehrt(self, pose):
        """Überlappt der Umriss in dieser Pose ein Hindernis? (Ecken in Polygonen, beide Richtungen,
        und sich kreuzende Kanten, etwa bei einer dünnen Wand quer über den mBot)"""
        x, y, th = pose
        c, s = math.cos(th), math.sin(th)
        ecken = [(x + c * px - s * py, y + s * px + c * py) for px, py in UMRISS]
        for poly in self.hindernisse:
            if any(_innen(e, poly) for e in ecken) or any(_innen(q, ecken) for q in poly):
                return True
            if any(_kreuzen(ecken[i - 1], ecken[i], poly[j - 1], poly[j])
                   for i in range(len(ecken)) for j in range(len(poly))):
                return True
        return False

    def stossen(self, winkel=0.0, seitlich=0.0):
        """Stoß von außen: dreht den mBot um winkel [Grad] und versetzt ihn seitlich [m].
        Der Gyro misst die Drehung mit, die Encoder merken nichts."""
        self.weiter()
        with self.lock:
            x, y, th = self.pose
            self.pose = [x - math.sin(th) * seitlich, y + math.cos(th) * seitlich, th + math.radians(winkel)]
            self.rotation["z"] += self.gyro_skala * winkel

    def schieben(self, strecke=0.0, winkel=0.0):
        """Von Hand schieben oder drehen: um strecke [m] in Fahrtrichtung und winkel [Grad] um die Mitte
        der Radachse, die Räder rollen dabei ab. Anders als beim Stoß zählen die Encoder mit (je Rad
        der eigene Weg), und der Gyro misst die Drehung. An einem Hindernis bleibt er stehen: in
        Teilschritten von höchstens 5 mm und 2°, damit er auch bei schneller Maus nicht hindurchspringt.
        Gibt zurück, ob der ganze Weg frei war."""
        self.weiter()
        n = max(1, math.ceil(abs(strecke) / 0.005), math.ceil(abs(winkel) / 2.0))
        ds, dw = strecke / n, winkel / n
        dth = math.radians(dw)
        s_l, s_r = ds - dth * self.b / 2, ds + dth * self.b / 2
        with self.lock:
            for _ in range(n):
                if not self.aufgebockt:
                    x, y, th = self.pose
                    m_ = th + dth / 2
                    neu = [x + ds * math.cos(m_), y + ds * math.sin(m_), th + dth]
                    if self.kollision and self._beruehrt(neu):
                        self.kollidiert = True
                        return False
                    self.pose = neu
                    self.rotation["z"] += self.gyro_skala * dw
                self.winkel["EM1"] += math.degrees(s_l / self.r_true)
                self.winkel["EM2"] -= math.degrees(s_r / self.r_rechts)      # EM2 spiegelbildlich eingebaut
            self.kollidiert = False
            return True

    def ruf(self, name, *args):
        if getattr(threading.current_thread(), "mbot_lauf", self.lauf) != self.lauf:
            raise SystemExit              # nach cyberpi.stop_all(): dieses Skript ist beendet
        with self.lock:
            self.aufrufe.append((name,) + args)
            if len(self.aufrufe) > 5000:
                del self.aufrufe[:1000]
        # Bei offenem Fenster kurz abgeben: Eine Schleife ohne Pause (while not is_press("a"): pass)
        # hielte sonst den Interpreter fest, und das Fenster im Hauptthread käme kaum zum Zeichnen.
        # time.sleep(0) reicht unter Windows nicht, 1 ms schon; ohne Fenster bleibt es bei voller Geschwindigkeit.
        if getattr(self, "fenster_offen", False):
            time.sleep(0.001)

    def alle_stoppen(self):
        """cyberpi.stop_all(): alle Skripte aus event.py enden bei ihrem nächsten API-Aufruf."""
        with self.lock:
            self.lauf += 1

    # ---------------------------------------------------------------- Ultraschall
    def ultraschall(self):
        """Abstand [m] vom Sensor zum nächsten Hindernis im Schallkegel, US_BEREICH[1] wenn nichts."""
        best = self.echo()
        if best >= US_BEREICH[1] or best < US_BEREICH[0]:
            return US_BEREICH[1]                       # nichts im Kegel, oder zu nah: der Sensor meldet das Maximum
        with self.lock:
            return best * (1.0 + self.rnd.gauss(0.0, US_FEHLER / 2))

    def echo(self):
        """Wahrer Abstand [m] vom Sensor zum nächsten Hindernis im Schallkegel, ohne Messfehler
        (auch für die Anzeige im Fenster, ohne den Zufall der Messungen zu verbrauchen)."""
        self.weiter()
        with self.lock:
            x, y, th = self.pose
            c, s = math.cos(th), math.sin(th)
            ox, oy = x + c * self.us_pos[0] - s * self.us_pos[1], y + s * self.us_pos[0] + c * self.us_pos[1]
            best = US_BEREICH[1]
            for k in range(-2, 3):                     # fünf Strahlen über den Kegel
                a = th + math.radians(US_KEGEL * k / 2.0)
                dx, dy = math.cos(a), math.sin(a)
                for poly in self.hindernisse:
                    for i in range(len(poly)):
                        d = _strahl(ox, oy, dx, dy, poly[i], poly[(i + 1) % len(poly)])
                        if d is not None and d < best:
                            best = d
            return best

    # ---------------------------------------------------------------- Linienfolger (Quad-RGB)
    def auf_linie(self):
        """Je Sonde L2, L1, R1, R2: liegt der Messfleck auf einem Klebeband?"""
        self.weiter()
        with self.lock:
            x, y, th = self.pose
            c, s = math.cos(th), math.sin(th)
            out = []
            for q in self.quad[1]:
                px, py = x + c * self.quad[0] - s * q, y + s * self.quad[0] + c * q
                out.append(any(_strecke(px, py, a, b) <= w / 2 for a, b, w in self.marken))
            return out

    # ---------------------------------------------------------------- für Tests
    def wahr(self):
        """Wahre Pose [x, y, th] des simulierten mBot."""
        self.weiter()
        with self.lock:
            return list(self.pose)

    def druecken(self, taste, an=True):
        with self.lock:
            (self.tasten.add if an else self.tasten.discard)(taste)

    def tastatur_lesen(self):
        """Tastendrücke im Terminal übernehmen (nur Windows, ohne Enter): a, b, m oder Enter = middle,
        Pfeiltasten = Joystick. Jeder Druck gilt TASTE_DAUER lang als gedrückt."""
        if not self.tastatur or msvcrt is None:
            return
        while msvcrt.kbhit():
            c = msvcrt.getwch()
            if c in (chr(0), chr(0xE0)):               # Sondertaste: ein zweites Zeichen folgt
                name = {"H": "up", "P": "down", "K": "left", "M": "right"}.get(msvcrt.getwch())
            else:
                name = {"a": "a", "b": "b", "m": "middle", chr(13): "middle"}.get(c.lower())
            if name:
                with self.lock:
                    self.tasten_bis[name] = time.monotonic() + TASTE_DAUER

    def gedrueckt(self, name):
        """True, wenn die Taste (bei 'any' irgendeine) gerade gedrückt ist."""
        self.tastatur_lesen()
        with self.lock:
            jetzt = time.monotonic()
            aktiv = set(self.tasten) | {k for k, bis in self.tasten_bis.items() if bis > jetzt}
            return bool(aktiv) if name == "any" else name in aktiv

    def fenster(self, ziel=None, pose=None, titel="mBot2, simuliert", plot=False, video=None, bild=None,
                thema="dunkel"):
        """Live-Fenster: Welt von oben, mBot2, Fahrweg, Sensoren. ziel() läuft dabei im Hintergrund
        (ein mBot2-Programm), das Fenster im Hauptthread. pose: Funktion, die die vom Programm
        berechnete Pose (x, y, theta in rad) liefert oder None; sie wird gestrichelt dazugezeichnet.
        plot: Verläufe darunter; video / bild: Lauf als MP4 bzw. Endbild als PNG speichern.
        thema: 'dunkel' (Standard) oder 'hell'; im Fenster schaltet Taste d um."""
        from fenster import zeigen                     # erst hier: matplotlib nur, wenn ein Fenster gewünscht ist
        return zeigen(self, ziel=ziel, pose=pose, titel=titel, plot=plot, video=video, bild=bild,
                      thema=thema)

    def anzeige(self):
        with self.lock:
            return list(self.zeilen)


def _innen(p, poly):
    """Punkt p im Polygon (Strahlverfahren)?"""
    x, y = p
    drin = False
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[i - 1]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            drin = not drin
    return drin


def _kreuzen(a, b, c, d):
    """Schneiden sich die Strecken a-b und c-d (echt, ohne bloßes Berühren)?"""
    def seite(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return seite(a, b, c) * seite(a, b, d) < 0 and seite(c, d, a) * seite(c, d, b) < 0


def _strecke(px, py, a, b):
    """Abstand des Punkts p zur Strecke a-b."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    L2 = ex * ex + ey * ey
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - a[0]) * ex + (py - a[1]) * ey) / L2))
    return math.hypot(px - a[0] - t * ex, py - a[1] - t * ey)


def _strahl(ox, oy, dx, dy, a, b):
    """Abstand entlang des Strahls (ox, oy) + t (dx, dy) bis zur Strecke a-b, oder None."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    den = dx * ey - dy * ex
    if abs(den) < 1e-12:
        return None
    wx, wy = a[0] - ox, a[1] - oy
    t = (wx * ey - wy * ex) / den
    u = (wx * dy - wy * dx) / den
    return t if t >= 0 and 0 <= u <= 1 else None


WELT = Welt()
