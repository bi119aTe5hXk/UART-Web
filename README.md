# UART-Web
Using UART on web with logging

# Screenshot
<img width="1356" height="963" alt="Screenshot 2025-11-20 at 23 53 54" src="https://github.com/user-attachments/assets/23f5b970-9379-4070-b3fd-6d7fec0916e9" />


# Install
```
sudo apt install python3 python3-full
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```
or just
```
sudo apt install python3 python3-pip
pip3 install -r requirements.txt --break-system-packages
```

# Useage
```
python3 app.py
```

Then open [http://localhost](http://localhost).

# Run on startup
```
sudo nano /etc/systemd/system/uart-web.service
```
```
[Unit]
Description=UART Web Console Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/UART-Web
ExecStart=/home/pi/UART-Web/.venv/bin/python /home/pi/UART-Web/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl daemon-reload
sudo systemctl start uart-web.service
sudo systemctl enable uart-web.service
```
If failed, then
```
sudo journalctl -u uart-web.service -f
sudo systemctl status uart-web.service
```
and ask AI for help.😉
