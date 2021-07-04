#!/bin/bash
cd /home/ec2-user/app
source environment/bin/activate
sudo pkill -f "bot.py"
