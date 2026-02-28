# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: CCSDS Space Packet Extractor
# GNU Radio version: 3.10.12.0

from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from space_packet_assembler import SpacePacketAssembler
from vcdu_parser import VcduParser
import threading







class ccsds_space_packet_extractor(gr.hier_block2):
    def __init__(self):
        gr.hier_block2.__init__(
            self, "CCSDS Space Packet Extractor",
                gr.io_signature(0, 0, 0),
                gr.io_signature(0, 0, 0),
        )
        self.message_port_register_hier_in("cadus")
        self.message_port_register_hier_out("space_packets")

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 32000

        ##################################################
        # Blocks
        ##################################################

        self.vcdu_parser_0 = VcduParser()
        self.space_packet_assembler_0 = SpacePacketAssembler()


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self, 'cadus'), (self.vcdu_parser_0, 'in'))
        self.msg_connect((self.space_packet_assembler_0, 'out'), (self, 'space_packets'))
        self.msg_connect((self.vcdu_parser_0, 'out'), (self.space_packet_assembler_0, 'in'))


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

