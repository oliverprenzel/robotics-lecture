# Mobile Robotik, Oliver Prenzel mit Claude (Anthropic) · github.com/oliverprenzel/robotics-lecture · MIT-Lizenz
"""mBot2 ohne Gerät: 1 m geradeaus fahren, die Strecke mit den Radencodern messen.

    python 04_mbot_strecke_fahren.py

Das Programm zwischen den beiden Trennlinien ist dasselbe, das in mBlock auf den mBot2 geladen
wird. Am PC kommen `cyberpi` und `mbot2` aus dem Ordner mbot_sim/: ein nachgebauter mBot2 mit
Motoren, Encodern, Gyro, Ultraschall, Tasten und Anzeige. Er läuft in Echtzeit, die Fahrt dauert
etwa 7 Sekunden. Die Anzeige des CyberPi erscheint in der Konsole.

Der simulierte mBot2 hat ein Rad, das 1 % größer ist als angenommen. Die Encoder merken davon
nichts: Der Bot hält, wenn er glaubt, 100 cm gefahren zu sein, und steht in Wahrheit weiter vorn.
"""
from mbot_sim import installieren

cyberpi, mbot2, welt = installieren()      # ab jetzt liefern import cyberpi, mbot2, mbuild den simulierten mBot2

# ---------------------------------------------------------------- Programm wie am mBot2
import math
import time

D = 6.5                                    # Raddurchmesser in cm
S = 100.0                                  # Soll-Strecke in cm
ziel = S * 360 / (math.pi * D)             # Drehwinkel des Rades in Grad für die Strecke S

cyberpi.display.show_label("Ziel: " + str(round(ziel)) + " Grad", 16, 0, 0)
cyberpi.led.on(0, 255, 0)                  # alle LEDs grün

mbot2.EM_reset_angle(1)
mbot2.EM_reset_angle(2)
mbot2.EM_set_speed(40, 1)                  # 40 U/min; die Motoren sind gespiegelt eingebaut,
mbot2.EM_set_speed(-40, 2)                 # deshalb dreht Motor 2 mit umgekehrtem Vorzeichen

while abs(mbot2.EM_get_angle(1)) < ziel:
    time.sleep(0.01)

mbot2.EM_stop()
cyberpi.led.on(255, 0, 0)                  # alle LEDs rot
cyberpi.display.show_label("Fertig", 16, 0, 0)
# ---------------------------------------------------------------- Ende des Programms

# Nur am PC: Die Simulation kennt die wahre Position. Am echten mBot2 misst das Maßband.
x, y, th = welt.wahr()
print("Encoder: %.1f cm gefahren" % (abs(mbot2.EM_get_angle(1)) * math.pi * D / 360))
print("wahr:    %.1f cm gefahren, %.1f cm seitlich, %.1f Grad gedreht" % (100 * x, 100 * y, math.degrees(th)))
