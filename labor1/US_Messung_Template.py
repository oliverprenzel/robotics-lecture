import cyberpi, mbuild, time

N = 20                                   # Messwerte pro Abstand

def warte(taste):
    while not cyberpi.controller.is_press(taste):
        time.sleep(0.05)
    while cyberpi.controller.is_press(taste):
        time.sleep(0.05)                 # erst loslassen, sonst zaehlt der Druck doppelt
    time.sleep(0.3)                      # Taste entprellen

while True:
    cyberpi.display.show_label("Abstand einstellen\nTaste B = messen", 16, 0, 0)
    warte("b")
    
    # leere Liste anlegen
    werte = []    
    # range(N) erzeugt Folge: 0 ... N-1
    for i in range(N):
        # einen Messwert in Liste "werte" anhängen:
        werte.append(mbuild.ultrasonic2.get(1)) 
        time.sleep( xxx )                  # 100 ms Abstand
    
    # Mittelwert berechnen
    m = sum(werte) / N

    # Liste der quadrierten Abweichungen aufbauen
    quadrate = []
    for x in werte:
        
        # (1) Abweichung vom Mittelwert
        
        quadrate.append(   ) # (2) Quadrat der Abweichung in Liste "quadrate"

    # Varianz und Standardabweichung
    varianz = sum(quadrate) / (N - 1)
    s = varianz ** 0.5
    
    cyberpi.display.show_label("Mittel %.1f\nMin %.1f\nMax %.1f\nSigma %.2f\nB = weiter" % (m, min(werte), max(werte), s), 16, 0, 0)
    warte("b")
    
   