from gnuradio import gr
import pmt
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict
from PIL import Image
from decode_jpeg import decode_14_blocks
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ---------------- CONSTANTS ----------------

BLOCKS_PER_LINE = 14
BLOCK_WIDTH = 8 * 14
BLOCK_HEIGHT = 8
IMAGE_WIDTH = BLOCKS_PER_LINE * BLOCK_WIDTH


# ---------------- DATA STRUCTURES ----------------

@dataclass
class Channel:
    apid: int
    big_rows: List[List[int]]
    current_line: Optional[List[List[int]]]


# ---------------- MAIN BLOCK ----------------

@dataclass
class SpacePacketHeader:
    version: int
    type: bool
    secondary_header_flag: bool
    apid: int
    sequence_flag: int
    packet_sequence_count: int
    packet_length: int

@dataclass
class SpacePacket:
    header: SpacePacketHeader
    payload: bytes



@dataclass
class Segment:
    timestamp: datetime           # datetime

    MCUN: int                  # uint8_t
    QT: int                    # uint8_t
    DC: int                    # uint8_t
    AC: int                    # uint8_t
    QFM: int                   # uint16_t
    QF: int                    # uint8_t
    payload: bytes

@dataclass
class Channel:
    apid: int
    big_rows: List[List[int]]
    current_line: int



def parse_ccsds_time_full_raw_utc(data: bytes,) -> datetime:
    METEOR_EPOCH = 11322

    assert len(data) >= 8, f"Need at least 8 bytes for CCSDS time, got {len(data)}"

    days = (data[0] << 8) | data[1]
    milliseconds_of_day = (
        (data[2] << 24)
        | (data[3] << 16)
        | (data[4] << 8)
        | data[5]
    )
    microseconds_of_millisecond = (data[6] << 8) | data[7]

    total_days = METEOR_EPOCH + days

    seconds_of_day = milliseconds_of_day / 1000 + microseconds_of_millisecond / 1000000
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    return epoch + timedelta(days=total_days, seconds=seconds_of_day)



def parse_segment(
    data: bytes,
) -> Segment:
    assert len(data) >= 14

    timestamp = parse_ccsds_time_full_raw_utc(data)

    MCUN = data[8]
    QT = data[9]
    DC = (data[10] & 0xF0) >> 4
    AC = data[10] & 0x0F
    QFM = (data[11] << 8) | data[12]
    QF = data[13]

    return Segment(
        timestamp=timestamp,
        MCUN=MCUN,
        QT=QT,
        DC=DC,
        AC=AC,
        QFM=QFM,
        QF=QF,
        payload=data[14:]
    )


SPACE_PACKET_HEADER_LEN = 6
def parse_space_packet(data):
    if len(data) < SPACE_PACKET_HEADER_LEN:
        raise ValueError(
            f"not enough bytes for CCSDS header (need {SPACE_PACKET_HEADER_LEN}, got {len(data)})"
        )

    version = (data[0] >> 5) & 0x07
    pkt_type = ((data[0] >> 4) & 0x01) == 1
    secondary_header_flag = ((data[0] >> 3) & 0x01) == 1
    apid = ((data[0] & 0x07) << 8) | data[1]

    sequence_flag = (data[2] >> 6) & 0x03
    packet_sequence_count = ((data[2] & 0x3F) << 8) | data[3]

    packet_length = ((data[4] << 8) | data[5]) + 1  # as in your reference

    return SpacePacket(
        SpacePacketHeader(
            version=version,
            type=pkt_type,
            secondary_header_flag=secondary_header_flag,
            apid=apid,
            sequence_flag=sequence_flag,
            packet_sequence_count=packet_sequence_count,
            packet_length=packet_length
        ),
        data[SPACE_PACKET_HEADER_LEN:]
    )

