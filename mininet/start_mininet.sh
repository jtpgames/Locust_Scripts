#!/bin/bash

# Default values
simulator_dir=""
model_to_use=1
corr_max=0

# Function to display usage information
usage() {
    echo "Usage: $0 [-d simulator_dir] [-m model_to_use] [-c corr_max] [-h]"
    echo "  -d simulator_dir  Set the directory for the simulator (default: empty)"
    echo "  -m model_to_use   Set the model to use (default: 1)"
    echo "  -c corr_max       Set the maximum correlation (default: 0)"
    echo "  -h                Display this help message"
    exit 1
}

# Parse command-line options
while getopts "d:m:c:h" opt; do
    case "$opt" in
        d) simulator_dir="$OPTARG" ;;
        m) model_to_use="$OPTARG" ;;
        c) corr_max="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Shift off the options and optional --
shift "$((OPTIND-1))"

# Print the values
echo "simulator_dir: $simulator_dir"
echo "model_to_use: $model_to_use"
echo "corr_max: $corr_max"

#sudo mn --custom simple_gs_topo.py --mac --nat --topo simple-topo --test LocustTest,simulator_dir=$simulator_dir,model_to_use=$model_to_use,corr_max=$corr_max --link tc
sudo mn --custom simple_gs_topo.py --topo simple-topo --test LocustTest,simulator_dir=$simulator_dir,model_to_use=$model_to_use,corr_max=$corr_max --link tc

