# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.10.12.0

import numpy as np
from gnuradio import gr
from gnuradio import gr
from gnuradio import fec

def _parity_u32(x: int) -> int:
    # parity of integer bits (0/1)
    x ^= x >> 16
    x ^= x >> 8
    x ^= x >> 4
    x &= 0xF
    return (0x6996 >> x) & 1


def _conv_encode_k7_r12(bits_u8: np.ndarray, poly0: int, poly1: int) -> np.ndarray:
    """
    Convolutional encode K=7, rate 1/2, polys given like the C++ code.
    If a poly is negative, we invert that output bit (matches your mapping).
    Output is unpacked bits (0/1) length = 2*len(bits).
    """
    inv0 = 1 if poly0 < 0 else 0
    inv1 = 1 if poly1 < 0 else 0
    p0 = abs(int(poly0))
    p1 = abs(int(poly1))

    reg = 0
    out = np.empty(bits_u8.size * 2, dtype=np.uint8)

    # K=7 => 7-bit shift reg. We'll keep it in lower 7 bits.
    # Convention here: shift left, OR in new bit at LSB (common in many encoders).
    # IMPORTANT: if your encoder uses opposite bit order, BER will differ.
    # But for CCSDS K=7 this convention typically matches common implementations.
    for i, b in enumerate(bits_u8):
        bit = int(b) & 1
        reg = ((reg << 1) | bit) & 0x7F

        o0 = _parity_u32(reg & p0) ^ inv0
        o1 = _parity_u32(reg & p1) ^ inv1

        out[2 * i + 0] = o0
        out[2 * i + 1] = o1

    return out


class ber_ccsds_soft_decoded(gr.basic_block):
    """
    Compute SatDump-like BER proxy:

      raw_u8 derived from soft float:
        raw_u8 = round(soft*127 + 128) clipped to [0..255]
      skip raw_u8 == 128
      hard = (raw_u8 > 127)
      compare hard to re-encoded bits from decoded bits
      ber = (errors/total) * scale

    Inputs:
      0: soft float stream (carrier)
      1: decoded bits stream (char, values 0/1, length = soft/2)

    Output:
      0: float BER stream (hold-last; updates when a full window is available)
    """

    def __init__(self, poly0=79, poly1=109, window=4096, erase_eps=0.0, scale=2.5):
        gr.basic_block.__init__(
            self,
            name="ber_ccsds_soft_decoded",
            in_sig=[np.float32, np.uint8],
            out_sig=[np.float32],
        )

        self._poly0 = int(poly0)
        self._poly1 = int(poly1)
        self._window = int(window)
        self._scale = float(scale)
        self._erase_eps = float(erase_eps)

        if self._window <= 0 or (self._window % 2) != 0:
            raise ValueError("window must be positive and even (rate 1/2)")

        self._soft_buf = np.empty(self._window, dtype=np.float32)
        self._dec_buf = np.empty(self._window // 2, dtype=np.uint8)
        self._soft_fill = 0
        self._dec_fill = 0

        self._last = 10.0 

    def general_work(self, input_items, output_items):
        soft_in = input_items[0]
        dec_in = input_items[1]
        out = output_items[0]

        n_soft = len(soft_in)
        n_dec = len(dec_in)

        # We need soft and decoded in the fixed ratio: window soft : window/2 decoded.
        # Consume as much as we can to fill buffers.
        soft_needed = self._window - self._soft_fill
        dec_needed = (self._window // 2) - self._dec_fill

        take_soft = min(n_soft, soft_needed)
        take_dec = min(n_dec, dec_needed)

        if take_soft > 0:
            self._soft_buf[self._soft_fill:self._soft_fill + take_soft] = soft_in[:take_soft]
            self._soft_fill += take_soft
            self.consume(0, take_soft)

        if take_dec > 0:
            # ensure 0/1
            self._dec_buf[self._dec_fill:self._dec_fill + take_dec] = (dec_in[:take_dec] & 1).astype(np.uint8)
            self._dec_fill += take_dec
            self.consume(1, take_dec)

        # If we have a full window, compute BER and reset buffers
        if self._soft_fill == self._window and self._dec_fill == (self._window // 2):
            # float soft -> raw_u8 
            # 0.0 maps to 128 exactly (after rounding)
            raw = np.rint(self._soft_buf * 127.0 + 128.0)
            raw = np.clip(raw, 0.0, 255.0).astype(np.uint8)

            if self._erase_eps > 0.0:
                er = np.abs(self._soft_buf) <= self._erase_eps
                raw[er] = 128

            # re-encode decoded bits
            renc = _conv_encode_k7_r12(self._dec_buf, self._poly0, self._poly1)

            mask = (raw != 128)
            total = int(mask.sum())
            if total > 0:
                hard = (raw > 127).astype(np.uint8)
                errors = int((hard[mask] != renc[mask]).sum())
                self._last = (errors / total) * self._scale
            else:
                self._last = 10.0

            self._soft_fill = 0
            self._dec_fill = 0

        # Output: hold-last value (emit as many as scheduler requests)
        n_out = len(out)
        if n_out == 0:
            return 0
        out[:] = np.float32(self._last)
        return n_out


class Viterbi(gr.hier_block2):
    def __init__(self):
        gr.hier_block2.__init__(
            self, "viterbi",
            gr.io_signature(1, 1, gr.sizeof_float),
            gr.io_signature(2, 2, [gr.sizeof_char, gr.sizeof_float]),
        )
        
        polys = [109, 79]
    

        self.dec_cc = dec_cc = fec.cc_decoder.make(
            80, 7, 2, polys, 0, -1, fec.CC_STREAMING, False)

        self.vit = fec.extended_decoder(
            decoder_obj_list=dec_cc, threading=None, ann=None,
            puncpat='11', integration_period=10000)

        self.connect((self.vit, 0), (self, 0))
        self.connect((self, 0), (self.vit, 0))

        self.ber = ber_ccsds_soft_decoded(poly0=polys[0], poly1=polys[1], window=4096, erase_eps=0.0, scale=2.5)

        self.connect((self, 0), (self.ber, 0))          # soft float
        self.connect((self.vit, 0), (self.ber, 1))      # decoded bits 0/1
        self.connect((self.ber, 0), (self, 1))          # BER float -> out1



