from dataclasses import dataclass
from typing import Iterator, Optional, List
from decode_jpeg import decode_14_blocks
from rs import CorrectRS255
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image

CADU_ASM = 0x1ACFFC1D
CADU_ASM_INV = CADU_ASM ^ 0xFFFFFFFF

CCSDS_PN = bytes([
    0xff, 0x48, 0x0e, 0xc0, 0x9a, 0x0d, 0x70, 0xbc,
    0x8e, 0x2c, 0x93, 0xad, 0xa7, 0xb7, 0x46, 0xce,
    0x5a, 0x97, 0x7d, 0xcc, 0x32, 0xa2, 0xbf, 0x3e,
    0x0a, 0x10, 0xf1, 0x88, 0x94, 0xcd, 0xea, 0xb1,
    0xfe, 0x90, 0x1d, 0x81, 0x34, 0x1a, 0xe1, 0x79,
    0x1c, 0x59, 0x27, 0x5b, 0x4f, 0x6e, 0x8d, 0x9c,
    0xb5, 0x2e, 0xfb, 0x98, 0x65, 0x45, 0x7e, 0x7c,
    0x14, 0x21, 0xe3, 0x11, 0x29, 0x9b, 0xd5, 0x63,
    0xfd, 0x20, 0x3b, 0x02, 0x68, 0x35, 0xc2, 0xf2,
    0x38, 0xb2, 0x4e, 0xb6, 0x9e, 0xdd, 0x1b, 0x39,
    0x6a, 0x5d, 0xf7, 0x30, 0xca, 0x8a, 0xfc, 0xf8,
    0x28, 0x43, 0xc6, 0x22, 0x53, 0x37, 0xaa, 0xc7,
    0xfa, 0x40, 0x76, 0x04, 0xd0, 0x6b, 0x85, 0xe4,
    0x71, 0x64, 0x9d, 0x6d, 0x3d, 0xba, 0x36, 0x72,
    0xd4, 0xbb, 0xee, 0x61, 0x95, 0x15, 0xf9, 0xf0,
    0x50, 0x87, 0x8c, 0x44, 0xa6, 0x6f, 0x55, 0x8f,
    0xf4, 0x80, 0xec, 0x09, 0xa0, 0xd7, 0x0b, 0xc8,
    0xe2, 0xc9, 0x3a, 0xda, 0x7b, 0x74, 0x6c, 0xe5,
    0xa9, 0x77, 0xdc, 0xc3, 0x2a, 0x2b, 0xf3, 0xe0,
    0xa1, 0x0f, 0x18, 0x89, 0x4c, 0xde, 0xab, 0x1f,
    0xe9, 0x01, 0xd8, 0x13, 0x41, 0xae, 0x17, 0x91,
    0xc5, 0x92, 0x75, 0xb4, 0xf6, 0xe8, 0xd9, 0xcb,
    0x52, 0xef, 0xb9, 0x86, 0x54, 0x57, 0xe7, 0xc1,
    0x42, 0x1e, 0x31, 0x12, 0x99, 0xbd, 0x56, 0x3f,
    0xd2, 0x03, 0xb0, 0x26, 0x83, 0x5c, 0x2f, 0x23,
    0x8b, 0x24, 0xeb, 0x69, 0xed, 0xd1, 0xb3, 0x96,
    0xa5, 0xdf, 0x73, 0x0c, 0xa8, 0xaf, 0xcf, 0x82,
    0x84, 0x3c, 0x62, 0x25, 0x33, 0x7a, 0xac, 0x7f,
    0xa4, 0x07, 0x60, 0x4d, 0x06, 0xb8, 0x5e, 0x47,
    0x16, 0x49, 0xd6, 0xd3, 0xdb, 0xa3, 0x67, 0x2d,
    0x4b, 0xbe, 0xe6, 0x19, 0x51, 0x5f, 0x9f, 0x05,
    0x08, 0x78, 0xc4, 0x4a, 0x66, 0xf5, 0x58
])

