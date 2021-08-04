#!/bin/bash 
sudo pip3 install virtualenv
cd /home/ec2-user/app
key=$(jq .BOT_KEY ../creds/creds.json) #retrieve key
virtualenv environment
source environment/bin/activate
echo KEY=$key > .env #inject key
sudo pip3 install -r scripts/requirements.txt
