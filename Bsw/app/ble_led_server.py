# -*-coding:utf-8-*-
#
# The CyberBrick Codebase License, see the file LICENSE for details.
#
# Copyright (c) 2025 MakerWorld
#
# BLE LED Command Server
# 控制板载 LED0 (pin 8) 单颗 NeoPixel LED
#
# 命令格式: LED:<CMD>:[args]
#   LED:ON:<hex_color>         - 常亮
#   LED:BR:<hex_color>:<ms>    - 呼吸 (可选周期ms, 默认2000)
#   LED:OFF                    - 关灯
#
# handle() 立即解析+渲染，不依赖 asyncio 循环也能工作。
# run() 是后台 asyncio 任务，持续渲染呼吸动画。
#

from machine import Pin, bitstream
import uasyncio as asyncio
import utime
import math

# ---- 预计算呼吸正弦表 (0-255) ----
_sin_table = [
    int(255 * (1 + math.sin(2 * math.pi * i / 256 - math.pi / 2)) / 2)
    for i in range(256)
]
del math

# ---- NeoPixel 驱动 ----
_ORDER = (1, 0, 2, 3)  # G R B W mapping


class _NeoPixel:
    def __init__(self, pin, n, bpp=3, timing=1):
        self.pin = pin
        self.n = n
        self.bpp = bpp
        self.buf = bytearray(n * bpp)
        self.pin.init(pin.OUT)
        self.timing = (
            ((400, 850, 800, 450) if timing else (400, 1000, 1000, 400))
            if isinstance(timing, int)
            else timing
        )

    def fill(self, v):
        b = self.buf
        l = len(self.buf)
        bpp = self.bpp
        for i in range(bpp):
            c = v[i]
            j = _ORDER[i]
            while j < l:
                b[j] = c
                j += bpp

    def __setitem__(self, i, v):
        offset = i * self.bpp
        for j in range(self.bpp):
            self.buf[offset + _ORDER[j]] = v[j]

    def write(self):
        bitstream(self.pin, 0, self.timing, self.buf)


# ---- LED 命令处理器 ----
class LEDCommandHandler:
    """管理 LED0 (pin 8) 单颗 NeoPixel LED 的状态与渲染。"""
    LED0_PIN = 8
    FPS = 50

    def __init__(self):
        self.np = _NeoPixel(Pin(self.LED0_PIN, Pin.OUT), 1, timing=0)
        self.np.fill((0, 0, 0))
        self.np.write()

        self._rgb = 0x000000
        self._mode = 'off'
        self._period = 2000
        self._start_time = utime.ticks_ms()

    # ---- 公开接口 ----

    def handle(self, cmd_str):
        """立即解析命令并渲染到 NeoPixel (同步，不依赖 asyncio)"""
        if cmd_str and isinstance(cmd_str, str):
            cmd = cmd_str.strip()
            if cmd:
                self._dispatch(cmd)
                self._render()
                print("[LED] OK:", cmd)

    async def run(self):
        """后台 asyncio 任务: 持续渲染呼吸动画"""
        frame_ms = 1000 // self.FPS
        while True:
            self._render()
            await asyncio.sleep_ms(frame_ms)

    def all_off(self):
        """立即关闭 LED"""
        self._mode = 'off'
        self.np.fill((0, 0, 0))
        self.np.write()

    # ---- 命令解析 ----

    def _dispatch(self, cmd_str):
        try:
            parts = cmd_str.split(':')
            if len(parts) < 2 or parts[0] != 'LED':
                print("[LED] Invalid prefix:", cmd_str)
                return

            cmd = parts[1].upper()

            if cmd == 'ON':
                rgb = int(parts[2], 16)
                self._rgb = rgb
                self._mode = 'solid'

            elif cmd == 'BR':
                rgb = int(parts[2], 16)
                period = int(parts[3]) if len(parts) > 3 else 2000
                self._rgb = rgb
                self._mode = 'breath'
                self._period = max(200, period)

            elif cmd == 'OFF':
                self._mode = 'off'

            else:
                print("[LED] Unknown cmd:", cmd)

        except Exception as e:
            print("[LED] Parse err:", e)

    # ---- 渲染 ----

    def _render(self):
        mode = self._mode
        rgb = self._rgb

        if mode == 'off':
            val = (0, 0, 0)
        elif mode == 'solid':
            val = ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF)
        elif mode == 'breath':
            t = utime.ticks_ms()
            elapsed = utime.ticks_diff(t, self._start_time)
            idx = (elapsed * 256 // self._period) % 256
            b = _sin_table[idx]
            val = (
                ((rgb >> 16) & 0xFF) * b // 255,
                ((rgb >> 8) & 0xFF) * b // 255,
                (rgb & 0xFF) * b // 255,
            )

        self.np[0] = val
        self.np.write()


# ---- 全局单例 ----
_led_handler = None


def get_handler():
    global _led_handler
    if _led_handler is None:
        _led_handler = LEDCommandHandler()
    return _led_handler