TO_DUAL_BASIS = bytes([
    0x00, 0x7b, 0xaf, 0xd4, 0x99, 0xe2, 0x36, 0x4d, 0xfa, 0x81, 0x55, 0x2e, 0x63, 0x18, 0xcc, 0xb7, 0x86, 0xfd, 0x29, 0x52, 0x1f,
    0x64, 0xb0, 0xcb, 0x7c, 0x07, 0xd3, 0xa8, 0xe5, 0x9e, 0x4a, 0x31, 0xec, 0x97, 0x43, 0x38, 0x75, 0x0e, 0xda, 0xa1, 0x16, 0x6d, 0xb9, 0xc2, 0x8f, 0xf4,
    0x20, 0x5b, 0x6a, 0x11, 0xc5, 0xbe, 0xf3, 0x88, 0x5c, 0x27, 0x90, 0xeb, 0x3f, 0x44, 0x09, 0x72, 0xa6, 0xdd, 0xef, 0x94, 0x40, 0x3b, 0x76, 0x0d, 0xd9,
    0xa2, 0x15, 0x6e, 0xba, 0xc1, 0x8c, 0xf7, 0x23, 0x58, 0x69, 0x12, 0xc6, 0xbd, 0xf0, 0x8b, 0x5f, 0x24, 0x93, 0xe8, 0x3c, 0x47, 0x0a, 0x71, 0xa5, 0xde,
    0x03, 0x78, 0xac, 0xd7, 0x9a, 0xe1, 0x35, 0x4e, 0xf9, 0x82, 0x56, 0x2d, 0x60, 0x1b, 0xcf, 0xb4, 0x85, 0xfe, 0x2a, 0x51, 0x1c, 0x67, 0xb3, 0xc8, 0x7f,
    0x04, 0xd0, 0xab, 0xe6, 0x9d, 0x49, 0x32, 0x8d, 0xf6, 0x22, 0x59, 0x14, 0x6f, 0xbb, 0xc0, 0x77, 0x0c, 0xd8, 0xa3, 0xee, 0x95, 0x41, 0x3a, 0x0b, 0x70,
    0xa4, 0xdf, 0x92, 0xe9, 0x3d, 0x46, 0xf1, 0x8a, 0x5e, 0x25, 0x68, 0x13, 0xc7, 0xbc, 0x61, 0x1a, 0xce, 0xb5, 0xf8, 0x83, 0x57, 0x2c, 0x9b, 0xe0, 0x34,
    0x4f, 0x02, 0x79, 0xad, 0xd6, 0xe7, 0x9c, 0x48, 0x33, 0x7e, 0x05, 0xd1, 0xaa, 0x1d, 0x66, 0xb2, 0xc9, 0x84, 0xff, 0x2b, 0x50, 0x62, 0x19, 0xcd, 0xb6,
    0xfb, 0x80, 0x54, 0x2f, 0x98, 0xe3, 0x37, 0x4c, 0x01, 0x7a, 0xae, 0xd5, 0xe4, 0x9f, 0x4b, 0x30, 0x7d, 0x06, 0xd2, 0xa9, 0x1e, 0x65, 0xb1, 0xca, 0x87,
    0xfc, 0x28, 0x53, 0x8e, 0xf5, 0x21, 0x5a, 0x17, 0x6c, 0xb8, 0xc3, 0x74, 0x0f, 0xdb, 0xa0, 0xed, 0x96, 0x42, 0x39, 0x08, 0x73, 0xa7, 0xdc, 0x91, 0xea,
    0x3e, 0x45, 0xf2, 0x89, 0x5d, 0x26, 0x6b, 0x10, 0xc4, 0xbf
])

