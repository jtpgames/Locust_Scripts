from pox.core import core
import pox.lib.packet as pkt
import pox.openflow.libopenflow_01 as of

from datetime import datetime, time

log = core.getLogger()


bytes_per_second_received: dict[time, int] = dict()
packets_per_second_received: dict[time, int] = dict()
last_total_bytes = 0
last_total_packets = 0


def request_aggregated_stats():
    # request aggregated flow stats from all switches
    for con in core.openflow.connections:
        con.send(of.ofp_stats_request(body=of.ofp_aggregate_stats_request()))
    
    core.callDelayed(1, request_aggregated_stats)


def handle_agg_flow_stats(event):
    stats = event.stats
    total_packets = stats.packet_count
    total_bytes = stats.byte_count
    total_flows = stats.flow_count
    
    log.debug("Total traffic: %s bytes over %s flows in %s packets", total_bytes, total_flows, total_packets)
    
    global last_total_bytes, last_total_packets
    diff_bytes = total_bytes - last_total_bytes
    diff_packets = total_packets - last_total_packets
    if diff_bytes <= 0:
        return
    
    time_of_stat = datetime.now().time()
    time_of_stat = time_of_stat.replace(microsecond=0)
    
    if time_of_stat not in bytes_per_second_received:
        bytes_per_second_received[time_of_stat] = diff_bytes
        packets_per_second_received[time_of_stat] = diff_packets
    else:
        bytes_per_second_received[time_of_stat] += diff_bytes
        packets_per_second_received[time_of_stat] += diff_packets
    last_total_bytes = total_bytes
    last_total_packets = total_packets


def go_down(event):
    log.info("Writing Statistics to file ...")
    log.info(bytes_per_second_received)
    log.info(packets_per_second_received)
    log.info("Stats Received per Second Collector shut down")


def launch():
    # Listen for aggregated flow stats
    core.openflow.addListenerByName("AggregateFlowStatsReceived", handle_agg_flow_stats)
    
    core.callDelayed(1, request_aggregated_stats)
    
    core.addListenerByName("DownEvent", go_down)

    log.info("Stats Received per Second Collector running")
