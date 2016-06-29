# -*- coding: utf-8 -*-

import pickle, os, subprocess

import sklearn, dpkt, pcapy

from PyQt4 import QtGui
from ui.ui_mainwindow import Ui_MainWindow

from models.trafficmodel import TrafficModel

from capthread import CapThread

S10_FILE = "model_s10.mdl"
S100_FILE = "model_s100.mdl"
S1000_FILE = "model_s1000.mdl"

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.prediction_models = []
        for num, file in zip((10, 100, 1000), (S10_FILE, S100_FILE, S1000_FILE)):
            model, scaler, labeler = pickle.load(open(file, "rb"))
            self.prediction_models.append({"num": num, "model": model, "scaler": scaler, "labeler": labeler})

        self.ui.action_start.triggered.connect(self.startCapture)
        self.ui.action_stop.triggered.connect(self.stopCapture)
        self.ui.tableView.doubleClicked.connect(self.viewDoubleClicked)
        self.thread = None

        self.model = TrafficModel(self.prediction_models, self)
        self.ui.tableView.setModel(self.model)
        self.ui.tableView.resizeColumnsToContents()

        ## Иконки:
        self.setWindowIcon(QtGui.QIcon("res/sherlock.png"))
        self.ui.action_start.setIcon(QtGui.QIcon("res/start.png"))
        self.ui.action_stop.setIcon(QtGui.QIcon("res/pause.png"))

    def startCapture(self):
        all_devs = sorted(pcapy.findalldevs())
        dev, ok = QtGui.QInputDialog.getItem(self, u"Выбор устройства", u"Выберите устройство:", all_devs, 0, False)
        if not ok: return

        self.model = TrafficModel(self.prediction_models, self)
        self.ui.tableView.setModel(self.model)
        self.ui.tableView.resizeColumnsToContents()

        self.ui.action_start.setEnabled(False)
        self.ui.action_stop.setEnabled(True)
        self.thread = CapThread(str(dev))
        self.thread.framesReceived.connect(self.addFrames)
        self.thread.start()

    def stopCapture(self):
        self.ui.action_start.setEnabled(True)
        self.ui.action_stop.setEnabled(False)
        self.thread.terminate()
        self.thread = None

    def addFrames(self, raws):
        flows = {}
        for raw in raws:
            eth = dpkt.ethernet.Ethernet(raw)
            if eth.type != dpkt.ethernet.ETH_TYPE_IP:
                continue
            ip = eth.data
            if ip.p == dpkt.ip.IP_PROTO_TCP:
                proto = "TCP"
            elif ip.p == dpkt.ip.IP_PROTO_UDP:
                proto = "UDP"
            else:
                continue
            seg = ip.data
            flow_key = (frozenset([(ip.src, seg.sport), (ip.dst, seg.dport)]), proto)
            if flow_key not in flows:
                flows[flow_key] = []
            flows[flow_key].append(eth)
        self.model.addFlows(flows)
        self.ui.tableView.resizeColumnsToContents()

    def viewDoubleClicked(self, index):
        flow = self.model.getFlow(index)
        outfile = dpkt.pcap.Writer(open("/tmp/dump.pcap", "wb"))
        for i, eth in enumerate(flow["dump"]):
            outfile.writepkt(eth, i)
        outfile.close()
        subprocess.call("echo 'wireshark /tmp/dump.pcap' | runuser sergio &", shell=True)