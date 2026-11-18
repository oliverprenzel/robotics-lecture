# Mobile Robotik: Codebeispiele zur Vorlesung

Beispiele zum Nachvollziehen und Ausprobieren: Laserscans auswerten, einen Flur kartieren und
Programme für den mBot2 ohne Gerät am PC testen.

## Repository (Code) herunterladen und aktualisieren

Am einfachsten in [VS Code](https://code.visualstudio.com/): Git ist dort eingebaut, eine Erweiterung
braucht es nicht. Fehlt Git auf dem Rechner, bietet VS Code in der Ansicht *Quellcodeverwaltung*
(Strg+Umschalt+G) den Download an; danach VS Code neu starten.

- **Klonen:** Strg+Umschalt+P, *Git: Klonen* (*Git: Clone*), die Adresse
  `https://github.com/oliverprenzel/robotics-lecture.git` einfügen, einen Ordner wählen. VS Code legt
  dort den Unterordner `robotics-lecture` an und bietet an, ihn zu öffnen.
- **Aktualisieren:** in der *Quellcodeverwaltung* über das Menü „…“ *Pull* (holt und übernimmt die
  Änderungen) oder *Fetch* (holt nur ab); oder der Kreispfeil unten links in der Statusleiste.

Dasselbe im Terminal (in VS Code: Strg+Ö), einmalig herunterladen:

```powershell
git clone https://github.com/oliverprenzel/robotics-lecture.git            # legt den Ordner robotics-lecture im aktuellen Verzeichnis an
git clone https://github.com/oliverprenzel/robotics-lecture.git vorlesung  # oder mit eigenem Ordnernamen
cd robotics-lecture                                                        # bzw. cd vorlesung
```

Vor jeder Vorlesung die neuesten Änderungen holen, im Ordner des Repos:

```powershell
git pull                                # holt die Änderungen und übernimmt sie in die Dateien
```

Wer erst sehen will, was neu ist, holt die Änderungen ohne sie zu übernehmen:

```powershell
git fetch                               # nur abholen, die Dateien bleiben unverändert
git log HEAD..origin/main --oneline     # zeigt, was neu ist
git merge                               # übernehmen (fetch + merge = pull)
```

Bricht `git pull` ab, weil eigene Änderungen an denselben Dateien im Weg sind: `git stash` (eigene
Änderungen beiseitelegen), `git pull`, `git stash pop` (zurückholen). Oder `git restore .` verwirft
die eigenen Änderungen. Neue eigene Dateien stören nicht.

## Umgebung einrichten

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

## Inhalt des Repositorys

| Datei | Inhalt |
|---|---|
| [01_lidar_polar_kartesisch.py](01_lidar_polar_kartesisch.py) | Auswertung eines Laserscans: Kiste vor Wand, Polarplot, Umrechnung nach x und y |
| [02_flur_mapping.py](02_flur_mapping.py) | Mapping: Ein Bot entdeckt einen Flur mit Einbuchtungen, Animation im eigenen Fenster |
| [03_lidar_realistisch.py](03_lidar_realistisch.py) | Derselbe Flur wie ein echter Scan, mit Rauschen, Aussetzern und Mischpixeln |
| [videos/](videos/) | Die Animationen aus 02 und 03 als Video (MP4), zum Ansehen ohne Python |
| [04_mbot_strecke_fahren.py](04_mbot_strecke_fahren.py) | Programm für den mBot2: 1 m geradeaus nach den Radencodern; am PC über den Starter |
| [05_mbot_wand.py](05_mbot_wand.py) | mBot2 ohne Gerät: vor einer Wand anhalten (Ultraschall), 90° drehen (Gyro), Live-Fenster |
| [filtern.py](filtern.py) | Messwerte filtern: Plausibilitätsprüfung, gleitender Mittelwert, gleitender Median |
| [labor1/US_Messung_Template.py](labor1/US_Messung_Template.py) | Labor 1: Vorlage Ultraschall-Messreihe (Mittelwert, Minimum, Maximum, Standardabweichung), Lücken zum Ergänzen |
| [labor2/programmgeruest.py](labor2/programmgeruest.py) | Labor 2: vorgegebenes Programmgerüst (Positionsbestimmung, Fahrfunktionen zum Ergänzen); am PC: `python mbot_sim_start.py labor2\programmgeruest.py` |
| [lidar_sim.py](lidar_sim.py) | Kleiner Laserscanner-Simulator für die Beispiele |
| [mbot_sim_start.py](mbot_sim_start.py) | Starter: ein mBot2-Programm unverändert am PC auf dem simulierten mBot2 laufen lassen |
| [mbot_sim/](mbot_sim/) | Simulierter mBot2 für den PC: `cyberpi`, `mbot2`, `mbuild`, `event` ohne Gerät |

## mBot2 Simulation (ohne Gerät)

Ein Programm für den mBot2 läuft unverändert am PC, so wie es in mBlock hochgeladen wird:

```powershell
python mbot_sim_start.py 04_mbot_strecke_fahren.py     # leerer Raum
python mbot_sim_start.py mein_programm.py --wand 80    # Wand 80 cm vor dem Ultraschallsensor
python mbot_sim_start.py mein_programm.py --realistisch   # ungleiche Räder, Schlupf, Gyro-Drift wie am echten mBot2
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
