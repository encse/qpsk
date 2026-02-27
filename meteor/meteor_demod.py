#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Meteor M N 2-x ,72k LRPT demodulator
# Author: HA7NCS
# Copyright: Copyright (c) 2026 David Nemeth-Csoka
# Description: Meteor M-N2 LRPT (72k) QPSK demodulator.
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
import os
import sys
import logging as log

def get_state_directory() -> str:
    oldpath = os.path.expanduser("~/.grc_gnuradio")
    try:
        from gnuradio.gr import paths
        newpath = paths.persistent()
        if os.path.exists(newpath):
            return newpath
        if os.path.exists(oldpath):
            log.warning(f"Found persistent state path '{newpath}', but file does not exist. " +
                     f"Old default persistent state path '{oldpath}' exists; using that. " +
                     "Please consider moving state to new location.")
            return oldpath
        # Default to the correct path if both are configured.
        # neither old, nor new path exist: create new path, return that
        os.makedirs(newpath, exist_ok=True)
        return newpath
    except (ImportError, NameError):
        log.warning("Could not retrieve GNU Radio persistent state directory from GNU Radio. " +
                 "Trying defaults.")
        xdgstate = os.getenv("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
        xdgcand = os.path.join(xdgstate, "gnuradio")
        if os.path.exists(xdgcand):
            return xdgcand
        if os.path.exists(oldpath):
            log.warning(f"Using legacy state path '{oldpath}'. Please consider moving state " +
                     f"files to '{xdgcand}'.")
            return oldpath
        # neither old, nor new path exist: create new path, return that
        os.makedirs(xdgcand, exist_ok=True)
        return xdgcand

sys.path.append(os.environ.get('GRC_HIER_PATH', get_state_directory()))

from cadu_framer import CaduFramer
from ccsds_image_decoder import CcsdsImageDecoder
from ccsds_image_viewer import CcsdsImageViewer
from PyQt5 import Qt, sip
from gnuradio import analog
from gnuradio import blocks
import pmt
from gnuradio import digital
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from space_packet_assembler import SpacePacketAssembler
from vcdu_parser import VcduParser
from viterbi import Viterbi  # grc-generated hier_block
import math
import satellites
import satellites.hier
import sip
import threading



class meteor_demod(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Meteor M N 2-x ,72k LRPT demodulator", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Meteor M N 2-x ,72k LRPT demodulator")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "meteor_demod")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.sym_rate = sym_rate = 72000
        self.sps = sps = 2
        self.pipeline_sample_rate = pipeline_sample_rate = sym_rate * sps
        self.input_sample_rate = input_sample_rate = 256000
        self.apid_to_decode = apid_to_decode = 65

        ##################################################
        # Blocks
        ##################################################

        self.viterbi_0 = Viterbi(
            code="NASA-DSN uninverted",
        )
        self.vcdu_parser_0 = VcduParser()
        self.space_packet_assembler_0 = SpacePacketAssembler()
        self.satellites_decode_rs_ccsds_0 = satellites.decode_rs(False, 4)
        self.satellites_ccsds_descrambler_0 = satellites.hier.ccsds_descrambler()
        self.rational_resampler_xxx_0 = filter.rational_resampler_ccc(
                interpolation=pipeline_sample_rate,
                decimation=int(input_sample_rate),
                taps=[],
                fractional_bw=0)
        self.qtgui_number_sink_0 = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_NONE,
            1,
            None # parent
        )
        self.qtgui_number_sink_0.set_update_time(0.10)
        self.qtgui_number_sink_0.set_title('')

        labels = ['BER', '', '', '', '',
            '', '', '', '', '']
        units = ['', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.qtgui_number_sink_0.set_min(i, 0)
            self.qtgui_number_sink_0.set_max(i, 1)
            self.qtgui_number_sink_0.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.qtgui_number_sink_0.set_label(i, "Data {0}".format(i))
            else:
                self.qtgui_number_sink_0.set_label(i, labels[i])
            self.qtgui_number_sink_0.set_unit(i, units[i])
            self.qtgui_number_sink_0.set_factor(i, factor[i])

        self.qtgui_number_sink_0.enable_autoscale(False)
        self._qtgui_number_sink_0_win = sip.wrapinstance(self.qtgui_number_sink_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_number_sink_0_win, 2, 0, 1, 1)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_freq_sink_x_0 = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            pipeline_sample_rate, #bw
            "", #name
            1,
            None # parent
        )
        self.qtgui_freq_sink_x_0.set_update_time(0.10)
        self.qtgui_freq_sink_x_0.set_y_axis((-140), 10)
        self.qtgui_freq_sink_x_0.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_0.enable_autoscale(False)
        self.qtgui_freq_sink_x_0.enable_grid(False)
        self.qtgui_freq_sink_x_0.set_fft_average(1.0)
        self.qtgui_freq_sink_x_0.enable_axis_labels(True)
        self.qtgui_freq_sink_x_0.enable_control_panel(False)
        self.qtgui_freq_sink_x_0.set_fft_window_normalized(False)



        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_0_win = sip.wrapinstance(self.qtgui_freq_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_freq_sink_x_0_win, 3, 0, 1, 1)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_const_sink_x_0_0_0_0 = qtgui.const_sink_c(
            4000, #size
            'Constellation', #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_0_0_0_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0_0_0_0.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_0_0_0_0.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_0_0_0_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_0_0_0_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0_0_0_0.enable_grid(False)
        self.qtgui_const_sink_x_0_0_0_0.enable_axis_labels(False)

        self.qtgui_const_sink_x_0_0_0_0.disable_legend()

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["red", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_0_0_0_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_0_0_0_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_0_0_0_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_0_0_0_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_0_0_0_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_0_0_0_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_0_0_0_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_0_0_0_0_win = sip.wrapinstance(self.qtgui_const_sink_x_0_0_0_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_const_sink_x_0_0_0_0_win, 0, 0, 2, 1)
        for r in range(0, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.fir_filter_xxx_1 = filter.fir_filter_ccc(1, firdes.root_raised_cosine(1.0, pipeline_sample_rate, sym_rate, alpha=0.5, ntaps=31))
        self.fir_filter_xxx_1.declare_sample_delay(0)
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(0.002, 4, False)
        self.digital_clock_recovery_mm_xx_0 = digital.clock_recovery_mm_cc(sps, (0.25 * 0.0087 * 0.0087), 0.5, 0.0087, 0.005)
        self.ccsds_image_viewer_0 = self.ccsds_image_viewer_0 = CcsdsImageViewer(1568)
        self._ccsds_image_viewer_0_win = sip.wrapinstance(self.ccsds_image_viewer_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._ccsds_image_viewer_0_win, 0, 1, 4, 1)
        for r in range(0, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.ccsds_image_decoder_0 = CcsdsImageDecoder(apid_to_decode)
        self.cadu_framer_0 = CaduFramer(
            cadu_len_bytes=1020,
            cadu_asm=0x1ACFFC1D,
        )
        self.blocks_multiply_const_vxx_0_1 = blocks.multiply_const_cc(1)
        self.blocks_interleave_0 = blocks.interleave(gr.sizeof_float*1, 1)
        self.blocks_float_to_complex_0_0 = blocks.float_to_complex(1)
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, '/Users/encse/projects/qpsk/2026-02-13_07-39-09_256000SPS_137900000Hz.cf32', False, 0, 0)
        self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)
        self.blocks_delay_0_0 = blocks.delay(gr.sizeof_float*1, (sps // 2))
        self.blocks_complex_to_float_0_0 = blocks.complex_to_float(1)
        self.blocks_complex_to_float_0 = blocks.complex_to_float(1)
        self.analog_agc2_xx_0 = analog.agc2_cc((1e-1), (1e-2), 1.0, 1.0, 65536)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.cadu_framer_0, 'cadu'), (self.satellites_ccsds_descrambler_0, 'in'))
        self.msg_connect((self.ccsds_image_decoder_0, 'out'), (self.ccsds_image_viewer_0, 'in'))
        self.msg_connect((self.satellites_ccsds_descrambler_0, 'out'), (self.satellites_decode_rs_ccsds_0, 'in'))
        self.msg_connect((self.satellites_decode_rs_ccsds_0, 'out'), (self.vcdu_parser_0, 'in'))
        self.msg_connect((self.space_packet_assembler_0, 'out'), (self.ccsds_image_decoder_0, 'in'))
        self.msg_connect((self.vcdu_parser_0, 'out'), (self.space_packet_assembler_0, 'in'))
        self.connect((self.analog_agc2_xx_0, 0), (self.fir_filter_xxx_1, 0))
        self.connect((self.blocks_complex_to_float_0, 0), (self.blocks_interleave_0, 0))
        self.connect((self.blocks_complex_to_float_0, 1), (self.blocks_interleave_0, 1))
        self.connect((self.blocks_complex_to_float_0_0, 1), (self.blocks_delay_0_0, 0))
        self.connect((self.blocks_complex_to_float_0_0, 0), (self.blocks_float_to_complex_0_0, 0))
        self.connect((self.blocks_delay_0_0, 0), (self.blocks_float_to_complex_0_0, 1))
        self.connect((self.blocks_file_source_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.blocks_float_to_complex_0_0, 0), (self.digital_clock_recovery_mm_xx_0, 0))
        self.connect((self.blocks_interleave_0, 0), (self.viterbi_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0_1, 0), (self.blocks_complex_to_float_0, 0))
        self.connect((self.digital_clock_recovery_mm_xx_0, 0), (self.blocks_multiply_const_vxx_0_1, 0))
        self.connect((self.digital_clock_recovery_mm_xx_0, 0), (self.qtgui_const_sink_x_0_0_0_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.blocks_complex_to_float_0_0, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.cadu_framer_0, 0))
        self.connect((self.fir_filter_xxx_1, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.analog_agc2_xx_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.qtgui_freq_sink_x_0, 0))
        self.connect((self.viterbi_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.viterbi_0, 1), (self.qtgui_number_sink_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "meteor_demod")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sym_rate(self):
        return self.sym_rate

    def set_sym_rate(self, sym_rate):
        self.sym_rate = sym_rate
        self.set_pipeline_sample_rate(self.sym_rate * self.sps)
        self.fir_filter_xxx_1.set_taps(firdes.root_raised_cosine(1.0, self.pipeline_sample_rate, self.sym_rate, alpha=0.5, ntaps=31))

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_pipeline_sample_rate(self.sym_rate * self.sps)
        self.blocks_delay_0_0.set_dly(int((self.sps // 2)))
        self.digital_clock_recovery_mm_xx_0.set_omega(self.sps)

    def get_pipeline_sample_rate(self):
        return self.pipeline_sample_rate

    def set_pipeline_sample_rate(self, pipeline_sample_rate):
        self.pipeline_sample_rate = pipeline_sample_rate
        self.fir_filter_xxx_1.set_taps(firdes.root_raised_cosine(1.0, self.pipeline_sample_rate, self.sym_rate, alpha=0.5, ntaps=31))
        self.qtgui_freq_sink_x_0.set_frequency_range(0, self.pipeline_sample_rate)

    def get_input_sample_rate(self):
        return self.input_sample_rate

    def set_input_sample_rate(self, input_sample_rate):
        self.input_sample_rate = input_sample_rate

    def get_apid_to_decode(self):
        return self.apid_to_decode

    def set_apid_to_decode(self, apid_to_decode):
        self.apid_to_decode = apid_to_decode




def main(top_block_cls=meteor_demod, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
