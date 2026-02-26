# -*- coding: utf-8 -*-
#
# vcdu_parser.py - GNU Radio PDU block (VCDU -> VC Data Unit)
#
# Behaviour:
# - Requires minimum 6 bytes (VCDU Primary Header)
# - Parses header fields
# - Outputs payload (bytes after first 6)
#

import pmt
from gnuradio import gr


class VcduParser(gr.basic_block):

    VCDU_PRIMARY_HEADER_LEN = 6

    def __init__(self):
        gr.basic_block.__init__(self, name="vcdu_parser", in_sig=None, out_sig=None)

        self.message_port_register_in(pmt.intern("in"))
        self.message_port_register_out(pmt.intern("out"))
        self.set_msg_handler(pmt.intern("in"), self._handle)

    def _handle(self, msg):
        meta_in = pmt.car(msg)
        data = bytes(pmt.u8vector_elements(pmt.cdr(msg)))

        if len(data) < self.VCDU_PRIMARY_HEADER_LEN:
            self.logger.error(f"VCDU too short: {len(data)} bytes")
            return

        b0, b1, b2, b3, b4, b5 = data[0:6]

        version_number = (b0 >> 6) & 0x03
        spacecraft_id = ((b0 & 0x3F) << 2) | ((b1 >> 6) & 0x03)
        virtual_channel_id = b1 & 0x3F
        vcdu_counter = (b2 << 16) | (b3 << 8) | b4

        signalling_field = b5
        replay_flag = (b5 >> 7) & 1

        payload = data[self.VCDU_PRIMARY_HEADER_LEN:]

        meta = meta_in
        meta = pmt.dict_add(meta, pmt.intern("version_number"), pmt.from_long(version_number))
        meta = pmt.dict_add(meta, pmt.intern("spacecraft_id"), pmt.from_long(spacecraft_id))
        meta = pmt.dict_add(meta, pmt.intern("virtual_channel_id"), pmt.from_long(virtual_channel_id))
        meta = pmt.dict_add(meta, pmt.intern("vcdu_counter"), pmt.from_long(vcdu_counter))
        meta = pmt.dict_add(meta, pmt.intern("signalling_field_raw"), pmt.from_long(signalling_field))
        meta = pmt.dict_add(meta, pmt.intern("replay_flag"), pmt.from_long(replay_flag))

        vec = pmt.init_u8vector(len(payload), list(payload))
        self.message_port_pub(pmt.intern("out"), pmt.cons(meta, vec))