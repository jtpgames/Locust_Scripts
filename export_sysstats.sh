sadf -g "$1" -- -w -r -u -n ALL -B -S -W > "$1.svg"
sadf -g "$1" -- -n SOCK -n TCP,ETCP > "$1_network.svg"