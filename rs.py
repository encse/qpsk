import ctypes as C
from ctypes import c_size_t, c_uint8, c_uint16, c_int, c_ssize_t, c_void_p, POINTER


class CorrectRS255:
    """
    Wrapper for libcorrect Reed-Solomon over GF(256), block (255, 255-nsym).
    Decode expects full 255-byte codeword and returns 223-byte payload for nsym=32.
    """

    def __init__(self, nsym: int, prim: int, fcr: int, generator_gap: int):
        self._lib = C.CDLL("./libcorrect.dylib")

        self._lib.correct_reed_solomon_create.argtypes = [c_uint16, c_uint8, c_uint8, c_size_t]
        self._lib.correct_reed_solomon_create.restype = c_void_p

        self._lib.correct_reed_solomon_destroy.argtypes = [c_void_p]
        self._lib.correct_reed_solomon_destroy.restype = None

        self._lib.correct_reed_solomon_decode.argtypes = [
            c_void_p,
            POINTER(c_uint8), c_size_t,
            POINTER(c_uint8),
        ]
        self._lib.correct_reed_solomon_decode.restype = c_ssize_t

        self._nsym = int(nsym)
        self._n = 255
        self._k = self._n - self._nsym

        rs_ptr = self._lib.correct_reed_solomon_create(
            c_uint16(prim),
            c_uint8(fcr),
            c_uint8(generator_gap),
            c_size_t(self._nsym),
        )
        if rs_ptr is None or rs_ptr == 0:
            raise RuntimeError("correct_reed_solomon_create failed")

        self._rs = rs_ptr

    def close(self) -> None:
        if self._rs is not None and self._rs != 0:
            self._lib.correct_reed_solomon_destroy(self._rs)
            self._rs = None

    def __enter__(self) -> "CorrectRS255":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def k(self) -> int:
        return self._k

    @property
    def n(self) -> int:
        return self._n

    @property
    def nsym(self) -> int:
        return self._nsym

    def decode(self, codeword255: bytes) -> bytes:
        if len(codeword255) != self._n:
            raise ValueError(f"expected {self._n} bytes, got {len(codeword255)}")

        in_buf = (c_uint8 * self._n).from_buffer_copy(codeword255)
        out_buf = (c_uint8 * self._k)()

        n_dec = self._lib.correct_reed_solomon_decode(self._rs, in_buf, c_size_t(self._n), out_buf)
        if n_dec < 0:
            raise RuntimeError("rs decode failed")
        # Usually returns k, but we don't rely on it.
        return bytes(out_buf[: self._k])
    

# # --- Types ---
# correct_convolutional = c_void_p
# correct_reed_solomon = c_void_p
# correct_conv_poly_t = c_uint16
# correct_soft_t = c_uint8

# # -----------------------------
# # Convolutional: signatures
# # -----------------------------
# lib.correct_convolutional_create.argtypes = [c_size_t, c_size_t, POINTER(correct_conv_poly_t)]
# lib.correct_convolutional_create.restype  = correct_convolutional

# lib.correct_convolutional_destroy.argtypes = [correct_convolutional]
# lib.correct_convolutional_destroy.restype  = None

# lib.correct_convolutional_encode_len.argtypes = [correct_convolutional, c_size_t]
# lib.correct_convolutional_encode_len.restype  = c_size_t  # returns bits

# lib.correct_convolutional_encode.argtypes = [
#     correct_convolutional,
#     POINTER(c_uint8), c_size_t,
#     POINTER(c_uint8),
# ]
# lib.correct_convolutional_encode.restype = c_size_t  # bits written

# lib.correct_convolutional_decode.argtypes = [
#     correct_convolutional,
#     POINTER(c_uint8), c_size_t,
#     POINTER(c_uint8),
# ]
# lib.correct_convolutional_decode.restype = c_ssize_t  # bytes written or -1

# lib.correct_convolutional_decode_soft.argtypes = [
#     correct_convolutional,
#     POINTER(correct_soft_t), c_size_t,
#     POINTER(c_uint8),
# ]
# lib.correct_convolutional_decode_soft.restype = c_ssize_t

# # -----------------------------
# # Reed-Solomon: signatures
# # -----------------------------
# lib.correct_reed_solomon_create.argtypes = [c_uint16, c_uint8, c_uint8, c_size_t]
# lib.correct_reed_solomon_create.restype  = correct_reed_solomon

# lib.correct_reed_solomon_destroy.argtypes = [correct_reed_solomon]
# lib.correct_reed_solomon_destroy.restype  = None

