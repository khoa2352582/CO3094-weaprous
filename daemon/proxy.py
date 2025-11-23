#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.proxy
~~~~~~~~~~~~~~~~~

This module implements a simple proxy server using Python's socket and threading libraries.
It routes incoming HTTP requests to backend services based on hostname mappings and returns
the corresponding responses to clients.
"""
import socket
import threading
from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict

#: A dictionary mapping hostnames to backend IP and port tuples.
#: Used to determine routing targets for incoming requests.
PROXY_PASS = {
    "192.168.56.103:8080": ('192.168.56.103', 9000),
    "app1.local": ('192.168.56.103', 9001),
    "app2.local": ('192.168.56.103', 9002),
}


def forward_request(host, port, request, custom_headers=None): #thêm custom_headers
    """
    Forwards an HTTP request to a backend server and retrieves the response.

    :params host (str): IP address of the backend server.
    :params port (int): port number of the backend server.
    :params request (str): incoming HTTP request.
    :params custom_headers (dict): optional custom headers to add/modify in the request.

    :rtype bytes: Raw HTTP response from the backend server. If the connection
                  fails, returns a 404 Not Found response.
    """

    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # ============================================
        # TEAM IMPLEMENTATION: Custom Header Injection
        # Implements proxy_set_header directive from proxy.conf
        # Supports variable substitution like $host (replaced with actual Host header value)
        # Modifies existing headers or adds new ones before forwarding to backend
        # ============================================
        if custom_headers:
            request_lines = request.split('\r\n')
            
            # Extract actual host value for $host substitution
            actual_host = None
            for line in request_lines:
                if line.lower().startswith('host:'):
                    actual_host = line.split(':', 1)[1].strip()
                    break
            
            # Process custom headers with variable substitution
            processed_headers = {}
            for name, value in custom_headers.items():
                if '$host' in value and actual_host:
                    value = value.replace('$host', actual_host)
                processed_headers[name.lower()] = (name, value)
            
            # Replace or keep original headers, add new ones
            modified_lines = []
            headers_section = True
            for line in request_lines:
                if headers_section and line == '':
                    # End of headers - add any missing custom headers
                    for name, value in processed_headers.values():
                        modified_lines.append("{}: {}".format(name, value))
                    processed_headers.clear()
                    headers_section = False
                    modified_lines.append(line)
                elif ':' in line and line.strip() and headers_section:
                    header_name = line.split(':', 1)[0].strip().lower()
                    if header_name in processed_headers:
                        # Replace with custom header
                        name, value = processed_headers.pop(header_name)
                        modified_lines.append("{}: {}".format(name, value))
                    else:
                        modified_lines.append(line)
                else:
                    modified_lines.append(line)
            
            request = '\r\n'.join(modified_lines)
        backend.connect((host, port))
        backend.sendall(request.encode('latin-1'))

        # Read complete backend response
        response = b""
        while True:
            chunk = backend.recv(4096)
            if not chunk:
                break
            response += chunk
        return response
        
    except socket.error as e:
        print("Socket error: {}".format(e))
        return b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 13\r\nConnection: close\r\n\r\n404 Not Found"
    finally:
        backend.close()


# ============================================
# TEAM IMPLEMENTATION: Routing Policy with Load Balancing
# Resolves backend target from hostname and routing configuration
# Supports:
# - Single backend (string): Direct routing
# - Multiple backends (list): Round-robin load balancing
# - Custom headers: proxy_set_header directives
# ============================================
def resolve_routing_policy(hostname, routes):
    """
    Handles an routing policy to return the matching proxy_pass.
    Fixed logic for handling both string and list proxy_map configurations.
    """
    print("[Proxy] Resolving policy for hostname: {}".format(hostname))

    # Get config or use default
    config = routes.get(hostname, (['127.0.0.1:9000'], 'round-robin', {}))
    proxy_map, policy = config[0], config[1]
    headers = config[2] if len(config) > 2 else {}
    
    print("[Proxy] Route config found: Map={}, Policy={}, Headers={}".format(proxy_map, policy, headers))

    # ============================================
    # TEAM IMPLEMENTATION: Handle both string and list proxy_map
    # - String: Single backend (e.g., "127.0.0.1:9000")
    # - List: Multiple backends with load balancing
    # ============================================
    
    # Convert string to list for uniform handling
    backends = [proxy_map] if isinstance(proxy_map, str) else proxy_map
    
    if not backends:
        proxy_host, proxy_port = '127.0.0.1', '9000'
    elif len(backends) == 1:
        proxy_host, proxy_port = backends[0].split(':', 1)
    else:
        # Round-robin load balancing
        print("[Proxy] Load balancing for: {}".format(hostname))
        if policy == 'round-robin':
            if not hasattr(resolve_routing_policy, 'counter'):
                resolve_routing_policy.counter = {}
            count = resolve_routing_policy.counter.get(hostname, 0)
            backend = backends[count % len(backends)]
            resolve_routing_policy.counter[hostname] = count + 1
            proxy_host, proxy_port = backend.split(':', 1)
        else:
            proxy_host, proxy_port = backends[0].split(':', 1)

    return proxy_host, proxy_port, headers


# ============================================
# TEAM IMPLEMENTATION: Robust Request Reading
# Reads complete HTTP request including headers and body
# Handles Content-Length to ensure full body is received
# Uses latin-1 encoding for binary-safe operations
# ============================================
def handle_client(ip, port, conn, addr, routes):
    """
    Handles an individual client connection by parsing the request,
    determining the target backend, and forwarding the request.
    Fixed version with robust request reading and proper encoding.
    """

    # ============================================
    # TEAM IMPLEMENTATION: Robust Request Reading
    # Reads complete HTTP request including headers and body
    # Handles Content-Length to ensure full body is received
    # Uses latin-1 encoding for binary-safe operations
    # ============================================
    
    try:
        # Read headers (until \r\n\r\n)
        data = b""
        conn.settimeout(5.0)
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                conn.close()
                return
            data += chunk
        conn.settimeout(None)

        # Parse headers and extract Content-Length
        header_part, _, body_part = data.partition(b"\r\n\r\n")
        headers_text = header_part.decode('latin-1')
        
        content_length = 0
        for line in headers_text.splitlines():
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
                break

        # Read remaining body if needed
        body_bytes = body_part
        remaining = content_length - len(body_bytes)
        if remaining > 0:
            conn.settimeout(5.0)
            while remaining > 0:
                chunk = conn.recv(min(remaining, 4096))
                if not chunk:
                    break
                body_bytes += chunk
                remaining -= len(chunk)
            conn.settimeout(None)

        # Reconstruct complete request
        full_request_str = headers_text + "\r\n\r\n" + body_bytes.decode('latin-1', errors='ignore')
        
    except Exception as e:
        print(f"[Proxy] Request reading error: {e}")
        conn.close()
        return


    # Extract hostname from Host header
    hostname = None
    for line in headers_text.splitlines():
        if line.lower().startswith('host:'):
            hostname = line.split(':', 1)[1].strip()
            break

    if not hostname:
        print(f"[Proxy] {addr} sent request without Host header")
        conn.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 15\r\nConnection: close\r\n\r\n400 Bad Request")
        conn.close()
        return

    print("[Proxy] {} requesting Host: {}".format(addr, hostname))

    # Resolve backend target and forward request
    resolved_host, resolved_port, custom_headers = resolve_routing_policy(hostname, routes)
    resolved_port = int(resolved_port) if resolved_port.isdigit() else 9000
    
    print("[Proxy] Forwarding {} to {}:{}".format(hostname, resolved_host, resolved_port))
    response = forward_request(resolved_host, resolved_port, full_request_str, custom_headers)
    
    conn.sendall(response)
    conn.close()


def run_proxy(ip, port, routes):
    """
    Starts the proxy server and listens for incoming connections. 

    The process dinds the proxy server to the specified IP and port.
    In each incomping connection, it accepts the connections and
    spawns a new thread for each client using `handle_client`.

    :params ip (str): IP address to bind the proxy server.
    :params port (int): port number to listen on.
    :params routes (dict): dictionary mapping hostnames and location.
    """

    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        proxy.bind((ip, port))
        proxy.listen(50)

        print("[Proxy] Listening on IP {} port {}".format(ip, port))
        while True:
            conn, addr = proxy.accept()
            
            # ============================================
            # TEAM IMPLEMENTATION: Multi-threaded Client Handling
            # Spawns daemon thread for each incoming connection
            # Allows concurrent processing of multiple client requests
            # ============================================
            client_thread = threading.Thread(
                target=handle_client,
                args=(ip, port, conn, addr, routes)
            )
            client_thread.daemon = True
            client_thread.start()
    except socket.error as e:
        print("Socket error: {}".format(e))

def create_proxy(ip, port, routes):
    """
    Entry point for launching the proxy server.

    :params ip (str): IP address to bind the proxy server.
    :params port (int): port number to listen on.
    :params routes (dict): dictionary mapping hostnames and location.
    """

    run_proxy(ip, port, routes)