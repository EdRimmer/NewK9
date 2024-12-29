#!/bin/bash
sudo rm /tmp/k9main.log
cd /home/ed/newk9
source /home/ed/newk9/.venv/bin/activate

/home/ed/newk9/.venv/bin/python3 main.py > /tmp/k9main.log 2>&1
