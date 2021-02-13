# Create a Python environment for this script.  Use ssh to log in to the pi, and run the following:
#
#     sudo apt install python3-venv
#     python3 -m venv /home/pi/plotly-env
#     /home/pi/plotly-env/bin/pip install -U plotly
#     mkdir /home/pi/probe_accuracy
#
# Download probe_accuracy.py and copy it to the pi into /home/pi/probe_accuracy/ .
#
# To collect data, ssh into the pi and run the below command before doing TEST_PROBE_ACCURACY:
#
#     /home/pi/plotly-env/bin/python3 /home/pi/probe_accuracy/probe_accuracy.py
#
# Leave that ssh session/window open for the duration of the test.  After the test completes, the
# chart should be in /tmp/probe_accuracy.html. Copy that file from the pi to your local machine
# and open it.
#
# If you specify --plot-only the script will not collect data from Klipper, but instead plot an
# existing JSON data file pointed to by --data-file.

import argparse
import json
import re
import socket
import time

import numpy as np, matplotlib

parser = argparse.ArgumentParser()
parser.add_argument('--klippy-uds', default='/tmp/klippy_uds')
parser.add_argument('--data-file', default='/tmp/probe_accuracy.json')
parser.add_argument('--chart-file', default='/tmp/probe_accuracy.html')
parser.add_argument('--plot-only', action='store_true',
                    help='plot existing file specified by --data-file instead of collecting data from Klipper')

KLIPPY_KEY = 31415926
GCODE_SUBSCRIBE = {
    'params': {'response_template': {'key': KLIPPY_KEY}},
    'id': 42,
    'method': 'gcode/subscribe_output'
}
TEST_END_MARKER = 'TEST_PROBE_ACCURACY: DONE'

BED_THERMISTOR_ID = 'B'
EXTRUDER_THERMISTOR_ID = 'T0'
START_RE = re.compile(r'// TEST_PROBE_ACCURACY: START')
# B:40.1 /40.0 PI:45.3 /0.0 T0:59.8 /60.0
TEMP_RE = re.compile(r'(?P<id>[\w-]+):(?P<temp>[0-9.]+)\s*/(?P<set>[0-9.]+)')
# // probe at 175.000,175.000 is z=2.027500
PROBE_RE = re.compile(r'^// probe at [0-9.,]+ is z=(?P<z>[0-9.-]+)')  # TODO: edge case '12:12:05  probe at 275.000,-0.000 is z=0.635000' not detected because of '-0.000'
# mesh_map_output {"mesh_max": [275.0, 275.0], "z_positions": [[-0.0225, 0.0225, 0.0275, 0.0225, -0.005], [0.0025, 0.03, 0.0375, 0.0325, 0.005], [-0.025, -0.005, 0.0, -0.005, -0.03], [-0.02, 0.0, 0.01, 0.0025, -0.02], [0.025, 0.0475, 0.0575, 0.0575, 0.045]], "mesh_min": [25.0, 25.0]}
MESH_MAP_RE = re.compile(r'mesh_map_output')

def get_klippy_output(klippy_uds: str):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(klippy_uds)

    try:
        sock.sendall(json.dumps(GCODE_SUBSCRIBE, separators=(',', ':')).encode() + b'\x03')

        remainder = b''
        while True:
            data = sock.recv(4096)
            parts = data.split(b'\x03')
            parts[0] = remainder + parts[0]
            remainder = parts.pop()
            for part in parts:
                line = part.decode()
                if str(KLIPPY_KEY) not in line:
                    continue
                if TEST_END_MARKER in line:
                    return
                yield line
    finally:
        sock.close()


def parse_response(response: str) -> dict:
    ts = time.time()

    # Parse thermistor output.
    tmatches = list(TEMP_RE.finditer(response))
    if tmatches:
        print('Thermistor output detected')
        d = {'ts': ts}
        for m in tmatches:
            if m.group('id') == BED_THERMISTOR_ID:
                d['btemp'] = float(m.group('temp'))
                d['bset'] = float(m.group('set'))
            elif m.group('id') == EXTRUDER_THERMISTOR_ID:
                d['etemp'] = float(m.group('temp'))
                d['eset'] = float(m.group('set'))
            else:
                ad = {
                    'id': m.group('id'),
                    'temp': float(m.group('temp')),
                    'set': float(m.group('set'))
                }
                try:
                    d['atherms'].append(ad)
                except KeyError:
                    d['atherms'] = [ad]
        return d

    # Parse bed mesh
    m = MESH_MAP_RE.match(response)
    if m:
        s = response.split(' ', 1)[1]   # strip 'mesh_map_output ' from string
        d = json.loads(s)               # get dict from json string
        d['ts'] = ts
        print('Mesh detected')
        return d

def get_data(klippy_uds: str, data_file: str) -> list:
    data = []
    with open(data_file, 'w') as f:
        for line in get_klippy_output(klippy_uds):
            klippy_response = json.loads(line)
            response = klippy_response['params']['response']

            d = parse_response(response)
            if d:
                data.append(d)
                f.write(json.dumps(d, separators=(',', ':')) + '\n')
                f.flush()

    return data


def load_data(data_file: str) -> list:
    with open(data_file, 'r') as f:
        return [json.loads(line) for line in f]


def main():
    args = parser.parse_args()

    if args.plot_only:
        data = load_data(args.data_file)
    else:
        print('Recording data, LEAVE THIS SESSION OPEN UNTIL THE SCRIPT SAYS "DONE"!')
        data = get_data(args.klippy_uds, args.data_file)

    # todo: plot data
    print('DONE')

if __name__ == '__main__':
    main()
