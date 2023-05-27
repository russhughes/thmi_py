"""
Copyright (c) 2020-2023 Russ Hughes

This file incorporates work covered by the following copyright and
permission notice and is licensed under the same terms:

The MIT License (MIT)

Copyright (c) 2019 Ivan Belokobylskiy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

The driver is based on devbis' st7789py_mpy module from
https://github.com/devbis/st7789py_mpy.

This driver adds support for:

- LilyGo T-HMI 320x240 TFT LCD display
- Display rotation
- Hardware based scrolling
- Drawing text using 8 and 16 bit wide bitmap fonts with heights that are
  multiples of 8.  Included are 12 bitmap fonts derived from classic pc
  BIOS text mode fonts.
- Drawing text using converted TrueType fonts.
- Drawing converted bitmaps

"""

from esp32 import RMT
import time
from micropython import const
from machine import mem32, Pin
import ustruct as struct

# memory mapped registers of ESP32S3 for setting and clearing GPIO pins
# see the ESP32S3 datasheet for more information.
GPIO_OUT_W1TS_REG = const(0x60004008)
GPIO_OUT_W1TC_REG = const(0x6000400C)
GPIO_OUT1_W1TS_REG = const(0x60004014)
GPIO_OUT1_W1TC_REG = const(0x60004018)

# see the make_gpio_table script in the utils directory
# of the repository for more information on these tables.
GPIO_OUT1_W1TC_MASK = const(0x0001E780)
# fmt: off
GPIO_OUT1_W1TS_MASKS = (
        0x0, 0x10000,  0x8000, 0x18000,
       0x80, 0x10080,  0x8080, 0x18080,
      0x100, 0x10100,  0x8100, 0x18100,
      0x180, 0x10180,  0x8180, 0x18180,
      0x200, 0x10200,  0x8200, 0x18200,
      0x280, 0x10280,  0x8280, 0x18280,
      0x300, 0x10300,  0x8300, 0x18300,
      0x380, 0x10380,  0x8380, 0x18380,
      0x400, 0x10400,  0x8400, 0x18400,
      0x480, 0x10480,  0x8480, 0x18480,
      0x500, 0x10500,  0x8500, 0x18500,
      0x580, 0x10580,  0x8580, 0x18580,
      0x600, 0x10600,  0x8600, 0x18600,
      0x680, 0x10680,  0x8680, 0x18680,
      0x700, 0x10700,  0x8700, 0x18700,
      0x780, 0x10780,  0x8780, 0x18780,
     0x2000, 0x12000,  0xa000, 0x1a000,
     0x2080, 0x12080,  0xa080, 0x1a080,
     0x2100, 0x12100,  0xa100, 0x1a100,
     0x2180, 0x12180,  0xa180, 0x1a180,
     0x2200, 0x12200,  0xa200, 0x1a200,
     0x2280, 0x12280,  0xa280, 0x1a280,
     0x2300, 0x12300,  0xa300, 0x1a300,
     0x2380, 0x12380,  0xa380, 0x1a380,
     0x2400, 0x12400,  0xa400, 0x1a400,
     0x2480, 0x12480,  0xa480, 0x1a480,
     0x2500, 0x12500,  0xa500, 0x1a500,
     0x2580, 0x12580,  0xa580, 0x1a580,
     0x2600, 0x12600,  0xa600, 0x1a600,
     0x2680, 0x12680,  0xa680, 0x1a680,
     0x2700, 0x12700,  0xa700, 0x1a700,
     0x2780, 0x12780,  0xa780, 0x1a780,
     0x4000, 0x14000,  0xc000, 0x1c000,
     0x4080, 0x14080,  0xc080, 0x1c080,
     0x4100, 0x14100,  0xc100, 0x1c100,
     0x4180, 0x14180,  0xc180, 0x1c180,
     0x4200, 0x14200,  0xc200, 0x1c200,
     0x4280, 0x14280,  0xc280, 0x1c280,
     0x4300, 0x14300,  0xc300, 0x1c300,
     0x4380, 0x14380,  0xc380, 0x1c380,
     0x4400, 0x14400,  0xc400, 0x1c400,
     0x4480, 0x14480,  0xc480, 0x1c480,
     0x4500, 0x14500,  0xc500, 0x1c500,
     0x4580, 0x14580,  0xc580, 0x1c580,
     0x4600, 0x14600,  0xc600, 0x1c600,
     0x4680, 0x14680,  0xc680, 0x1c680,
     0x4700, 0x14700,  0xc700, 0x1c700,
     0x4780, 0x14780,  0xc780, 0x1c780,
     0x6000, 0x16000,  0xe000, 0x1e000,
     0x6080, 0x16080,  0xe080, 0x1e080,
     0x6100, 0x16100,  0xe100, 0x1e100,
     0x6180, 0x16180,  0xe180, 0x1e180,
     0x6200, 0x16200,  0xe200, 0x1e200,
     0x6280, 0x16280,  0xe280, 0x1e280,
     0x6300, 0x16300,  0xe300, 0x1e300,
     0x6380, 0x16380,  0xe380, 0x1e380,
     0x6400, 0x16400,  0xe400, 0x1e400,
     0x6480, 0x16480,  0xe480, 0x1e480,
     0x6500, 0x16500,  0xe500, 0x1e500,
     0x6580, 0x16580,  0xe580, 0x1e580,
     0x6600, 0x16600,  0xe600, 0x1e600,
     0x6680, 0x16680,  0xe680, 0x1e680,
     0x6700, 0x16700,  0xe700, 0x1e700,
     0x6780, 0x16780,  0xe780, 0x1e780,
)
# fmt: on

