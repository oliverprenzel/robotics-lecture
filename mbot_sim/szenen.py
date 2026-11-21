"""Szenen für den simulierten mBot2: Hindernisse, Klebeband am Boden, Ziele und Startpose.

    python mbot_sim_start.py PROGRAMM.py --welt zielpunkte --gui  # eingebaute Szene
    python mbot_sim_start.py PROGRAMM.py --welt meine.toml --gui  # eigene Szene aus einer Datei

    from mbot_sim.szenen import szene                  # im eigenen Programm
    welt.konfigurieren(**szene("hindernis"))

Eingebaut: zielpunkte (Startmarke und drei Zielpunkte Z1 bis Z3), hindernis (dazu eine Kiste auf
dem Weg zu Z1) und raum (Raum 3 m × 2 m mit Wänden). Koordinaten in Metern, Ursprung am Start
des mBot2, x in Fahrtrichtung beim Start, y nach links.

Szenendatei (TOML, braucht Python 3.11 oder das Paket tomli):

    name = "Mein Parcours"
    start = [0.0, 0.0, 0.0]               # wahre Startpose: x, y in m, Winkel in Grad (Standard 0, 0, 0)

    [[hindernis]]
    name = "Kiste"
    rechteck = [0.45, -0.075, 0.60, 0.075]  # x0, y0, x1, y1
    [[hindernis]]
    punkte = [[1.0, 0.2], [1.2, 0.2], [1.1, 0.4]]   # beliebiges Vieleck
    [[hindernis]]
    kreis = [1.5, -0.3, 0.1]              # Mitte x, y und Radius

    [[marke]]                             # Klebeband am Boden (Linienfolger)
    von = [0.088, -0.05]
    bis = [0.088, 0.05]
    breite = 0.019                        # m, Standard 19 mm
    [[linie]]                             # Klebeband als Streckenzug durch diese Punkte
    punkte = [[0.0, 0.0], [1.0, 0.0], [1.2, 0.2]]
    geschlossen = false                   # true: zurück zum ersten Punkt

    [[ziel]]                             # nur zum Ansehen im Fenster
    punkt = [1.2, 0.8]
    name = "Ziel"
"""
import math
import os

BAND = 0.019                                          # m, Klebeband
STARTMARKE = ((0.088, -0.05), (0.088, 0.05), BAND)    # quer unter dem Linienfolger, 8,8 cm vor der Radachse

_ZIELPUNKTE = [(1.2, 0.0, "Z1"), (1.2, 0.8, "Z2"), (0.4, 0.8, "Z3")]       # nur zum Ansehen im Fenster


def _rechteck(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _kreis(x, y, r, n=24):
    return [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def _wand(x0, y0, x1, y1, d=0.05):
    """Raum mit Wänden der Dicke d um das Innere x0..x1, y0..y1."""
    return [_rechteck(x0 - d, y0 - d, x1 + d, y0), _rechteck(x0 - d, y1, x1 + d, y1 + d),
            _rechteck(x0 - d, y0, x0, y1), _rechteck(x1, y0, x1 + d, y1)]


EINGEBAUT = {
    "zielpunkte": dict(marken=[STARTMARKE], ziele=_ZIELPUNKTE),
    "hindernis": dict(marken=[STARTMARKE], ziele=_ZIELPUNKTE,
                      hindernisse=[_rechteck(0.45, -0.075, 0.60, 0.075)]),
    "raum": dict(marken=[STARTMARKE], hindernisse=_wand(-0.5, -1.0, 2.5, 1.0)),
}


def szene(name):
    """Szene als Argumente für welt.konfigurieren(): eingebaut (Name) oder aus einer TOML-Datei."""
    if name in EINGEBAUT:
        return {k: list(v) for k, v in EINGEBAUT[name].items()}
    if not os.path.exists(name):
        raise SystemExit(f"Szene {name!r} gibt es nicht; eingebaut: {', '.join(EINGEBAUT)}, oder eine .toml-Datei")
    try:
        import tomllib
    except ImportError:                               # Python 3.10
        try:
            import tomli as tomllib
        except ImportError:
            raise SystemExit("Szenendateien brauchen Python 3.11 oder das Paket tomli (pip install tomli)")
    with open(name, "rb") as f:
        d = tomllib.load(f)
    hindernisse = []
    for h in d.get("hindernis", []):
        if "rechteck" in h:
            hindernisse.append(_rechteck(*h["rechteck"]))
        elif "kreis" in h:
            hindernisse.append(_kreis(*h["kreis"]))
        elif "punkte" in h:
            hindernisse.append([tuple(p) for p in h["punkte"]])
        else:
            raise SystemExit(f"{name}: Hindernis {h.get('name', '')!r} braucht rechteck, kreis oder punkte")
    marken = [(tuple(m["von"]), tuple(m["bis"]), float(m.get("breite", BAND))) for m in d.get("marke", [])]
    for li in d.get("linie", []):                     # Streckenzug: ein Stück Klebeband je Abschnitt
        p = [tuple(q) for q in li["punkte"]]
        if li.get("geschlossen", False):
            p.append(p[0])
        marken += [(a, b, float(li.get("breite", BAND))) for a, b in zip(p, p[1:])]
    ziele = [(z["punkt"][0], z["punkt"][1], z.get("name", "")) for z in d.get("ziel", [])]
    x, y, grad = d.get("start", (0.0, 0.0, 0.0))
    return dict(hindernisse=hindernisse, marken=marken, ziele=ziele, start=(x, y, math.radians(grad)))
