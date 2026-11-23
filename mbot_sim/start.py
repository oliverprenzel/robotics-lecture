"""Ein mBot2-Programm unverändert am PC laufen lassen, auf dem simulierten mBot2.

    python mbot_sim_start.py PROGRAMM.py              # leerer Raum
    python mbot_sim_start.py PROGRAMM.py --wand 80    # Wand 80 cm vor dem Ultraschallsensor
    python mbot_sim_start.py PROGRAMM.py --realistisch   # ungleiche Räder, Schlupf, Gyro-Drift
    python mbot_sim_start.py PROGRAMM.py --gui        # Fenster: Welt, Hindernisse, mBot2, Fahrweg
    python mbot_sim_start.py PROGRAMM.py --pose       # dazu die Pose, die das Programm berechnet (x, y, theta)
    python mbot_sim_start.py PROGRAMM.py --welt zielpunkte --gui   # Szene: zielpunkte, hindernis, raum oder .toml-Datei
    python mbot_sim_start.py PROGRAMM.py --plot       # Fenster mit Verläufen (Ultraschall, Drehwinkel, Räder)
    python mbot_sim_start.py PROGRAMM.py --video fahrt.mp4 --bild fahrt.png   # Lauf aufzeichnen

Die Programmdatei bleibt, wie sie auf den mBot2 geladen wird: `cyberpi`, `mbot2`, `mbuild` und
`event` kommen hier aus mbot_sim. Die Tasten des CyberPi: a und b, die Pfeiltasten als Joystick,
m oder Enter als Joystick-Mitte; ohne Fenster im Terminal (nur Windows). Die Anzeige erscheint
in der Konsole, höchstens zweimal je Sekunde. Am Ende, oder nach Ctrl+C, steht die wahre
Position des simulierten mBot2 da: Die Simulation kennt sie, am echten mBot2 misst das Maßband.

Mit --gui zeigt ein Fenster (fenster.py) die Welt von oben; die Tasten des CyberPi sind dann die
Tasten a, b, m und die Pfeile im Fenster, auf jedem System. --pose liest dazu während der Fahrt die
globalen Variablen x, y, theta des Programms (Meter, theta in rad) und zeichnet sie gestrichelt;
andere Namen mit --pose px,py,kurs. --pose, --plot, --video und --bild schalten das Fenster mit
ein. Im Fenster schiebt Ziehen mit der Maus den mBot2 von Hand (mit Umschalt: drehen), ein Klick
neben den mBot2 stößt ihn um 10° an. Das Fenster ist dunkel; --hell oder
Taste d im Fenster schaltet auf hell. Szenen: szenen.py.
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
                         "Gyro mit Maßstabsfehler und Drift 0,1 °/min")
    ap.add_argument("--aufgebockt", action="store_true", help="Räder drehen frei, der mBot2 bleibt stehen")
    ap.add_argument("--welt", metavar="SZENE", help="Szene: zielpunkte, hindernis, raum oder eine .toml-Datei (szenen.py)")
    ap.add_argument("--gui", action="store_true", help="Fenster mit Welt, Hindernissen, mBot2 und Fahrweg")
    ap.add_argument("--plot", action="store_true", help="im Fenster Verläufe: Ultraschall, Drehwinkel, Raddrehzahl")
    ap.add_argument("--kurven", dest="plot", action="store_true", help=argparse.SUPPRESS)   # alter Name
    ap.add_argument("--video", metavar="DATEI.mp4", help="Lauf als Video speichern (braucht imageio-ffmpeg)")
    ap.add_argument("--bild", metavar="DATEI.png", help="letztes Bild des Fensters speichern")
    ap.add_argument("--hell", action="store_true", help="Fenster hell statt dunkel (im Fenster: Taste d)")
    ap.add_argument("--pose", nargs="?", const="x,y,theta", metavar="X,Y,THETA",
                    help="im Fenster auch die vom Programm berechnete Pose zeigen: Namen der globalen Variablen "
                         "(Standard x,y,theta; Meter und rad)")
    a = ap.parse_args(argv)
    if not os.path.exists(a.datei):
        raise SystemExit(f"{a.datei} gibt es nicht")
    cyberpi, mbot2, welt = installieren()
    import event

    import _mbot_welt
    import szenen
    szene = szenen.szene(a.welt) if a.welt else {}
    hindernisse = list(szene.pop("hindernisse", []))
    if a.wand is not None:
        x = US_VORN + a.wand / 100
        hindernisse.append([(x, -1.0), (x + 0.05, -1.0), (x + 0.05, 1.0), (x, 1.0)])
    modell = dict(_mbot_welt.REALISTISCH) if a.realistisch else {}
    welt.konfigurieren(hindernisse=hindernisse, tastatur=True, aufgebockt=a.aufgebockt, protokoll=True,
                       kollision=True, **szene, **modell)         # protokoll: cyberpi.console auch in der Konsole zeigen

    if not hasattr(time, "ticks_ms"):             # MicroPython-Uhr, die es am PC nicht gibt
        time.ticks_ms = lambda: int(time.monotonic() * 1000)
        time.ticks_diff = lambda neu, alt: neu - alt
        time.ticks_add = lambda t, d: t + d

    zeigen = cyberpi.display.show_label
    gezeigt, offen = [0.0, None], [None]          # eine Schleife mit 20 Hz soll die Konsole nicht fluten

    def show_label(message, fontsize=16, x=0, y=0, index=0):
        cyberpi.display._merken(message, index)   # für das Fenster immer, auch wenn die Konsole wartet
        args, kw = (fontsize, x, y, index), {}
        if message == gezeigt[1]:
            return
        if time.monotonic() - gezeigt[0] < 0.5:
            offen[0] = (message, args, kw)        # zu früh: merken, am Ende nachholen
            return
        gezeigt[:], offen[0] = [time.monotonic(), message], None
        zeigen(message, *args, **kw)

    cyberpi.display.show_label = show_label
    sys.path.insert(0, os.path.dirname(os.path.abspath(a.datei)))     # das Programm findet seine Nachbardateien
    mit_fenster = a.gui or a.pose or a.plot or a.video or a.bild
    if mit_fenster:
        print(f"{os.path.basename(a.datei)} auf dem simulierten mBot2. Tasten a, b, m, Pfeile im FENSTER "
              "(nicht im Terminal; reagiert es nicht, einmal rechts in die Anzeige des Fensters klicken). "
              "Ende: Fenster schließen")
    else:
        print(f"{os.path.basename(a.datei)} auf dem simulierten mBot2. Tasten a, b, m, Pfeile hier im Terminal. "
              "Ende: Ctrl+C")
    if mit_fenster:
        g = {"__name__": "__main__", "__file__": os.path.abspath(a.datei)}
        with open(a.datei, encoding="utf-8") as f:
            code = compile(f.read(), os.path.abspath(a.datei), "exec")

        def programm():
            exec(code, g)
            if event.angemeldet():
                while True:                       # Programme mit Tasten-Ereignissen laufen, bis das Fenster zu ist
                    time.sleep(0.2)

        pose = None
        if a.pose:
            namen = [n.strip() for n in a.pose.split(",")]
            if len(namen) != 3:
                raise SystemExit("--pose: drei Namen, z. B. --pose x,y,theta")

            def pose():
                if all(n in g for n in namen):
                    return tuple(float(g[n]) for n in namen)
                return None
        welt.fenster(programm, pose=pose, titel=os.path.basename(a.datei) + " auf dem simulierten mBot2",
                     plot=a.plot, video=a.video, bild=a.bild, thema="hell" if a.hell else "dunkel")
    else:
        try:
            runpy.run_path(a.datei, run_name="__main__")
            if event.angemeldet():
                event.warten()                    # Programme mit Tasten-Ereignissen laufen weiter bis Ctrl+C
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
