# -*-coding:utf-8-*-
#
# The CyberBrick Codebase License, see the file LICENSE for details.
#
# Copyright (c) 2025 MakerWorld
#
# This file is executed on every boot (including wake-boot from deepsleep)

# ---- 立即熄灭 NeoPixel，最小化上电闪烁 ----
from machine import Pin, bitstream
_seq = (400, 1000, 1000, 400)
# LED0 (pin 8): 单颗板载
_buf0 = bytearray(3)
bitstream(Pin(8, Pin.OUT), 0, _seq, _buf0)
del _seq, _buf0, Pin, bitstream

import bbl_product
import sys

_PRODUCT_NAME = "RC"
_PRODUCT_VERSION = "01.00.00.21"

bbl_product.set_app_name(_PRODUCT_NAME)
bbl_product.set_app_version(_PRODUCT_VERSION)
del bbl_product
del _PRODUCT_NAME
del _PRODUCT_VERSION

sys.path.append("/app")
sys.path.append("/bbl")

import rc_main
rc_main.main()
