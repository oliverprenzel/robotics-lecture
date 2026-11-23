"""Nachbau des Makeblock-Moduls `mbot2` (nachgebaut für Tests am PC, nicht vom Hersteller).

Encodermotoren an EM1 (linkes Rad) und EM2 (rechtes Rad, spiegelbildlich: mbot2.forward
entspricht drive_speed(+v, -v)). Drehzahlen in U/min, Winkel in Grad. Werte kommen aus dem
simulierten mBot2 in _mbot_welt.py. Nicht nachgebaut: Servos, Gleichstrommotoren an DC1-4,
Sensoren am mBuild-Bus.
"""
from _mbot_welt import RPM_MAX, WELT

_PORTS = ("EM1", "EM2")


def _ports(port):
    p = str(port).upper()
    if p == "ALL":
        return _PORTS
    if p in ("1", "2"):
        p = "EM" + p
    if p not in _PORTS:
        raise ValueError("port: 'EM1', 'EM2' oder 'ALL'")
    return (p,)


# Kennlinie Leistung -> Drehzahl ohne Regelung (EM_set_power, drive_power), Drehzahl =
# steigung * (|Leistung| - null) in U/min. Aus dem Stand läuft der Motor erst ab "an" an (Haftreibung;
# vorwärts und rückwärts bezogen auf den mBot2), dreht er schon, bleibt er erst unter "aus" stehen.
# Die Werte hier sind ANGENOMMEN (plausibel, nicht gemessen): Wie der echte mBot2 sich verhält,
# misst man selbst. Eigene Messwerte: Datei _kennlinie_privat.py neben dieser anlegen,
# mit einem Dict KENNLINIE wie unten; sie ersetzt dann diese Werte.
KENNLINIE = {
    "boden":      dict(steigung=2.4, null=5.0, an_vor=7.0, an_rueck=7.0, aus=6.0),
    "aufgebockt": dict(steigung=2.4, null=4.0, an_vor=6.0, an_rueck=6.0, aus=5.0),
}
try:
    from _kennlinie_privat import KENNLINIE          # gemessene Werte, falls vorhanden
except ImportError:
    pass


def _leistung(port, power):
    p = max(-100.0, min(100.0, float(power)))
    WELT.weiter()
    with WELT.lock:
        k = KENNLINIE["aufgebockt" if WELT.aufgebockt else "boden"]
        for m in _ports(port):
            vor = (p > 0) == (m == "EM1")                  # EM2 spiegelbildlich: negative Leistung = vorwärts
            if abs(WELT.rpm[m]) > 2.0:
                schwelle = k["aus"]
            else:
                schwelle = k["an_vor"] if vor else k["an_rueck"]
            rpm = 0.0 if abs(p) < schwelle else k["steigung"] * (abs(p) - k["null"])
            WELT.soll[m] = rpm if p >= 0 else -rpm


def _setzen(port, rpm):
    WELT.weiter()
    with WELT.lock:
        for p in _ports(port):
            WELT.soll[p] = max(-RPM_MAX, min(RPM_MAX, float(rpm)))


# ---------------------------------------------------------------- Encodermotoren einzeln
def EM_set_speed(speed, port="ALL"):
    """Drehzahl [U/min], im Drehsinn des Motors."""
    WELT.ruf("EM_set_speed", speed, port)
    _setzen(port, speed)


def EM_set_power(power, port="ALL"):
    """Leistung [-100..100 %] ohne Drehzahlregelung, im Drehsinn des Motors. Die Drehzahl folgt
    der Kennlinie oben (KENNLINIE): Totzone mit Haftreibung, darüber linear."""
    WELT.ruf("EM_set_power", power, port)
    _leistung(port, power)


def EM_get_speed(port):
    WELT.ruf("EM_get_speed", port)
    WELT.weiter()
    with WELT.lock:
        return WELT.rpm[_ports(port)[0]]


def EM_get_angle(port):
    """Aufsummierter Winkel [Grad] seit EM_reset_angle, ganzzahlig wie die Encoder."""
    WELT.ruf("EM_get_angle", port)
    WELT.weiter()
    with WELT.lock:
        p = _ports(port)[0]
        return int(WELT.winkel[p] - WELT.null[p])


def EM_reset_angle(port="ALL"):
    WELT.ruf("EM_reset_angle", port)
    WELT.weiter()
    with WELT.lock:
        for p in _ports(port):
            WELT.null[p] = WELT.winkel[p]


def EM_stop(port="ALL"):
    WELT.ruf("EM_stop", port)
    _setzen(port, 0.0)


# ---------------------------------------------------------------- beide Motoren
def drive_speed(EM1_speed, EM2_speed):
    WELT.ruf("drive_speed", EM1_speed, EM2_speed)
    _setzen("EM1", EM1_speed)
    _setzen("EM2", EM2_speed)


def drive_power(EM1_power, EM2_power):
    """Leistung beider Motoren [-100..100 %], ohne Drehzahlregelung (siehe EM_set_power)."""
    WELT.ruf("drive_power", EM1_power, EM2_power)
    _leistung("EM1", EM1_power)
    _leistung("EM2", EM2_power)


def forward(speed=50):
    WELT.ruf("forward", speed)
    drive_speed(speed, -speed)


def backward(speed=50):
    WELT.ruf("backward", speed)
    drive_speed(-speed, speed)


def turn_left(speed=50):
    WELT.ruf("turn_left", speed)
    drive_speed(-speed, -speed)


def turn_right(speed=50):
    WELT.ruf("turn_right", speed)
    drive_speed(speed, speed)