# RMT pulse duration
#   increase if you see display glitches
#   decrease to speed up updates
PULSE = const(16)

# GPIO Pin Masks for setting and clearing pins
PIN_WR = const(8)
MASK_DC = const(1 << 7)  # OUT
MASK_CS = const(1 << 6)  # OUT
MASK_BACKLIGHT = const(1 << 38 - 32)  # OUT1

# ST7796 contoller  commands
ST7796_NOP = const(0x00)
ST7796_SWRESET = const(0x01)
ST7796_RDDID = const(0x04)
ST7796_RDDST = const(0x09)

ST7796_SLPIN = const(0x10)
ST7796_SLPOUT = const(0x11)
ST7796_PTLON = const(0x12)
ST7796_NORON = const(0x13)

ST7796_INVOFF = const(0x20)
ST7796_INVON = const(0x21)
ST7796_DISPOFF = const(0x28)
ST7796_DISPON = const(0x29)
ST7796_CASET = const(0x2A)
ST7796_RASET = const(0x2B)
ST7796_RAMWR = const(0x2C)
ST7796_RAMRD = const(0x2E)

ST7796_PTLAR = const(0x30)
ST7796_VSCRDEF = const(0x33)
ST7796_COLMOD = const(0x3A)
ST7796_MADCTL = const(0x36)
ST7796_VSCSAD = const(0x37)

ST7796_MADCTL_MY = const(0x80)
ST7796_MADCTL_MX = const(0x40)
ST7796_MADCTL_MV = const(0x20)
ST7796_MADCTL_ML = const(0x10)
ST7796_MADCTL_BGR = const(0x08)
ST7796_MADCTL_MH = const(0x04)
ST7796_MADCTL_RGB = const(0x00)

ST7796_RDID1 = const(0xDA)
ST7796_RDID2 = const(0xDB)
ST7796_RDID3 = const(0xDC)
ST7796_RDID4 = const(0xDD)

COLOR_MODE_65K = const(0x50)
COLOR_MODE_262K = const(0x60)
COLOR_MODE_12BIT = const(0x03)
COLOR_MODE_16BIT = const(0x05)
COLOR_MODE_18BIT = const(0x06)
COLOR_MODE_16M = const(0x07)

# Color definitions
BLACK = const(0x0000)
BLUE = const(0x001F)
RED = const(0xF800)
GREEN = const(0x07E0)
CYAN = const(0x07FF)
MAGENTA = const(0xF81F)
YELLOW = const(0xFFE0)
WHITE = const(0xFFFF)

_ENCODE_PIXEL = const(">H")
_ENCODE_POS = const(">HH")
_DECODE_PIXEL = const(">BBB")

_BUFFER_PIXELS = const(256)

_BIT7 = const(0x80)
_BIT6 = const(0x40)
_BIT5 = const(0x20)
_BIT4 = const(0x10)
_BIT3 = const(0x08)
_BIT2 = const(0x04)
_BIT1 = const(0x02)
_BIT0 = const(0x01)

