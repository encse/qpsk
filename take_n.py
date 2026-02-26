# -*- coding: utf-8 -*-
#
# take_n.py - GNU Radio PDU block (pass first N PDUs, then drop)
#
import pmt
from gnuradio import gr


class TakeN(gr.basic_block):
    def __init__(self, n=1):
        gr.basic_block.__init__(self, name="take_n", in_sig=None, out_sig=None)

        self._n = int(n)
        if self._n < 0:
            self._n = 0

        self._count = 0

        self.message_port_register_in(pmt.intern("in"))
        self.message_port_register_out(pmt.intern("out"))
        self.set_msg_handler(pmt.intern("in"), self._handle)

    def _handle(self, msg):
        if self._count >= self._n:
            return

        self._count += 1
        self.message_port_pub(pmt.intern("out"), msg)