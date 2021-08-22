import base64
import sys

from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np


hostName = '0.0.0.0'
serverPort = 8888
DATA_DIR = Path('data')

html_tmpl = '''<html>
<head><title>Environmental Stats</title></head>
<meta http-equiv="refresh" content="600">
<style>
body {{
  background-color: #c0c0c0;
  font-family: sans-serif;
}}

.main-cards {{
  column-count: 2;
  column-gap: 20px;
  margin: 20px;
}}

.single-column {{
  column-count: 1 !important;
}}

.card {{
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
  width: 100%;
  background-color: #ffffff;
  margin-bottom: 20px;
  -webkit-column-break-inside: avoid;
  padding: 24px;
  box-sizing: border-box;
}}

.container {{
  display: flex;
  padding: 2px 16px;
}}

.container-child {{
  flex: 1;
}}

.container-child:first-child {{
  margin-right: 20px;
}}

.right {{
  text-align: right;
}}

td {{
  text-align: right;
  font-size: 1.5vw;
}}

td.datetime {{
  font-size: 1vw !important;
}}

td.alert {{
  font-weight: bold;
  background-color: yellow;
}}

.temp {{
  font-size: 5.5vw;
  font-weight: bold;
  text-align: right;
}}

.humidity {{
  font-size: 3vw;
}}
</style>

<body>
 <div class="main-cards">
  {sensor_data_html}
 </div>
 <div class="main-cards single-column">
  <div class="card">
   <img width="100%" src="data:image/png;base64,{graph}">
  </div>
 </div>
</body>
</html>
'''

sensor_data_tmpl = '''
<div class="card">
  <h4>{name}</h4>
  <div class="container">
  <div class="container-child">
   <div class="temp">{temp:.1f}<br>&deg;C</div>
  </div>
  <div class="container-child right">
   <table>
    <tr><td colspan=2><div class="humidity">{humidity:.1f}% RH</div></td></tr>
    <tr><td>BATTERY</td><td>{battery:.0f}%</td></tr>
    <tr><td></td><td>({battery_voltage:.2f}V)</td></tr>
    <tr><td>RSSI</td><td>{rssi}dB</td></tr>
    <tr><td colspan=2 class="datetime {alert}">{timedelta}</td></tr>
   </table>
  </div>
 </div>
</div>
'''


def approx_timedelta_str(td):
    attrs = ['seconds', 'minutes', 'hours', 'days', 'months', 'years']
    durations = [60, 60, 24, 30, 12] # duration[i] is number of attrs[i] in attrs[i + 1]

    value = td.total_seconds()
    i = 0
    while value / durations[i] >= 1:
        value /= durations[i]
        i += 1

    return f'~{round(value, 0):.0f} {attrs[i]} ago'

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        name, graph, sensor_data_html = create_graph()
        b64_graph = base64.b64encode(graph.getvalue()).decode()

        self.wfile.write(html_tmpl.format(
            name=name,
            sensor_data_html=sensor_data_html,
            graph=b64_graph,
        ).encode())

    def log_request(self, code='-', size='-'):
        return

def create_graph():
    sensor_data_html = ''
    fig, (ax_temp, ax_humid)  = plt.subplots(2, 1, sharex=True, figsize=(10, 5))

    for mac, name in sensor_names.items():
        data = np.genfromtxt(
            DATA_DIR / f'{mac}_log.txt',
            dtype=[
                ('Time','object'),
                ('Temperature', 'f4'),
                ('Humidity', 'f4'),
                ('Battery_voltage', 'f4'),
                ('Battery_percent', 'i4'),
                ('RSSI', 'i4'),
                ('Counter', 'i4')
            ],
            converters={0: lambda x: datetime.fromisoformat(x.decode('utf-8'))}
        )

        ax_temp.plot(data['Time'], data['Temperature'], label=name)
        ax_humid.plot(data['Time'], data['Humidity'], label=name)

        reading_age = datetime.now().astimezone() - data['Time'][-1]

        sensor_data_html += sensor_data_tmpl.format(
            name=name,
            temp=data['Temperature'][-1],
            humidity=data['Humidity'][-1],
            battery=data['Battery_percent'][-1],
            battery_voltage=data['Battery_voltage'][-1],
            rssi=data['RSSI'][-1],
            timedelta=approx_timedelta_str(reading_age),
            alert='alert' if reading_age > timedelta(minutes=5) else '',
        )

    ax_temp.set_ylabel('Temperature (degC)')
    ax_temp.legend(loc='upper left')
    ax_temp.grid(axis='both', which='major', color='#cccccc', linestyle='-')
    ax_temp.grid(axis='x', which='minor', color='#cccccc', linestyle='-', alpha=0.3)

    ax_humid.set_ylabel('Humidity (%)')
    ax_humid.set_xlabel('Time')
    ax_humid.xaxis.set_major_locator(mdates.DayLocator())
    ax_humid.xaxis.set_minor_locator(mdates.HourLocator(range(0, 24, 6)))
    ax_humid.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax_humid.grid(axis='both', which='major', color='#cccccc', linestyle='-')
    ax_humid.grid(axis='x', which='minor', color='#cccccc', linestyle='-', alpha=0.3)
    ax_humid.set_xlim([datetime.now() - timedelta(days=7), datetime.now()])

    fig.subplots_adjust(hspace=0)

    figdata = BytesIO()
    fig.savefig(figdata, format='png', bbox_inches='tight')
    plt.close(fig)

    return name, figdata, sensor_data_html


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), MyServer)
    #print(f'Server started http://{hostName}:{serverPort}')

    sensor_names = {}
    with open(DATA_DIR / 'sensor_names.txt') as file:
        for line in file:
            mac, name = line.strip().split('\t')
            sensor_names[mac] = name

    if len(sensor_names) == 0:
        #print('No sensors named in sensor_names.txt')
        sys.exit(1)

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    #print('Server stopped.')

