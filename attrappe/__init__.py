"""Nachgebaute CyberPi-API: die Makeblock-Module `cyberpi`, `mbot2` und `mbuild` (Ultraschall) als Attrappe für den PC.

Damit laufen die mBot-Firmware und das gebaute Programm (mbot/build/mbot_programm.py) ohne
Gerät: Motoren, Encoder, Gyro, Ultraschall, Akku, Tasten, Anzeige, LED und WLAN verhalten sich wie ein
simulierter mBot2 (_attrappe_welt.py). Nachgebaut nach der Makeblock-Python-Dokumentation,
nicht vom Hersteller: Was am echten Gerät anders ist, fällt erst dort auf.

    from mbot import attrappe
    cyberpi, mbot2, welt = attrappe.installieren()   # danach liefert `import cyberpi` die Attrappe
    welt.konfigurieren(gyro_bias=0.5)                # Modell zurücksetzen / einstellen
    welt.druecken("a"); welt.wahr(); welt.anzeige(); welt.aufrufe

    python -m mbot.attrappe [mbot/build/mbot_programm.py]   # gebautes Programm am PC laufen lassen

In einem Editor (Autovervollständigung, eigene Versuche) reicht es, dieses Verzeichnis
(mbot/attrappe) in den Suchpfad zu nehmen: dann ist `import cyberpi, mbot2` die Attrappe.
"""
import os
import sys

PFAD = os.path.dirname(os.path.abspath(__file__))


def installieren():
    """Verzeichnis in sys.path, Module laden; gibt (cyberpi, mbot2, WELT) zurück."""
    if PFAD not in sys.path:
        sys.path.insert(0, PFAD)
    for name in ("cyberpi", "mbot2", "mbuild"):
        m = sys.modules.get(name)
        if m is not None and not getattr(m, "__file__", "").startswith(PFAD):
            raise RuntimeError(f"Modul {name} ist schon geladen und ist nicht die Attrappe: {m}")
    import _attrappe_welt
    import cyberpi
    import mbot2
    import mbuild  # noqa: F401  (Ultraschallsensor 2)
    return cyberpi, mbot2, _attrappe_welt.WELT
