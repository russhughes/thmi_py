"""
lines.py

    Draws lines and rectangles in random colors at random locations on the
    display.

"""

from machine import freq
import random
import thmi


def main():
    tft = thmi.THMI(0)
    tft.clear()

    while True:
        tft.line(
            random.randint(0, tft.width),
            random.randint(0, tft.height),
            random.randint(0, tft.width),
            random.randint(0, tft.height),
            thmi.color565(
                random.getrandbits(8), random.getrandbits(8), random.getrandbits(8)
            ),
        )

        width = random.randint(0, tft.width // 2)
        height = random.randint(0, tft.height // 2)
        col = random.randint(0, tft.width - width)
        row = random.randint(0, tft.height - height)
        tft.fill_rect(
            col,
            row,
            width,
            height,
            thmi.color565(
                random.getrandbits(8), random.getrandbits(8), random.getrandbits(8)
            ),
        )


freq(240_000_000)
main()
