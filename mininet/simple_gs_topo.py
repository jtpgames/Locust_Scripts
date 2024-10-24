from mininet.node import Node
# noinspection PyPackageRequirements
from mininet.topo import Topo
# noinspection PyPackageRequirements
from mininet.cli import CLI
# noinspection PyPackageRequirements
from mininet.log import lg, info

import time


class SimpleTopo(Topo):
    """
        host (AS)
        --- switch (rounter at customer's home) --- (ISP router cust)
        --- switch(ISP router AP) --- switch (router at ARC)
        --- host (ARC)
    """

    def build(self):
        # Add hosts and switches
        alarm_system = self.addHost('h_as')
        alarm_receiving_centre = self.addHost('h_arc')

        customerSwitch = self.addSwitch('s1')
        ispCustomerSwitch = self.addSwitch('s2')
        ispAPSwitch = self.addSwitch('s3')
        apSwitch = self.addSwitch('s4')

        # Add links

        # -- Test Oversimplified links for testing purposes --
        #linkopts = {'delay':'10ms' }
        #self.addLink( alarm_system, customerSwitch, **linkopts )
        #linkopts = {'delay':'0.5s' }
        #self.addLink( customerSwitch, apSwitch, **linkopts )
        #linkopts = {'delay':'10ms' }
        #self.addLink( apSwitch, alarm_receiving_centre, **linkopts )

        # self.addLink( alarm_system, customerSwitch) 
        # self.addLink( customerSwitch, apSwitch)
        # self.addLink( apSwitch, alarm_receiving_centre)

        # return
        # --

        # Simulate production system
        # customer has 1 Gigabit Ethernet (GbE) connection to his router 
        linkopts = {'bw': 1000, 'delay': '0.45ms'}
        self.addLink(alarm_system, customerSwitch, **linkopts)

        # customer has VDSL 100 (100 MBit Download, 30 MBit Upload) 
        linkopts = {'bw': 30, 'delay': '2.4ms', 'jitter': '5.2ms'}
        self.addLink(customerSwitch, ispCustomerSwitch, **linkopts)

        # ISP Interlink (10 GbE connection) 
        # 1 Gigabit is the maximum bandwidth allowed by mininet
        linkopts = {'bw': 1000, 'delay': '13.3ms', 'jitter': '3.15ms'}
        self.addLink(ispCustomerSwitch, ispAPSwitch, **linkopts)

        # alarm provider sadly does NOT have SDSL, rather LACP-based Uplinks: VDSL100, VDSL50 combined
        linkopts = {'bw': 50, 'delay': '7.97ms', 'jitter': '2.9ms'}
        self.addLink(ispAPSwitch, apSwitch, **linkopts)

        # alarm provider has 2 GbE connection to his router
        # 1 Gigabit is the maximum bandwidth allowed by mininet
        linkopts = {'bw': 1000, 'delay': '0.19ms', 'jitter': '0.06ms'}
        self.addLink(apSwitch, alarm_receiving_centre, **linkopts)


python_configured_hosts = []


def setup_python_on_host(host):
    if host in python_configured_hosts:
        return

    host.cmd('cd ../')
    print("{}: Current Working Directory:".format(host))
    host.cmdPrint('pwd')
    host.cmd('source activate_venv.sh')
    # host.cmd('alias python=venv/bin/python')
    # host.cmd('alias python3=venv/bin/python3')
    # host.cmd('alias locust=venv/bin/locust')
    host.cmdPrint('python --version')
    host.cmdPrint('python3 --version')
    host.cmdPrint('locust --version')

    python_configured_hosts.append(host)


def startars(self, args):
    """Starts the ARS on the ARC host"""

    print(self)
    print(args)

    net = self.mn
    start_ARS(net, "", 1, 0)


def start_ARS(net, simulator_dir, model_to_use, corr_max):
    """Starts the ARS on the ARC host"""

    arc = net.get('h_arc')
    setup_python_on_host(arc)

    arc.cmd('./start_sysstat.sh arc')
    time.sleep(5)

    if simulator_dir == "":
        print("ARC: Starting ARS.")
        arc.cmd('python ARS_simulation.py &> mininet/ars.out &')
    else:
        arc.cmd(f'cd {simulator_dir}')
        print("ARC: Current Working Directory:")
        arc.cmdPrint('pwd')
        arc.cmdPrint(f'java -jar build/libs/Rast-Simulator-all.jar -m {model_to_use} -c {corr_max} &> /dev/null &')
        time.sleep(1)
        arc.cmdPrint('chmod 666 ars_simulation.log')


def startprodworkload(self, args):
    """Starts a locust test simulating the production workload"""

    net = self.mn
    start_production_workload(net)


def start_production_workload(net):
    """Starts a locust test simulating the production workload"""

    h_as = net.get('h_as')
    arc = net.get('h_arc')

    setup_python_on_host(h_as)

    h_as.cmd('./start_sysstat.sh alarm_system')
    time.sleep(5)

    cmd = 'python executor.py locust/gen_gs_prod_workload.py -u http://{}:1337 --silent'.format(arc.IP())
    print("AS: Starting Production Workload ...")
    print(cmd)

    cmd_output = h_as.cmd("{} &> /dev/null &".format(cmd))
    print(cmd_output)


def startasworkload(self, args):
    """Starts a locust test simulating one or many alarm devices"""

    net = self.mn
    start_alarm_system_workload(net)


def start_alarm_system_workload(net):
    """Starts a locust test simulating one or many alarm devices"""

    h_as = net.get('h_as')
    arc = net.get('h_arc')

    setup_python_on_host(h_as)

    cmd = 'python locust-parameter-variation.py locust/gen_gs_alarm_device_workload.py -u http://{}:1337 -m 500 -p'.format(
        arc.IP())
    print("AS: Starting Alarm Device Workload ...")
    print(cmd)

    cmd_output = h_as.cmd("{} &> /dev/null &".format(cmd))
    print(cmd_output)


def stop_workloads(self, args):
    """Stop all running workloads"""

    net = self.mn
    h_as = net.get('h_as')

    h_as.cmd('killall locust')


def LocustTest(net, simulator_dir, model_to_use, corr_max):
    lg.setLogLevel('info')

    # # Add a NAT node to provide internet access to ARC host node
    # nat = net.get('nat0')
    # apSwitch = net.get('s4')
    # print(nat)
    # net.addLink(nat, apSwitch)
    #
    # # Enable IP forwarding on the Mininet host machine
    # root = Node('root', inNamespace=False)
    # root.cmd('sysctl -w net.ipv4.ip_forward=1')
    #
    # # Set up NAT rules
    # host_network_intf = "wlp0s20f3"
    #
    # root.cmd(f'iptables -t nat -A POSTROUTING -o {host_network_intf} -j MASQUERADE')
    # root.cmd(f'iptables -A FORWARD -i {host_network_intf} -o nat0 -m state --state RELATED,ESTABLISHED -j ACCEPT')
    # root.cmd(f'iptables -A FORWARD -i nat0 -o {host_network_intf} -j ACCEPT')

    start_ARS(net, simulator_dir, model_to_use, corr_max)
    time.sleep(5)
    start_production_workload(net)
    time.sleep(1)
    start_alarm_system_workload(net)

    # net.start()
    CLI(net)
    # net.stop()


topos = {'simple-topo': (lambda: SimpleTopo())}
tests = {'LocustTest': LocustTest}

CLI.do_startars = startars
CLI.do_startprodworkload = startprodworkload
CLI.do_startasworkload = startasworkload
CLI.do_stopworkloads = stop_workloads
