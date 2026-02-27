# -*- coding: utf-8 -*-
#
# cadu_framer.py - GNU Radio Python block (stream bits -> CADU bit-PDUs)
#
# Input:  stream of uint8 bits (0/1)
# Output: message port 'cadu' with PMT PDU (u8vector) of length cadu_len_bits
#
import numpy as np
from gnuradio import gr
import pmt


class CaduFramer(gr.basic_block):
    """
    CADU framer:
      - input: stream of bits as unsigned char (0/1)
      - output: PDUs on message port 'cadu', each PDU is one CADU frame as UNPACKED BITS (0/1)
      - behavior: shifter-based ASM search + automatic bit inversion (ASM or ~ASM)
      - output format: u8vector of bits (0/1), length = cadu_len_bytes*8
      - meta: packet_len = number of items (bits)
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

        # store bits as 0/1 (bytearray is fine)
        self._bits = bytearray(self.cadu_size_bits)

        self._port = pmt.intern("cadu")
        self.message_port_register_out(self._port)

    def _reset_frame(self):
        self._bit_of_frame = 0
        # no need to clear the whole buffer every time; we'll overwrite sequentially

    def _write_bit(self, b):
        # store unpacked bit (0 or 1)
        self._bits[self._bit_of_frame] = int(b) & 1
        self._bit_of_frame += 1

    def _emit_frame(self):
        vec = pmt.init_u8vector(self.cadu_size_bits, list(self._bits))

        meta = pmt.make_dict()
        meta = pmt.dict_add(meta, pmt.intern("packet_len"), pmt.from_long(self.cadu_size_bits))

        msg = pmt.cons(meta, vec)
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