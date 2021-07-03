#!/bin/bash
cd /home/ec2-user/app
source environment/bin/activate
sudo python3 bot.py &
