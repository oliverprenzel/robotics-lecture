# Mobile Robotik, Oliver Prenzel mit Claude (Anthropic) · github.com/oliverprenzel/robotics-lecture · MIT-Lizenz
"""mBot2 ohne Gerät: geradeaus fahren, vor einer Wand anhalten, 90° nach links drehen.

    python 05_mbot_wand.py

Die Funktion fahrt() enthält das Programm, wie es am mBot2 läuft: Der Ultraschallsensor misst
den Abstand zur Wand, der Gyro den Drehwinkel. Am PC kommen `cyberpi`, `mbot2` und `mbuild` aus
dem Ordner mbot_sim/, die Wand ist ein Hindernis in der simulierten Welt. Der simulierte mBot2
läuft in Echtzeit, die Fahrt dauert einige Sekunden.

Ein Fenster zeigt live die Welt von oben und darunter den Verlauf von Ultraschall-Abstand,
Drehwinkel und Raddrehzahlen (mbot_sim/fenster.py). Die Fahrt läuft in einem eigenen Thread,
das Fenster im Hauptthread. So bremst das Zeichnen die Regelung nicht.
"""
import math
import time

from mbot_sim import installieren

cyberpi, mbot2, welt = installieren()      # ab jetzt liefern import cyberpi, mbot2, mbuild den simulierten mBot2
import mbuild

# Wand quer zur Fahrtrichtung, 60 cm vor dem Start
WAND = [(0.60, -0.5), (0.65, -0.5), (0.65, 0.5), (0.60, 0.5)]
welt.konfigurieren(hindernisse=[WAND], kollision=True)


# ---------------------------------------------------------------- Fahrt, so wie am mBot2
def fahrt():
    us = mbuild.ultrasonic2.get(1)
    print("Start:  Ultraschall", us, "cm,  Akku", cyberpi.get_battery(), "%")

    # Geradeaus, bis die Wand näher als 20 cm ist
    mbot2.EM_reset_angle("ALL")
    mbot2.forward(50)
    while mbuild.ultrasonic2.get(1) > 20:
        time.sleep(0.01)
    mbot2.EM_stop("ALL")
    time.sleep(0.3)                         # ausrollen lassen

    links, rechts = mbot2.EM_get_angle("EM1"), mbot2.EM_get_angle("EM2")
    weg = abs(links) / 360 * 2 * math.pi * 3.25        # Raddurchmesser 6,5 cm
    x, y, th = welt.wahr()
    print(f"Halt:   Encoder EM1 {links}°, EM2 {rechts}°  ->  etwa {weg:.1f} cm gefahren")
    print(f"        wahr: x = {x * 100:.1f} cm, Ultraschall {mbuild.ultrasonic2.get(1)} cm")

    # 90° nach links drehen, gemessen mit dem Gyro
    cyberpi.reset_rotation("z")
    mbot2.turn_left(30)
    while cyberpi.get_rotation("z") < 90:
        time.sleep(0.01)
    mbot2.EM_stop("ALL")
    time.sleep(0.3)

    x, y, th = welt.wahr()
    print(f"Dreh:   Gyro {cyberpi.get_rotation('z'):.0f}°, wahr {math.degrees(th):.0f}°")
    print(f"        Ultraschall jetzt {mbuild.ultrasonic2.get(1)} cm (Wand liegt seitlich)")
    print("Fertig, Fenster schließen zum Beenden")


# ---------------------------------------------------------------- Anzeige
welt.fenster(fahrt, plot=True, titel="mBot2, simuliert: vor der Wand anhalten")
