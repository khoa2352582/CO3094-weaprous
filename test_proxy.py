# test_proxy.py
#
# Script để test proxy server
#

import socket
import time

def test_proxy(host, port, target_host, path="/"):
    """
    Test proxy server by sending a simple HTTP request.
    
    :param host: Proxy server IP
    :param port: Proxy server port
    :param target_host: Target hostname for Host header
    :param path: Request path
    """
    try:
        # Tạo socket connection
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))
        
        # Tạo HTTP request
        request = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}\r\n"
            "User-Agent: ProxyTestClient/1.0\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).format(path, target_host)
        
        print("[Test] Sending request to proxy {}:{}".format(host, port))
        print("[Test] Target host: {}".format(target_host))
        print("[Test] Request:\n{}".format(request))
        
        # Gửi request
        client.sendall(request.encode())
        
        # Nhận response
        response = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response += chunk
        
        print("[Test] Response received ({} bytes):".format(len(response)))
        print(response.decode('utf-8', errors='ignore'))
        
        client.close()
        return True
        
    except Exception as e:
        print("[Test] Error: {}".format(e))
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Proxy Server")
    print("=" * 60)
    
    # Test 1: Direct IP:Port mapping
    print("\n--- Test 1: 192.168.56.103:8080 ---")
    test_proxy("127.0.0.1", 8080, "192.168.56.103:8080", "/")
    
    time.sleep(1)
    
    # Test 2: app1.local
    print("\n--- Test 2: app1.local ---")
    test_proxy("127.0.0.1", 8080, "app1.local", "/")
    
    time.sleep(1)
    
    # Test 3: app2.local (with SRTF load balancing)
    print("\n--- Test 3: app2.local (SRTF test 1) ---")
    test_proxy("127.0.0.1", 8080, "app2.local", "/")
    
    time.sleep(1)
    
    print("\n--- Test 4: app2.local (SRTF test 2) ---")
    test_proxy("127.0.0.1", 8080, "app2.local", "/")
    
    time.sleep(1)
    
    print("\n--- Test 5: app2.local (SRTF test 3) ---")
    test_proxy("127.0.0.1", 8080, "app2.local", "/")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
