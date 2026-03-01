import numpy as np
import math
import pmt
from gnuradio import gr


class TagToFloat(gr.basic_block):
    """
    Consume a stream (any samples) and emit one float per matching stream tag.

    - Input:  complex64 stream (only used as a carrier for tags)
    - Output: float32 stream (1 item per matched tag)
    - Behavior: reads tags with key=tag_key, converts tag value to float, emits it.
      No passthrough of input samples.
    """

    def __init__(self, tag_key="snr"):
        gr.basic_block.__init__(
            self,
            name="tag_value_to_float",
            in_sig=[np.complex64],
            out_sig=[np.float32],
        )

        self._key = pmt.intern(str(tag_key))
        self._pending = []  # pending float values to output

    def general_work(self, input_items, output_items):
        x = input_items[0]
        out = output_items[0]

        n_in = len(x)
        n_out_max = len(out)

        if n_in == 0 and len(self._pending) == 0:
            return 0

        produced = 0

        # 1) Flush pending first
        while produced < n_out_max and len(self._pending) > 0:
            out[produced] = self._pending.pop(0)
            produced += 1

        # 2) Scan tags in the current input window, enqueue values
        if n_in > 0:
            start = self.nitems_read(0)
            end = start + n_in

            tags = self.get_tags_in_range(0, start, end, self._key)

            for t in tags:
                try:
                    v = float(pmt.to_double(t.value))
                except Exception:
                    continue
                if math.isfinite(v):
                    self._pending.append(v)

            # Consume all input samples (we do not forward them)
            self.consume(0, n_in)

        # 3) Output more after enqueue
        while produced < n_out_max and len(self._pending) > 0:
            out[produced] = self._pending.pop(0)
            produced += 1

        return produced