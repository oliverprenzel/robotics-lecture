"""Nachbau des mBlock-Moduls `event` (nachgebaut für Tests am PC, nicht vom Hersteller).

Nachgebaut sind die Ereignisse, mit denen mBlock-Programme starten:

    @event.start                  # läuft einmal beim Programmstart
    @event.is_press('a')          # läuft bei jedem Druck auf die Taste ('a', 'b', 'middle', 'up', ...)

Jedes Ereignis läuft wie am CyberPi als eigenes Skript (hier: ein Thread). Ein Wächter fragt die
Tasten alle 20 ms ab und startet das Skript bei jedem neuen Druck. `cyberpi.stop_all()` beendet
alle laufenden Skripte; die Ereignisse bleiben scharf. Nicht nachgebaut: Nachrichten, Schwellwerte
(greater_than), Neigung und Schütteln.
"""
import threading
import time

from _mbot_welt import WELT

ABFRAGE = 0.02                # s zwischen zwei Abfragen der Tasten
_tasten = []                  # (Taste, Funktion) in der Reihenfolge des Programms
_waechter = None


def _skript(f):
    """f als eigenes Skript starten; cyberpi.stop_all() beendet es beim nächsten API-Aufruf."""
    t = threading.Thread(target=f, daemon=True, name="skript " + getattr(f, "__name__", "?"))
    t.mbot_lauf = WELT.lauf
    t.start()
    return t


def _abfragen():
    war = {}
    while True:
        for name, f in list(_tasten):
            jetzt = WELT.gedrueckt(name)
            if jetzt and not war.get((name, f)):
                _skript(f)
            war[(name, f)] = jetzt
        time.sleep(ABFRAGE)


def start(f):
    """Skript, das beim Programmstart einmal läuft."""
    _skript(f)
    return f


def is_press(name):
    """Skript, das bei jedem Druck auf die Taste `name` läuft."""
    def anmelden(f):
        global _waechter
        _tasten.append((name, f))
        if _waechter is None:
            _waechter = threading.Thread(target=_abfragen, daemon=True, name="event-Wächter")
            _waechter.start()
        return f
    return anmelden


def warten():
    """Nur am PC: Programm am Leben halten, bis Ctrl+C kommt. Am CyberPi läuft es von selbst weiter."""
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
