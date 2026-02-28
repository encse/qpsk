# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Meteor LRPT
# GNU Radio version: 3.10.12.0

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

from apid_filter import ApidFilter
from ccsds_channel_decoder import ccsds_channel_decoder  # grc-generated hier_block
from ccsds_space_packet_extractor import ccsds_space_packet_extractor  # grc-generated hier_block
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import signal
from oqpsk_demodulator import oqpsk_demodulator  # grc-generated hier_block
import threading







class meteor_lrpt(gr.hier_block2):
    def __init__(self, sample_rate=0):
        gr.hier_block2.__init__(
            self, "Meteor LRPT",
                gr.io_signature(1, 1, gr.sizeof_gr_complex*1),
                gr.io_signature.makev(2, 2, [gr.sizeof_gr_complex*1, gr.sizeof_float*1]),
        )
        self.message_port_register_hier_out("msu_mr_1")
        self.message_port_register_hier_out("msu_mr_2")
        self.message_port_register_hier_out("msu_mr_3")
        self.message_port_register_hier_out("msu_mr_4")
        self.message_port_register_hier_out("msu_mr_5")
        self.message_port_register_hier_out("msu_mr_6")
        self.message_port_register_hier_out("telemetry")

        ##################################################
        # Parameters
        ##################################################
        self.sample_rate = sample_rate

        ##################################################
        # Blocks
        ##################################################

        self.oqpsk_demodulator_0 = oqpsk_demodulator(
            sample_rate=sample_rate,
        )
        self.ccsds_space_packet_extractor_0 = ccsds_space_packet_extractor()
        self.ccsds_channel_decoder_0 = ccsds_channel_decoder()
        self.ccsds_apid_filter_0_0_0_0_0_0_0 = ApidFilter(apid=70)
        self.ccsds_apid_filter_0_0_0_0_0_0 = ApidFilter(apid=69)
        self.ccsds_apid_filter_0_0_0_0_0 = ApidFilter(apid=68)
        self.ccsds_apid_filter_0_0_0_0 = ApidFilter(apid=67)
        self.ccsds_apid_filter_0_0_0 = ApidFilter(apid=66)
        self.ccsds_apid_filter_0_0 = ApidFilter(apid=65)
        self.ccsds_apid_filter_0 = ApidFilter(apid=64)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.ccsds_apid_filter_0, 'out'), (self, 'msu_mr_1'))
        self.msg_connect((self.ccsds_apid_filter_0_0, 'out'), (self, 'msu_mr_2'))
        self.msg_connect((self.ccsds_apid_filter_0_0_0, 'out'), (self, 'msu_mr_3'))
        self.msg_connect((self.ccsds_apid_filter_0_0_0_0, 'out'), (self, 'msu_mr_4'))
        self.msg_connect((self.ccsds_apid_filter_0_0_0_0_0, 'out'), (self, 'msu_mr_5'))
        self.msg_connect((self.ccsds_apid_filter_0_0_0_0_0_0, 'out'), (self, 'msu_mr_6'))
        self.msg_connect((self.ccsds_apid_filter_0_0_0_0_0_0_0, 'out'), (self, 'telemetry'))
        self.msg_connect((self.ccsds_channel_decoder_0, 'cadus'), (self.ccsds_space_packet_extractor_0, 'cadus'))
        self.msg_connect((self.ccsds_space_packet_extractor_0, 'space_packets'), (self.ccsds_apid_filter_0, 'in'))
        self.msg_connect((self.ccsds_space_packet_extractor_0, 'space_packets'), (self.ccsds_apid_filter_0_0, 'in'))
        self.msg_connect((self.ccsds_space_packet_extractor_0, 'space_packets'), (self.ccsds_apid_filter_0_0_0, 'in'))
        self.msg_connect((self.ccsds_space_packet_extractor_0, 'space_packets'), (self.ccsds_apid_filter_0_0_0_0, 'in'))
        self.msg_connect((self.ccsds_space_packet_extractor_0, 'space_packets'), (self.ccsds_apid_filter_0_0_0_0_0, 'in'))
        self.msg_connect((self.ccsds_space_packet_extractor_0, 'space_packets'), (self.ccsds_apid_filter_0_0_0_0_0_0, 'in'))
        self.msg_connect((self.ccsds_space_packet_extractor_0, 'space_packets'), (self.ccsds_apid_filter_0_0_0_0_0_0_0, 'in'))
        self.connect((self.ccsds_channel_decoder_0, 0), (self, 1))
        self.connect((self.oqpsk_demodulator_0, 1), (self.ccsds_channel_decoder_0, 0))
        self.connect((self.oqpsk_demodulator_0, 0), (self, 0))
        self.connect((self, 0), (self.oqpsk_demodulator_0, 0))


    def get_sample_rate(self):
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
        self.oqpsk_demodulator_0.set_sample_rate(self.sample_rate)

