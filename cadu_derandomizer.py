# -*- coding: utf-8 -*-
#
# cadu_derandomizer.py - GNU Radio Python block (PDU -> PDU)
#
# Keeps first header_len bytes (default 4, CADU ASM) unchanged,
# XORs the rest with CCSDS TM pseudo-random sequence (seed=0xFF).
#
import pmt
from gnuradio import gr


def _ccsds_random_bytes(n: int) -> bytes:
    """
    CCSDS TM randomizer sequence (byte-oriented view), generated bitwise MSB-first.

    This generator matches the well-known prefix:
      ff 48 0e c0 9a 0d 70 bc ...

    Polynomial (per CCSDS TM): x^8 + x^7 + x^5 + x^3 + 1
    Implementation form here (Fibonacci, left shift):
      feedback = bit7 ^ bit4 ^ bit2 ^ bit0
      out_bit  = bit7 (MSB)
    """
    state = 0xff
    out = bytearray()

    for _ in range(n):
        byte = 0
        for _ in range(8):
            out_bit = (state >> 7) & 1
            byte = ((byte << 1) & 0xff) | out_bit

            feedback = ((state >> 7) ^ (state >> 4) ^ (state >> 2) ^ (state >> 0)) & 1
            state = ((state << 1) & 0xff) | feedback

        out.append(byte)

    return bytes(out)


class CaduDerandomizer(gr.basic_block):
    """
    Input:  PDU on message port 'in' (PMT pair: (meta . u8vector))
    Output: PDU on message port 'out' (same meta, derandomized payload)

    Derandomizes bytes by XOR with CCSDS random sequence.
    The sequence restarts at the beginning for each PDU (standard behavior).
    """

    def __init__(self):
        gr.basic_block.__init__(self, name="cadu_derandomizer", in_sig=[], out_sig=[])

        self._mask = _ccsds_random_bytes(0xff)
        self._in_port = pmt.intern("in")
        self._out_port = pmt.intern("out")
        self.message_port_register_in(self._in_port)
        self.message_port_register_out(self._out_port)
        self.set_msg_handler(self._in_port, self._handle_msg)

    def _handle_msg(self, msg):
        # Expect PDU: (meta . u8vector)
        if pmt.is_pair(msg) is False:
            return

        meta = pmt.car(msg)
        data = pmt.cdr(msg)

        if pmt.is_u8vector(data) is False:
            return

        raw = bytes(pmt.u8vector_elements(data))
        out_raw = bytearray(raw)
        for i in range(len(out_raw)):
            out_raw[i] ^= self._mask[i % 0xff]

        out_vec = pmt.init_u8vector(len(out_raw), list(out_raw))
        out_msg = pmt.cons(meta, out_vec)
        self.message_port_pub(self._out_port, out_msg)
