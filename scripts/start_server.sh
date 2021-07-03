#!/bin/bash
cd /home/ec2-user/app
source environment/bin/activate
supervisorctl -c supervisord.conf