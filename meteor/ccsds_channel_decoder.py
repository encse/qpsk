# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: CCSDS Channel Decoder
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

from cadu_framer import CaduFramer
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import signal
from viterbi import Viterbi  # grc-generated hier_block
import satellites
import satellites.hier
import threading







class ccsds_channel_decoder(gr.hier_block2):
    def __init__(self):
        gr.hier_block2.__init__(
            self, "CCSDS Channel Decoder",
                gr.io_signature(1, 1, gr.sizeof_float*1),
                gr.io_signature(1, 1, gr.sizeof_float*1),
        )
        self.message_port_register_hier_out("cadus")

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 32000

        ##################################################
        # Blocks
        ##################################################

        self.viterbi_0 = Viterbi()
        self.satellites_decode_rs_ccsds_0 = satellites.decode_rs(False, 4)
        self.satellites_ccsds_descrambler_0 = satellites.hier.ccsds_descrambler()
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.cadu_framer_0 = CaduFramer(
            cadu_len_bytes=1020,
            cadu_asm=0x1ACFFC1D,
        )


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.cadu_framer_0, 'cadu'), (self.satellites_ccsds_descrambler_0, 'in'))
        self.msg_connect((self.satellites_ccsds_descrambler_0, 'out'), (self.satellites_decode_rs_ccsds_0, 'in'))
        self.msg_connect((self.satellites_decode_rs_ccsds_0, 'out'), (self, 'cadus'))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.cadu_framer_0, 0))
        self.connect((self, 0), (self.viterbi_0, 0))
        self.connect((self.viterbi_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.viterbi_0, 1), (self, 0))


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

