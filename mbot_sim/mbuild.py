"""Attrappe des Makeblock-Moduls `mbuild` (nachgebaut, nicht vom Hersteller): Ultraschall-
sensor 2 und Quad-RGB-Sensor (Linienfolger) des mBot2.

- mbuild.ultrasonic2.get(index) -> Abstand in cm (5..300, außerhalb des Bereichs 300),
  wie OpenRoberta ihn aufruft (Mbot2PythonVisitor).
- mbuild.quad_rgb_sensor.get_line_sta(ch="all", index=1) -> 0..15, ein Bit je Sonde,
  L2 = höchstes Bit; Bit gesetzt = Hintergrund, nicht Linie (wie naman466/mBot2-simulator;
  am Gerät prüfen: rover/mbot.toml quad_linie_bit). is_line(ch, index) -> bool.
"""
from _attrappe_welt import WELT


class _Ultraschall2:
    def get(self, index=1):
        WELT.ruf("ultrasonic2.get", index)
        return round(float(WELT.ultraschall()) * 100.0, 1)

    def set_bri(self, *a):
        WELT.ruf("ultrasonic2.set_bri", *a)


ultrasonic2 = _Ultraschall2()

_SONDEN = ("L2", "L1", "R1", "R2")


class _QuadRgb:
    def get_line_sta(self, ch="all", index=1):
        WELT.ruf("quad_rgb_sensor.get_line_sta", ch, index)
        sta = 0
        for i, on in enumerate(WELT.auf_linie()):
            if not on:
                sta |= 1 << (3 - i)
        return sta

    def is_line(self, ch="any", index=1):
        WELT.ruf("quad_rgb_sensor.is_line", ch, index)
        on = WELT.auf_linie()
        if ch == "any":
            return any(on)
        if ch == "all":
            return all(on)
        return on[_SONDEN.index(str(ch).upper())]

    def is_background(self, ch="any", index=1):
        on = [not x for x in WELT.auf_linie()]
        return any(on) if ch == "any" else all(on) if ch == "all" else on[_SONDEN.index(str(ch).upper())]


quad_rgb_sensor = _QuadRgb()
