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
