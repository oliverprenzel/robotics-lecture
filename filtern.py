D_MIN, D_MAX = 3, 300      # Messbereich in cm, am Datenblatt prüfen

def plausibel(d):
    return D_MIN <= d <= D_MAX

def gleitender_mittelwert(fenster):
    return sum(fenster) / len(fenster)

def gleitender_median(fenster):
    s = sorted(fenster)
    return s[len(s) // 2]   # für ungerade Fensterlänge

messwerte = [30, 30, 31, 300, 30, 29, 60, 60, 61]

fenster = []
K = 3
for d in messwerte:
    if not plausibel(d):
        continue            # Wert verwerfen
    fenster.append(d)
    if len(fenster) > K:
        fenster.pop(0)   # erstes Listenelement entfernen
    abstand = gleitender_mittelwert(fenster)
    print(round(abstand, 2), end=" ")

