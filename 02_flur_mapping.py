# Mobile Robotik, Oliver Prenzel mit Claude (Anthropic) · github.com/oliverprenzel/robotics-lecture · MIT-Lizenz
# %% [markdown]
# # Mapping: Ein Bot entdeckt einen Flur mit Einbuchtungen
#
# Der Bot fährt durch den Flur und scannt nach jedem Schritt. Die Karte ist ein Gitter,
# jede Zelle ist unbekannt (grau), frei (weiß) oder belegt (schwarz):
#
# - Die Zellen entlang eines Strahls sind frei.
# - Die Zelle am Ende des Strahls ist belegt.
# - Wo kein Strahl hinkommt, bleibt die Zelle unbekannt.
#
# Vereinfachung: Der Bot kennt seine Position exakt, es gibt also keinen Lokalisierungsfehler.
#
# Die Animation läuft in einem eigenen Fenster. Zum Weitermachen das Fenster schließen.

# %% Vorbereitung
import matplotlib
matplotlib.use("TkAgg")      # eigenes Fenster, im Interactive Window läuft keine Animation
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from lidar_sim import flur, messe

# %% Parameter. Hier live ändern und die Zellen darunter neu ausführen
laenge, breite = 10.0, 2.0     # Flur in Metern
einbuchtungen = [              # Seite, von x, bis x, Tiefe
    ("links", 2.0, 3.0, 0.8),
    ("rechts", 4.0, 5.0, 1.0),
    ("links", 6.5, 8.0, 0.5),
]

delta_phi = 5      # Schrittweite des Scanners in Grad
r_max = 3.0        # Reichweite des Scanners in Metern
rauschen = 0.01    # Standardabweichung in Metern
schritt = 0.05      # Fahrweg zwischen zwei Scans in Metern
zelle = 0.1        # Kantenlänge einer Gitterzelle in Metern
pause = 0.2        # Wartezeit nach jedem Scan in Sekunden, größer: langsamer

# %% Flur und leere Karte
strecken = flur(laenge, breite, einbuchtungen)
phi_grad = np.arange(0, 360, delta_phi)

UNBEKANNT, FREI, BELEGT = 0.5, 1.0, 0.0

rand = 0.5
x_min, x_max = -rand, laenge + rand
y_min, y_max = -breite / 2 - 1.5, breite / 2 + 1.5
karte = np.full((round((y_max - y_min) / zelle), round((x_max - x_min) / zelle)), UNBEKANNT)


def zelle_von(x, y):
    """Zeile und Spalte der Gitterzelle zu den Koordinaten x, y."""
    spalte = np.clip(((x - x_min) / zelle).astype(int), 0, karte.shape[1] - 1)
    zeile = np.clip(((y - y_min) / zelle).astype(int), 0, karte.shape[0] - 1)
    return zeile, spalte


# %% Ein Scan aktualisiert die Karte
def trage_scan_ein(x_S, y_S, r):
    """Trägt einen Scan von der Position (x_S, y_S) in die Karte ein."""
    phi = np.deg2rad(phi_grad)
    for ri, p in zip(r, phi):
        laenge_strahl = min(ri, r_max)                       # ohne Echo: frei bis zur Reichweite
        s = np.arange(0, laenge_strahl, zelle / 2)           # Punkte entlang des Strahls
        z, sp = zelle_von(x_S + s * np.cos(p), y_S + s * np.sin(p))
        frei = karte[z, sp] != BELEGT
        karte[z[frei], sp[frei]] = FREI
        if ri < r_max:                                       # Echo: Hier ist ein Hindernis
            xe, ye = np.array([x_S + ri * np.cos(p)]), np.array([y_S + ri * np.sin(p)])
            karte[zelle_von(xe, ye)] = BELEGT


# %% Fahrt durch den Flur
fig, (ax_welt, ax_karte) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

for (x1, y1), (x2, y2) in strecken:
    ax_welt.plot([x1, x2], [y1, y2], color="black", linewidth=2)
strahlen = LineCollection([], colors="tab:red", linewidths=0.4, alpha=0.5)
ax_welt.add_collection(strahlen)
bot, = ax_welt.plot([], [], "o", color="tab:blue", markersize=10)
ax_welt.set_title("Wirklichkeit: Der Bot scannt")
ax_welt.set_ylabel("y in m")
ax_welt.set_ylim(y_min, y_max)
ax_welt.set_aspect("equal")

bild = ax_karte.imshow(karte, cmap="gray", vmin=0, vmax=1, origin="lower",
                       extent=(x_min, x_max, y_min, y_max), interpolation="nearest")
spur, = ax_karte.plot([], [], "-", color="tab:blue", linewidth=1)
ax_karte.set_title("Karte des Bots: grau unbekannt, weiß frei, schwarz belegt")
ax_karte.set_xlabel("x in m")
ax_karte.set_ylabel("y in m")

fig.tight_layout()

bahn_x = np.arange(0.5, laenge - 0.4, schritt)
y_S = 0.0                                            # Der Bot fährt auf der Mittellinie

for k, x_S in enumerate(bahn_x):
    r = messe(phi_grad, sensor=(x_S, y_S), rauschen=rauschen, seed=k, strecken=strecken)
    trage_scan_ein(x_S, y_S, r)

    enden = np.minimum(np.nan_to_num(r, nan=r_max), r_max)
    phi = np.deg2rad(phi_grad)
    strahlen.set_segments([[(x_S, y_S), (x_S + d * np.cos(p), y_S + d * np.sin(p))]
                           for d, p in zip(enden, phi)])
    bot.set_data([x_S], [y_S])
    bild.set_data(karte)
    spur.set_data(bahn_x[:k + 1], np.full(k + 1, y_S))
    plt.pause(pause)

bekannt = np.mean(karte != UNBEKANNT) * 100
print(f"{len(bahn_x)} Scans, {bekannt:.0f} % der Gitterzellen bekannt")
plt.show()

# %% [markdown]
# ## Diskussion
#
# - Warum wird die Einbuchtung erst vollständig sichtbar, wenn der Bot auf ihrer Höhe ist?
# - Warum bleiben die Bereiche hinter den Wänden grau, also unbekannt und nicht frei?
# - Was passiert mit der Karte bei `r_max = 1.5` oder `delta_phi = 15`?
# - Was würde passieren, wenn die Position des Bots ungenau wäre?