FROM_DUAL_BASIS = bytes([
    0x00, 0xcc, 0xac, 0x60, 0x79, 0xb5, 0xd5, 0x19, 0xf0, 0x3c, 0x5c, 0x90, 0x89, 0x45, 0x25, 0xe9, 0xfd, 0x31, 0x51, 0x9d,
    0x84, 0x48, 0x28, 0xe4, 0x0d, 0xc1, 0xa1, 0x6d, 0x74, 0xb8, 0xd8, 0x14, 0x2e, 0xe2, 0x82, 0x4e, 0x57, 0x9b, 0xfb, 0x37, 0xde, 0x12, 0x72, 0xbe, 0xa7,
    0x6b, 0x0b, 0xc7, 0xd3, 0x1f, 0x7f, 0xb3, 0xaa, 0x66, 0x06, 0xca, 0x23, 0xef, 0x8f, 0x43, 0x5a, 0x96, 0xf6, 0x3a, 0x42, 0x8e, 0xee, 0x22, 0x3b, 0xf7,
    0x97, 0x5b, 0xb2, 0x7e, 0x1e, 0xd2, 0xcb, 0x07, 0x67, 0xab, 0xbf, 0x73, 0x13, 0xdf, 0xc6, 0x0a, 0x6a, 0xa6, 0x4f, 0x83, 0xe3, 0x2f, 0x36, 0xfa, 0x9a,
    0x56, 0x6c, 0xa0, 0xc0, 0x0c, 0x15, 0xd9, 0xb9, 0x75, 0x9c, 0x50, 0x30, 0xfc, 0xe5, 0x29, 0x49, 0x85, 0x91, 0x5d, 0x3d, 0xf1, 0xe8, 0x24, 0x44, 0x88,
    0x61, 0xad, 0xcd, 0x01, 0x18, 0xd4, 0xb4, 0x78, 0xc5, 0x09, 0x69, 0xa5, 0xbc, 0x70, 0x10, 0xdc, 0x35, 0xf9, 0x99, 0x55, 0x4c, 0x80, 0xe0, 0x2c, 0x38,
    0xf4, 0x94, 0x58, 0x41, 0x8d, 0xed, 0x21, 0xc8, 0x04, 0x64, 0xa8, 0xb1, 0x7d, 0x1d, 0xd1, 0xeb, 0x27, 0x47, 0x8b, 0x92, 0x5e, 0x3e, 0xf2, 0x1b, 0xd7,
    0xb7, 0x7b, 0x62, 0xae, 0xce, 0x02, 0x16, 0xda, 0xba, 0x76, 0x6f, 0xa3, 0xc3, 0x0f, 0xe6, 0x2a, 0x4a, 0x86, 0x9f, 0x53, 0x33, 0xff, 0x87, 0x4b, 0x2b,
    0xe7, 0xfe, 0x32, 0x52, 0x9e, 0x77, 0xbb, 0xdb, 0x17, 0x0e, 0xc2, 0xa2, 0x6e, 0x7a, 0xb6, 0xd6, 0x1a, 0x03, 0xcf, 0xaf, 0x63, 0x8a, 0x46, 0x26, 0xea,
    0xf3, 0x3f, 0x5f, 0x93, 0xa9, 0x65, 0x05, 0xc9, 0xd0, 0x1c, 0x7c, 0xb0, 0x59, 0x95, 0xf5, 0x39, 0x20, 0xec, 0x8c, 0x40, 0x54, 0x98, 0xf8, 0x34, 0x2d,
    0xe1, 0x81, 0x4d, 0xa4, 0x68, 0x08, 0xc4, 0xdd, 0x11, 0x71, 0xbd
])

@dataclass(frozen=True, slots=True)
class Mpdu:
    first_header_pointer: int
    payload: bytes

@dataclass
class VcduFrame:
    version: int            # 2 bits
    spacecraft_id: int      # 8 bits (6+2)
    vcid: int               # 6 bits
    counter: int            # 24-bit, big-endian
    replay_flag: bool       # 1 bit (MSB of header byte 5)
    mpdu: Mpdu              # 886 bytes
    

@dataclass
class Cadu:
    header: bytes
    payload: bytes

@dataclass
class CcsdsHeader:
    version: int
    type: bool
    secondary_header_flag: bool
    apid: int
    sequence_flag: int
    packet_sequence_count: int
    packet_length: int

