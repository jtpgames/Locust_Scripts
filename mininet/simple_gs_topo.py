"""GS topologies

SimpleTopo:

  host (AS) 
    --- switch (rounter at customer's home) --- (internet connection cust) 
    --- switch(internet connection AP) --- switch (router at ARC) 
  --- host (ARC)

"""

from mininet.topo import Topo
from mininet.cli import CLI

class SimpleTopo( Topo ):
    def build( self ):

        # Add hosts and switches
        alarm_system = self.addHost( 'h_as' )
        alarm_receiving_centre = self.addHost( 'h_arc' )
        
        leftSwitch = self.addSwitch( 's1' )
        ispSwitch = self.addSwitch( 's2' )
        rightSwitch = self.addSwitch( 's3' )

        # Add links

        # Oversimplified links for testing purposes
        linkopts = {'delay':'1s' }
        self.addLink( alarm_system, leftSwitch, **linkopts )
        linkopts = {'delay':'2s' }
        self.addLink( leftSwitch, rightSwitch, **linkopts )
        linkopts = {'delay':'1s' }
        self.addLink( rightSwitch, alarm_receiving_centre, **linkopts )

        return
        
        # Simulate production system
        # customer has 1 Gigabit Ethernet (GbE) connection to his router 
        linkopts = {'bw':1000, 'delay':'1ms' }
        self.addLink( alarm_system, leftSwitch, **linkopts )

        # customer has VDSL 100 (100 MBit Download, 40 MBit Upload) 
        linkopts = {'bw':40, 'delay':'1ms' }
        self.addLink( leftSwitch, ispSwitch, **linkopts )
        
        # alarm provider has SDSL 100 (100 MBit Down- /Upload)
        linkopts = {'bw':100, 'delay':'1ms' }
        self.addLink( ispSwitch, rightSwitch, **linkopts )

        # alarm provider has 1 GbE connection to his router
        linkopts = {'bw':1000, 'delay':'0.3ms', 'loss':16 }
        self.addLink( rightSwitch, alarm_receiving_centre, **linkopts )


python_configured_hosts = []


def setup_python_on_host(host):
    if host in python_configured_hosts:
        return

    host.cmd('cd ../')
    print("ARC: Current Working Directory:")
    host.cmdPrint('pwd')
    host.cmd('alias python=venv/bin/python')
    host.cmd('alias python3=venv/bin/python3')
    host.cmd('alias locust=venv/bin/locust')
    host.cmdPrint('python --version')
    host.cmdPrint('python3 --version')
    host.cmdPrint('locust --version')

    python_configured_hosts.append(host)


def startars(self, args):
    """Starts the ARS on the ARC host"""

    print(self)
    print(args)
    
    net = self.mn
    start_ARS(net)


def start_ARS(net):
    """Starts the ARS on the ARC host"""

    arc = net.get('h_arc')
    setup_python_on_host(arc) 

    print("ARC: Starting ARS.")
    arc.cmd('python ARS_simulation.py &> mininet/ars.out &')


def startprodworkload(self, args):
    """Starts a locust test simulating the production workload"""

    net = self.mn
    start_production_workload(net)


def start_production_workload(net):
    """Starts a locust test simulating the production workload"""

    h_as = net.get('h_as')
    arc = net.get('h_arc')
    
    setup_python_on_host(h_as)

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

    cmd = 'python locust-parameter-variation.py locust/gen_gs_alarm_device_workload.py -u http://{}:1337 -p'.format(arc.IP())
    print("AS: Starting Production Workload ...")
    print(cmd)

    cmd_output = h_as.cmd("{} &> /dev/null &".format(cmd))
    print(cmd_output)


def stop_workloads(self, args):
    """Stop all running workloads"""

    net = self.mn
    h_as = net.get('h_as')

    h_as.cmd('killall locust')

def LocustTest(net):
    
    start_ARS(net)
    # start_production_workload(net)

    # net.start()
    CLI(net)
    # net.stop()

topos = { 'simple-topo': ( lambda: SimpleTopo() ) }
tests = { 'LocustTest': LocustTest }

CLI.do_startars = startars
CLI.do_startprodworkload = startprodworkload
CLI.do_startasworkload = startasworkload
CLI.do_stopworkloads = stop_workloads
