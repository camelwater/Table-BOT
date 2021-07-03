#!/bin/bash
cd /home/ec2-user/app
source environment/bin/activate
sudo -f pkill "bot.py"