@dataclass
class CcsdsPacket:
    header: CcsdsHeader
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

def derandomize(data: bytes) -> bytes:
    out = bytearray(len(data))
    for i in range(len(data)):
        out[i] = data[i] ^ CCSDS_PN[i % 255]
    return bytes(out)


def deinterleave4(payload: bytes) -> bytearray:
    assert len(payload) == 1020

    lanes = 4
    lane_size = len(payload) // lanes

    out = bytearray(len(payload))

    for lane in range(lanes):
        for i in range(lane_size):
            out[lane * lane_size + i] = payload[i * lanes + lane]

    return out


def interleave4(payload: bytes) -> bytearray:
    if not payload:
        return None
    
    assert len(payload) % 4 == 0

    lanes = 4
    lane_size = len(payload) // lanes

    out = bytearray(len(payload))

    for lane in range(lanes):
        for i in range(lane_size):
            out[i * lanes + lane] = payload[lane * lane_size + i]

    return out

def rs_decode_interleaved_4(rs: CorrectRS255, payload: bytes) -> bytes:
    assert len(payload) == 1020

    lanes = 4
    decoded_len = 223
    out = bytearray(lanes * decoded_len)

    for lane in range(lanes):
        lane255 = payload[lane::lanes]  # 255 bytes interleaved readout
        assert len(lane255) == 255

        try:
            decoded223 = rs.decode(lane255)
            assert len(decoded223) == decoded_len

            # write back interleaved
            for i in range(decoded_len):
                out[i * lanes + lane] = decoded223[i]

        except Exception:
            return None

    return out


def parse_vcdu(vcdu: Optional[bytes]) -> Optional[VcduFrame]:

    VCDU_HEADER_LEN = 6
    VCDU_MPDU_LEN = 886
    VCDU_TOTAL_LEN = VCDU_HEADER_LEN + VCDU_MPDU_LEN


    if vcdu is None:
        return None

    data = bytes(vcdu)

    assert len(data) == VCDU_TOTAL_LEN, \
        f"VCDU must be {VCDU_TOTAL_LEN} bytes, got {len(data)}"

    version = data[0] >> 6
    spacecraft_id = ((data[0] & 0b0011_1111) << 2) | (data[1] >> 6)
    vcid = data[1] & 0b0011_1111
    counter = (data[2] << 16) | (data[3] << 8) | data[4]
    replay_flag = (data[5] >> 7) == 1

    mpdu = data[VCDU_HEADER_LEN:]

    # ---- MPDU ----
    # first_header_pointer from bytes 8 and 9
    first_header_pointer = ((data[8] & 0b0000_0111) << 8) | data[9]

    # MPDU payload begins at byte 10
    mpdu_payload = data[10:]

    mpdu = Mpdu(
        first_header_pointer=first_header_pointer,
        payload=mpdu_payload,
    )

    return VcduFrame(
        version=version,
        spacecraft_id=spacecraft_id,
        vcid=vcid,
        counter=counter,
        replay_flag=replay_flag,
        mpdu=mpdu,
    )


CCSDS_HEADER_LEN = 6
def parse_ccsds_header(data: bytes) -> tuple[CcsdsHeader, bytes]:

    assert len(data) >= CCSDS_HEADER_LEN, \
        f"not enough bytes for CCSDS header (need {CCSDS_HEADER_LEN}, got {len(data)})"

    version = data[0] >> 5
    pkt_type = ((data[0] >> 4) & 0x01) == 1
    secondary_header_flag = ((data[0] >> 3) & 0x01) == 1
    apid = ((data[0] & 0b0000_0111) << 8) | data[1]

    sequence_flag = data[2] >> 6
    packet_sequence_count = ((data[2] & 0b0011_1111) << 8) | data[3]

    packet_length = (data[4] << 8) | data[5] 
    packet_length += 1

    rest = data[CCSDS_HEADER_LEN:]
    header = CcsdsHeader(
        version=version,
        type=pkt_type,
        secondary_header_flag=secondary_header_flag,
        apid=apid,
        sequence_flag=sequence_flag,
        packet_sequence_count=packet_sequence_count,
        packet_length=packet_length,
    )

    return header, rest

