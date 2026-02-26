# -*- coding: utf-8 -*-
#
# cadu_framer.py - GNU Radio Python block (stream bits -> CADU PDUs)
#
# Input:  stream of uint8 bits (0/1)
# Output: message port 'cadu' with PMT PDU (u8vector) of length cadu_len_bytes
#
import numpy as np
from gnuradio import gr
import pmt

class cadu_framer(gr.basic_block):
    """
    CADU framer:
      - input: stream of bits as unsigned char (0/1)
      - output: PDUs on message port 'cadu', each PDU is one CADU frame (cadu_len_bytes bytes)
      - behavior: shifter-based ASM search + automatic bit inversion (ASM or ~ASM)
      - packing: MSB-first (byte = (byte<<1)|bit), matching the reference code
    """

    def __init__(self, cadu_len_bytes=1024, cadu_asm=0x1ACFFC1D):
        gr.basic_block.__init__(
            self,
            name="cadu_framer",
            in_sig=[np.uint8],
            out_sig=[]
        )

        self.cadu_len_bytes = int(cadu_len_bytes)
        self.cadu_size_bits = self.cadu_len_bytes * 8

        self.CADU_ASM = int(cadu_asm) & 0xFFFFFFFF
        self.CADU_ASM_INV = (~self.CADU_ASM) & 0xFFFFFFFF

        self._shifter = 0
        self._in_frame = False
        self._bit_inversion = 0
        self._bit_of_frame = 0
        self._frame_buf = bytearray(self.cadu_len_bytes)

        self._port = pmt.intern("cadu")
        self.message_port_register_out(self._port)

    def _reset_frame(self):
        # Pre-fill with uninverted ASM bytes.
        self._frame_buf[:] = b"\x00" * self.cadu_len_bytes
        self._frame_buf[0] = (self.CADU_ASM >> 24) & 0xFF
        self._frame_buf[1] = (self.CADU_ASM >> 16) & 0xFF
        self._frame_buf[2] = (self.CADU_ASM >>  8) & 0xFF
        self._frame_buf[3] = (self.CADU_ASM >>  0) & 0xFF
        self._bit_of_frame = 32

    def _write_bit(self, b):
        byte_i = self._bit_of_frame // 8
        self._frame_buf[byte_i] = ((self._frame_buf[byte_i] << 1) & 0xFF) | (int(b) & 1)
        self._bit_of_frame += 1

    def _emit_frame(self):
        vec = pmt.init_u8vector(self.cadu_len_bytes, list(self._frame_buf))
        msg = pmt.cons(pmt.PMT_NIL, vec)
        self.message_port_pub(self._port, msg)

    def general_work(self, input_items, output_items):
        in0 = input_items[0]

        for b in in0:
            bit = int(b) & 1
            self._shifter = ((self._shifter << 1) & 0xFFFFFFFF) | bit

            if self._in_frame:
                self._write_bit(bit ^ self._bit_inversion)
                if self._bit_of_frame == self.cadu_size_bits:
                    self._emit_frame()
                    self._in_frame = False
                continue

            if self._shifter == self.CADU_ASM:
                self._bit_inversion = 0
                self._reset_frame()
                self._in_frame = True
            elif self._shifter == self.CADU_ASM_INV:
                self._bit_inversion = 1
                self._reset_frame()
                self._in_frame = True

        self.consume_each(len(in0))
        return 0
