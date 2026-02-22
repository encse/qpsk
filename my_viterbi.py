# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.10.12.0

from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
import satellites.hier
import threading
import numpy as np
from gnuradio import gr

def _parity(x: int) -> int:
    return bin(x).count("1") & 1

class ber_ccsds_soft_decoded(gr.basic_block):
    def __init__(self, poly0=79, poly1=-109, constraint_len=7,
                 window=4096, erase_eps=0.0, scale=2.5):
        gr.basic_block.__init__(
            self,
            name="ber_ccsds_soft_decoded",
            in_sig=[np.float32, np.uint8],
            out_sig=[np.float32],
        )

        self.inv0 = (int(poly0) < 0)
        self.inv1 = (int(poly1) < 0)
        self.g0 = abs(int(poly0))
        self.g1 = abs(int(poly1))

        self.K = int(constraint_len)
        self.mask = (1 << self.K) - 1
        self.reg = 0

        self.window = int(window)
        self.erase_eps = float(erase_eps)
        self.scale = float(scale)

        self.err0 = self.tot0 = 0
        self.err1 = self.tot1 = 0
        self.last = 0.0

    def _encode_pair(self, bit: int):
        self.reg = ((self.reg << 1) | (bit & 1)) & self.mask
        e0 = _parity(self.reg & self.g0)
        e1 = _parity(self.reg & self.g1)
        if self.inv0:
            e0 ^= 1
        if self.inv1:
            e1 ^= 1
        return e0, e1

    def general_work(self, input_items, output_items):
        soft = input_items[0]
        dec  = input_items[1]
        out  = output_items[0]

        n_dec = len(dec)
        n_soft = len(soft)

        # Need 2 soft items per decoded bit, plus 1 extra for shift=1

        n_dec  = len(dec)
        n_soft = len(soft)
        n_out  = len(out)
        # Need: for i = n-1, max soft index is 2*i+2 => 2*(n-1)+2 <= n_soft-1  => n <= n_soft//2
        n = min(n_dec, n_soft // 2, n_out)
        if n <= 0:
            return 0

        for i in range(n):
            b = int(dec[i] & 1)
            e0, e1 = self._encode_pair(b)

            # shift 0: soft[2*i], soft[2*i+1]
            # shift 1: soft[2*i+1], soft[2*i+2]
            for shift in (0, 1):
                s0 = float(soft[2*i + shift])
                s1 = float(soft[2*i + shift + 1])

                if abs(s0) <= self.erase_eps or abs(s1) <= self.erase_eps:
                    continue

                h0 = 1 if s0 > 0.0 else 0
                h1 = 1 if s1 > 0.0 else 0

                if shift == 0:
                    self.err0 += (h0 != e0) + (h1 != e1)
                    self.tot0 += 2
                else:
                    self.err1 += (h0 != e0) + (h1 != e1)
                    self.tot1 += 2

            if self.tot0 >= self.window and self.tot1 >= self.window:
                ber0 = (self.err0 / self.tot0) * self.scale
                ber1 = (self.err1 / self.tot1) * self.scale
                self.last = ber0 if ber0 <= ber1 else ber1
                self.err0 = self.tot0 = 0
                self.err1 = self.tot1 = 0

            out[i] = self.last

        self.consume(0, 2 * n)  # keep 1 soft sample for shift=1 lookahead naturally
        self.consume(1, n)
        return n



class my_viterbi(gr.hier_block2):
    def __init__(self, code="CCSDS uninverted"):
        gr.hier_block2.__init__(
            self, "my_viterbi",
            gr.io_signature(1, 1, gr.sizeof_float),
            gr.io_signature(2, 2, [gr.sizeof_char, gr.sizeof_float]),
        )

        ##################################################
        # Parameters
        ##################################################
        self.code = code


        ##################################################
        # Blocks
        ##################################################


        if code not in ['CCSDS', 'NASA-DSN', 'CCSDS uninverted', 'NASA-DSN uninverted']:
            raise Exception("coki")

        
        polys = {'CCSDS': [79, -109],
            'NASA-DSN': [-109, 79],
            'CCSDS uninverted': [79, 109],
            'NASA-DSN uninverted': [109, 79],
            }[code]
    
        self.vit = satellites.hier.ccsds_viterbi(code)
        self.ber = ber_ccsds_soft_decoded(poly0=polys[0], poly1=polys[1], window=4096, erase_eps=0.0, scale=2.5)

        ##################################################
        # Connections
        ##################################################
        self.connect((self, 0), (self.vit, 0))
        self.connect((self.vit, 0), (self, 0))          # decoded -> out0

        # BER needs BOTH inputs: soft + decoded
        self.connect((self, 0), (self.ber, 0))          # soft float
        self.connect((self.vit, 0), (self.ber, 1))      # decoded bits 0/1
        self.connect((self.ber, 0), (self, 1))          # BER float -> out1


    def get_code(self):
        return self.code

    def set_code(self, code):
        self.code = code


