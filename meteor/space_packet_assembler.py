# -*- coding: utf-8 -*-
#
# space_packet_assembler.py - GNU Radio PDU block (VC Data Unit / MPDU -> CCSDS Space Packets)
#
# Input:  PDU (u8vector) containing an MPDU-like buffer where:
#         - first_header_pointer is stored in bytes [2] and [3] (11 bits)
#         - payload begins at byte [4]
# Output: PDUs, each one is a complete CCSDS Space Packet payload (data field),
#         with SpacePacketHeader fields exported to PDU metadata.

import pmt
from gnuradio import gr


class SpacePacketAssembler(gr.basic_block):
    SPACE_PACKET_HEADER_LEN = 6

    def __init__(self):
        gr.basic_block.__init__(self, name="space_packet_assembler", in_sig=None, out_sig=None)

        self._partial = None  # type: bytes | None

        self.message_port_register_in(pmt.intern("in"))
        self.message_port_register_out(pmt.intern("out"))
        self.set_msg_handler(pmt.intern("in"), self._handle)

    def _parse_space_packet_header(self, data):
        if len(data) < self.SPACE_PACKET_HEADER_LEN:
            raise ValueError(
                f"not enough bytes for CCSDS header (need {self.SPACE_PACKET_HEADER_LEN}, got {len(data)})"
            )

        version = (data[0] >> 5) & 0x07
        pkt_type = ((data[0] >> 4) & 0x01) == 1
        secondary_header_flag = ((data[0] >> 3) & 0x01) == 1
        apid = ((data[0] & 0x07) << 8) | data[1]

        sequence_flag = (data[2] >> 6) & 0x03
        packet_sequence_count = ((data[2] & 0x3F) << 8) | data[3]

        packet_length = ((data[4] << 8) | data[5]) + 1  # as in your reference

        header = {
            "version": version,
            "type": 1 if pkt_type else 0,
            "secondary_header_flag": 1 if secondary_header_flag else 0,
            "apid": apid,
            "sequence_flag": sequence_flag,
            "packet_sequence_count": packet_sequence_count,
            "packet_length": packet_length,
        }
        return header

    def _emit_space_packet(self, meta_in, payload_bytes):
        meta = meta_in
        # meta = pmt.dict_add(meta, pmt.intern("space_packet.ccsds_version"), pmt.from_long(header["version"]))
        # meta = pmt.dict_add(meta, pmt.intern("space_packet.ccsds_type"), pmt.from_long(header["type"]))
        # meta = pmt.dict_add(meta, pmt.intern("space_packet.secondary_header_flag"), pmt.from_long(header["secondary_header_flag"]))
        # meta = pmt.dict_add(meta, pmt.intern("space_packet.apid"), pmt.from_long(header["apid"]))
        # meta = pmt.dict_add(meta, pmt.intern("space_packet.sequence_flag"), pmt.from_long(header["sequence_flag"]))
        # meta = pmt.dict_add(meta, pmt.intern("space_packet.packet_sequence_count"), pmt.from_long(header["packet_sequence_count"]))
        # meta = pmt.dict_add(meta, pmt.intern("space_packet.packet_length"), pmt.from_long(header["packet_length"]))

        vec = pmt.init_u8vector(len(payload_bytes), list(payload_bytes))
        self.message_port_pub(pmt.intern("out"), pmt.cons(meta, vec))

    def _handle(self, msg):
        meta_in = pmt.car(msg)
        mpdu = bytes(pmt.u8vector_elements(pmt.cdr(msg)))

        if len(mpdu) < 4:
            self.logger.error(f"MPDU too short: {len(mpdu)} bytes (need at least 4)")
            return

        first_header_pointer = ((mpdu[2] & 0x07) << 8) | mpdu[3]
        payload = mpdu[4:]

        # If a new header starts in this frame:
        if first_header_pointer != 0x7FF:
            # Close previous partial (if any)
            if self._partial is not None:
                self._partial = self._partial + payload[:first_header_pointer]

                # Expect one complete packet in _partial. If too short, drop.
                # If longer, emit first complete packet and ignore the rest.
                if len(self._partial) >= self.SPACE_PACKET_HEADER_LEN:
                    try:
                        header = self._parse_space_packet_header(self._partial)
                        full_packet_len = self.SPACE_PACKET_HEADER_LEN + header["packet_length"]
                        if len(self._partial) >= full_packet_len:
                            pkt_payload = self._partial[:full_packet_len]
                            self._emit_space_packet(meta_in, pkt_payload)
                    except Exception as e:
                        self.logger.error(f"Failed to parse/emit partial space packet: {e}")

                self._partial = None

            payload = payload[first_header_pointer:]

        # Parse complete packets from payload
        while len(payload) >= self.SPACE_PACKET_HEADER_LEN:
            try:
                header = self._parse_space_packet_header(payload)
            except Exception as e:
                self.logger.error(f"Failed to parse space packet header: {e}")
                return
            
            full_packet_len = self.SPACE_PACKET_HEADER_LEN + header["packet_length"]

            if len(payload) >= full_packet_len:
                pkt_payload = payload[:full_packet_len]
                self._emit_space_packet(meta_in, pkt_payload)
                payload = payload[full_packet_len:]
            else:
                # Not enough: store as partial
                if self._partial is None:
                    self._partial = payload
                else:
                    self._partial = self._partial + payload
                payload = b""

        # Any leftover bytes become/extend partial
        if len(payload) > 0:
            if self._partial is None:
                self._partial = payload
            else:
                self._partial = self._partial + payload