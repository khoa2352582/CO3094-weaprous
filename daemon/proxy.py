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


def forward_request(host, port, request, custom_headers=None):
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
        #
        # TODO: Apply custom headers if provided (e.g., proxy_set_header directives)
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

        # ===================================================================
        # SỬA LỖI MÃ HÓA (FIX 1)
        # Gửi request bằng 'latin-1' vì nó được decode bằng 'latin-1'
        backend.sendall(request.encode('latin-1'))
        # ===================================================================

        response = b""
        while True:
            chunk = backend.recv(4096)
            if not chunk:
                break
            response += chunk
        return response
    except socket.error as e:
        print("Socket error: {}".format(e))
        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode('utf-8')
    finally:
        backend.close()


def resolve_routing_policy(hostname, routes):
    """
    Handles an routing policy to return the matching proxy_pass.
    (Phiên bản sửa lỗi logic string/list)
    """
    print("[Proxy] Resolving policy for hostname: {}".format(hostname))

    # Cấu hình mặc định (phòng trường hợp config sai)
    default_target = '127.0.0.1:9000'
    default_policy = 'round-robin'
    default_headers = {}
    default_config = ([default_target], default_policy, default_headers)

    config = routes.get(hostname)
    
    if not config:
        print("[Proxy] WARNING: Hostname '{}' not found directly in routes. Using default.".format(hostname))
        config = default_config
    
    if len(config) == 2:
        proxy_map, policy = config
        headers = {}
    else:
        proxy_map, policy, headers = config
    
    print("[Proxy] Route config found: Map={}, Policy={}, Headers={}".format(proxy_map, policy, headers))

    proxy_host = ''
    proxy_port = '9000'
    
    # =================== SỬA LỖI Ở ĐÂY ===================
    # Kiểm tra xem proxy_map là list (nhiều backend) hay string (một backend)
    if isinstance(proxy_map, list):
        # Đây là code cho nhiều backend (như app2.local)
        print("[Proxy] Route is a list (multiple backends).")
        if len(proxy_map) == 0:
            print("[Proxy] Empty resolved routing of hostname {}".format(hostname))
            proxy_host, proxy_port = default_target.split(":", 2)
        elif len(proxy_map) == 1:
            proxy_host, proxy_port = proxy_map[0].split(":", 2)
        else:
            # Xử lý load balancing
            print("[Proxy] Load balancing for: {}".format(hostname))
            if policy == 'round-robin':
                if not hasattr(resolve_routing_policy, 'counter'):
                    resolve_routing_policy.counter = {}
                if hostname not in resolve_routing_policy.counter:
                    resolve_routing_policy.counter[hostname] = 0
                index = resolve_routing_policy.counter[hostname] % len(proxy_map)
                resolve_routing_policy.counter[hostname] += 1
                backend = proxy_map[index]
                proxy_host, proxy_port = backend.split(":", 2)
            else:
                proxy_host, proxy_port = proxy_map[0].split(":", 2)
    else:
        # Đây là trường hợp của bạn: proxy_map là một string (ví dụ: '127.0.0.1:9000')
        print("[Proxy] Route is a single string (singular).")
        proxy_host, proxy_port = proxy_map.split(":", 2)
    # =================== KẾT THÚC SỬA LỖI ===================

    return proxy_host, proxy_port, headers

# ===================================================================
# SỬA LỖI ĐỌC REQUEST (FIX 2)
# Đây là hàm handle_client đã được sửa
def handle_client(ip, port, conn, addr, routes):
    """
    Handles an individual client connection by parsing the request,
    determining the target backend, and forwarding the request.
    (Phiên bản đã sửa lỗi đọc và mã hóa)
    """

    # --- BẮT ĐẦU LOGIC ĐỌC ROBUST ---
    data = b""
    try:
        conn.settimeout(5.0) # Đặt 5 giây timeout
        # Đọc cho đến khi toàn bộ header được nhận
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                conn.close()
                return  # Client ngắt kết nối
            data += chunk
    except socket.error as e:
        print(f"[Proxy] Socket error while reading headers: {e}")
        conn.close()
        return

    conn.settimeout(None) # Tắt timeout

    header_part, sep, body_part = data.partition(b"\r\n\r\n")
    try:
        # Dùng 'latin-1' để KHÔNG BAO GIỜ crash khi decode
        headers_text = header_part.decode('latin-1') 
    except Exception as e:
        print(f"[Proxy] Header decode error: {e}")
        headers_text = "" 

    # Tìm Content-Length để đọc body
    content_length = 0
    for line in headers_text.splitlines():
        if line.lower().startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except:
                content_length = 0
            break

    # Đọc phần body còn lại
    body_bytes = body_part
    remaining = content_length - len(body_bytes)
    try:
        conn.settimeout(5.0) # Đặt timeout cho body
        while remaining > 0:
            chunk = conn.recv(min(remaining, 4096))
            if not chunk:
                break # Client ngắt kết nối sớm
            body_bytes += chunk
            remaining -= len(chunk)
    except socket.error as e:
        print(f"[Proxy] Socket error while reading body: {e}")
        conn.close()
        return

    conn.settimeout(None) 

    # Tái tạo lại request đầy đủ (dưới dạng string 'latin-1')
    try:
        full_request_str = headers_text + "\r\n\r\n" + body_bytes.decode('latin-1')
    except Exception as e:
        print(f"[Proxy] Body decode error: {e}")
        full_request_str = headers_text + "\r\n\r\n"
    # --- KẾT THÚC LOGIC ĐỌC ROBUST ---


    # Trích xuất hostname từ headers_text đã đọc
    hostname = None
    for line in headers_text.splitlines():
        if line.lower().startswith('host:'):
            hostname = line.split(':', 1)[1].strip()
            break 

    if not hostname:
        print(f"[Proxy] {addr} sent a request with no Host header. Closing.")
        response = (
            "HTTP/1.1 400 Bad Request\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 15\r\n"
            "Connection: close\r\n"
            "\r\n"
            "400 Bad Request"
        ).encode('utf-8')
        conn.sendall(response)
        conn.close()
        return

    print("[Proxy] {} at Host: {}".format(addr, hostname))

    # Resolve the matching destination
    resolved_host, resolved_port, custom_headers = resolve_routing_policy(hostname, routes)
    try:
        resolved_port = int(resolved_port)
    except ValueError:
        print(f"[Proxy] Invalid port '{resolved_port}' for host {hostname}. Using 9000.")
        resolved_port = 9000 # Cổng mặc định an toàn

    if resolved_host:
        print("[Proxy] Host name {} is forwarded to {}:{}".format(hostname,resolved_host, resolved_port))

        # Gọi forward_request với request đầy đủ
        response = forward_request(resolved_host, resolved_port, full_request_str, custom_headers)        
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
# ===================================================================


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