"""Ein mBot2-Programm unverändert am PC laufen lassen, auf dem simulierten mBot2.

    python mbot_sim_start.py PROGRAMM.py              # leerer Raum
    python mbot_sim_start.py PROGRAMM.py --wand 80    # Wand 80 cm vor dem Ultraschallsensor
    python mbot_sim_start.py PROGRAMM.py --realistisch   # ungleiche Räder, Schlupf, Gyro-Drift

Die Programmdatei bleibt, wie sie auf den mBot2 geladen wird: `cyberpi`, `mbot2`, `mbuild` und
`event` kommen hier aus mbot_sim. Die Tasten des CyberPi sind die Tasten a, b, m und die
Pfeiltasten im Terminal (nur Windows). Die Anzeige erscheint in der Konsole, höchstens zweimal
je Sekunde. Am Ende, oder nach Ctrl+C, steht die wahre Position des simulierten mBot2 da:
Die Simulation kennt sie, am echten mBot2 misst das Maßband.
"""
import argparse
import math
import os
import runpy
import sys
import time

from . import installieren

US_VORN = 0.105                                   # m, Ultraschallsensor vor der Radachse (wie in _mbot_welt.py)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datei", help="Programm für den mBot2 (.py)")
    ap.add_argument("--wand", type=float, metavar="CM", help="Wand in diesem Abstand vor dem Ultraschallsensor")
    ap.add_argument("--realistisch", action="store_true",
                    help="typische Fehler eines echten mBot2: rechtes Rad 1 %% größer, Schlupf beim Drehen, "
                         "Gyro mit Maßstabsfehler und Drift 0,6 °/min")
    ap.add_argument("--aufgebockt", action="store_true", help="Räder drehen frei, der mBot2 bleibt stehen")
    a = ap.parse_args(argv)
    if not os.path.exists(a.datei):
        raise SystemExit(f"{a.datei} gibt es nicht")
    cyberpi, mbot2, welt = installieren()
    import event

    hindernisse = []
    if a.wand is not None:
        x = US_VORN + a.wand / 100
        hindernisse = [[(x, -1.0), (x + 0.05, -1.0), (x + 0.05, 1.0), (x, 1.0)]]
    import _mbot_welt
    modell = dict(_mbot_welt.REALISTISCH) if a.realistisch else {}
    welt.konfigurieren(hindernisse=hindernisse, tastatur=True, aufgebockt=a.aufgebockt, protokoll=True,
                       **modell)                  # protokoll: cyberpi.console auch in der Konsole zeigen

    zeigen = cyberpi.display.show_label
    gezeigt, offen = [0.0, None], [None]          # eine Schleife mit 20 Hz soll die Konsole nicht fluten

    def show_label(message, *args, **kw):
        if message == gezeigt[1]:
            return
        if time.monotonic() - gezeigt[0] < 0.5:
            offen[0] = (message, args, kw)        # zu früh: merken, am Ende nachholen
            return
        gezeigt[:], offen[0] = [time.monotonic(), message], None
        zeigen(message, *args, **kw)

    cyberpi.display.show_label = show_label
    sys.path.insert(0, os.path.dirname(os.path.abspath(a.datei)))     # das Programm findet seine Nachbardateien
    print(f"{os.path.basename(a.datei)} auf dem simulierten mBot2. Tasten: a, b, m, Pfeile. Ende: Ctrl+C")
    try:
        runpy.run_path(a.datei, run_name="__main__")
        if event.angemeldet():
            event.warten()                        # Programme mit Tasten-Ereignissen laufen weiter bis Ctrl+C
    except KeyboardInterrupt:
        pass
    if offen[0] is not None:
        zeigen(offen[0][0], *offen[0][1], **offen[0][2])
    x, y, th = welt.wahr()
    print(f"\nwahre Position: {100 * x:.1f} cm gefahren, {100 * y:.1f} cm seitlich, {math.degrees(th):.1f}° gedreht")
    if a.wand is not None:
        print(f"wahrer Abstand Sensor - Wand: {a.wand - 100 * x:.1f} cm")


if __name__ == "__main__":
    main()
