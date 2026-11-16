# Mobile Robotik: Codebeispiele zur Vorlesung

Beispiele zum Nachvollziehen und Ausprobieren: Laserscans auswerten, einen Flur kartieren und
Programme für den mBot2 ohne Gerät am PC testen.

## Einrichten

Python 3.10 oder neuer. Im Ordner dieses Repos:

```powershell
python -m venv .venv                    # einmalig: eigene Python-Umgebung anlegen
.venv\Scripts\Activate.ps1              # in jedem neuen Terminal: Umgebung aktivieren
pip install -r requirements.txt         # einmalig: Pakete installieren
python 01_lidar_polar_kartesisch.py     # ganzes Beispiel auf einmal ausführen
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
| [04_mbot_strecke_fahren.py](04_mbot_strecke_fahren.py) | Programm für den mBot2: 1 m geradeaus nach den Radencodern; am PC über den Starter |
| [05_mbot_wand.py](05_mbot_wand.py) | mBot2 ohne Gerät: vor einer Wand anhalten (Ultraschall), 90° drehen (Gyro), Live-Fenster |
| [filtern.py](filtern.py) | Messwerte filtern: Plausibilitätsprüfung, gleitender Mittelwert, gleitender Median |
| [lidar_sim.py](lidar_sim.py) | Kleiner Laserscanner-Simulator für die Beispiele |
| [mbot_sim_start.py](mbot_sim_start.py) | Starter: ein mBot2-Programm unverändert am PC auf dem simulierten mBot2 laufen lassen |
| [mbot_sim/](mbot_sim/) | Simulierter mBot2 für den PC: `cyberpi`, `mbot2`, `mbuild`, `event` ohne Gerät |

## mBot2 ohne Gerät

Ein Programm für den mBot2 läuft unverändert am PC, so wie es in mBlock hochgeladen wird:

```powershell
python mbot_sim_start.py 04_mbot_strecke_fahren.py     # leerer Raum
python mbot_sim_start.py mein_programm.py --wand 80    # Wand 80 cm vor dem Ultraschallsensor
```

`cyberpi`, `mbot2`, `mbuild` und `event` kommen dabei aus [mbot_sim/](mbot_sim/). Die Tasten des CyberPi
sind die Tasten a, b, m und die Pfeiltasten im Terminal (nur Windows), die Anzeige erscheint in der
Konsole. Am Ende, oder nach Ctrl+C, nennt der Starter die wahre Position des simulierten mBot2.

Wer die simulierte Welt selbst einrichten oder auslesen will (Hindernisse, wahre Position), bindet
sie im Programm ein, wie in [05_mbot_wand.py](05_mbot_wand.py):

```python
from mbot_sim import installieren
cyberpi, mbot2, welt = installieren()     # danach liefern import cyberpi, mbot2, mbuild den simulierten mBot2
```

Dieses Repo ist eine Kopie zum Lesen und Ausprobieren und wird vor den Vorlesungen aktualisiert.
Eigene Änderungen am besten in einer eigenen Kopie (Fork) machen.

## Lizenz

MIT-Lizenz, siehe [LICENSE](LICENSE): Der Code darf frei genutzt, geändert und weitergegeben werden,
solange der Urheberhinweis erhalten bleibt.

Die Beispiele sind mit Unterstützung von Claude (Anthropic) entstanden.
