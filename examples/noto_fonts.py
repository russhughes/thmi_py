"""
noto_fonts Writes the names of three Noto fonts centered on the display
    using the font. The fonts were converted from True Type fonts using
    the font2bitmap utility.
"""

from machine import freq
import thmi
import NotoSans_32 as noto_sans
import NotoSerif_32 as noto_serif
import NotoSansMono_32 as noto_mono


def main():
    def center(font, string, row, color=thmi.WHITE):
        screen = tft.width  # get screen width
        width = tft.write_width(font, string)  # get the width of the string
        col = tft.width // 2 - width // 2 if width and width < screen else 0
        tft.write(font, string, col, row, color)  # and write the string

    # enable display and clear screen
    tft = thmi.THMI(0)
    tft.clear()

    row = 16

    # center the name of the first font, using the font
    center(noto_sans, "NotoSans", row, thmi.RED)
    row += noto_sans.HEIGHT

    # center the name of the second font, using the font
    center(noto_serif, "NotoSerif", row, thmi.GREEN)
    row += noto_serif.HEIGHT

    # center the name of the third font, using the font
    center(noto_mono, "NotoSansMono", row, thmi.BLUE)
    row += noto_mono.HEIGHT


freq(240_000_000)
main()
