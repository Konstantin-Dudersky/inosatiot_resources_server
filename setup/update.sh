#!/bin/bash

# Получить актуальный проект с git

echo
echo "-----> Stop service:"
sudo systemctl stop inosatiot_resources_server.service

echo
echo "-----> Go to directory:"
cd ~/inosatiot/inosatiot_resources_server/ || exit

echo
echo "-----> Fetch from git:"
git fetch origin && git reset --hard origin/master && git clean -f -d

echo
echo "-----> Execute setup.sh:"
chmod +x setup/setup.sh && setup/setup.sh