class CcsdsImageSink(gr.basic_block):

    def __init__(self, out_dir: str = "output"):
        gr.basic_block.__init__(self, name="ccsds_image_sink", in_sig=[], out_sig=[])

        self.message_port_register_in(pmt.intern("in"))
        self.message_port_register_out(pmt.intern("img_out"))

        self.set_msg_handler(pmt.intern("in"), self.handle_msg)
        
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.apid_to_channel: Dict[int, Channel] = {}

    # ---------------- MESSAGE HANDLER ----------------

    def handle_msg(self, msg):
        meta = pmt.car(msg)
        data = pmt.cdr(msg)

        payload = bytes(pmt.u8vector_elements(data))

        space_packet = parse_space_packet(payload)
        self.process_packet(space_packet)

    # ---------------- PACKET PROCESSING ----------------

    def process_packet(self, space_packet:SpacePacket):
        apid = space_packet.header.apid
        payload = space_packet.payload

        if apid == 70:
            return

        if 60 <= apid < 70:

            channel = self.apid_to_channel.get(apid)
            if channel is None:
                channel = Channel(apid=apid, big_rows=[], current_line=None)
                self.apid_to_channel[apid] = channel

            segment = parse_segment(payload)
            pixels = decode_14_blocks(segment.payload, segment.QF)

            packet_idx_in_line = segment.MCUN // 14
            x0 = packet_idx_in_line * BLOCK_WIDTH

            # If new line starts but previous wasn't complete → flush partial
            if packet_idx_in_line == 0 and channel.current_line is not None:
                channel.big_rows.extend(channel.current_line)
                if apid == 64:
                    # flatten 8 rows
                    flat = [
                        pixel
                        for row in channel.current_line
                        for pixel in row
                    ]

                    vec = pmt.init_u8vector(len(flat), flat)
                    msg = pmt.cons(pmt.PMT_NIL, vec)

                    self.message_port_pub(pmt.intern("img_out"), msg)
                channel.current_line = None

            if channel.current_line is None:
                channel.current_line = [
                    [0] * IMAGE_WIDTH for _ in range(BLOCK_HEIGHT)
                ]

            for row in range(BLOCK_HEIGHT):
                channel.current_line[row][x0:x0 + BLOCK_WIDTH] = pixels[row]

            if packet_idx_in_line == BLOCKS_PER_LINE - 1:
                channel.big_rows.extend(channel.current_line)
                if apid == 64:
                    for row in channel.current_line:
                        vec = pmt.init_u8vector(len(row), row)
                        msg = pmt.cons(pmt.PMT_NIL, vec)
                        self.message_port_pub(pmt.intern("img_out"), msg)
                channel.current_line = None

        # Raw dump
        out_path = self.out_dir / f"{apid}.bin"
        with out_path.open("ab") as f:
            f.write(payload)

    # ---------------- STOP / FINAL FLUSH ----------------

    def stop(self):
        self.flush_images()
        return super().stop()

    # ---------------- IMAGE GENERATION ----------------

    def flush_images(self):
        for channel in self.apid_to_channel.values():
            if len(channel.big_rows) > 0:
                img = self.channel_to_gray_image(channel)
                img.save(self.out_dir / f"pic{channel.apid}.png")

        # RGB composite (adjust APIDs if needed)
        r_ch = self.apid_to_channel.get(65)
        g_ch = self.apid_to_channel.get(66)
        b_ch = self.apid_to_channel.get(64)

        if r_ch and g_ch and b_ch:
            if r_ch.big_rows and g_ch.big_rows and b_ch.big_rows:

                r = self.channel_to_gray_image(r_ch)
                g = self.channel_to_gray_image(g_ch)
                b = self.channel_to_gray_image(b_ch)

                h = min(r.height, g.height, b.height)

                r = r.crop((0, 0, IMAGE_WIDTH, h))
                g = g.crop((0, 0, IMAGE_WIDTH, h))
                b = b.crop((0, 0, IMAGE_WIDTH, h))

                rgb = Image.merge("RGB", (r, g, b))
                rgb.save(self.out_dir / "composite_rgb.png")

    def channel_to_gray_image(self, channel: Channel) -> Image.Image:
        height = len(channel.big_rows)
        img = Image.new("L", (IMAGE_WIDTH, height))
        flat = [pixel for row in channel.big_rows for pixel in row]
        img.putdata(flat)
        return img