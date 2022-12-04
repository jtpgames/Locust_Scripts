#!/bin/sh

#sar -o "$1.sar" -A 1 >/dev/null 2>&1 &
sar -o "$1.sar" -n SOCK,IP,EIP,TCP,ETCP 1 >/dev/null 2>&1 &
