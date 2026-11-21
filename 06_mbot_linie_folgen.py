# Mobile Robotik, Oliver Prenzel mit Claude (Anthropic) - github.com/oliverprenzel/robotics-lecture - MIT-Lizenz
#
# mBot2: einer Linie aus Klebeband folgen und vor einem Hindernis anhalten.
#
# Diese Datei ist das Programm fuer den mBot2, so wie es in mBlock hochgeladen wird.
# Am PC laeuft sie unveraendert auf dem simulierten mBot2, in der Szene aus 06_parcours.toml:
#
#     python mbot_sim_start.py 06_mbot_linie_folgen.py --welt 06_parcours.toml --plot
#
# Der Linienfolger (Quad-RGB-Sensor) hat vier Sonden L2, L1, R1, R2 quer zur Fahrtrichtung.
# Aus den Sonden, die das Band sehen, ergibt sich, wie weit die Linie links oder rechts liegt;
# entsprechend lenkt der mBot2 nach (P-Regler). Sieht keine Sonde das Band, dreht er in die
# Richtung, in der er es zuletzt gesehen hat. Der Ultraschallsensor stoppt ihn vor der Kiste.
#
# Taste A startet, Taste B haelt an. Pfeil hoch/runter vor dem Start: Geschwindigkeit.
# Zum Ausprobieren: K groesser oder kleiner, V schneller, die Kiste in 06_parcours.toml verschieben.
#
# Ohne Umlaute und ohne f-Strings, damit die Datei auf dem CyberPi (MicroPython) laeuft.
import cyberpi, mbot2, mbuild, time

V = 25            # U/min Grundgeschwindigkeit
K = 6             # U/min Lenkkorrektur je Einheit Ablage
ABSTAND = 15      # cm: Abstand zum Hindernis geringer: anhalten
GEWICHT = (3, 1, -1, -3)          # Lage der Sonden L2, L1, R1, R2: links positiv


def raeder(v_l, v_r):
    mbot2.EM_set_speed(int(v_l), 1)          # Motoren gespiegelt eingebaut:
    mbot2.EM_set_speed(int(-v_r), 2)         # Motor 2 dreht mit umgekehrtem Vorzeichen


def linie():
    # get_line_sta: ein Bit je Sonde, L2 = hoechstes Bit; Bit gesetzt = Hintergrund, nicht Band
    sta = mbuild.quad_rgb_sensor.get_line_sta("all", 1)
    return [not (sta >> (3 - i)) & 1 for i in range(4)]


# ---- Start ----
cyberpi.led.on(0, 0, 255)
while not cyberpi.controller.is_press("a"):
    if cyberpi.controller.is_press("up"):
        V = min(50, V + 5)
        time.sleep(0.3)
    if cyberpi.controller.is_press("down"):
        V = max(10, V - 5)
        time.sleep(0.3)
    cyberpi.display.show_label("Linie folgen\nV = %d U/min\nhoch/runter\nTaste A: Start" % V, 16, 0, 0)
    time.sleep(0.05)

# ---- Linie folgen ----
cyberpi.led.on(0, 255, 0)
letzte = 0                        # Ablage beim letzten Mal, als eine Sonde das Band sah
grund = "Taste B"
while not cyberpi.controller.is_press("b"):
    abstand = mbuild.ultrasonic2.get(1)
    if abstand < ABSTAND:
        grund = "Hindernis %d cm" % abstand
        break
    auf_band = linie()
    n = sum(1 for s in auf_band if s)
    if n > 0:
        ablage = sum(g for g, s in zip(GEWICHT, auf_band) if s) / n
        letzte = ablage
        u = K * ablage
        raeder(V - u, V + u)
    elif letzte >= 0:             # Band verloren: dorthin drehen, wo es zuletzt war
        raeder(-V / 2, V)
    else:
        raeder(V, -V / 2)
    cyberpi.display.show_label("Linie %d%d%d%d\nUltraschall %d cm"
                               % (auf_band[0], auf_band[1], auf_band[2], auf_band[3], abstand), 16, 0, 0)
    time.sleep(0.02)

mbot2.EM_stop()
cyberpi.led.on(255, 0, 0)
cyberpi.display.show_label("Angehalten\n" + grund, 16, 0, 0)
print("Angehalten: " + grund)
