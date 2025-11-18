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

Requirement:
-----------------
- socket: provides socket networking interface.
- threading: enables concurrent client handling via threads.
- response: customized :class: `Response <Response>` utilities.
- httpadapter: :class: `HttpAdapter <HttpAdapter >` adapter for HTTP request processing.
- dictionary: :class: `CaseInsensitiveDict <CaseInsensitiveDict>` for managing headers and cookies.

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
        backend.sendall(request.encode())
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


def resolve_routing_policy(hostname, routes):
    """
    Handles an routing policy to return the matching proxy_pass.
    It determines the target backend to forward the request to.

    :params host (str): IP address of the request target server.
    :params port (int): port number of the request target server.
    :params routes (dict): dictionary mapping hostnames and location.
    """

    print(hostname)
    #
    # TODO: Handle both old format (2 items) and new format (3 items with headers)
    #
    default_config = ('127.0.0.1:9000', 'srtf', {})
    config = routes.get(hostname, default_config)
    
    if len(config) == 2:
        proxy_map, policy = config
        headers = {}
    else:
        proxy_map, policy, headers = config
    
    print(proxy_map)
    print(policy)

    proxy_host = ''
    proxy_port = '9000'
    
    if isinstance(proxy_map, list):
        if len(proxy_map) == 0:
            print("[Proxy] Emtpy resolved routing of hostname {}".format(hostname))
            print("Empty proxy_map result")
            # TODO: implement the error handling for non mapped host
            #       the policy is design by team, but it can be 
            #       basic default host in your self-defined system
            # Use a dummy host to raise an invalid connection
            proxy_host = '127.0.0.1'
            proxy_port = '9000'
        elif len(proxy_map) == 1:
            proxy_host, proxy_port = proxy_map[0].split(":", 2)
        #elif: # apply the policy handling 
        #   proxy_map
        #   policy
        else:
            #
            # TODO: Multiple backends - apply load balancing policy
            #       Implement round-robin or other policies here
            #
            
            # ========== ROUND-ROBIN ALGORITHM (COMMENTED OUT) ==========
            # if policy == 'round-robin':
            #     if not hasattr(resolve_routing_policy, 'counter'):
            #         resolve_routing_policy.counter = {}
            #     
            #     if hostname not in resolve_routing_policy.counter:
            #         resolve_routing_policy.counter[hostname] = 0
            #     
            #     index = resolve_routing_policy.counter[hostname] % len(proxy_map)
            #     resolve_routing_policy.counter[hostname] += 1
            #     
            #     backend = proxy_map[index]
            #     proxy_host, proxy_port = backend.split(":", 2)
            # ============================================================
            
            # ========== SRTF (Shortest Remaining Time First) ALGORITHM ==========
            if policy in ['srtf', 'shortest-time']:
                # Initialize tracking structures
                if not hasattr(resolve_routing_policy, 'response_times'):
                    resolve_routing_policy.response_times = {}
                if not hasattr(resolve_routing_policy, 'request_count'):
                    resolve_routing_policy.request_count = {}
                
                # Initialize for this hostname if needed
                if hostname not in resolve_routing_policy.response_times:
                    resolve_routing_policy.response_times[hostname] = {}
                    resolve_routing_policy.request_count[hostname] = {}
                    # Initialize all backends with default time (0.1s)
                    for backend in proxy_map:
                        resolve_routing_policy.response_times[hostname][backend] = 0.1
                        resolve_routing_policy.request_count[hostname][backend] = 0
                
                # Find backend with shortest average response time
                shortest_time = float('inf')
                best_backend = proxy_map[0]  # fallback to first backend
                
                for backend in proxy_map:
                    avg_time = resolve_routing_policy.response_times[hostname].get(backend, 0.1)
                    if avg_time < shortest_time:
                        shortest_time = avg_time
                        best_backend = backend
                
                proxy_host, proxy_port = best_backend.split(":", 2)
                
                print("[Proxy] SRTF selected {} (avg response time: {:.3f}s)".format(
                    best_backend, shortest_time))
            # ====================================================================
            else:
                # Out-of-handle mapped host or unsupported policy
                print("[Proxy] Unsupported policy '{}', using fallback".format(policy))
                proxy_host = '127.0.0.1'
                proxy_port = '9000'
    else:
        print("[Proxy] resolve route of hostname {} is a singulair to".format(hostname))
        proxy_host, proxy_port = proxy_map.split(":", 2)

    # Normalize port to integer where possible; fallback to 9000
    try:
        proxy_port = int(proxy_port)
    except Exception:
        try:
            # in case port contains extra parts
            proxy_port = int(str(proxy_port).split(':')[-1])
        except Exception:
            proxy_port = 9000

    return proxy_host, proxy_port, headers

def handle_client(ip, port, conn, addr, routes):
    """
    Handles an individual client connection by parsing the request,
    determining the target backend, and forwarding the request.

    The handler extracts the Host header from the request to
    matches the hostname against known routes. In the matching
    condition,it forwards the request to the appropriate backend.

    The handler sends the backend response back to the client or
    returns 404 if the hostname is unreachable or is not recognized.

    :params ip (str): IP address of the proxy server.
    :params port (int): port number of the proxy server.
    :params conn (socket.socket): client connection socket.
    :params addr (tuple): client address (IP, port).
    :params routes (dict): dictionary mapping hostnames and location.
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

    print("[Proxy] {} at Host: {}".format(addr, hostname))

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
        print("[Proxy] Listening on IP {} port {}".format(ip,port))
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
