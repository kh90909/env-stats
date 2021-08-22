# env-stats

Data logger and web server for Xiaomi MiThermometers LYWSD03MMC temperature + humidity
sensors running the [pvvx custom firmware](https://github.com/pvvx/ATC_MiThermometer).

## Installation and setup on Raspberry Pi (Buster)

    sudo apt install git python3-venv libatlas-base-dev libopenjp2-7 libtiff5
    git clone https://github.com/kh90909/env-stats
    cd env-stats
    python3 -m venv env
    source env/bin/activate
    pip3 install -r requirements-versioned.txt

Create `data/sensor_names.txt` to specify the addresses and human readable labels for
the sensors to be reported on the web server page, e.g.

    a4c138012345	Living Room
    a4c138123456	Kitchen

Note that the address and label should be separated by a tab.

Modify *.service files to adjust paths and username if required

    sudo cp *.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable env-stats-server.service
    sudo systemctl start env-stats-server.service
    sudo systemctl enable env-sensors-scanner.service
    sudo systemctl start env-sensors-scanner.service
