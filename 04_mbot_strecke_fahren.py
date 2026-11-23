# Mobile Robotik, Oliver Prenzel mit Claude (Anthropic) - github.com/oliverprenzel/robotics-lecture - MIT-Lizenz
#
# mBot2: 1 m geradeaus fahren, die Strecke mit den Radencodern messen.
#
# Diese Datei ist das Programm fuer den mBot2, so wie es in mBlock hochgeladen wird.
# Am PC laeuft sie unveraendert auf dem simulierten mBot2:
#
#     python mbot_sim_start.py 04_mbot_strecke_fahren.py          # nur Konsole
#     python mbot_sim_start.py 04_mbot_strecke_fahren.py --gui    # mit Fenster
#
# Das Programm wartet auf die Taste B. Am PC ist das die Taste b: ohne Fenster im Terminal
# (nur Windows), mit Fenster im Fenster der Simulation.
# Die Fahrt dauert etwa 7 Sekunden. Am Ende nennt der Starter die wahre Strecke: Der simulierte
# mBot2 hat ein Rad, das 1 % groesser ist als angenommen. Die Encoder merken davon nichts.
#
# Ohne Umlaute, damit die Datei auf dem CyberPi sicher laeuft.
import cyberpi, mbot2, time, math

D = 6.5                                    # Raddurchmesser in cm
S = 100.0                                  # Soll-Strecke in cm
ziel = S * 360 / (math.pi * D)             # Drehwinkel des Rades in Grad fuer die Strecke S

cyberpi.display.show_label("Taste B druecken", 16, 0, 0)
while not cyberpi.controller.is_press("b"):
    pass

cyberpi.display.show_label("Ziel: " + str(round(ziel)) + " Grad", 16, 0, 0)
cyberpi.led.on(0, 255, 0)                  # alle LEDs gruen

mbot2.EM_reset_angle(1)
mbot2.EM_reset_angle(2)
mbot2.EM_set_speed(40, 1)                  # 40 U/min; die Motoren sind gespiegelt eingebaut,
mbot2.EM_set_speed(-40, 2)                 # deshalb dreht Motor 2 mit umgekehrtem Vorzeichen

while abs(mbot2.EM_get_angle(1)) < ziel:
    time.sleep(0.01)

mbot2.EM_stop()
cyberpi.led.on(255, 0, 0)                  # alle LEDs rot

weg = abs(mbot2.EM_get_angle(1)) * math.pi * D / 360
cyberpi.display.show_label("Fertig\nEncoder: %.1f cm" % weg, 16, 0, 0)
