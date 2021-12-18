#!/bin/bash 
sudo pip3 install virtualenv
cd /home/ec2-user/app
# sudo yum install jq (jq needs to be installed)
key=$(jq .KEY ../creds/creds.json) #retrieve key
virtualenv environment
source environment/bin/activate
echo KEY=$key > .env #inject key
sudo pip3 install -r scripts/requirements.txt
