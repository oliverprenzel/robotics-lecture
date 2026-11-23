# Labor 2 - Programmgeruest Positionsbestimmung und Navigation
import cyberpi
import mbot2
import math
import time

# Fahrzeugparameter: kalibrierte Werte aus Labor 1 eintragen
R = 0.0          # Radradius in m
B = 0.0          # Spurweite in m

VARIANTE = "B"   # "A": Kurswinkel aus Encodern, "B": Kurswinkel aus Gyroskop
DT = 0.05        # Schleifenzeit in s

# ---- Hardware-Funktionen (wie in Labor 1: EM1 links, EM2 rechts, Motoren gespiegelt) ----
def encoder_winkel():
    # Drehwinkel des linken und rechten Rades in Grad, Vorwaertsfahrt positiv.
    phi_l = mbot2.EM_get_angle(1)
    phi_r = -mbot2.EM_get_angle(2)
    return phi_l, phi_r

def gyro_kurs():
    # Kurswinkel um die Hochachse in Grad, gegen den Uhrzeigersinn positiv.
    # ZU PRUEFEN: Einheit und Vorzeichen (Aufgabe 5.1).
    return cyberpi.get_rotation("z")

def setze_raeder(v_l, v_r):
    # Drehzahl des linken und rechten Rades in U/min, Vorwaertsfahrt positiv.
    mbot2.EM_set_speed(v_l, 1)
    mbot2.EM_set_speed(-v_r, 2)

# ---- Hilfsfunktionen ----
def normiere(winkel):
    # Winkel in rad auf den Bereich -pi bis +pi abbilden
    return (winkel + math.pi) % (2 * math.pi) - math.pi

def begrenze(wert, grenze):
    # Wert auf den Bereich -grenze bis +grenze beschraenken
    return max(-grenze, min(grenze, wert))

# ---- Positionsbestimmung (vorgegeben) ----
# Pose in m und rad. Am PC zeichnet die Simulation sie mit --pose gestrichelt ins Fenster;
# x, y, theta sind dafuer die Standardnamen. Andere Namen dort angeben, z. B. --pose px,py,kurs
x, y, theta = 0.0, 0.0, 0.0
cyberpi.reset_rotation("all")
phi_l_alt, phi_r_alt = encoder_winkel()

def schritt():
    global x, y, theta, phi_l_alt, phi_r_alt
    phi_l, phi_r = encoder_winkel()
    s_l = R * math.radians(phi_l - phi_l_alt)
    s_r = R * math.radians(phi_r - phi_r_alt)
    phi_l_alt, phi_r_alt = phi_l, phi_r

    ds = (s_l + s_r) / 2
    if VARIANTE == "A":
        theta_neu = theta + (s_r - s_l) / B
    else:
        theta_neu = math.radians(gyro_kurs())

    theta_mittel = theta + normiere(theta_neu - theta) / 2
    x += ds * math.cos(theta_mittel)
    y += ds * math.sin(theta_mittel)
    theta = theta_neu

# ---- Anhalten (vorgegeben): am Ende jeder Fahrfunktion aufrufen ----
def anhalten():
    # Motoren stoppen und die Pose fortschreiben, bis beide Raeder stehen: drei Schleifen
    # hintereinander keine Aenderung der Encoderwinkel, hoechstens 20 Schleifen (etwa 1 s)
    setze_raeder(0, 0)
    ruhig = 0
    for _ in range(20):
        alt = encoder_winkel()
        time.sleep(DT)
        schritt()
        ruhig = ruhig + 1 if encoder_winkel() == alt else 0
        if ruhig == 3:
            break

# ---- Fahrfunktionen: von Ihnen zu ergaenzen ----
def drehe_auf(theta_soll):
    # Termin 5: auf der Stelle drehen, bis |normiere(theta_soll - theta)| < Toleranz
    pass

def fahre_gerade(strecke, theta_soll):
    # Termin 6: Strecke fahren und den Kurswinkel mit einem P-Regler halten
    pass

def fahre_zu(x_ziel, y_ziel):
    # Termin 7: Zielpunkt mit Zieltoleranz anfahren
    pass

# ---- Testbetrieb: Roboter von Hand bewegen und Pose beobachten ----
while True:
    schritt()
    # Pose und Radwinkel (L, R: Encoderwinkel links und rechts in Grad, Aufgabe 5.1)
    print("{:.3f};{:.3f};{:.1f};{};{}".format(x, y, math.degrees(theta), phi_l_alt, phi_r_alt))
    # print sieht man nur am PC; im Hochlade-Modus die Werte auf dem Display ablesen
    cyberpi.display.show_label("x={:.2f} y={:.2f}\nth={:.1f}\nL={} R={}".format(
        x, y, math.degrees(theta), phi_l_alt, phi_r_alt), 16, 0, 0)
    time.sleep(DT)