def parse_ccsds_packet(header: CcsdsHeader, payload: bytes) -> CcsdsPacket:
    assert len(payload) == header.packet_length
    return CcsdsPacket(
        header=header,
        payload=payload,
    )


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

def extract_cadu_frames(bits, cadu_len_bytes=1024) -> Iterator[Cadu]:
    """
    bits: list[int] of 0/1
    Returns: list[bytes] (each is a full CADU frame, length = cadu_len_bytes)
    Behavior: shifter-based ASM search + automatic bit inversion (ASM or ~ASM)
    """
    cadu_size_bits = cadu_len_bytes * 8
    shifter = 0

    in_frame = False
    bit_inversion = 0  # 0 or 1
    bit_of_frame = 0

    frame_buf = bytearray(cadu_len_bytes)

    def reset_frame():
        nonlocal bit_of_frame, frame_buf
        frame_buf[:] = b"\x00" * cadu_len_bytes
        frame_buf[0] = (CADU_ASM >> 24) & 0xFF
        frame_buf[1] = (CADU_ASM >> 16) & 0xFF
        frame_buf[2] = (CADU_ASM >>  8) & 0xFF
        frame_buf[3] = (CADU_ASM >>  0) & 0xFF
        bit_of_frame = 32

    def write_bit(b):
        nonlocal bit_of_frame
        byte_i = bit_of_frame // 8
        frame_buf[byte_i] = ((frame_buf[byte_i] << 1) & 0xFF) | (b & 1)
        bit_of_frame += 1

    for b in bits:
        bit = b & 1
        shifter = ((shifter << 1) & 0xFFFFFFFF) | bit

        if in_frame:
            write_bit(bit ^ bit_inversion)

            if bit_of_frame == cadu_size_bits:
                frame = bytes(frame_buf)
                yield Cadu(frame[:4], frame[4:])
                in_frame = False
            continue

        if shifter == CADU_ASM:
            bit_inversion = 0
            reset_frame()
            in_frame = True
        elif shifter == CADU_ASM_INV:
            bit_inversion = 1
            reset_frame()
            in_frame = True


def extract_vcdu_frames(bits) -> Iterator[VcduFrame]:
    with CorrectRS255(nsym=32, prim=0x187, fcr=112, generator_gap=11) as rs:
        for cadu in extract_cadu_frames(bits):
            cvcdu = derandomize(cadu.payload)
            res = rs_decode_interleaved_4(rs, cvcdu)
            if res:
                yield parse_vcdu(res)
            else:
                yield None
        

def extract_ccsds_packets(bits) -> Iterator[CcsdsPacket]:

    ccsds_bytes = None
    for vcdu in extract_vcdu_frames(bits):
        if vcdu is None:
            ccsds_bytes = None
            continue

        payload = vcdu.mpdu.payload
        if vcdu.mpdu.first_header_pointer != 0x7ff:
            if ccsds_bytes is not None:
                ccsds_bytes = ccsds_bytes + payload[:vcdu.mpdu.first_header_pointer]

                # We expect one complete packet in ccsds_bytes.
                # If shorter than required, drop it.
                # If longer, emit the first complete packet and ignore the rest.
                if len(ccsds_bytes) >= CCSDS_HEADER_LEN:
                    ccsds_header, rest = parse_ccsds_header(ccsds_bytes)
                    if len(rest) >= ccsds_header.packet_length:
                        yield parse_ccsds_packet(ccsds_header, rest[:ccsds_header.packet_length])
                ccsds_bytes = None
            payload = payload[vcdu.mpdu.first_header_pointer:]

        while len(payload) >= CCSDS_HEADER_LEN:
            ccsds_header, rest = parse_ccsds_header(payload)
            if len(rest) >= ccsds_header.packet_length:
                yield parse_ccsds_packet(ccsds_header, rest[:ccsds_header.packet_length])
                payload = rest[ccsds_header.packet_length:]
            else:
                if ccsds_bytes is None:
                    ccsds_bytes = payload
                else:
                    ccsds_bytes = ccsds_bytes + payload
                payload = b""

        if len(payload) > 0:
            ccsds_bytes = payload


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


