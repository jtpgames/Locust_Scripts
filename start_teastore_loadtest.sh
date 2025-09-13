#!/bin/bash

# Default values
ip_address="127.0.0.1"
port="8080"
use_port=true
silent_execution=true

# Parse arguments in any order
while [[ $# -gt 0 ]]; do
    case $1 in
        --ip)
            if [ -n "$2" ]; then
                ip_address="$2"
                shift 2
            else
                echo "Error: --ip requires an IP address argument"
                exit 1
            fi
            ;;
        --port)
            if [ -n "$2" ]; then
                port="$2"
                shift 2
            else
                echo "Error: --port requires a port number argument"
                exit 1
            fi
            ;;
        --no_port)
            use_port=false
            shift
            ;;
        --verbose)
            silent_execution=false
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--ip IP_ADDRESS] [--port PORT_NUMBER] [--no_port] [--verbose]"
            exit 1
            ;;
    esac
done

# Construct the URL
if [ "$use_port" = true ]; then
    url="http://$ip_address:$port"
else
    url="http://$ip_address"
fi

echo "Using URL: $url"

# Construct the python command with conditional silent flag
if [ "$silent_execution" = true ]; then
    python3 executor.py locust/official_teastore_locustfile.py -u "$url" -s
else
    python3 executor.py locust/official_teastore_locustfile.py -u "$url"
fi
