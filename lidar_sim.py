# Mobile Robotik, Oliver Prenzel mit Claude (Anthropic) · github.com/oliverprenzel/robotics-lecture · MIT-Lizenz
"""Kleiner Laserscanner-Simulator für die Vorlesungsbeispiele.

Szene aus Skript 3.5: Der Roboter steht im Ursprung und schaut in +x-Richtung
(x nach vorn, y nach links). Eine lange, gerade Wand steht 1,0 m vor ihm,
davor, etwas links, eine Kiste. Die Szene besteht aus Strecken.
"""
import numpy as np

WAND_X = 1.0                       # Abstand der Wand [m]
WAND_Y = (-5.0, 5.0)               # Länge der Wand [m]
KISTE_X = (0.6, 0.9)               # Vorderseite bei 0,6 m; die Tiefe von 0,3 m ist angenommen
KISTE_Y = (0.1, 0.4)               # Breite der Kiste [m]


def szene():
    """Liefert die Szene als Liste von Strecken ((x1, y1), (x2, y2))."""
    x0, x1 = KISTE_X
    y0, y1 = KISTE_Y
    return [
        ((WAND_X, WAND_Y[0]), (WAND_X, WAND_Y[1])),
        ((x0, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    ]


def flur(laenge, breite, einbuchtungen):
    """Liefert einen geschlossenen Flur als Liste von Strecken.

    Der Flur liegt um die x-Achse, von x = 0 bis x = laenge.
    einbuchtungen: Liste von (seite, x_von, x_bis, tiefe), seite "links" (+y) oder "rechts" (-y)
    """
    h = breite / 2
    punkte = [(0.0, -h)]
    for _, x0, x1, t in sorted((e for e in einbuchtungen if e[0] == "rechts"), key=lambda e: e[1]):
        punkte += [(x0, -h), (x0, -h - t), (x1, -h - t), (x1, -h)]
    punkte += [(laenge, -h), (laenge, h)]
    for _, x0, x1, t in sorted((e for e in einbuchtungen if e[0] == "links"), key=lambda e: -e[1]):
        punkte += [(x1, h), (x1, h + t), (x0, h + t), (x0, h)]
    punkte += [(0.0, h)]
    return list(zip(punkte, punkte[1:] + punkte[:1]))


def zeichne_szene(ax, ausschnitt_y=(-2.0, 2.0)):
    """Zeichnet Wand und Kiste von oben in hellem Grau."""
    wand, *kiste = szene()
    (x1, _), (x2, _) = wand
    ax.plot([x1, x2], ausschnitt_y, color="lightgray", linewidth=4)
    for (x1, y1), (x2, y2) in kiste:
        ax.plot([x1, x2], [y1, y2], color="lightgray", linewidth=4)


def strahlen(phi, sensor, strecken):
    """Schneidet alle Strahlen mit allen Strecken.

    phi: Richtungen der Strahlen in Radiant
    Liefert r (Abstand bis zum ersten Treffer, NaN ohne Treffer) und cos_einfall
    (1: senkrecht auf die Fläche, nahe 0: streifend).
    """
    phi = np.asarray(phi, dtype=float)
    dx, dy = np.cos(phi)[:, None], np.sin(phi)[:, None]
    punkte = np.array(strecken, dtype=float)
    a = punkte[:, 0] - sensor
    e = punkte[:, 1] - punkte[:, 0]
    nenner = dx * e[:, 1] - dy * e[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (a[:, 0] * e[:, 1] - a[:, 1] * e[:, 0]) / nenner   # Weg entlang des Strahls
        u = (a[:, 0] * dy - a[:, 1] * dx) / nenner             # Lage auf der Strecke (0..1)
    t[~((np.abs(nenner) > 1e-12) & (t > 0) & (u >= 0) & (u <= 1))] = np.inf
    i = np.arange(len(phi))
    j = np.argmin(t, axis=1)
    r = t[i, j]
    cos_einfall = np.abs(nenner[i, j]) / np.linalg.norm(e[j], axis=1)
    r[np.isinf(r)] = np.nan
    return r, cos_einfall


def messe(phi_grad, sensor=(0.0, 0.0), rauschen=0.0, seed=1, strecken=None):
    """Simuliert einen Scan.

    phi_grad: Winkel der Strahlen in Grad
    sensor:   Position (x_S, y_S) des Scanners in Metern
    rauschen: Standardabweichung des Abstands in Metern
    strecken: Szene als Liste von Strecken, ohne Angabe die Szene aus Skript 3.5
    Liefert die Abstände r in Metern (NaN: kein Echo).
    """
    if strecken is None:
        strecken = szene()
    s = np.array(sensor)
    rng = np.random.default_rng(seed)
    r, _ = strahlen(np.deg2rad(phi_grad), s, strecken)
    return r + rng.normal(0.0, rauschen, r.shape)
