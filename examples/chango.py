"""
chango.py

    Test for font2bitmap converter for the driver.
    See the font2bitmap program in the utils directory.
"""

from machine import freq
import thmi
import gc
import chango_16 as font_16
import chango_32 as font_32
import chango_64 as font_64

gc.collect()


def main():
    # enable display and clear screen
    tft = thmi.THMI(0)
    tft.clear()

    row = 0
    tft.write(font_16, "abcdefghijklmnopqrst", 0, row, thmi.RED)
    row += font_16.HEIGHT

    tft.write(font_32, "abcdefghij", 0, row, thmi.GREEN)
    row += font_32.HEIGHT

    tft.write(font_64, "abcd", 0, row, thmi.BLUE)
    row += font_64.HEIGHT


freq(240_000_000)
main()
