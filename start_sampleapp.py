#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

import json
import socket
import argparse
import time
from urllib.parse import parse_qs

from daemon.weaprous import WeApRous

PORT = 8000  # Default port

# create app and an in-memory peer registry
app = WeApRous()
app.peers = {}  # key: 'ip:port' -> {ip, port, last_seen}
app.messages = []  # store received peer messages for local inspection


@app.route('/register', methods=['POST'])
def register(headers=None, body=None):
    """Register a peer. Expects form-encoded body: ip=...&port=...

    Returns JSON: {'status':'ok'} on success.
    """
    try:
        # try parse body as form data
        data = {}
        if isinstance(body, str):
            data = {k: v[0] for k, v in parse_qs(body).items()}
        elif isinstance(body, dict):
            data = body

        ip = data.get('ip')
        port = data.get('port')
        if not ip or not port:
            return json.dumps({'status': 'error', 'reason': 'missing ip or port'})

        key = f"{ip}:{port}"
        app.peers[key] = {'ip': ip, 'port': int(port), 'last_seen': time.time()}
        print(f"[Tracker] Registered peer {key}")
        return json.dumps({'status': 'ok'})
    except Exception as e:
        print('[Tracker] register error:', e)
        return json.dumps({'status': 'error', 'reason': str(e)})


@app.route('/get-peers', methods=['GET'])
def get_peers(headers=None, body=None):
    """Return a JSON list of currently known peers."""
    try:
        # filter out stale peers (older than 5 minutes)
        now = time.time()
        timeout = 300
        alive = []
        remove = []
        for k, v in app.peers.items():
            if now - v['last_seen'] <= timeout:
                alive.append({'ip': v['ip'], 'port': v['port']})
            else:
                remove.append(k)
        for k in remove:
            del app.peers[k]

        return json.dumps({'peers': alive})
    except Exception as e:
        return json.dumps({'status': 'error', 'reason': str(e)})


@app.route('/send-peer', methods=['POST'])
def send_peer(headers=None, body=None):
    """Receive a message sent directly from another peer.

    Accepts either JSON body like {"from_ip":"...","from_port":9001,"message":"..."}
    or form-encoded data with the same keys. Stores the message in `app.messages`
    and returns {'status':'ok'} on success.
    """
    try:
        data = {}
        # body can be a JSON string, a dict, or form-encoded string
        if isinstance(body, dict):
            data = body
        elif isinstance(body, str):
            # try JSON first
            try:
                data = json.loads(body)
            except Exception:
                data = {k: v[0] for k, v in parse_qs(body).items()}

        sender_ip = data.get('from_ip') or data.get('ip') or data.get('from')
        sender_port = data.get('from_port') or data.get('port')
        message = data.get('message') or data.get('msg') or data.get('text')

        if not message:
            return json.dumps({'status': 'error', 'reason': 'missing message'})

        entry = {
            'from_ip': sender_ip,
            'from_port': int(sender_port) if sender_port else None,
            'message': message,
            'received_at': time.time()
        }
        app.messages.append(entry)
        print(f"[Peer] Received message from {sender_ip}:{sender_port} -> {message}")
        return json.dumps({'status': 'ok'})
    except Exception as e:
        print('[Peer] send-peer error:', e)
        return json.dumps({'status': 'error', 'reason': str(e)})


@app.route('/messages', methods=['GET'])
def get_messages(headers=None, body=None):
    """Return stored peer messages for inspection (JSON)."""
    try:
        return json.dumps({'messages': app.messages})
    except Exception as e:
        return json.dumps({'status': 'error', 'reason': str(e)})


if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Tracker', description='Peer tracker', epilog='WeApRous tracker')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Prepare and launch the RESTful tracker application
    app.prepare_address(ip, port)
    app.run()