# Rotation tables (width, height)[rotation % 4]

ROTATIONS = ((240, 320), (320, 240), (240, 320), (320, 240))

# MADCTL ROTATIONS[rotation % 4]
MADCTLS = (0x00, 0x60, 0xC0, 0xA0)


def color565(red, green=0, blue=0):
    """
    Convert red, green and blue values (0-255) into a 16-bit 565 encoding.
    """
    try:
        red, green, blue = red  # see if the first var is a tuple/list
    except TypeError:
        pass
    return (red & 0xF8) << 8 | (green & 0xFC) << 3 | blue >> 3


def _encode_pos(x, y):
    """Encode a postion into bytes."""
    return struct.pack(_ENCODE_POS, x, y)


def _encode_pixel(color):
    """Encode a pixel color into bytes."""
    return struct.pack(_ENCODE_PIXEL, color)


class THMI:
    """
    T_HMI driver class

    Args:
        rotation (int): display rotation
            - 0-Portrait
            - 1-Landscape
            - 2-Inverted Portrait
            - 3-Inverted Landscape

        rotations (list): list of rotation values
    """

    def __init__(
        self,
        rotation=0,
        rotations=MADCTLS,
    ):
        """
        Initialize T_HMI's st7789 display.
        """

        # turn on display
        Pin(10, Pin.OUT, value=1)
        time.sleep_ms(100)

        # configure pins
        Pin(48, Pin.OUT)
        Pin(47, Pin.OUT)
        Pin(39, Pin.OUT)
        Pin(40, Pin.OUT)
        Pin(41, Pin.OUT)
        Pin(42, Pin.OUT)
        Pin(45, Pin.OUT)
        Pin(46, Pin.OUT)

        Pin(7, Pin.OUT)  # dc
        Pin(6, Pin.OUT)  # cs

        self.wr = Pin(PIN_WR, Pin.OUT, value=1)  # wr
        self.rmt = RMT(0, pin=self.wr, clock_div=1)
        self.pulse = [0, 1]

        self.bl = Pin(38, Pin.OUT)  # backlight0

        self.last = None
        self._rotation = rotation % 4
        self._rotations = rotations

        mem32[GPIO_OUT_W1TS_REG] = MASK_CS
        mem32[GPIO_OUT_W1TS_REG] = MASK_DC

        self.soft_reset()
        self.sleep_mode(False)
        self._set_color_mode(COLOR_MODE_65K | COLOR_MODE_16BIT)
        time.sleep_ms(50)
        self.rotation(self._rotation)
        self.inversion_mode(False)
        time.sleep_ms(10)
        self._write(ST7796_NORON)
        time.sleep_ms(10)
        self.backlight_on()
        self._write(ST7796_DISPON)
        time.sleep_ms(125)

    def backlight_on(self):
        self.bl.value(1)

    def backlight_off(self):
        self.bl.value(0)

    @micropython.native
    def _write_byte(self, b):
        """Write to the display using 8 bit parallel mode. Note: this is not fast."""
        if b != self.last:
            out1 = GPIO_OUT1_W1TS_MASKS[b]
            mem32[GPIO_OUT1_W1TS_REG] = out1
            mem32[GPIO_OUT1_W1TC_REG] = out1 ^ GPIO_OUT1_W1TC_MASK
            self.last = b

        self.rmt.write_pulses(PULSE, self.pulse)

    @micropython.native
    def _write(self, command=None, data=None):
        """Write to the display: command and/or data."""

        mem32[GPIO_OUT_W1TC_REG] = MASK_CS

        if command is not None:
            mem32[GPIO_OUT_W1TC_REG] = MASK_DC
            for b in bytes([command]):
                self._write_byte(b)
        if data is not None:
            mem32[GPIO_OUT_W1TS_REG] = MASK_DC
            for b in data:
                self._write_byte(b)

        mem32[GPIO_OUT_W1TS_REG] = MASK_CS

    def soft_reset(self):
        """
        Soft reset display.
        """
        self._write(ST7796_SWRESET)
        time.sleep_ms(150)

    def sleep_mode(self, value):
        """
        Enable or disable display sleep mode.

        Args:
            value (bool): if True enable sleep mode. if False disable sleep
            mode
        """
        if value:
            self._write(ST7796_SLPIN)
        else:
            self._write(ST7796_SLPOUT)

    def inversion_mode(self, value):
        """
        Enable or disable display inversion mode.

        Args:
            value (bool): if True enable inversion mode. if False disable
            inversion mode
        """
        if value:
            self._write(ST7796_INVON)
        else:
            self._write(ST7796_INVOFF)

    def _set_color_mode(self, mode):
        """
        Set display color mode.

        Args:
            mode (int): color mode
                COLOR_MODE_65K, COLOR_MODE_262K, COLOR_MODE_12BIT,
                COLOR_MODE_16BIT, COLOR_MODE_18BIT, COLOR_MODE_16M
        """
        self._write(ST7796_COLMOD, bytes([mode & 0x77]))

    def rotation(self, rotation):
        """
        Set display rotation.

        Args:
            rotation (int):
                - 0-Portrait
                - 1-Landscape
                - 2-Inverted Portrait
                - 3-Inverted Landscape
        """

        rotation %= 4
        self._rotation = rotation
        madctl = self._rotations[rotation]
        self.width, self.height = ROTATIONS[rotation]
        self._write(ST7796_MADCTL, bytes([madctl]))

    @micropython.native
    def _set_window(self, x0, y0, x1, y1):
        """
        Set window to column and row address.

        Args:
            x0 (int): column start address
            y0 (int): row start address
            x1 (int): column end address
            y1 (int): row end address
        """
        if x0 <= x1 <= self.width and y0 <= y1 <= self.height:
            self._write(ST7796_CASET, _encode_pos(x0, x1))
            self._write(ST7796_RASET, _encode_pos(y0, y1))
            self._write(ST7796_RAMWR)

    def vline(self, x, y, length, color):
        """
        Draw vertical line at the given location and color.

        Args:
            x (int): x coordinate
            Y (int): y coordinate
            length (int): length of line
            color (int): 565 encoded color
        """
        self.fill_rect(x, y, 1, length, color)

    def hline(self, x, y, length, color):
        """
        Draw horizontal line at the given location and color.

        Args:
            x (int): x coordinate
            Y (int): y coordinate
            length (int): length of line
            color (int): 565 encoded color
        """
        self.fill_rect(x, y, length, 1, color)

    def pixel(self, x, y, color):
        """
        Draw a pixel at the given location and color.

        Args:
            x (int): x coordinate
            Y (int): y coordinate
            color (int): 565 encoded color
        """
        self._set_window(x, y, x, y)
        self._write(None, _encode_pixel(color))

    def blit_buffer(self, buffer, x, y, width, height):
        """
        Copy buffer to display at the given location.

        Args:
            buffer (bytes): Data to copy to display
            x (int): Top left corner x coordinate
            Y (int): Top left corner y coordinate
            width (int): Width
            height (int): Height
        """
        self._set_window(x, y, x + width - 1, y + height - 1)
        self._write(None, buffer)

    def rect(self, x, y, w, h, color):
        """
        Draw a rectangle at the given location, size and color.

        Args:
            x (int): Top left corner x coordinate
            y (int): Top left corner y coordinate
            width (int): Width in pixels
            height (int): Height in pixels
            color (int): 565 encoded color
        """
        self.hline(x, y, w, color)
        self.vline(x, y, h, color)
        self.vline(x + w - 1, y, h, color)
        self.hline(x, y + h - 1, w, color)

    @micropython.native
    def fill_rect(self, x, y, width, height, color):
        """
        Draw a rectangle at the given location, size and filled with color.

        Args:
            x (int): Top left corner x coordinate
            y (int): Top left corner y coordinate
            width (int): Width in pixels
            height (int): Height in pixels
            color (int): 565 encoded color
        """
        high_byte = color >> 8
        low_byte = color & 0xFF

        self._set_window(x, y, x + width - 1, y + height - 1)
        mem32[GPIO_OUT_W1TC_REG] = MASK_CS
        mem32[GPIO_OUT_W1TS_REG] = MASK_DC

        for _ in range(width * height):
            self._write_byte(high_byte)
            self._write_byte(low_byte)

        mem32[GPIO_OUT_W1TS_REG] = MASK_CS

    def fill(self, color):
        """
        Fill the entire FrameBuffer with the specified color.

        Args:
            color (int): 565 encoded color
        """
        self.fill_rect(0, 0, self.width, self.height, color)

    @micropython.native
    def clear(self, color=None):
        """
        Very fast clear screen.

        Args:
            color (bool): True to clear to white, False to clear to black
            or
            color (int): 565 encoded color, with the upper and lower bytes
                being set the same value as color.
        """
        if isinstance(color, bool):
            color = 0xFF if color else 0
        elif color is None:
            color = 0
        else:
            color &= 0xFF

        self._set_window(0, 0, self.width, self.height)

        out1 = GPIO_OUT1_W1TS_MASKS[color]

        mem32[GPIO_OUT1_W1TS_REG] = out1
        mem32[GPIO_OUT1_W1TC_REG] = out1 ^ GPIO_OUT1_W1TC_MASK

        mem32[GPIO_OUT_W1TC_REG] = MASK_CS
        mem32[GPIO_OUT_W1TS_REG] = MASK_DC

        pulses = [0, 1] * self.width
        count = self.height + 1

        for _ in range(count * 2):
            self.rmt.write_pulses(PULSE, pulses)
            self.rmt.wait_done()

        mem32[GPIO_OUT_W1TS_REG] = MASK_CS

    @micropython.native
    def line(self, x0, y0, x1, y1, color):
        """
        Draw a single pixel wide line starting at x0, y0 and ending at x1, y1.

        Args:
            x0 (int): Start point x coordinate
            y0 (int): Start point y coordinate
            x1 (int): End point x coordinate
            y1 (int): End point y coordinate
            color (int): 565 encoded color
        """
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
        dx = x1 - x0
        dy = abs(y1 - y0)
        err = dx // 2
        ystep = 1 if y0 < y1 else -1
        while x0 <= x1:
            if steep:
                self.pixel(y0, x0, color)
            else:
                self.pixel(x0, y0, color)
            err -= dy
            if err < 0:
                y0 += ystep
                err += dx
            x0 += 1

    def vscrdef(self, tfa, vsa, bfa):
        """
        Set Vertical Scrolling Definition.

        To scroll a 135x240 display these values should be 40, 240, 40.
        There are 40 lines above the display that are not shown followed by
        240 lines that are shown followed by 40 more lines that are not shown.
        You could write to these areas off display and scroll them into view by
        changing the TFA, VSA and BFA values.

        Args:
            tfa (int): Top Fixed Area
            vsa (int): Vertical Scrolling Area
            bfa (int): Bottom Fixed Area
        """
        struct.pack(">HHH", tfa, vsa, bfa)
        self._write(ST7796_VSCRDEF, struct.pack(">HHH", tfa, vsa, bfa))

    def vscsad(self, vssa):
        """
        Set Vertical Scroll Start Address of RAM.

        Defines which line in the Frame Memory will be written as the first
        line after the last line of the Top Fixed Area on the display

        Example:

            for line in range(40, 280, 1):
                tft.vscsad(line)
                utime.sleep(0.01)

        Args:
            vssa (int): Vertical Scrolling Start Address

        """
        self._write(ST7796_VSCSAD, struct.pack(">H", vssa))

    @micropython.native
    def text(self, font, text, x0, y0, color=WHITE, background=BLACK):
        """
        Draw text on display in specified font and colors. 8 and 16 bit wide
        fonts are supported.

        Args:
            font (module): font module to use.
            text (str): text to write
            x0 (int): column to start drawing at
            y0 (int): row to start drawing at
            color (int): 565 encoded color to use for characters
            background (int): 565 encoded color to use for background
        """
        wide = font.WIDTH // 8
        fg_hi = color >> 8
        fg_lo = color & 0xFF
        bg_hi = background >> 8
        bg_lo = background & 0xFF

        buffer = bytearray(font.WIDTH * font.HEIGHT * 2)
        for char in text:
            ch = ord(char)
            if (
                font.FIRST <= ch < font.LAST
                and x0 + font.WIDTH <= self.width
                and y0 + font.HEIGHT <= self.height
            ):
                buf_idx = 0
                chr_idx = (ch - font.FIRST) * (font.HEIGHT * wide)
                for _ in range(font.HEIGHT):
                    for _ in range(wide):
                        chr_data = font.FONT[chr_idx]
                        for _ in range(8):
                            if chr_data & 0x80:
                                buffer[buf_idx] = fg_hi
                                buffer[buf_idx + 1] = fg_lo
                            else:
                                buffer[buf_idx] = bg_hi
                                buffer[buf_idx + 1] = bg_lo
                            buf_idx += 2
                            chr_data <<= 1
                        chr_idx += 1

                to_col = x0 + font.WIDTH - 1
                to_row = y0 + font.HEIGHT - 1
                if self.width > to_col and self.height > to_row:
                    self._set_window(x0, y0, to_col, to_row)
                    self._write(None, buffer)

                x0 += font.WIDTH

    @micropython.native
    def bitmap(self, bitmap, x, y, index=0):
        """
        Draw a bitmap on display at the specified column and row

        Args:
            bitmap (bitmap_module): The module containing the bitmap to draw
            x (int): column to start drawing at
            y (int): row to start drawing at
            index (int): Optional index of bitmap to draw from multiple bitmap
                module

        """
        bitmap_size = bitmap.HEIGHT * bitmap.WIDTH
        buffer_len = bitmap_size * 2
        buffer = bytearray(buffer_len)
        bs_bit = bitmap.BPP * bitmap_size * index if index > 0 else 0

        for i in range(0, buffer_len, 2):
            color_index = 0
            for _ in range(bitmap.BPP):
                color_index <<= 1
                color_index |= (
                    bitmap.BITMAP[bs_bit // 8] & 1 << (7 - (bs_bit % 8))
                ) > 0
                bs_bit += 1

            color = bitmap.PALETTE[color_index]
            buffer[i + 1] = (color & 0xFF00) >> 8
            buffer[i] = color & 0xFF

        to_col = x + bitmap.WIDTH - 1
        to_row = y + bitmap.HEIGHT - 1
        if self.width > to_col and self.height > to_row:
            self._set_window(x, y, to_col, to_row)
            self._write(None, buffer)

    @micropython.native
    def write(self, font, string, x, y, fg=WHITE, bg=BLACK):
        """
        Write a string using a converted true-type font on the display starting
        at the specified column and row

        Args:
            font (font): The module containing the converted true-type font
            s (string): The string to write
            x (int): column to start writing
            y (int): row to start writing
            fg (int): foreground color, optional, defaults to WHITE
            bg (int): background color, optional, defaults to BLACK
        """
        buffer_len = font.HEIGHT * font.MAX_WIDTH * 2
        buffer = bytearray(buffer_len)
        fg_hi = (fg & 0xFF00) >> 8
        fg_lo = fg & 0xFF

        bg_hi = (bg & 0xFF00) >> 8
        bg_lo = bg & 0xFF

        for character in string:
            try:
                char_index = font.MAP.index(character)
                offset = char_index * font.OFFSET_WIDTH
                bs_bit = font.OFFSETS[offset]
                if font.OFFSET_WIDTH > 1:
                    bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 1]

                if font.OFFSET_WIDTH > 2:
                    bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 2]

                char_width = font.WIDTHS[char_index]
                buffer_needed = char_width * font.HEIGHT * 2

                for i in range(0, buffer_needed, 2):
                    if font.BITMAPS[bs_bit // 8] & 1 << (7 - (bs_bit % 8)) > 0:
                        buffer[i] = fg_hi
                        buffer[i + 1] = fg_lo
                    else:
                        buffer[i] = bg_hi
                        buffer[i + 1] = bg_lo

                    bs_bit += 1

                to_col = x + char_width - 1
                to_row = y + font.HEIGHT - 1
                if self.width > to_col and self.height > to_row:
                    self._set_window(x, y, to_col, to_row)
                    self._write(None, buffer[:buffer_needed])

                x += char_width

            except ValueError:
                pass

    def write_width(self, font, string):
        """
        Returns the width in pixels of the string if it was written with the
        specified font

        Args:
            font (font): The module containing the converted true-type font
            string (string): The string to measure
        """
        width = 0
        for character in string:
            try:
                char_index = font.MAP.index(character)
                width += font.WIDTHS[char_index]

            except ValueError:
                pass

        return width
