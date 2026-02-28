# -*- coding: utf-8 -*-
import pmt
from gnuradio import gr

class ApidFilter(gr.basic_block):
    """
    Pass-through filter for PDUs based on meta["space_packet.apid"] == apid.
    Input/Output are message ports carrying PDUs: (meta_dict, u8vector).
    """
    def __init__(self, apid=65, key="space_packet.apid"):
        gr.basic_block.__init__(self, name="apid_filter", in_sig=None, out_sig=None)

        self._apid = int(apid)
        self._key_str = str(key)
        self._key = pmt.intern(self._key_str)

        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self._handle_msg)

        self.message_port_register_out(pmt.intern("out"))

    def set_apid(self, apid):
        self._apid = int(apid)

    def apid(self):
        return self._apid

    def set_key(self, key):
        self._key_str = str(key)
        self._key = pmt.intern(self._key_str)

    def key(self):
        return self._key_str

    def _handle_msg(self, msg):
        # Expect PDU pair: (meta, data)
        if pmt.is_pair(msg) is False:
            return

        meta = pmt.car(msg)
        if pmt.is_dict(meta) is False:
            return

        if pmt.dict_has_key(meta, self._key) is False:
            return

        apid_pmt = pmt.dict_ref(meta, self._key, pmt.PMT_NIL)
        if apid_pmt == pmt.PMT_NIL:
            return

        apid_val = pmt.to_long(apid_pmt)
        if apid_val == self._apid:
            self.message_port_pub(pmt.intern("out"), msg)