# lib.correct_reed_solomon_encode.argtypes = [
#     correct_reed_solomon,
#     POINTER(c_uint8), c_size_t,
#     POINTER(c_uint8),
# ]
# lib.correct_reed_solomon_encode.restype = c_ssize_t

# lib.correct_reed_solomon_decode.argtypes = [
#     correct_reed_solomon,
#     POINTER(c_uint8), c_size_t,
#     POINTER(c_uint8),
# ]
# lib.correct_reed_solomon_decode.restype = c_ssize_t

# lib.correct_reed_solomon_decode_with_erasures.argtypes = [
#     correct_reed_solomon,
#     POINTER(c_uint8), c_size_t,
#     POINTER(c_uint8), c_size_t,
#     POINTER(c_uint8),
# ]
# lib.correct_reed_solomon_decode_with_erasures.restype = c_ssize_t


# def _bits_to_bytes(nbits: int) -> int:
#     return (nbits + 7) // 8


# # -----------------------------
# # Example: Convolutional encode/decode
# # Rate 1/2, order 7, polynomials: 0161, 0127 (octal!)
# # -----------------------------
# def conv_example():
#     inv_rate = 2
#     order = 7

#     # IMPORTANT: these literals in the header are octal.
#     # Python: 0o161, 0o127
#     polys = (correct_conv_poly_t * inv_rate)(0o161, 0o127)

#     conv = lib.correct_convolutional_create(inv_rate, order, polys)
#     if not conv:
#         raise RuntimeError("correct_convolutional_create failed")

#     try:
#         msg = b"hello"
#         msg_arr = (c_uint8 * len(msg)).from_buffer_copy(msg)

#         encoded_bits = lib.correct_convolutional_encode_len(conv, len(msg))
#         encoded_len_bytes = _bits_to_bytes(encoded_bits)
#         encoded_buf = (c_uint8 * encoded_len_bytes)()

#         written_bits = lib.correct_convolutional_encode(conv, msg_arr, len(msg), encoded_buf)
#         written_bytes = _bits_to_bytes(written_bits)
#         encoded = bytes(encoded_buf[:written_bytes])

#         # decode needs output buffer; conservative: rate * bits -> bytes
#         out_max = _bits_to_bytes(written_bits // inv_rate)
#         out_buf = (c_uint8 * out_max)()

#         decoded_n = lib.correct_convolutional_decode(conv, encoded_buf, written_bits, out_buf)
#         if decoded_n < 0:
#             raise RuntimeError("decode failed")

#         decoded = bytes(out_buf[:decoded_n])
#         return encoded, decoded

#     finally:
#         lib.correct_convolutional_destroy(conv)


# # -----------------------------
# # Example: RS (255,223) CCSDS primitive poly 0x187, num_roots=32
# # parity = 32 bytes, payload up to 223
# # -----------------------------
# def rs_example():
#     primitive_poly = 0x187  # CCSDS
#     first_root = 112
#     root_gap = 11
#     num_roots = 32

#     rs = lib.correct_reed_solomon_create(primitive_poly, first_root, root_gap, num_roots)
#     if not rs:
#         raise RuntimeError("correct_reed_solomon_create failed")

#     try:
#         msg = b"payload"

#         K = 223
#         N = 255
#         PARITY = num_roots  # 32

#         # pad to 223 bytes
#         payload = msg + b"\x00" * (K - len(msg))
#         payload_arr = (c_uint8 * K).from_buffer_copy(payload)

#         encoded_buf = (c_uint8 * N)()
#         n_enc = lib.correct_reed_solomon_encode(rs, payload_arr, K, encoded_buf)
#         if n_enc < 0:
#             raise RuntimeError("rs encode failed")
#         if n_enc != N:
#             raise RuntimeError(f"unexpected encoded length: {n_enc} (expected {N})")

#         out_buf = (c_uint8 * K)()
#         n_dec = lib.correct_reed_solomon_decode(rs, encoded_buf, N, out_buf)
#         if n_dec < 0:
#             raise RuntimeError("rs decode failed")
#         if n_dec != K:
#             # néha visszaadhat K-től eltérőt, de a legtöbb CCSDS (255,223)-nál K lesz
#             pass

#         decoded_payload = bytes(out_buf[:K])
#         decoded_msg = decoded_payload[:len(msg)]
#         return bytes(encoded_buf[:N]), decoded_msg

#     finally:
#         lib.correct_reed_solomon_destroy(rs)


# if __name__ == "__main__":
#     enc, dec = conv_example()
#     print("conv decoded:", dec)

#     enc2, dec2 = rs_example()
#     print("rs decoded:", dec2)