def channel_to_gray_image(channel: Channel, image_width: int) -> Image.Image:
    height = len(channel.big_rows)
    img = Image.new("L", (image_width, height))
    flat = [pixel for row in channel.big_rows for pixel in row]
    img.putdata(flat)
    return img


def main():
    bits = [b & 1 for b in open("differential.bin","rb").read()]

    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)


    BLOCKS_PER_LINE = 14
    BLOCK_WIDTH = 8 * 14
    BLOCK_HEIGHT = 8
    IMAGE_WIDTH = BLOCKS_PER_LINE * BLOCK_WIDTH  # 1568


    apid_to_channel: dict[int, Channel] = {}

    for ccsds in extract_ccsds_packets(bits=bits):
        ccsds.header.packet_sequence_count

        apid = ccsds.header.apid
        payload = ccsds.payload
        if apid == 70:
            # telemetry 
            if len(payload) >= 16:
                print(parse_ccsds_time_full_raw_utc(payload))
        elif apid >= 60 and apid < 70:

            channel = apid_to_channel.get(apid)
            if channel is None:
                channel = Channel(apid=apid, big_rows=[], current_line=None)
                apid_to_channel[apid] = channel

            segment = parse_segment(payload)
            pixels = decode_14_blocks(segment.payload, segment.QF)

            packet_idx_in_line = segment.MCUN // 14
            x0 = packet_idx_in_line * BLOCK_WIDTH

            # Start-of-line marker arrived while we still have a line in progress.
            if packet_idx_in_line == 0 and channel.current_line is not None:
                # emit partial line
                channel.big_rows.extend(channel.current_line)
                channel.current_line = None

            if channel.current_line is None:
                channel.current_line = [[0] * IMAGE_WIDTH for _ in range(BLOCK_HEIGHT)]

            for row in range(BLOCK_HEIGHT):
                channel.current_line[row][x0:x0 + BLOCK_WIDTH] = pixels[row]

            if packet_idx_in_line == BLOCKS_PER_LINE - 1:
                channel.big_rows.extend(channel.current_line)
                channel.current_line = None


        out_path = out_dir / f"{apid}.bin"

        with out_path.open("ab") as f:
            f.write(payload)

    for channel in apid_to_channel.values():
        if len(channel.big_rows) > 0:
            img = channel_to_gray_image(channel, IMAGE_WIDTH)
            img.save(f"output/pic{channel.apid}.png")

    r_ch = apid_to_channel.get(65)
    g_ch = apid_to_channel.get(65)
    b_ch = apid_to_channel.get(64)

    if r_ch is not None and g_ch is not None and b_ch is not None:
        if len(r_ch.big_rows) > 0 and len(g_ch.big_rows) > 0 and len(b_ch.big_rows) > 0:
            r = channel_to_gray_image(r_ch, IMAGE_WIDTH)
            g = channel_to_gray_image(g_ch, IMAGE_WIDTH)
            b = channel_to_gray_image(b_ch, IMAGE_WIDTH)

            # Ensure same height (crop all to the smallest common height)
            h = min(r.height, g.height, b.height)
            if r.height != h: r = r.crop((0, 0, IMAGE_WIDTH, h))
            if g.height != h: g = g.crop((0, 0, IMAGE_WIDTH, h))
            if b.height != h: b = b.crop((0, 0, IMAGE_WIDTH, h))

            rgb = Image.merge("RGB", (r, g, b))
            rgb.save("output/composite_64_65_67_rgb.png")

if __name__ == '__main__':
    main()

