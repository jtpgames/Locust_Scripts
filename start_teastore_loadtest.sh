#!/bin/bash

# Check if the IP address argument is provided
if [ "$1" = "--ip" ] && [ -n "$2" ]; then
    ip_address="$2"
    ip_address="http://$2:8080"
else
    # Set a default IP address
    ip_address="http://127.0.0.1:8080"
fi

echo "Using URL: $ip_address"

python3 executor.py locust/official_teastore_locustfile.py -u "$ip_address"
