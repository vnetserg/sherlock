# -*- coding: utf-8 -*-

from PyQt4 import QtCore

import time

import dpkt
import pandas as ps

from util import ip_address, forge_flow

class TrafficModel(QtCore.QAbstractTableModel):
    def __init__(self, models, parent = None):
        super(TrafficModel, self).__init__(parent)
        self.models = models
        self.flows = []
        self.flows_index = {}
        self.idlers = []
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.timerTick)
        self.timer.start(1000)

    def timerTick(self):
        self.dataChanged.emit(self.index(0, 3), self.index(self.rowCount()-1, 3))
        new_idlers = []
        now = time.time()
        for flow in self.idlers:
            if flow["type"] == u"Не определён" or flow["type"] == u"Неизвестен":
                if len(flow["dump"]) > 1 and now - flow["ts_started"] > 1:
                    flow["type"] = self.flowType(flow, self.models[0])
                else:
                    new_idlers.append(flow)
        self.idlers = new_idlers

    def addFlows(self, flows):
        for key, frames in flows.iteritems():
            if key not in self.flows_index:
                eth = frames[0]
                ip = eth.data
                seg = ip.data
                proto = key[1]
                flow = {
                    "client_ip": ip.src,
                    "client_port": seg.sport,
                    "server_ip": ip.dst,
                    "server_port": seg.dport,
                    "proto": proto,
                    "ts_started": time.time(),
                    "dump": [],
                    "packets": 0,
                    "payload": 0,
                    "type": u"Не определён",
                    "last_payload": "client",
                    "index": len(flows)
                }
                if isinstance(seg, dpkt.tcp.TCP) and not (seg.flags & dpkt.tcp.TH_SYN):
                    continue
                self.beginInsertRows(QtCore.QModelIndex(), 0, 0)
                self.flows.append(flow)
                self.flows_index[key] = flow
                self.idlers.append(flow)
                self.endInsertRows()

            flow = self.flows_index[key]
            flow["packets"] += len(frames)
            flow["dump"] += frames
            for eth in frames:
                ip = eth.data
                seg = ip.data
                flow["payload"] += len(seg.data)
            self.checkThreshold(flow, flow["packets"] - len(frames))

            self.dataChanged.emit(self.index(self.rowCount()-flow["index"]-1, 0),
                self.index(flow["index"], self.columnCount()-1))

    def getFlow(self, index):
        return self.flows[self.rowCount()-index.row()-1]

    def checkThreshold(self, flow, old_len):
        new_len = flow["packets"]
        for mdl in self.models:
            if old_len < mdl["num"] <= new_len:
                flow["type"] = self.flowType(flow, mdl)
                break

    def flowType(self, flow, model):
        stats = forge_flow(flow["dump"], model["num"])
        if not stats: return u"Неизвестен"
        data = ps.DataFrame({key: [val] for key, val in stats.iteritems()})
        X = model["scaler"].transform(data)
        y = model["model"].predict(X)
        labels = model["labeler"].inverse_transform(y)
        return labels[0]

    def get_size_string(self, bts):
        if bts < 1024:
            return u"{} байт".format(bts)
        if bts < 2**20:
            return u"{:.02f} Кбайт".format(bts/1024.0)
        else:
            return u"{:.02f} Мбайт".format(float(bts)/2**20)
    
    def columnCount(self, index = None):
       return 7
    
    def rowCount(self, index = QtCore.QModelIndex()):
       return len(self.flows)
    
    def data(self, index, role = QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            row, col = index.row(), index.column()
            flow = self.flows[-row-1]
            return [
                "{}:{}".format(ip_address(flow["client_ip"]), flow["client_port"]),
                "{}:{}".format(ip_address(flow["server_ip"]), flow["server_port"]),
                flow["proto"].upper(), u"{} сек".format(int(time.time() - flow["ts_started"])),
                flow["packets"], self.get_size_string(flow["payload"]),
                flow["type"]
            ][col]
    
    def headerData(self, col, orientation, role = QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return [u"Клиент", u"Сервер", u"Протокол", u"Длительность", u"Пакетов", u"Данных", u"Тип трафика"][col]
    
    def flags(self, index):
        if index.isValid():
            flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            return flags