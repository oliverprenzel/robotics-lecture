# Mobile Robotik: Codebeispiele zur Vorlesung

Beispiele zum Nachvollziehen und Ausprobieren: Laserscans auswerten, einen Flur kartieren und
Programme für den mBot2 ohne Gerät am PC testen.

## Einrichten

Python 3.10 oder neuer. Im Ordner dieses Repos:

```powershell
python -m venv .venv                    # einmalig: eigene Python-Umgebung anlegen
.venv\Scripts\Activate.ps1              # in jedem neuen Terminal: Umgebung aktivieren
pip install -r requirements.txt         # einmalig: Pakete installieren
python 01_lidar_polar_kartesisch.py     # alles am Stück
```

Nach dem Aktivieren steht `(.venv)` vor der Eingabezeile. Meldet PowerShell, dass Skripte nicht
ausgeführt werden dürfen, einmalig `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` eingeben.
Unter Linux und macOS aktiviert `source .venv/bin/activate`.

In VS Code läuft jede Zelle (`# %%`) einzeln mit Shift+Enter. Als Interpreter `.venv` wählen.

## Inhalt

| Datei | Inhalt |
|---|---|
| [01_lidar_polar_kartesisch.py](01_lidar_polar_kartesisch.py) | Auswertung eines Laserscans: Kiste vor Wand, Polarplot, Umrechnung nach x und y |
| [02_flur_mapping.py](02_flur_mapping.py) | Mapping: Ein Bot entdeckt einen Flur mit Einbuchtungen, Animation im eigenen Fenster |
| [03_lidar_realistisch.py](03_lidar_realistisch.py) | Derselbe Flur wie ein echter Scan, mit Rauschen, Aussetzern und Mischpixeln |
| [04_mbot_strecke_fahren.py](04_mbot_strecke_fahren.py) | mBot2 ohne Gerät: 1 m geradeaus nach den Radencodern, Vergleich mit der wahren Strecke |
| [filtern.py](filtern.py) | Messwerte filtern: Plausibilitätsprüfung, gleitender Mittelwert, gleitender Median |
| [lidar_sim.py](lidar_sim.py) | Kleiner Laserscanner-Simulator für die Beispiele |
| [mbot_sim/](mbot_sim/) | Simulierter mBot2 für den PC: `cyberpi`, `mbot2`, `mbuild` ohne Gerät |

## mBot2 ohne Gerät

```python
from mbot_sim import installieren
cyberpi, mbot2, welt = installieren()     # danach liefern import cyberpi, mbot2, mbuild den simulierten mBot2
welt.konfigurieren(tastatur=True)         # Tasten a, b, m, Pfeiltasten im Terminal (Windows)
```

`cyberpi.display.show_label` schreibt in die Konsole. Ein vollständiges Beispiel ist
[04_mbot_strecke_fahren.py](04_mbot_strecke_fahren.py).

Dieses Repo ist eine Kopie zum Lesen und Ausprobieren und wird vor den Vorlesungen aktualisiert.
Eigene Änderungen am besten in einer eigenen Kopie (Fork) machen.

## Lizenz

MIT-Lizenz, siehe [LICENSE](LICENSE): Der Code darf frei genutzt, geändert und weitergegeben werden,
solange der Urheberhinweis erhalten bleibt.

Die Beispiele sind mit Unterstützung von Claude (Anthropic) entstanden.
