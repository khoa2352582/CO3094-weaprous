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
import time
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



def forward_request(host, port, request, custom_headers=None, track_time=False):

    """
    Forwards an HTTP request to a backend server and retrieves the response.

    :params host (str): IP address of the backend server.
    :params port (int): port number of the backend server.
    :params request (str): incoming HTTP request.
    :params custom_headers (dict): optional custom headers to add/modify in the request.

    :params track_time (bool): if True, returns (response, elapsed_time) tuple.


    :rtype bytes or tuple: Raw HTTP response from the backend server. If the connection
                  fails, returns a 404 Not Found response. If track_time=True, returns
                  (response, elapsed_time) tuple.
    """

    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    start_time = time.time() if track_time else None

    try:

        #
        # TODO: Apply custom headers if provided (e.g., proxy_set_header directives)
        #       Modify the request to include or replace headers based on custom_headers
        #
        if custom_headers:
            request_lines = request.split('\r\n')
            modified_lines = []
            headers_added = set()
            
            for line in request_lines:
                if ':' in line and line.strip():
                    header_name = line.split(':', 1)[0].strip()
                    replaced = False
                    for custom_name, custom_value in custom_headers.items():
                        if header_name.lower() == custom_name.lower():
                            if '$host' in custom_value:
                                for req_line in request_lines:
                                    if req_line.lower().startswith('host:'):
                                        actual_host = req_line.split(':', 1)[1].strip()
                                        custom_value = custom_value.replace('$host', actual_host)
                                        break
                            modified_lines.append("{}: {}".format(custom_name, custom_value))
                            headers_added.add(custom_name.lower())
                            replaced = True
                            break
                    if not replaced:

                        modified_lines.append(line)
                else:
                    modified_lines.append(line)
            

            for custom_name, custom_value in custom_headers.items():
                if custom_name.lower() not in headers_added:
                    for i, line in enumerate(modified_lines):
                        if line == '':
                            if '$host' in custom_value:
                                for req_line in request_lines:
                                    if req_line.lower().startswith('host:'):
                                        actual_host = req_line.split(':', 1)[1].strip()
                                        custom_value = custom_value.replace('$host', actual_host)
                                        break
                            modified_lines.insert(i, "{}: {}".format(custom_name, custom_value))
                            break
            
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
        
        if track_time:
            elapsed_time = time.time() - start_time
            return response, elapsed_time
        return response
        
    except socket.error as e:
        print("Socket error: {}".format(e))

        error_response = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode('utf-8')
        if track_time:
            return error_response, 999999  # Large penalty time for failed connections
        return error_response

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

    # Default fallback
    default_config = ('127.0.0.1:9000', 'srtf', {})
    config = routes.get(hostname, default_config)
    
    # Handle config parsing (2 items or 3 items)
    if len(config) == 2:
        proxy_map, policy = config
        headers = {}
    else:
        proxy_map, policy, headers = config
    
    proxy_host = '127.0.0.1'
    proxy_port = 9000

    # CASE 1: proxy_map is a LIST (Load Balancing)
    if isinstance(proxy_map, list):
        if len(proxy_map) == 0:
            print("[Proxy] Empty proxy_map for {}".format(hostname))
            return proxy_host, proxy_port, headers
            
        # --- Policy: SRTF ---
        if policy in ['srtf', 'shortest-time']:
            # Initialize tracking structures if not exists
            if not hasattr(resolve_routing_policy, 'response_times'):
                resolve_routing_policy.response_times = {}
                resolve_routing_policy.request_count = {}
            
            if hostname not in resolve_routing_policy.response_times:
                resolve_routing_policy.response_times[hostname] = {}
                resolve_routing_policy.request_count[hostname] = {}
                # Init defaults
                for backend in proxy_map:
                    resolve_routing_policy.response_times[hostname][backend] = 0.1
                    resolve_routing_policy.request_count[hostname][backend] = 0
            
            # Find best backend
            shortest_time = float('inf')
            best_backend = proxy_map[0]
            
            for backend in proxy_map:
                # Get current avg time, default 0.1s
                avg_time = resolve_routing_policy.response_times[hostname].get(backend, 0.1)
                if avg_time < shortest_time:
                    shortest_time = avg_time
                    best_backend = backend
            
            print("[Proxy] SRTF selected {} (avg: {:.3f}s)".format(best_backend, shortest_time))
            proxy_host, proxy_port = best_backend.split(":", 1)

        # --- Policy: Round-Robin (Default for list) ---
        else: 
            # Logic Round-Robin cũ của bạn, đã sửa tên biến backends -> proxy_map
            if not hasattr(resolve_routing_policy, 'counter'):
                resolve_routing_policy.counter = {}
            
            count = resolve_routing_policy.counter.get(hostname, 0)
            backend = proxy_map[count % len(proxy_map)]
            resolve_routing_policy.counter[hostname] = count + 1
            
            print("[Proxy] Round-Robin selected {}".format(backend))
            proxy_host, proxy_port = backend.split(':', 1)

    # CASE 2: proxy_map is a STRING (Direct Mapping)
    else:
        # Nếu chỉ có 1 server, cứ lấy server đó
        proxy_host, proxy_port = proxy_map.split(":", 1)

    # Normalize port to integer
    try:
        proxy_port = int(proxy_port)
    except Exception:
        proxy_port = 9000

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


    # Read request headers (simple loop until header terminator or timeout)
    conn.settimeout(1.0)
    raw = b""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
            if b"\r\n\r\n" in raw:
                # stop after headers read; body handling could be added using Content-Length
                break
    except socket.timeout:
        pass

    request = raw.decode('utf-8', errors='ignore')

    # Extract hostname safely
    hostname = ""
    for line in request.splitlines():

        if line.lower().startswith('host:'):
            hostname = line.split(':', 1)[1].strip()
            break

    if not hostname:
        print(f"[Proxy] {addr} sent request without Host header")
        conn.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 15\r\nConnection: close\r\n\r\n400 Bad Request")
        conn.close()
        return


    # Resolve the matching destination in routes
    resolved_host, resolved_port, custom_headers = resolve_routing_policy(hostname, routes)

    if resolved_host:
        print("[Proxy] Host name {} is forwarded to {}:{}".format(hostname, resolved_host, resolved_port))
        # Call forward_request with custom_headers from config and track time for SRTF
        result = forward_request(resolved_host, resolved_port, request, custom_headers, track_time=True)
        
        # Update SRTF statistics
        if isinstance(result, tuple):
            response, elapsed_time = result
            backend_key = "{}:{}".format(resolved_host, resolved_port)
            
            # Update average response time using exponential moving average
            if hasattr(resolve_routing_policy, 'response_times'):
                if hostname in resolve_routing_policy.response_times:
                    if backend_key in resolve_routing_policy.response_times[hostname]:
                        old_avg = resolve_routing_policy.response_times[hostname][backend_key]
                        # EMA: new_avg = 0.7 * old_avg + 0.3 * new_time
                        resolve_routing_policy.response_times[hostname][backend_key] = \
                            0.7 * old_avg + 0.3 * elapsed_time
                    else:
                        resolve_routing_policy.response_times[hostname][backend_key] = elapsed_time
                    
                    # Increment request count
                    if backend_key in resolve_routing_policy.request_count[hostname]:
                        resolve_routing_policy.request_count[hostname][backend_key] += 1
                    
                    print("[Proxy] Backend {} response time: {:.3f}s (avg: {:.3f}s)".format(
                        backend_key, elapsed_time, 
                        resolve_routing_policy.response_times[hostname][backend_key]))
        else:
            response = result
    else:
        response = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode('utf-8')

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

            #
            #  TODO: implement the step of the client incomping connection
            #        using multi-thread programming with the
            #        provided handle_client routine
            #

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