# Mobile Robotik, Oliver Prenzel mit Claude (Anthropic) · github.com/oliverprenzel/robotics-lecture · MIT-Lizenz
"""mBot2 ohne Gerät: geradeaus fahren, vor einer Wand anhalten, 90° nach links drehen.

    python 05_mbot_wand.py

Die Funktion fahrt() enthält das Programm, wie es am mBot2 läuft: Der Ultraschallsensor misst
den Abstand zur Wand, der Gyro den Drehwinkel. Am PC kommen `cyberpi`, `mbot2` und `mbuild` aus
dem Ordner mbot_sim/, die Wand ist ein Hindernis in der simulierten Welt. Der simulierte mBot2
läuft in Echtzeit, die Fahrt dauert einige Sekunden.

Ein Fenster zeigt live die Welt von oben, den Ultraschall-Abstand und den Drehwinkel.
Die Fahrt läuft in einem eigenen Thread, das Fenster im Hauptthread. So bremst das
Zeichnen die Regelung nicht.
"""
import math
import threading
import time

import matplotlib.pyplot as plt

from mbot_sim import installieren

cyberpi, mbot2, welt = installieren()      # ab jetzt liefern import cyberpi, mbot2, mbuild den simulierten mBot2
import mbuild

# Wand quer zur Fahrtrichtung, 60 cm vor dem Start
WAND = [(0.60, -0.5), (0.65, -0.5), (0.65, 0.5), (0.60, 0.5)]
welt.konfigurieren(hindernisse=[WAND])

t0 = time.monotonic()
log = {"t": [], "x": [], "y": [], "th": [], "us": [], "rot": []}


def messen():
    """Ultraschall [cm] und Drehwinkel [°] lesen und mit der wahren Pose protokollieren."""
    x, y, th = welt.wahr()
    us = mbuild.ultrasonic2.get(1)
    rot = cyberpi.get_rotation("z")
    for k, v in zip(log, (time.monotonic() - t0, x, y, th, us, rot)):
        log[k].append(v)
    return us, rot


def warten(sekunden):
    """Weiter messen, während der mBot ausläuft."""
    ende = time.monotonic() + sekunden
    while time.monotonic() < ende:
        messen()
        time.sleep(0.01)


# ---------------------------------------------------------------- Fahrt, so wie am mBot2
def fahrt():
    us, _ = messen()
    print("Start:  Ultraschall", us, "cm,  Akku", cyberpi.get_battery(), "%")

    # Geradeaus, bis die Wand näher als 20 cm ist
    mbot2.EM_reset_angle("ALL")
    mbot2.forward(50)
    while messen()[0] > 20:
        time.sleep(0.01)
    mbot2.EM_stop("ALL")
    warten(0.3)

    links, rechts = mbot2.EM_get_angle("EM1"), mbot2.EM_get_angle("EM2")
    weg = abs(links) / 360 * 2 * math.pi * 3.25        # Raddurchmesser 6,5 cm
    x, y, th = welt.wahr()
    print(f"Halt:   Encoder EM1 {links}°, EM2 {rechts}°  ->  etwa {weg:.1f} cm gefahren")
    print(f"        wahr: x = {x * 100:.1f} cm, Ultraschall {mbuild.ultrasonic2.get(1)} cm")

    # 90° nach links drehen, gemessen mit dem Gyro
    cyberpi.reset_rotation("z")
    mbot2.turn_left(30)
    while messen()[1] < 90:
        time.sleep(0.01)
    mbot2.EM_stop("ALL")
    warten(0.3)

    x, y, th = welt.wahr()
    print(f"Dreh:   Gyro {cyberpi.get_rotation('z'):.0f}°, wahr {math.degrees(th):.0f}°")
    print(f"        Ultraschall jetzt {mbuild.ultrasonic2.get(1)} cm (Wand liegt seitlich)")
    print("Fertig, Fenster schließen zum Beenden")


# ---------------------------------------------------------------- Anzeige
fig, (ax_welt, ax_us, ax_rot) = plt.subplots(1, 3, figsize=(14, 4.5),
                                             gridspec_kw={"width_ratios": [1.3, 1, 1]})
fig.canvas.manager.set_window_title("mBot2, simuliert")

ax_welt.fill(*zip(*WAND), color="gray")
spur, = ax_welt.plot([], [], "-", color="tab:blue", linewidth=1)
bot, = ax_welt.plot([], [], marker=(3, 0, -90), color="tab:blue", markersize=14, linestyle="")
ax_welt.set_xlim(-0.15, 0.8)
ax_welt.set_ylim(-0.45, 0.45)
ax_welt.set_aspect("equal")
ax_welt.grid(True)
ax_welt.set_title("Welt von oben (wahre Pose)")
ax_welt.set_xlabel("x in m")
ax_welt.set_ylabel("y in m")

linie_us, = ax_us.plot([], [], color="tab:orange")
ax_us.axhline(20, color="gray", linestyle=":", linewidth=1)
ax_us.set_title("Ultraschall (Halt unter 20 cm)")
ax_us.set_xlabel("Zeit in s")
ax_us.set_ylabel("Abstand in cm")
ax_us.grid(True)

linie_rot, = ax_rot.plot([], [], color="tab:green")
ax_rot.axhline(90, color="gray", linestyle=":", linewidth=1)
ax_rot.set_title("Drehwinkel z (Gyro, Halt bei 90°)")
ax_rot.set_xlabel("Zeit in s")
ax_rot.set_ylabel("Winkel in °")
ax_rot.grid(True)
fig.tight_layout()


def zeichnen():
    n = len(log["t"])                       # nur vollständig geschriebene Zeilen zeichnen
    if n == 0:
        return
    d = {k: v[:n] for k, v in log.items()}
    spur.set_data(d["x"], d["y"])
    bot.set_data([d["x"][-1]], [d["y"][-1]])
    bot.set_marker((3, 0, math.degrees(d["th"][-1]) - 90))
    linie_us.set_data(d["t"], d["us"])
    linie_rot.set_data(d["t"], d["rot"])
    for ax in (ax_us, ax_rot):
        ax.relim()
        ax.autoscale_view()


thread = threading.Thread(target=fahrt, daemon=True)
thread.start()
while thread.is_alive() and plt.fignum_exists(fig.number):
    zeichnen()
    plt.pause(0.1)
zeichnen()
plt.show()
