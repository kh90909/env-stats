import json
import struct

from datetime import datetime
from pathlib import Path

from bluepy.btle import Scanner, DefaultDelegate


DATA_DIR = Path('data')

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, scanEntry, isNewDev, isNewData):
        data = scanEntry.getValue(scanEntry.SERVICE_DATA_16B)
        if data and data[:2] == b'\x1a\x18' and len(data) == 17:
            now = datetime.now().astimezone().replace(microsecond=0).isoformat()
            uuid, mac, temp_degC_x100, humidity_percent_x100, battery_mv, battery_percent, counter, flags = struct.unpack('<H6shHHBBB', data)
            hex_mac = ''.join(f'{b:02x}' for b in reversed(mac))
            rssi = scanEntry.rssi

            parsed = {
                'timestamp': now,
                'data': data.hex(),
                'mac': hex_mac,
                'temperature': temp_degC_x100 / 100,
                'humidity': humidity_percent_x100 / 100,
                'battery_volt': battery_mv / 1000,
                'battery_percent': battery_percent,
                'count': counter,
            }

            if mac not in db_files:
                fn = DATA_DIR / f'{hex_mac}_log.txt'
                db_files[mac] = {
                    'fn': fn,
                    'last_counter': None
                }

            if counter != db_files[mac]['last_counter']:
                db_files[mac]['last_counter'] = counter
                line = f'{now}\t{parsed["temperature"]:4.1f}\t{parsed["humidity"]:5.1f}\t{parsed["battery_volt"]:4.2f}\t{battery_percent}\t{rssi:4d}\t{counter:3d}'
                #print(hex_mac, line)
                with open(db_files[mac]['fn'], 'a') as f:
                    print(line, file=f)

if __name__ == '__main__':
    db_files = {}
    #print('Scanning for advertisements from LYWSD03MMC temp/humidity sensors...')
    scanner = Scanner().withDelegate(ScanDelegate())
    scanner.scan(timeout=None, passive=True)
