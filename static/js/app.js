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
      const res = await fetch(trackerBase + '/register', {
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
      }
    } catch (e) {
      console.error('Registration failed:', e);
      appendMessage('System', 'Registration failed: ' + e.message);
    }
  }

  async function checkPeerOnline(peerId) {
    try {
      // Use get-peers and look up the peerId
      const res = await fetch(`${trackerBase}/get-peers`);
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
      const res = await fetch(`${trackerBase}/get-peers`);
      const data = await res.json();
      if (data.status === 'ok') {
        const select = $('peerSelect');
        // preserve current selection so a user doesn't lose their choice while typing
        const previous = select ? select.value : '';
        select.innerHTML = '<option value="">Select a peer to chat with...</option>';
        
        // Sort peers by last seen time (most recent first)
        const peers = Object.entries(data.peers || {})
          .map(([id, info]) => ({ id, ...info }))
          .sort((a, b) => b.last_seen - a.last_seen);
        
        // Add peers to select, excluding ourselves
        peers.forEach(peer => {
          if (String(peer.port) !== String(myPort) || peer.ip !== myIp) {
            const opt = document.createElement('option');
            opt.value = `${peer.ip}:${peer.port}`;
            opt.textContent = `Peer at ${peer.ip}:${peer.port}`;
            select.appendChild(opt);
          }
        });

        // Restore previous selection if still available
        if (previous) {
          const found = Array.from(select.options).some(o => o.value === previous);
          if (found) select.value = previous;
        }
        
        // Update UI if no peers available
        if (select.options.length === 1) { // Only the default option
          appendMessage('System', 'No other peers online');
        }
      }
    } catch (e) {
      console.error('Update peer list failed:', e);
      appendMessage('System', 'Failed to get peer list: ' + e.message);
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
