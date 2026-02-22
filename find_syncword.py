print("Start")

bits = [b & 1 for b in open("differential.bin","rb").read()]
def invert(h):
    return [1 - b for b in h]

def dibit_swap(h):
    out = h[:]  # copy
    for i in range(0, len(out) - 1, 2):
        out[i], out[i + 1] = out[i + 1], out[i]
    return out

def reverse8(x):
    return int(f"{x:08b}"[::-1], 2)

# FC4EF4FD0CC2DF89 the syncword after viterbi
# pat_msb = bytes.fromhex("FC4EF4FD")

pat_msb = bytes.fromhex("1ACFFC1D")
pat_lsb = bytes([reverse8(b) for b in pat_msb])

def to_bits_msb_first(pat_bytes):
    return [(b >> (7 - i)) & 1 for b in pat_bytes for i in range(8)]

pbits8_msb = to_bits_msb_first(pat_msb)
pbits8_lsb = to_bits_msb_first(pat_lsb)
pbits6_msb = pbits8_msb[:24]
pbits6_lsb = pbits8_lsb[:24]

def find_all(h, p):
    m = len(p)
    for i in range(len(h) - m + 1):
        if h[i:i+m] == p:
            yield i

def check_stream(stream, label, p6, p8, pat_label):
    candidates = list(find_all(stream, p6))
    print(f"{label} {pat_label} 6-bit candidates:", len(candidates))

    full_hits = 0
    for pos in candidates:
        if stream[pos:pos+len(p8)] == p8:
            print(f"{label} {pat_label} FULL match at bit", pos)
            full_hits += 1
    if full_hits == 0:
        print(f"{label} {pat_label} FULL matches: none")

streams = [
    ("Normal", bits),
    ("Invert", invert(bits)),
    ("DibitSwap", dibit_swap(bits)),
    ("DibitSwapInvert", invert(dibit_swap(bits))),
]

for name, s in streams:
    check_stream(s, name, pbits6_msb, pbits8_msb, "MSB")
    check_stream(s, name, pbits6_lsb, pbits8_lsb, "LSB-per-byte")

print("stop")