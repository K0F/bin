#!/bin/bash
stat "$1" 2>/dev/null | grep Modify | awk '{print $2}'
