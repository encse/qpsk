from PyQt5 import QtCore, QtWidgets, QtGui, sip
from gnuradio import gr
import pmt

class _GuiBridge(QtCore.QObject):
    request_update = QtCore.pyqtSignal()

    def __init__(self, owner_block, parent=None):
        super().__init__(parent)
        self._owner = owner_block
        self.request_update.connect(self._on_request_update, QtCore.Qt.QueuedConnection)

    @QtCore.pyqtSlot()
    def _on_request_update(self):
        self._owner._update_image_queued_impl()

class CcsdsImageViewer(gr.sync_block):
    def __init__(self, width=1568):
        gr.sync_block.__init__(self, name="ccsds_image_viewer", in_sig=None, out_sig=None)

        self.width = int(width)

        self._byte_buffer = bytearray()   # accumulates partial rows
        self._image_buf = bytearray()     # full rows only (the image)
        self._last_pixmap = None
        self._update_pending = False
        self._lock = QtCore.QMutex()

        self.widget = QtWidgets.QWidget()
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setMinimumSize(400, 300)

        placeholder = QtGui.QPixmap(400, 300)
        placeholder.fill(QtGui.QColor(80, 80, 80))
        self.label.setPixmap(placeholder)

        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.addWidget(self.label)

        self._bridge = _GuiBridge(self, parent=self.widget)

        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self.handle_msg)

    def qwidget(self):
        return sip.unwrapinstance(self.widget)

    def handle_msg(self, msg):
        data = pmt.cdr(msg)
        payload = bytes(pmt.u8vector_elements(data))

        locker = QtCore.QMutexLocker(self._lock)
        try:
            self._byte_buffer.extend(payload)

            # move only complete rows into the image buffer
            full = (len(self._byte_buffer) // self.width) * self.width
            if full > 0:
                self._image_buf.extend(self._byte_buffer[:full])
                del self._byte_buffer[:full]

                if self._update_pending is False:
                    self._update_pending = True
                    self._bridge.request_update.emit()
        finally:
            del locker

    def _update_image_queued_impl(self):
        # runs on Qt thread
        locker = QtCore.QMutexLocker(self._lock)
        try:
            self._update_pending = False

            n = len(self._image_buf)
            if n < self.width:
                return

            height = n // self.width

            # WARNING QImage(data, ...) wraps external memory (zero-copy) and 
            # does NOT take ownership. Here `bytes(self._image_buf)` is Python-owned 
            # (and would otherwise be a temporary), so we immediately call `.copy()`
            # to deep-copy pixels into Qt-owned memory. 
            pixmap = QtGui.QPixmap.fromImage(
                QtGui.QImage(
                    bytes(self._image_buf), # <- Python owned memory
                    self.width,
                    height,
                    self.width,
                    QtGui.QImage.Format_Grayscale8
                ).copy() # <- to Qt-owned memory
            )
        finally:
            del locker
        
        target = self.label.size()
        if target.width() <= 1 or target.height() <= 1:
            return

        scaled = pixmap.scaled(
            target,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.label.setPixmap(scaled)