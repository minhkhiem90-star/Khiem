#!/bin/bash
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
nohup python3 widget.py >/dev/null 2>&1 &
