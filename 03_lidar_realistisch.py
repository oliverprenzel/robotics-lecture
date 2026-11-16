"""Demo: Derselbe Flur wie in 02_flur_mapping.py, so wie ihn ein echter Laserscanner sieht.

Nur zum Vorführen, das Skript läuft am Stück:
    .venvLecture\\Scripts\\python lecture\\03_lidar_realistisch.py

Der Scanner entspricht dem Beispiel aus Vorlesung 5: 270° in 0,25°-Schritten, 1081 Strahlen.
Hinter dem Scanner liegt ein toter Winkel von 90°.

Effekte echter Scans:
- Rauschen des Abstands, wächst mit der Entfernung
- Aussetzer bei streifend getroffenen Flächen
- Mischpixel: Punkte in der Luft an Kanten, wenn ein Strahl zwei Flächen trifft
- vereinzelte Ausreißer, etwa durch Staub
- Intensität: nahe und senkrecht getroffene Flächen reflektieren stärker

Farbe der Punkte: Intensität des aktuellen Scans. Der blaue Untergrund sammelt alle bisherigen Punkte.
Die Bahn des Bots ist bekannt, die Punkte werden also ohne Lokalisierungsfehler eingetragen.
"""
import matplotlib
matplotlib.use("TkAgg")
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, Wedge

from lidar_sim import flur, strahlen

# Derselbe Flur wie in 02_flur_mapping.py
LAENGE, BREITE = 10.0, 2.0
EINBUCHTUNGEN = [
    ("links", 2.0, 3.0, 0.8),
    ("rechts", 4.0, 5.0, 1.0),
    ("links", 6.5, 8.0, 0.5),
]

OEFFNUNG = 270         # Öffnungswinkel in Grad
DELTA_PHI = 0.25       # Schrittweite in Grad
SCHRITT = 0.04         # Fahrweg zwischen zwei Scans in Metern
PAUSE = 0.03           # Wartezeit nach jedem Scan in Sekunden, größer: langsamer

X_MIN, X_MAX = -0.5, 10.5
Y_MIN, Y_MAX = -3.0, 3.0
ZELLE = 0.02           # Auflösung des Untergrunds in Metern

HINTERGRUND = "#0b0f14"
LINIEN = "#2a3644"
SCHRIFT = "#c9d3de"


def echter_scan(x, y, gier, winkel, strecken, rng):
    """Liefert die Punkte eines Scans in Flurkoordinaten und ihre Intensität."""
    phi = gier + winkel
    r, cos_einfall = strahlen(phi, (x, y), strecken)
    n = len(r)

    # Mischpixel: An Sprüngen landet ein Teil der Strahlen zwischen den Flächen
    kanten = np.flatnonzero(np.abs(np.diff(r)) > 0.25)
    kanten = kanten[rng.random(len(kanten)) < 0.5]
    r_rein = r.copy()
    r[kanten] += rng.uniform(0.2, 0.8, len(kanten)) * (r_rein[kanten + 1] - r_rein[kanten])

    # Rauschen wächst mit der Entfernung
    r += rng.normal(0.0, 0.006 + 0.002 * r)

    # Ausreißer durch Staub
    staub = rng.random(n) < 0.001
    r[staub] *= rng.uniform(0.2, 0.9, staub.sum())

    # Intensität mit Speckle, Mischpixel und Staub sind schwach
    intensitaet = np.sqrt(cos_einfall) / (1 + (r / 6) ** 2) * rng.lognormal(0.0, 0.25, n)
    intensitaet[kanten] *= 0.4
    intensitaet[staub] *= 0.3

    # Aussetzer: flacher Einfall und große Entfernung kosten Echos
    p_aussetzer = 0.01 + 0.7 * (1 - cos_einfall) ** 3 + 0.01 * r
    da = (rng.random(n) > p_aussetzer) & np.isfinite(r)

    return (x + r[da] * np.cos(phi[da]), y + r[da] * np.sin(phi[da]),
            np.clip(intensitaet[da], 0.0, 1.0), n)


