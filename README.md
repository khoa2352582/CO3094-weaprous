<<<<<<< HEAD
# Đồ án Mạng Máy Tính: HTTP Server & Chat Hybrid

Đây là hướng dẫn đầy đủ để cài đặt, chạy và kiểm tra cả hai phần của đồ án.

## Yêu cầu

* Python 3.x
* Một công cụ test API như **Postman** (rất quan trọng cho Task 1)
* Một trình duyệt web hiện đại (Chrome, Firefox...) (cho Task 2)

## Cấu hình (Rất quan trọng!)

Toàn bộ dự án này được thiết kế để chạy trên máy cục bộ của bạn (`127.0.0.1` hay `localhost`).

Trước khi chạy bất cứ thứ gì, hãy đảm bảo file `config/proxy.conf` của bạn đã được cấu hình để trỏ đến `127.0.0.1`.

**File `config/proxy.conf` phải trông như thế này:**
```conf
host "127.0.0.1:8080" {
    proxy_pass [http://127.0.0.1:9000](http://127.0.0.1:9000);
}

host "app1.local" {
    proxy_pass [http://127.0.0.1:9001](http://127.0.0.1:9001);
}
## Nếu chạy bằng máy ảo hãy ifconfig để lấy ip máy ảo và thay thế 127.0.0.1
# ... và các host khác cũng trỏ về 127.0.0.1 ...
🚀 Task 1: Kiểm tra Máy chủ HTTP & Cookie Session (backend.py, httpadapter.py, proxy.py, request.py, respone.py, proxy.conf, index va css)
Phần này kiểm tra xem máy chủ có bảo vệ trang index.html và cấp cookie khi đăng nhập đúng hay không.

Bước 1: Chạy 2 Terminal
Bạn cần 2 cửa sổ terminal đang chạy.

Terminal 1 (Backend):

Bash

# (Đảm bảo bạn đang ở trong thư mục dự án)
python3 start_backend.py --server-ip 127.0.0.1 --server-port 9000
Kết quả mong đợi: [Backend] Listening on port 9000

Terminal 2 (Proxy):

Bash

# (Đảm bảo bạn đang ở trong thư mục dự án)
python3 start_proxy.py --server-ip 127.0.0.1 --server-port 8080
Kết quả mong đợi: [Proxy] Listening on IP 127.0.0.1 port 8080

Bước 2: Dùng Postman để Kiểm tra
Mở Postman và thực hiện 3 bài test sau:

Test 1 (Truy cập thất bại):

Method: GET

URL: http://127.0.0.1:8080/index.html

Kết quả: Status: 401 Unauthorized. (Điều này là ĐÚNG)

Test 2 (Đăng nhập thành công):

Method: POST

URL: http://127.0.0.1:8080/login

Tab Body: Chọn x-www-form-urlencoded

Nhập:

username = admin

password = password

Kết quả: Status: 200 OK. Trong tab "Cookies" của phản hồi, bạn sẽ thấy auth=true.

Test 3 (Truy cập thành công):

Quay lại Test 1 (cái GET lúc nãy).

Nhấn Send một lần nữa.

Kết quả: Status: 200 OK. (Vì Postman đã tự động gửi cookie auth=true theo).

💬 Task 2: Chạy Ứng dụng Chat Hybrid (P2P) (weaprous.py, index.html, styles.css, app.js, start_sampleapp.py)
Phần này cho phép nhiều người dùng chat với nhau.

(Lưu ý: Bạn có thể TẮT 2 terminal của Task 1 đi nếu muốn, Task 2 chạy độc lập)

Bước 1: Chạy 4 Terminal (hoặc 3 nếu bạn chat 1-1)
Bạn cần tối thiểu 3 terminal (Tracker, Peer A, Peer B). Chúng ta sẽ dùng 4 terminal để phục vụ file HTML riêng biệt cho rõ ràng.

Terminal 1 (File Server @ 8080):

Nhiệm vụ: Phục vụ index.html và app.js cho trình duyệt.

Bash

python3 start_backend.py --server-ip 127.0.0.1 --server-port 8080
Log: [Backend] Listening on port 8080

Terminal 2 (Tracker Server @ 8000):

Nhiệm vụ: Máy chủ trung tâm để đăng ký và tìm bạn.



python3 start_sampleapp.py --server-ip 127.0.0.1 --server-port 8000
Log: (Backend) Listening on port 8000

Terminal 3 (Peer A @ 9001):

Nhiệm vụ: Lắng nghe tin nhắn P2P cho Peer A.



python3 start_sampleapp.py --server-ip 127.0.0.1 --server-port 9001
Log: (Backend) Listening on port 9001

Terminal 4 (Peer B @ 9002):

Nhiệm vụ: Lắng nghe tin nhắn P2P cho Peer B.



python3 start_sampleapp.py --server-ip 127.0.0.1 --server-port 9002
Log: (Backend) Listening on port 9002

Bước 2: Mở 2 Tab Trình duyệt
Khi cả 4 terminal trên đều đang chạy:

Mở Tab 1 (Peer A):

Truy cập: http://127.0.0.1:8080 (Cổng của File Server).

Đổi tên "guest" thành Peer A.

Quan trọng: Đổi "Your port:" thành 9001 (khớp với Terminal 3).

Nhấn "Register with Tracker".

Mở Tab 2 (Peer B):

Truy cập: http://127.0.0.1:8080

Đổi tên "guest" thành Peer B.

Quan trọng: Đổi "Your port:" thành 9002 (khớp với Terminal 4).

Nhấn "Register with Tracker".

Bước 3: Chat!
Quay lại Tab 1 (Peer A). Trong menu thả xuống, chọn "Peer at 127.0.0.1:9002". Gửi một tin nhắn.

Tin nhắn sẽ xuất hiện ngay lập tức trên Tab 2 (Peer B).

Bạn có thể chat ngược lại, hoặc mở thêm Terminal 5/Tab 3 và test tính năng "BROADCAST TO ALL".
