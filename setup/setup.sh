#!/bin/bash

echo
echo "-----> Python version:"
python3 -V

echo
echo "-----> Updating system:"
sudo apt update
sudo apt -y upgrade

echo
echo "-----> Install python base packages:"
sudo apt install -y python3-pip
sudo apt install -y python3-venv

echo
echo "-----> Create virtual environment:"
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r setup/requirements.txt

echo
echo "-----> Execute collectstatic:"
python3 manage.py collectstatic

echo
echo "-----> Create systemd service:"
python3 setup/service.py
sudo mv setup/inosatiot_resources_server.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable inosatiot_resources_server.service

#echo
#echo "-----> Share folder:"
#sudo apt install -y samba
#sudo smbpasswd -a "$USER"
#sudo python3 setup/samba.py
#sudo systemctl restart smbd.service

echo
echo "-----> Start:"
sudo systemctl start inosatiot_resources_server.service

echo
echo "-----> Finish!"