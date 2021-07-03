#!/bin/bash
cd /home/ec2-user/app
source environment/bin/activate
supervisor -c supervisord.conf