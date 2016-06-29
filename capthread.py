# -*- coding: utf-8 -*-

from PyQt4.QtCore import QThread, pyqtSignal

import pcapy, time

class CapThread(QThread):
    framesReceived = pyqtSignal(object)

    def __init__(self, dev, parent=None):
        super(CapThread, self).__init__(parent)
        self.dev = dev
        self.exiting = False

    def __del__(self):
        self.exiting = True
        self.wait()

    def run(self):
        pcap = pcapy.open_live(self.dev, 65536, False, 100)
        pcap.setnonblock(1)
        while not self.exiting:
            frames = [1]
            while frames[-1]:
                frames.append(pcap.next()[1])
            if len(frames) > 2:
                self.framesReceived.emit(frames[1:-1])
            time.sleep(0.05)