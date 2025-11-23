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

# ============================================
# TEAM IMPLEMENTATION - TASK 2: HYBRID P2P CHAT
# Tracker server for peer discovery and messaging
# Implements 4 RESTful API endpoints for P2P communication
# ============================================

# create app and an in-memory peer registry
app = WeApRous()
app.peers = {}  # key: 'ip:port' -> {ip, port, last_seen}
app.messages = []  # store received peer messages for local inspection


# ============================================
# API 1: /submit-info (POST)
# Registers a peer in the tracker's peer list
# Used during initial connection and periodic keepalive
# ============================================
@app.route('/submit-info', methods=['POST'])
def register(headers=None, body=None):
    """
    Register a peer. Expects form-encoded body: ip=...&port=...
    Returns JSON: {'status':'ok'} on success.
    """
    try:
        # Parse body (dict or form-encoded string)
        data = body if isinstance(body, dict) else {k: v[0] for k, v in parse_qs(body).items()}
        
        ip = data.get('ip')
        port = data.get('port')
        if not ip or not port:
            return json.dumps({'status': 'error', 'reason': 'missing ip or port'})

        # Store peer with timestamp for timeout management
        key = f"{ip}:{port}"
        app.peers[key] = {'ip': ip, 'port': int(port), 'last_seen': time.time()}
        print(f"[Tracker] Registered peer {key}")
        return json.dumps({'status': 'ok'})
    except Exception as e:
        print('[Tracker] register error:', e)
        return json.dumps({'status': 'error', 'reason': str(e)})


# ============================================
# API 2: /get-list (GET)
# Returns list of active peers for discovery
# Automatically removes stale peers (5-minute timeout)
# ============================================
@app.route('/get-list', methods=['GET'])
def get_peers(headers=None, body=None):
    """
    Return a list of currently active peers and their status.
    Returns: {'status': 'ok', 'peers': [{ip, port, last_seen},...]}
    """
    try:
        # Filter active peers (seen in last 5 minutes)
        now = time.time()
        timeout = 300  # 5 minutes
        active_peers = {}
        
        for key, peer in list(app.peers.items()):
            if now - peer['last_seen'] <= timeout:
                active_peers[key] = {
                    'ip': peer['ip'],
                    'port': peer['port'],
                    'last_seen': peer['last_seen']
                }
            else:
                # Clean up stale peers
                del app.peers[key]
        
        return json.dumps({
            'status': 'ok',
            'peers': active_peers
        })
    except Exception as e:
        print('[Tracker] get-peers error:', e)
        return json.dumps({'status': 'error', 'reason': str(e)})


# ============================================
# API 3: /send-peer (POST)
# Handles P2P messaging with handshake protocol
# First contact: Sender info + is_first=true -> Receiver responds with their info
# Subsequent messages: Direct P2P communication
# ============================================
@app.route('/send-peer', methods=['POST'])
def send_peer(headers=None, body=None):
    """
    Handle peer messages with the initial handshake protocol.
    
    First message: Sender includes their info, receiver responds with their info
    Subsequent messages: Direct P2P communication
    
    Accepts JSON: {"from_ip": "...", "from_port": 9001, "message": "...", "is_first": true/false}
    """
    try:
        # Parse JSON or form-encoded body
        if isinstance(body, dict):
            data = body
        elif isinstance(body, str):
            try:
                data = json.loads(body)
            except:
                data = {k: v[0] for k, v in parse_qs(body).items()}
        else:
            return json.dumps({'status': 'error', 'reason': 'invalid body format'})

        sender_ip = data.get('from_ip') or data.get('ip')
        sender_port = data.get('from_port') or data.get('port')
        message = data.get('message')
        is_first = data.get('is_first', False)

        if not sender_ip or not sender_port or not message:
            return json.dumps({'status': 'error', 'reason': 'missing required fields'})

        # Store message
        app.messages.append({
            'from_ip': sender_ip,
            'from_port': int(sender_port),
            'message': message,
            'received_at': time.time()
        })
        
        # Handshake Protocol: If first contact, respond with our info for P2P
        if is_first:
            print(f"[Peer] First contact from {sender_ip}:{sender_port}")
            return json.dumps({
                'status': 'ok',
                'request_info': True,
                'ip': app.ip,
                'port': app.port
            })
        
        print(f"[Peer] Message from {sender_ip}:{sender_port} -> {message}")
        return json.dumps({'status': 'ok'})
        
    except Exception as e:
        print('[Peer] send-peer error:', e)
        return json.dumps({'status': 'error', 'reason': str(e)})


# ============================================
# API 4: /messages (GET)
# Returns all stored peer messages (for debugging/inspection)
# Clears message buffer after retrieval
# ============================================
@app.route('/messages', methods=['GET'])
def get_messages(headers=None, body=None):
    """Return stored peer messages for inspection (JSON)."""
    try:
        messages_to_send = list(app.messages)
        app.messages.clear()
        return json.dumps({'messages': messages_to_send})
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