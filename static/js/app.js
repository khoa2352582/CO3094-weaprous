// WeApRous P2P Chat Client
(function(){
  const trackerBase = window.TRACKER_BASE || (window.location.protocol + '//' + window.location.hostname + ':8000');
  const $ = id => document.getElementById(id);
  
  // Store known peer connections
  const knownPeers = new Map(); // {peerId -> {ip, port}}
  let myIp, myPort;

  async function register() {
    myIp = window.location.hostname;
    myPort = $('port').value || '9001';
    const name = $('username').value || 'guest';

    try {
      const body = `ip=${encodeURIComponent(myIp)}&port=${encodeURIComponent(myPort)}`;
      const res = await fetch(trackerBase + '/submit-info', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: body
      });
      const data = await res.json();
      if (data.status === 'ok') {
        appendMessage('System', `Registered as ${name} (${myIp}:${myPort})`);
        $('btnRegister').disabled = true;
        $('port').disabled = true;
        $('username').disabled = true;
        
        // Start updating peer list immediately and periodically
        updatePeerList();
        setInterval(updatePeerList, 5000);
        
        // Enable chat interface
        $('peerSelect').disabled = false;
        $('messageInput').disabled = false;
        $('btnSend').disabled = false;
        // ===== THÊM DÒNG NÀY =====
    // Bắt đầu tự động kiểm tra tin nhắn mới mỗi 2 giây
        setInterval(pollForMessages, 2000);
      }
    } catch (e) {
      console.error('Registration failed:', e);
      appendMessage('System', 'Registration failed: ' + e.message);
    }
  }

  async function checkPeerOnline(peerId) {
    try {
      // Use get-peers and look up the peerId
      const res = await fetch(`${trackerBase}/get-list`);
      const data = await res.json();
      if (data.status === 'ok') {
        const peer = data.peers && data.peers[peerId];
        if (peer) {
          return { status: 'ok', online: true, ip: peer.ip, port: peer.port };
        }
        return { status: 'ok', online: false };
      }
      return null;
    } catch (e) {
      console.error('Check peer failed:', e);
      return null;
    }
  }

  async function sendFirstMessage(peerIp, peerPort, message) {
    try {
      const url = `http://${peerIp}:${peerPort}/send-peer`;
      const res = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          from_ip: myIp,
          from_port: myPort,
          message: message,
          is_first: true
        })
      });
      
      const data = await res.json();
      if (data.status === 'ok' && data.request_info) {
        // Store peer info for future direct communication
        const peerId = `${peerIp}:${peerPort}`;
        knownPeers.set(peerId, { ip: peerIp, port: peerPort });
        appendMessage('System', `Connected to peer ${peerId}`);
        return true;
      }
    } catch (e) {
      console.error('First message failed:', e);
      return false;
    }
  }

  async function sendDirectMessage(peerIp, peerPort, message) {
    try {
      const url = `http://${peerIp}:${peerPort}/send-peer`;
      const res = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          from_ip: myIp,
          from_port: myPort,
          message: message,
          is_first: false
        })
      });
      return await res.json();
    } catch (e) {
      console.error('Direct message failed:', e);
      return null;
    }
  }

  async function sendMessage() {
    const msgInput = $('messageInput');
    const msg = msgInput.value.trim();
    if (!msg) return;

    const targetPeer = $('peerSelect').value;
    if (!targetPeer) {
      appendMessage('System', 'Please select a peer first');
      return;
    }
    if (targetPeer === "broadcast") {
        // Gửi tin nhắn cho TẤT CẢ peer trong danh sách
        appendMessage('Me (Broadcast)', msg);
        msgInput.value = '';
        
        const select = $('peerSelect');
        for (let i = 0; i < select.options.length; i++) {
            const opt = select.options[i];
            const peerId = opt.value;
            
            // Bỏ qua các tùy chọn không phải là peer (như "Select..." và "broadcast")
            if (peerId && peerId !== "broadcast") {
                const [peerIp, peerPort] = peerId.split(':');
                
                // (Chúng ta copy-paste logic gửi tin nhắn từ bên dưới)
                if (!knownPeers.has(peerId)) {
                    // Liên hệ lần đầu
                    console.log(`Broadcasting (first contact) to ${peerId}`);
                    await sendFirstMessage(peerIp, peerPort, msg);
                } else {
                    // Liên hệ trực tiếp (đã quen)
                    console.log(`Broadcasting (direct) to ${peerId}`);
                    await sendDirectMessage(peerIp, peerPort, msg);
                }
            }
        }
        return; // Kết thúc sau khi gửi broadcast
    }
    const [peerIp, peerPort] = targetPeer.split(':');
    
    // Check if we already know this peer
    if (!knownPeers.has(targetPeer)) {
      // First contact - check if peer is online
      const peerStatus = await checkPeerOnline(targetPeer);
      if (!peerStatus || !peerStatus.online) {
        appendMessage('System', `Peer ${targetPeer} is not online`);
        return;
      }

      // Send first message with our info
      const success = await sendFirstMessage(peerIp, peerPort, msg);
      if (!success) {
        appendMessage('System', `Failed to establish connection with ${targetPeer}`);
        return;
      }
    } else {
      // Direct P2P message
      const result = await sendDirectMessage(peerIp, peerPort, msg);
      if (!result || result.status !== 'ok') {
        appendMessage('System', `Failed to send message to ${targetPeer}`);
        return;
      }
    }

    appendMessage('Me', msg);
    msgInput.value = '';
  }
  async function pollForMessages() {
    // Client này gọi API /messages của chính máy chủ P2P của nó
    // để kiểm tra xem có ai gửi tin nhắn cho nó không.
    const url = `http://${myIp}:${myPort}/messages`; 

    try {
        const res = await fetch(url);
        const data = await res.json();

        // Nếu có tin nhắn mới, hiển thị chúng
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                const senderId = `${msg.from_ip}:${msg.from_port}`;
                // Dùng hàm appendMessage đã có sẵn
                appendMessage(`Peer ${senderId}`, msg.message); 
            });
        }
    } catch (e) {
        // Bỏ qua lỗi (ví dụ: máy chủ chưa sẵn sàng),
        // vòng lặp sẽ tự động thử lại
        console.warn("Polling error:", e.message);
    }
}
  function appendMessage(sender, text) {
    const box = $('messages');
    const el = document.createElement('div');
    const time = new Date().toLocaleTimeString();
    el.className = 'message';
    el.innerHTML = `
      <span class="time">[${time}]</span>
      <span class="sender">${sender}</span>: 
      <span class="text">${text}</span>
    `;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
  }

  async function updatePeerList() {
    try {
      const res = await fetch(`${trackerBase}/get-list`);
      const data = await res.json();
      if (data.status === 'ok') {
        const peersObject = data.peers || {}; // Lấy object
        const peerIdList = Object.keys(peersObject); // Lấy danh sách key (ID)
        
        // Kiểm tra xem client "nghĩ" là nó đã đăng ký chưa
        const isRegistered = $('btnRegister').disabled;
        const myPeerId = `${myIp}:${myPort}`;

        
        // Logic mới: Nếu tôi "nghĩ" là tôi đã đăng ký (isRegistered = true)
        // NHƯNG danh sách từ Tracker không chứa ID của tôi
        // -> Tracker đã khởi động lại. Tôi cần đăng ký lại.
        if (isRegistered && myPeerId && !peersObject.hasOwnProperty(myPeerId)) {
            
            console.warn(`Tracker list does not contain me (${myPeerId}). Re-registering...`);
            appendMessage('System', 'Tracker reset detected. Re-connecting...');
            
            // Mở khóa UI để hàm register() có thể chạy
            $('btnRegister').disabled = false;
            $('port').disabled = false;
            $('username').disabled = false;
            
            // Tự động gọi lại hàm register()
            await register(); 
            
            // Dừng hàm này ngay lập tức, register() sẽ lo phần còn lại
            return; 
        }
        const select = $('peerSelect');
        // preserve current selection so a user doesn't lose their choice while typing
        const previous = select ? select.value : '';
        select.innerHTML = '<option value="">Select a peer to chat with...</option>';
        
        // Dùng peerIdList để tạo sortedPeers
        const sortedPeers = peerIdList
          .map(id => ({ id, ...peersObject[id] })) // Chuyển object thành array
          .sort((a, b) => b.last_seen - a.last_seen);
          //broadcast option
        const broadcastOpt = document.createElement('option');
        broadcastOpt.value = "broadcast";
        broadcastOpt.textContent = "== BROADCAST TO ALL ==";
        select.appendChild(broadcastOpt);
        // Add peers to select, excluding ourselves
      
        sortedPeers.forEach(peer => {
          if (peer.id !== myPeerId) { // So sánh bằng ID 'ip:port'
            const opt = document.createElement('option');
            opt.value = peer.id; // giá trị là ID
            opt.textContent = `Peer at ${peer.id}`;
            select.appendChild(opt);
          }
        });

        // Restore previous selection if still available
        if (previous) {
          const found = Array.from(select.options).some(o => o.value === previous);
          if (found) select.value = previous;
        }
        
        // Update UI if no peers available
        if (select.options.length <= 2 ) { // Only the default option
          if (isRegistered) { // Chỉ hiển thị nếu chúng ta thực sự đăng ký
             //appendMessage('System', 'No other peers online');
           }
        }
      }
    }
     catch (e) {
      console.error('Update peer list failed:', e);
      // appendMessage('System', 'Failed to get peer list: ' + e.message);
    }
  }

  // Set up UI event listeners
  window.addEventListener('load', () => {
    $('btnRegister').addEventListener('click', register);
    $('btnSend').addEventListener('click', sendMessage);
    $('messageInput').addEventListener('keypress', e => {
      if (e.key === 'Enter') sendMessage();
    });
    
  });

})();
