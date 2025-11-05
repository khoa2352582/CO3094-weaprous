// Simple client script for the WeApRous sample chat
(function(){
  const trackerBase = window.TRACKER_BASE || (window.location.protocol + '//' + window.location.hostname + ':8000');

  const $ = id => document.getElementById(id);

  async function register() {
    const name = $('username').value || 'guest';
    const port = $('port').value || '9001';
    const ip = window.location.hostname;

    try {
      const body = `ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`;
      const res = await fetch(trackerBase + '/register', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: body,
      });
      const txt = await res.text();
      console.log('register result', txt);
      appendMessage('system', 'Registered with tracker');
      await refreshPeers();
    } catch (e) {
      console.error('register failed', e);
      appendMessage('system', 'Register failed: ' + e.message);
    }
  }

  async function refreshPeers() {
    try {
      const res = await fetch(trackerBase + '/get-peers');
      const txt = await res.text();
      const obj = JSON.parse(txt);
      const list = obj.peers || [];
      renderPeers(list);
    } catch (e) {
      console.error('get-peers failed', e);
      appendMessage('system', 'get-peers failed: ' + e.message);
    }
  }

  function renderPeers(peers) {
    const ul = $('peerList');
    ul.innerHTML = '';
    peers.forEach(p => {
      const li = document.createElement('li');
      li.textContent = `${p.ip}:${p.port}`;
      ul.appendChild(li);
    });
  }

  function appendMessage(sender, text) {
    const box = $('messages');
    const el = document.createElement('div');
    el.innerHTML = `<strong>${sender}</strong>: ${text}`;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
  }

  async function sendMessage() {
    const msg = $('messageInput').value;
    if (!msg) return;
    appendMessage('me', msg);
    // broadcast to peers via HTTP POST to /send-peer (best-effort)
    try {
      const res = await fetch(trackerBase + '/get-peers');
      const txt = await res.text();
      const obj = JSON.parse(txt);
      const peers = obj.peers || [];
      peers.forEach(async p => {
        try {
          const url = `http://${p.ip}:${p.port}/send-peer`;
          await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: `from=${encodeURIComponent(window.location.hostname)}&msg=${encodeURIComponent(msg)}`
          });
        } catch (e) {
          console.debug('send to peer failed', p, e.message);
        }
      });
    } catch (e) {
      console.error('broadcast failed', e);
    }
    $('messageInput').value = '';
  }

  // wire UI
  window.addEventListener('load', () => {
    $('btnRegister').addEventListener('click', register);
    $('btnRefresh').addEventListener('click', refreshPeers);
    $('btnSend').addEventListener('click', sendMessage);
  });

})();
