from gnuradio import gr
import pmt
from PyQt5 import QtCore, QtWidgets, QtGui, sip
import numpy as np


class CcsdsImageViewer(gr.sync_block):
    def __init__(self, width=1568):
        gr.sync_block.__init__(
            self,
            name="ccsds_image_viewer",
            in_sig=None,
            out_sig=None
        )

        print("BLOCK INIT CALLED")

        self.width = int(width)
        self._byte_buffer = bytearray()
        self.image_rows = []
        self._last_arr = None

        self.widget = QtWidgets.QWidget()
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setMinimumSize(400, 300)

        placeholder = QtGui.QPixmap(400, 300)
        placeholder.fill(QtGui.QColor(80, 80, 80))
        self.label.setPixmap(placeholder)

        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.addWidget(self.label)

        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self.handle_msg)

    def qwidget(self):
        return sip.unwrapinstance(self.widget)

    def handle_msg(self, msg):
        data = pmt.cdr(msg)
        payload = bytes(pmt.u8vector_elements(data))

        # append incoming bytes to rolling buffer
        self._byte_buffer.extend(payload)

        # while we have enough bytes for a full row
        while len(self._byte_buffer) >= self.width:
            row = self._byte_buffer[:self.width]
            del self._byte_buffer[:self.width]

            self.image_rows.append(list(row))

        if len(self.image_rows) > 0:
            self.update_image()

    def update_image(self):
        
        if not self.image_rows:
            return

        height = len(self.image_rows)
        arr = np.asarray(self.image_rows, dtype=np.uint8)
        self._last_arr = arr

        qimg = QtGui.QImage(
            self._last_arr.data,
            self.width,
            height,
            self.width,
            QtGui.QImage.Format_Grayscale8
        )

        self._last_pixmap = QtGui.QPixmap.fromImage(qimg)
        self._apply_scale()

    def _apply_scale(self):
        if self._last_pixmap is None:
            return

        target = self.label.size()
        if target.width() <= 1 or target.height() <= 1:
            return

        scaled = self._last_pixmap.scaled(
            target,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.label.setPixmap(scaled)