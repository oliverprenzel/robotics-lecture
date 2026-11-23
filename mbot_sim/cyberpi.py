"""Nachbau des Makeblock-Moduls `cyberpi` (nachgebaut für Tests am PC, nicht vom Hersteller).

Nachgebaut ist, was die mBot-Firmware nutzt, plus naheliegende Nachbarn, mit Namen und
Einheiten nach der Makeblock-Python-Dokumentation. Werte kommen aus dem simulierten mBot2
in _mbot_welt.py (gemeinsam mit mbot2.py). Nicht nachgebaut: Ton, Kamera, Cloud, Sprache.
"""
import threading

from _mbot_welt import WELT

_ACHSEN = ("x", "y", "z")


def _achse(axis):
    a = str(axis).lower()
    if a not in _ACHSEN:
        raise ValueError("axis: 'x', 'y' oder 'z'")
    return a


# ---------------------------------------------------------------- Bewegungssensor (Gyro, Beschleunigung)
# Auflösung wie am Gerät: Drehrate und Drehwinkel in ganzen Grad, Beschleunigung mit einer Nachkommastelle.
# Gerundet ist eine Annahme (am Gerät abgelesen sind nur die Stufen): hier auf int ändern, falls abgeschnitten wird.
def _ganz(v):
    return int(round(v))


def get_gyro(axis):
    """Drehrate [Grad/s], ganzzahlig; z: links herum positiv (Annahme, am Gerät prüfen: vz_gyro)."""
    a = _achse(axis)
    WELT.ruf("get_gyro", a)
    WELT.weiter()
    with WELT.lock:
        if a != "z":
            return _ganz(WELT.rnd.gauss(0.0, WELT.rauschen))
        import math
        return _ganz(WELT.gyro_skala * math.degrees(WELT.w) + WELT.bias + WELT.rnd.gauss(0.0, WELT.rauschen))


def get_rotation(axis):
    """Aufsummierter Drehwinkel [Grad, ganzzahlig] seit reset_rotation, mit Maßstabsfehler und Drift (rotation_drift)."""
    a = _achse(axis)
    WELT.ruf("get_rotation", a)
    WELT.weiter()
    with WELT.lock:
        return _ganz(WELT.rotation[a])


def reset_rotation(axis="all"):
    WELT.ruf("reset_rotation", axis)
    with WELT.lock:
        for a in (_ACHSEN if axis == "all" else (_achse(axis),)):
            WELT.rotation[a] = 0.0


def get_acc(axis):
    """Beschleunigung [m/s^2], eine Nachkommastelle; z: Erdschwere."""
    a = _achse(axis)
    WELT.ruf("get_acc", a)
    with WELT.lock:
        return round((9.81 if a == "z" else 0.0) + WELT.rnd.gauss(0.0, 0.02), 1)


def get_yaw():
    import math
    WELT.ruf("get_yaw")
    WELT.weiter()
    with WELT.lock:
        return (math.degrees(WELT.pose[2]) + 180.0) % 360.0 - 180.0


# ---------------------------------------------------------------- Skripte
def stop_all():
    """Alle laufenden Skripte beenden, auch das aufrufende. Motoren und LEDs behalten ihren Zustand."""
    WELT.ruf("stop_all")
    WELT.alle_stoppen()
    if hasattr(threading.current_thread(), "mbot_lauf"):
        raise SystemExit


# ---------------------------------------------------------------- Akku
def get_battery():
    """Ladezustand [%]."""
    WELT.ruf("get_battery")
    with WELT.lock:
        return int(round(WELT.akku))


# ---------------------------------------------------------------- Tasten und Joystick
class _Controller:
    def is_press(self, name):
        """name: 'a', 'b', 'middle', 'up', 'down', 'left', 'right', 'any'."""
        WELT.ruf("controller.is_press", name)
        return WELT.gedrueckt(name)


controller = _Controller()


# ---------------------------------------------------------------- Anzeige und LED
class _Console:
    def _schreib(self, text, neu):
        with WELT.lock:
            if neu or not WELT.zeilen:
                WELT.zeilen.append(str(text))
            else:
                WELT.zeilen[-1] += str(text)
            del WELT.zeilen[:-8]                       # der kleine Bildschirm zeigt nur wenige Zeilen
            if WELT.protokoll:
                print("[CyberPi] " + str(text))

    def println(self, text):
        WELT.ruf("console.println", text)
        self._schreib(text, True)

    def print(self, text):
        WELT.ruf("console.print", text)
        self._schreib(text, False)

    def clear(self):
        WELT.ruf("console.clear")
        with WELT.lock:
            WELT.zeilen = []


console = _Console()


class _Display:
    """Anzeige mit frei platzierten Texten. Der Nachbau gibt sie mit print aus."""

    def show_label(self, message, fontsize=16, x=0, y=0, index=0):
        WELT.ruf("display.show_label", message, fontsize, x, y, index)
        self._merken(message, index)
        print("[CyberPi] " + str(message))

    def _merken(self, message, index=0):
        """Text für das Fenster (WELT.fenster) merken."""
        with WELT.lock:
            WELT.labels[index] = str(message)

    def clear(self):
        WELT.ruf("display.clear")
        with WELT.lock:
            WELT.labels = {}


display = _Display()


class _Led:
    def on(self, r, g, b, id="all"):
        WELT.ruf("led.on", r, g, b, id)
        with WELT.lock:
            WELT.led = (r, g, b)

    def off(self, id="all"):
        self.on(0, 0, 0, id)


led = _Led()


# ---------------------------------------------------------------- WLAN
class _Wifi:
    def connect(self, ssid, password):
        WELT.ruf("wifi.connect", ssid, "***")          # Passwort nicht ins Aufrufprotokoll
        with WELT.lock:
            WELT.wlan_versuche.append((ssid, password))
            s, p = WELT.netz
            WELT.wlan_verbunden = s is None or (ssid == s and password == p)

    def is_connect(self):
        WELT.ruf("wifi.is_connect")
        with WELT.lock:
            return WELT.wlan_verbunden


wifi = _Wifi()
