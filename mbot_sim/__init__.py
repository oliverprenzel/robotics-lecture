"""Nachgebaute CyberPi-API: die Makeblock-Module `cyberpi`, `mbot2` und `mbuild` (Ultraschall) für den PC.

Damit laufen die mBot-Firmware und das gebaute Programm (mbot/build/mbot_programm.py) ohne
Gerät: Motoren, Encoder, Gyro, Ultraschall, Akku, Tasten, Anzeige, LED und WLAN verhalten sich wie ein
simulierter mBot2 (_mbot_welt.py). Nachgebaut nach der Makeblock-Python-Dokumentation,
nicht vom Hersteller: Was am echten Gerät anders ist, fällt erst dort auf.

    from mbot import mbot_sim                        # im Lehr-Repo: import mbot_sim
    cyberpi, mbot2, welt = mbot_sim.installieren()   # danach liefert `import cyberpi` den simulierten mBot2
    welt.konfigurieren(gyro_bias=0.5)                # Modell zurücksetzen / einstellen
    welt.druecken("a"); welt.wahr(); welt.anzeige(); welt.aufrufe

    python -m mbot.mbot_sim [mbot/build/mbot_programm.py]   # gebautes Programm am PC laufen lassen

In einem Editor (Autovervollständigung, eigene Versuche) reicht es, dieses Verzeichnis
(mbot/mbot_sim) in den Suchpfad zu nehmen: dann ist `import cyberpi, mbot2` der simulierte mBot2.
"""
import os
import sys

PFAD = os.path.dirname(os.path.abspath(__file__))


def installieren():
    """Verzeichnis in sys.path, Module laden; gibt (cyberpi, mbot2, WELT) zurück."""
    if PFAD not in sys.path:
        sys.path.insert(0, PFAD)
    for name in ("cyberpi", "mbot2", "mbuild", "event"):
        m = sys.modules.get(name)
        if m is not None and not getattr(m, "__file__", "").startswith(PFAD):
            raise RuntimeError(f"Modul {name} ist schon geladen und kommt nicht aus mbot_sim: {m}")
    import _mbot_welt
    import cyberpi
    import mbot2
    import mbuild  # noqa: F401  (Ultraschallsensor 2)
    import event  # noqa: F401  (Ereignisse aus mBlock: Programmstart, Tasten)
    return cyberpi, mbot2, _mbot_welt.WELT
