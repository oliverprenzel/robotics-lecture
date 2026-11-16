# %% [markdown]
# # Auswertung eines Laserscans (Abschnitt 3.5, Vorlesung 5)
#
# Ein Laserscanner liefert eine Folge von Abständen r₀, r₁, …
# Der Winkel ergibt sich aus dem Index: ϕᵢ = ϕ₀ + i·Δϕ
#
# Für Hinderniserkennung und Kartierung brauchen wir kartesische Koordinaten:
#
#     x = x_S + r·cos ϕ
#     y = y_S + r·sin ϕ
#
# Szene: Wand in 1,0 m, davor eine Kiste in 0,6 m.
# Roboter-Frame: x nach vorn, y nach links, Winkel gegen den Uhrzeigersinn.

# %% Vorbereitung
import numpy as np
import matplotlib.pyplot as plt

from lidar_sim import messe, zeichne_szene

# %% Parameter des Scans. Hier live ändern und die Zellen darunter neu ausführen
phi_0 = -60        # Startwinkel ϕ₀ in Grad
delta_phi = 15     # Schrittweite Δϕ in Grad, echte Scanner: 0,25 bis 1
anzahl = int(120 / delta_phi) + 1

x_S, y_S = 0.0, 0.0   # Scanner in der Robotermitte, danach ausprobieren: x_S = 0.08
rauschen = 0.0        # Standardabweichung in Metern, danach ausprobieren: 0.01

# %% Messung: Der Roboter bekommt nur diese Liste
i = np.arange(anzahl)
phi_grad = phi_0 + i * delta_phi
r = messe(phi_grad, sensor=(x_S, y_S), rauschen=rauschen)

print(f"{anzahl} Strahlen")
print("Winkel [°]   Abstand r [m]")
for w, a in zip(phi_grad, r):
    print(f"{w:10.2f}   {a:6.2f}")

# %% Rohdaten: r über ϕ. Woran erkennt man die Kiste?
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(phi_grad, r, "o-", markersize=4)
ax.set_xlabel(r"Winkel $\varphi$ in °")
ax.set_ylabel("Abstand r in m")
ax.set_title(r"Rohdaten: $r$ über $\varphi$")
ax.grid(True)
plt.show()

# %% Polarplot: dieselben Zahlen als (r, ϕ)
phi = np.deg2rad(phi_grad)   # cos und sin rechnen in Radiant

fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(6, 6))
ax.plot(phi, r, "o", markersize=4)
ax.set_thetamin(-75)
ax.set_thetamax(75)
ax.set_title(r"Polarkoordinaten $(r, \varphi)$")
plt.show()

# %% Rechenbeispiel zum Anschreiben: Scanner 8 cm vor der Robotermitte
phi_b = np.deg2rad(30)
r_b = 0.69
x_b = r_b * np.cos(phi_b)
y_b = r_b * np.sin(phi_b)
print(f"Sensor-Frame:  x = {x_b:.3f} m, y = {y_b:.3f} m")
print(f"Roboter-Frame: x = {0.08 + x_b:.3f} m, y = {y_b:.3f} m")

# %% Umrechnung aller Messwerte
x = x_S + r * np.cos(phi)
y = y_S + r * np.sin(phi)

# %% Punkte im Roboter-Frame, grau die echte Szene
fig, ax = plt.subplots(figsize=(5, 7))
zeichne_szene(ax)
ax.plot(x, y, "o", markersize=4, label="Messpunkte")
ax.plot(x_S, y_S, "r^", markersize=10, label="Scanner")
ax.set_xlabel("x in m")
ax.set_ylabel("y in m")
ax.set_title(r"Nach $x = x_S + r \cos\varphi$, $y = y_S + r \sin\varphi$")
ax.set_aspect("equal")
ax.grid(True)
ax.legend()
plt.show()

# %% Punktabstand auf der Wand: ungefähr r · Δϕ
print(f"Punktabstand in 1 m: {1.0 * np.deg2rad(delta_phi) * 100:.0f} cm")

# %% [markdown]
# ## Diskussion
#
# - In welcher Darstellung erkennt man Wand und Kiste?
# - Woran erkennt man die Kiste in der Liste?
# - Was weiß der Roboter über die Stelle hinter der Kiste?
# - Wie weit liegen benachbarte Wandpunkte auseinander, und was folgt daraus
#   für ein schmales Hindernis wie ein Stuhlbein?
# - Was passiert, wenn wir `np.deg2rad` vergessen?
#
# Zum Ausprobieren in der Parameterzelle: `delta_phi = 1`, `x_S = 0.08`, `rauschen = 0.01`
