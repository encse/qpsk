from gnuradio import gr
import pmt
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from decode_jpeg import decode_14_blocks


# ---------------- CONSTANTS ----------------

BLOCKS_PER_LINE = 14
BLOCK_WIDTH = 8 * 14          # 112
BLOCK_HEIGHT = 8
IMAGE_WIDTH = BLOCKS_PER_LINE * BLOCK_WIDTH  # 1568


# ---------------- DATA STRUCTURES ----------------

@dataclass
class SpacePacketHeader:
    apid: int

@dataclass
class SpacePacket:
    header: SpacePacketHeader
    payload: bytes

@dataclass
class Segment:
    MCUN: int
    QF: int
    payload: bytes


# ---------------- PARSERS ----------------

SPACE_PACKET_HEADER_LEN = 6

def parse_space_packet(data: bytes) -> SpacePacket:
    if len(data) < SPACE_PACKET_HEADER_LEN:
        raise ValueError("CCSDS header too short")

    apid = ((data[0] & 0x07) << 8) | data[1]

    return SpacePacket(
        header=SpacePacketHeader(apid=apid),
        payload=data[SPACE_PACKET_HEADER_LEN:]
    )

def parse_segment(data: bytes) -> Segment:
    if len(data) < 14:
        raise ValueError("Segment too short")

    MCUN = data[8]
    QF = data[13]

    return Segment(
        MCUN=MCUN,
        QF=QF,
        payload=data[14:]
    )


# ---------------- GNU RADIO BLOCK ----------------

class CcsdsImageDecoder(gr.basic_block):
    """
    Input:  message port "in"  (u8vector CCSDS space packet)
    Output: message port "out" (u8vector, one image row per message)
    """

    def __init__(self, apid: int):
        gr.basic_block.__init__(self, name="ccsds_image_decoder", in_sig=[], out_sig=[])

        self.apid = int(apid)
        self.current_line: Optional[List[List[int]]] = None

        self.message_port_register_in(pmt.intern("in"))
        self.message_port_register_out(pmt.intern("out"))
        self.set_msg_handler(pmt.intern("in"), self._handle_msg)

    def _handle_msg(self, msg):
        payload = bytes(pmt.u8vector_elements(pmt.cdr(msg)))

        sp = parse_space_packet(payload)
        if sp.header.apid != self.apid:
            return

        self._process_packet(sp)

    def _emit_rows(self, rows: List[List[int]]):
        for row in rows:
            vec = pmt.init_u8vector(len(row), row)
            out_msg = pmt.cons(pmt.PMT_NIL, vec)
            self.message_port_pub(pmt.intern("out"), out_msg)

    def _process_packet(self, sp: SpacePacket):
        seg = parse_segment(sp.payload)

        pixels_8x112 = decode_14_blocks(seg.payload, seg.QF)

        packet_idx_in_line = seg.MCUN // 14
        x0 = packet_idx_in_line * BLOCK_WIDTH

        # New line but previous incomplete → flush
        if packet_idx_in_line == 0 and self.current_line is not None:
            self._emit_rows(self.current_line)
            self.current_line = None

        if self.current_line is None:
            self.current_line = [[0] * IMAGE_WIDTH for _ in range(BLOCK_HEIGHT)]

        for r in range(BLOCK_HEIGHT):
            self.current_line[r][x0:x0 + BLOCK_WIDTH] = pixels_8x112[r]

        # End of line
        if packet_idx_in_line == (BLOCKS_PER_LINE - 1):
            self._emit_rows(self.current_line)
            self.current_line = None