def main():
    rng = np.random.default_rng(3)
    strecken = flur(LAENGE, BREITE, EINBUCHTUNGEN)
    anzahl = round(OEFFNUNG / DELTA_PHI) + 1
    winkel = np.deg2rad(np.linspace(-OEFFNUNG / 2, OEFFNUNG / 2, anzahl))

    summe = np.zeros((round((Y_MAX - Y_MIN) / ZELLE), round((X_MAX - X_MIN) / ZELLE)))

    fig, ax = plt.subplots(figsize=(13, 7.5), facecolor=HINTERGRUND)
    fig.canvas.manager.set_window_title("Laserscan im Flur")
    ax.set_facecolor(HINTERGRUND)
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")
    ax.set_xticks(np.arange(0, 11))
    ax.set_yticks(np.arange(-3, 4))
    ax.grid(True, color=LINIEN, linewidth=0.5)
    ax.tick_params(colors=SCHRIFT, labelsize=9, length=0)
    ax.set_xlabel("x in m", color=SCHRIFT)
    ax.set_ylabel("y in m", color=SCHRIFT)
    for rand in ax.spines.values():
        rand.set_color(LINIEN)

    untergrund = LinearSegmentedColormap.from_list("spur", [HINTERGRUND, "#1d4e6b", "#4aa3c7"])
    bild = ax.imshow(summe, cmap=untergrund, vmin=0, vmax=1, origin="lower", zorder=1,
                     extent=(X_MIN, X_MAX, Y_MIN, Y_MAX), interpolation="nearest")
    punkte = ax.scatter([], [], c=[], s=3, cmap="turbo", vmin=0, vmax=1, linewidths=0, zorder=3)
    blick = Wedge((0, 0), 1.0, 0, 0, facecolor="#ffffff", alpha=0.06, zorder=2)
    ax.add_patch(blick)
    ringe = [Circle((0, 0), d, fill=False, edgecolor="#5c7186", linewidth=0.6, linestyle=":", zorder=2)
             for d in (1, 2, 4)]
    for ring in ringe:
        ax.add_patch(ring)
    bot, = ax.plot([], [], marker=(3, 0, -90), color="white", markersize=11, zorder=4)
    anzeige = ax.text(0.01, 0.97, "", transform=ax.transAxes, va="top", color=SCHRIFT,
                      family="monospace", fontsize=10, zorder=5)
    fig.tight_layout()

    for k, x in enumerate(np.arange(0.5, 9.5, SCHRITT)):
        if not plt.fignum_exists(fig.number):      # Fenster wurde geschlossen
            return

        # Der Bot fährt nicht perfekt gerade
        y = 0.06 * np.sin(1.3 * x)
        gier = 0.078 * np.cos(1.3 * x) + rng.normal(0.0, 0.002)

        px, py, intensitaet, n = echter_scan(x, y, gier, winkel, strecken, rng)

        spalte = ((px - X_MIN) / ZELLE).astype(int)
        zeile = ((py - Y_MIN) / ZELLE).astype(int)
        drin = (spalte >= 0) & (spalte < summe.shape[1]) & (zeile >= 0) & (zeile < summe.shape[0])
        np.add.at(summe, (zeile[drin], spalte[drin]), 1.0)

        bild.set_data(1 - np.exp(-0.5 * summe))
        punkte.set_offsets(np.column_stack((px, py)))
        punkte.set_array(intensitaet)
        blick.set_center((x, y))
        blick.set_radius(12.0)
        blick.set_theta1(np.rad2deg(gier) - OEFFNUNG / 2)
        blick.set_theta2(np.rad2deg(gier) + OEFFNUNG / 2)
        for ring in ringe:
            ring.set_center((x, y))
        bot.set_data([x], [y])
        anzeige.set_text(f"Scan {k + 1:4d}   {len(px):4d} von {n} Strahlen mit Echo   "
                         f"{OEFFNUNG}° in {DELTA_PHI}°-Schritten")
        plt.pause(PAUSE)

    plt.show()


if __name__ == "__main__":
    main()
