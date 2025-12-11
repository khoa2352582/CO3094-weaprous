# Đồ án Mạng Máy Tính: HTTP Server & Chat Hybrid

Đây là hướng dẫn đầy đủ để cài đặt, chạy và kiểm tra cả hai phần của đồ án trên môi trường **Máy ảo Linux**.

## 📋 Yêu cầu

* **Trên Máy ảo:** Python 3.x
* **Trên Máy thật (Windows/Mac):**
    * Công cụ test API như **Postman** (cho Task 1)
    * Trình duyệt web (Chrome, Firefox...) (cho Task 2)
* **Cấu hình mạng:** Máy ảo nên để chế độ **Bridged Adapter** để có IP riêng.

---

## ⚙️ Cấu hình (Bước đầu tiên quan trọng!)

Trước khi chạy, bạn cần biết địa chỉ IP của máy ảo.

1.  Mở terminal trên máy ảo, chạy lệnh:
    ```bash
    ifconfig
    ```
    *(Ghi lại địa chỉ IP, ví dụ: `192.168.1.50`. Trong bài hướng dẫn này, chúng ta gọi nó là `<IP_MAY_AO>`)*.

2.  Sửa file `config/proxy.conf`:
    Thay thế tất cả `127.0.0.1` bằng `<IP_MAY_AO>` của bạn.
    
    **Ví dụ (nếu IP là 192.168.1.50):**
    ```conf
   host "192.168.1.50:8080" {
    proxy_pass http://192.168.1.50:9000;

    dist_policy srtf;

    }
host "app1.local" {
    proxy_pass http://192.168.1.50:9001;
}
host "app2.local" {
    proxy_set_header Host $host;
    
    proxy_pass http://192.168.1.50:9002;  # Sửa cả những IP này
    dist_policy round-robin;
}

---

## 🚀 Task 1: Kiểm tra Máy chủ HTTP & Cookie Session
*(Các file liên quan: backend.py, httpadapter.py, proxy.py, request.py, respone.py, proxy.conf, index.html, styles.css)*

Phần này kiểm tra xem máy chủ có bảo vệ trang web và cấp cookie khi đăng nhập đúng hay không.

### Bước 1: Chạy 2 Terminal trên Máy ảo

**Lưu ý:** Chúng ta dùng `--server-ip 0.0.0.0` để chấp nhận kết nối từ máy thật.

* **Terminal 1 (Backend):**
    ```bash
    # (Đảm bảo bạn đang ở trong thư mục dự án)
    python3 start_backend.py --server-ip 0.0.0.0 --server-port 9000
    ```
    *Log mong đợi:* `[Backend] Listening on port 9000`

* **Terminal 2 (Proxy):**
    ```bash
    # (Đảm bảo bạn đang ở trong thư mục dự án)
    python3 start_proxy.py --server-ip 0.0.0.0 --server-port 8080
    ```
    *Log mong đợi:* `[Proxy] Listening on IP 0.0.0.0 port 8080`

### Bước 2: Dùng Postman trên Máy thật để kiểm tra

Mở Postman trên Windows/Mac và thực hiện test với IP của máy ảo.

1.  **Test 1 (Truy cập thất bại):**
    * Method: `GET`
    * URL: `http://<IP_MAY_AO>:8080/index.html` (Ví dụ: `http://192.168.1.50:8080/index.html`)
    * **Kết quả:** Status `401 Unauthorized`.

2.  **Test 2 (Đăng nhập thành công):**
    * Method: `POST`
    * URL: `http://<IP_MAY_AO>:8080/login`
    * Body: `x-www-form-urlencoded` -> `username`: `admin`, `password`: `password`
    * **Kết quả:** Status `200 OK`. (Cookie `auth=true` được lưu).

3.  **Test 3 (Truy cập thành công):**
    * Method: `GET`
    * URL: `http://<IP_MAY_AO>:8080/index.html`
    * **Kết quả:** Status `200 OK`.

---

## 💬 Task 2: Chạy Ứng dụng Chat Hybrid (P2P)
*(Các file liên quan: weaprous.py, index.html, styles.css, app.js, start_sampleapp.py)*

Phần này chạy hệ thống chat P2P. Bạn có thể tắt các terminal của Task 1 đi.

### Bước 1: Chạy 4 Terminal trên Máy ảo

Sử dụng `--server-ip 0.0.0.0` cho tất cả các lệnh để các máy khác có thể kết nối.

* **Terminal 1 (File Server - Phục vụ Web):**
    ```bash
    python3 start_backend.py --server-ip 0.0.0.0 --server-port 8080
    ```

* **Terminal 2 (Tracker Server - Máy chủ trung tâm):**
    ```bash
    python3 start_sampleapp.py --server-ip 0.0.0.0 --server-port 8000
    ```

* **Terminal 3 (Peer A - Người dùng 1):**
    ```bash
    python3 start_sampleapp.py --server-ip 0.0.0.0 --server-port 9001
    ```

* **Terminal 4 (Peer B - Người dùng 2):**
    ```bash
    python3 start_sampleapp.py --server-ip 0.0.0.0 --server-port 9002
    ```

### Bước 2: Mở Trình duyệt trên Máy thật

Mở trình duyệt (Chrome/Edge/Firefox) trên máy tính thật của bạn.

1.  **Tab 1 (Dành cho Peer A):**
    * Truy cập: `http://<IP_MAY_AO>:8080`
    * **Your IP:** Nhập `<IP_MAY_AO>` (Ví dụ: `192.168.1.50`). **Rất quan trọng!**
    * **Your Port:** `9001`
    * **Name:** Peer A
    * Nhấn **Register**.

2.  **Tab 2 (Dành cho Peer B):**
    * Truy cập: `http://<IP_MAY_AO>:8080`
    * **Your IP:** Nhập `<IP_MAY_AO>` (Vẫn là IP máy ảo đó).
    * **Your Port:** `9002`
    * **Name:** Peer B
    * Nhấn **Register**.

### Bước 3: Chat P2P

* Quay lại Tab 1. Trong danh sách Peer, bạn sẽ thấy Peer B.
* Gửi tin nhắn và kiểm tra bên Tab 2.
* Thử tính năng **BROADCAST TO ALL**.
* Thử tắt Terminal 2 (Tracker 8000) để kiểm chứng chat P2P vẫn hoạt động.