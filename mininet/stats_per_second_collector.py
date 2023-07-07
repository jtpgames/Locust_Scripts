import json
from dataclasses import dataclass, asdict
from json import JSONEncoder

from pox.core import core
import pox.lib.packet as pkt
import pox.openflow.libopenflow_01 as of

from datetime import datetime, time


@dataclass(init=False)
class SwitchAggFlowStats:
    def __init__(self, switch_id: int):
        self.switch_id = switch_id
        self.bytes_per_second_received: dict[time, int] = dict()
        self.packets_per_second_received: dict[time, int] = dict()

    def add_agg_flow_stats(self, bytes_per_second: int, packets_per_second: int):
        time_of_stat = datetime.now().time()
        time_of_stat = time_of_stat.replace(microsecond=0)

        if time_of_stat not in self.bytes_per_second_received:
            self.bytes_per_second_received[time_of_stat] = bytes_per_second
            self.packets_per_second_received[time_of_stat] = packets_per_second
        else:
            self.bytes_per_second_received[time_of_stat] += bytes_per_second
            self.packets_per_second_received[time_of_stat] += packets_per_second

    def get_bytes_per_second_for(self, timestamp: datetime):
        time_of_request = timestamp.time()
        time_of_request = time_of_request.replace(time_of_request.hour, time_of_request.minute, time_of_request.second, 0)
        if time_of_request not in self.bytes_per_second_received:
            return 0
        return self.bytes_per_second_received[time_of_request]

    def get_packets_per_second_for(self, timestamp: datetime):
        time_of_request = timestamp.time()
        time_of_request = time_of_request.replace(time_of_request.hour, time_of_request.minute, time_of_request.second, 0)
        if time_of_request not in self.packets_per_second_received:
            return 0
        return self.packets_per_second_received[time_of_request]

    def __str__(self):
        return json.dumps(self, cls=SwitchAggFlowStatsEncoder)


class SwitchAggFlowStatsEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, SwitchAggFlowStats):
            return {
                'switch_id': o.switch_id,
                'bytes_per_second_received':  {str(k): v for k, v in o.bytes_per_second_received.items()},
                'packets_per_second_received': {str(k): v for k, v in o.packets_per_second_received.items()}
            }
        return super().default(o)


statistics_file_path = ""
log = core.getLogger()

agg_flow_stats: dict[int, SwitchAggFlowStats] = dict()

last_total_bytes = 0
last_total_packets = 0


def request_aggregated_stats():
    # request aggregated flow stats from all connected switches
    for con in core.openflow.connections:
        con.send(of.ofp_stats_request(body=of.ofp_aggregate_stats_request()))

    core.callDelayed(1, request_aggregated_stats)


def handle_agg_flow_stats(event):
    if event.connection.dpid not in agg_flow_stats:
        agg_flow_stats[event.connection.dpid] = SwitchAggFlowStats(event.connection.dpid)

    stats = event.stats
    total_packets = stats.packet_count
    total_bytes = stats.byte_count
    total_flows = stats.flow_count

    log.debug("Total traffic for switch %i: %s bytes over %s flows in %s packets", event.connection.dpid, total_bytes, total_flows, total_packets)

    global last_total_bytes, last_total_packets
    diff_bytes = total_bytes - last_total_bytes
    diff_packets = total_packets - last_total_packets

    agg_flow_stats[event.connection.dpid].add_agg_flow_stats(diff_bytes, diff_packets)

    last_total_bytes = total_bytes
    last_total_packets = total_packets


def go_down(event):
    log.info("Writing Statistics to file ...")
    with open(statistics_file_path, "w") as file:
        file.truncate()
        json.dump(agg_flow_stats, file, cls=SwitchAggFlowStatsEncoder, indent=2)
    log.info("Stats Received per Second Collector shut down")


def launch(file: str = "switch_flow_stats.json"):
    global statistics_file_path
    statistics_file_path = file

    # Listen for aggregated flow stats
    core.openflow.addListenerByName("AggregateFlowStatsReceived", handle_agg_flow_stats)

    core.callDelayed(1, request_aggregated_stats)

    core.addListenerByName("DownEvent", go_down)

    log.info("Stats Received per Second Collector running")
