import getpass
import os

path = os.getcwd()

service = f"""[Unit]
Description=Server for resources
StartLimitIntervalSec=120
StartLimitBurst=5

[Service]
Restart=on-failure
RestartSec=5s
Type=simple
User={getpass.getuser()}
Group={getpass.getuser()}
EnvironmentFile=/etc/environment
WorkingDirectory={path}
ExecStart={path}/venv/bin/daphne -b 0.0.0.0 -p 8080 inosatiot_resources_server.asgi:application

[Install]
WantedBy=multi-user.target"""

f = open("setup/inosatiot_resources_server.service", "w")
f.write(service)
f.close()

print(f'Created service file: \n{service}')
