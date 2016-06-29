# -*- coding: utf-8 -*-

from __future__ import division

import dpkt
import numpy as np

def ip_address(bytes):
    return ".".join([str(ord(b)) for b in bytes])

def forge_flow(frames, strip = None):
    ip = frames[0].data
    seg = ip.data
    if isinstance(seg, dpkt.tcp.TCP):
        proto = "tcp"
        frames = frames[3:] # срезаем tcp handshake
    elif isinstance(seg, dpkt.udp.UDP):
        proto = "udp"
    else:
        raise ValueErrur("Unknown transport protocol: `{}`".format(
            seg.__class__.__name__))

    if strip:
        frames = frames[:strip]

    client = (ip.src, seg.sport)
    server = (ip.dst, seg.dport)

    client_bulks = []
    server_bulks = []
    client_packets = []
    server_packets = []

    cur_bulk_size = 0
    cur_bulk_owner = "client"
    client_fin = False
    server_fin = False
    for eth in frames:
        ip = eth.data
        seg = ip.data
        if (ip.src, seg.sport) == client:
            if client_fin: continue
            if proto == "tcp":
                client_fin = bool(seg.flags & dpkt.tcp.TH_FIN)
            client_packets.append(len(seg))
            if cur_bulk_owner == "client":
                cur_bulk_size += len(seg.data)
            elif len(seg.data) > 0:
                server_bulks.append(cur_bulk_size)
                cur_bulk_owner = "client"
                cur_bulk_size = len(seg.data)
        elif (ip.src, seg.sport) == server:
            if server_fin: continue
            if proto == "tcp":
                server_fin = bool(seg.flags & dpkt.tcp.TH_FIN)
            server_packets.append(len(seg))
            if cur_bulk_owner == "server":
                cur_bulk_size += len(seg.data)
            elif len(seg.data) > 0:
                client_bulks.append(cur_bulk_size)
                cur_bulk_owner = "server"
                cur_bulk_size = len(seg.data)
        else:
            raise ValueError("There is more than one flow!")

    if cur_bulk_owner == "client":
        client_bulks.append(cur_bulk_size)
    else:
        server_bulks.append(cur_bulk_size)

    flow = {
        "bulk0": client_bulks[0] if len(client_bulks) > 0 else 0,
        "bulk1": server_bulks[0] if len(server_bulks) > 0 else 0,
        "bulk2": client_bulks[1] if len(client_bulks) > 1 else 0,
        "bulk3": server_bulks[1] if len(server_bulks) > 1 else 0,
        "client_packet0": client_packets[0] if len(client_packets) > 0 else 0,
        "client_packet1": client_packets[1] if len(client_packets) > 1 else 0,
        "server_packet0": server_packets[0] if len(server_packets) > 0 else 0,
        "server_packet1": server_packets[1] if len(server_packets) > 1 else 0,
    }

    if client_bulks and client_bulks[0] == 0:
        client_bulks = client_bulks[1:]

    if not client_bulks or not server_bulks:
        return None

    flow.update({
        "client_bulksize_avg": np.mean(client_bulks),
        "client_bulksize_dev": np.std(client_bulks),
        "server_bulksize_avg": np.mean(server_bulks),
        "server_bulksize_dev": np.std(server_bulks),
        "client_packetsize_avg": np.mean(client_packets),
        "client_packetsize_dev": np.std(client_packets),
        "server_packetsize_avg": np.mean(server_packets),
        "server_packetsize_dev": np.std(server_packets),
        "client_packets_per_bulk": len(client_packets)/len(client_bulks),
        "server_packets_per_bulk": len(server_packets)/len(server_bulks),
        "client_effeciency": sum(client_bulks)/sum(client_packets),
        "server_efficiency": sum(server_bulks)/sum(server_packets),
        "byte_ratio": sum(client_packets)/sum(server_packets),
        "payload_ratio": sum(client_bulks)/sum(server_bulks),
        "packet_ratio": len(client_packets)/len(server_packets),
        "client_bytes": sum(client_packets),
        "client_payload": sum(client_bulks),
        "client_packets": len(client_packets),
        "client_bulks": len(client_bulks),
        "server_bytes": sum(server_packets),
        "server_payload": sum(server_bulks),
        "server_packets": len(server_packets),
        "server_bulks": len(server_bulks),
        #"proto": int(proto == "tcp")
        "is_tcp": int(proto == "tcp")
    })

    return flow