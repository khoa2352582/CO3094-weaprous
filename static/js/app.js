// ============================================
// TEAM IMPLEMENTATION - TASK 2: P2P CHAT CLIENT
// Client-side JavaScript for hybrid P2P chat application
// Features:
// - Peer registration with tracker
// - P2P handshake protocol for first contact
// - Direct peer-to-peer messaging
// - Auto re-registration when tracker restarts
// - Message polling for incoming messages
// ============================================

// WeApRous P2P Chat Client
(function () {
  const trackerBase =
    window.TRACKER_BASE ||
    window.location.protocol + "//" + window.location.hostname + ":8000";
  const $ = (id) => document.getElementById(id);

  // Store known peer connections (peers we've already contacted)
  const knownPeers = new Map(); // {peerId -> {ip, port}}
  let myIp, myPort;

  // ============================================
  // REGISTER: Register this peer with tracker
  // Called on initial connection and when tracker restarts
  // ============================================
  async function register() {
    myIp = window.location.hostname;
    myPort = $("port").value || "9001";
    const name = $("username").value || "guest";

    try {
      const body = `ip=${encodeURIComponent(myIp)}&port=${encodeURIComponent(
        myPort
      )}`;
      const res = await fetch(trackerBase + "/submit-info", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body,
      });
      const data = await res.json();
      if (data.status === "ok") {
        appendMessage("System", `Registered as ${name} (${myIp}:${myPort})`);
        $("btnRegister").disabled = true;
        $("port").disabled = true;
        $("username").disabled = true;

        // Start peer list updates (check for new peers every 5 seconds)
        updatePeerList();
        setInterval(updatePeerList, 5000);

        // Enable chat interface
        $("peerSelect").disabled = false;
        $("messageInput").disabled = false;
        $("btnSend").disabled = false;

        // Start polling for incoming messages (check every 2 seconds)
        setInterval(pollForMessages, 2000);
      }
    } catch (e) {
      console.error("Registration failed:", e);
      appendMessage("System", "Registration failed: " + e.message);
    }
  }

  // ============================================
  // CHECK PEER ONLINE: Query tracker for peer status
  // Used before first contact to ensure peer is available
  // ============================================
  async function checkPeerOnline(peerId) {
    try {
      const res = await fetch(`${trackerBase}/get-list`);
      const data = await res.json();
      if (data.status === "ok") {
        const peer = data.peers && data.peers[peerId];
        if (peer) {
          return { status: "ok", online: true, ip: peer.ip, port: peer.port };
        }
        return { status: "ok", online: false };
      }
      return null;
    } catch (e) {
      console.error("Check peer failed:", e);
      return null;
    }
  }

  // ============================================
  // FIRST MESSAGE: P2P Handshake Protocol
  // Send first message with is_first=true to initiate P2P connection
  // Receiver responds with their info for direct communication
  // ============================================
  async function sendFirstMessage(peerIp, peerPort, message) {
    try {
      const url = `http://${peerIp}:${peerPort}/send-peer`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_ip: myIp,
          from_port: myPort,
          message: message,
          is_first: true, // Handshake flag
        }),
      });

      const data = await res.json();
      if (data.status === "ok" && data.request_info) {
        // Store peer info for future direct communication
        const peerId = `${peerIp}:${peerPort}`;
        knownPeers.set(peerId, { ip: peerIp, port: peerPort });
        appendMessage("System", `Connected to peer ${peerId}`);
        return true;
      }
    } catch (e) {
      console.error("First message failed:", e);
      return false;
    }
  }

  // ============================================
  // DIRECT MESSAGE: P2P Communication
  // Send direct message to already-known peer (after handshake)
  // ============================================
  async function sendDirectMessage(peerIp, peerPort, message) {
    try {
      const url = `http://${peerIp}:${peerPort}/send-peer`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_ip: myIp,
          from_port: myPort,
          message: message,
          is_first: false, // Not a handshake
        }),
      });
      return await res.json();
    } catch (e) {
      console.error("Direct message failed:", e);
      return null;
    }
  }

  // ============================================
  // SEND MESSAGE: Main message sending logic
  // Handles both first contact (handshake) and subsequent messages
  // Supports broadcast mode to send to all peers
  // ============================================
  async function sendMessage() {
    const msgInput = $("messageInput");
    const msg = msgInput.value.trim();
    if (!msg) return;

    const targetPeer = $("peerSelect").value;
    if (!targetPeer) {
      appendMessage("System", "Please select a peer first");
      return;
    }

    // Broadcast mode: Send to all peers
    if (targetPeer === "broadcast") {
      appendMessage("Me (Broadcast)", msg);
      msgInput.value = "";

      const select = $("peerSelect");
      for (let i = 0; i < select.options.length; i++) {
        const opt = select.options[i];
        const peerId = opt.value;

        // Skip non-peer options (like "Select..." and "broadcast")
        if (peerId && peerId !== "broadcast") {
          const [peerIp, peerPort] = peerId.split(":");

          // Send to each peer (handshake if first contact, direct if known)
          if (!knownPeers.has(peerId)) {
            console.log(`Broadcasting (first contact) to ${peerId}`);
            await sendFirstMessage(peerIp, peerPort, msg);
          } else {
            console.log(`Broadcasting (direct) to ${peerId}`);
            await sendDirectMessage(peerIp, peerPort, msg);
          }
        }
      }
      return;
    }

    // Single peer mode
    const [peerIp, peerPort] = targetPeer.split(":");

    // Check if we already know this peer
    if (!knownPeers.has(targetPeer)) {
      // First contact - check if peer is online
      const peerStatus = await checkPeerOnline(targetPeer);
      if (!peerStatus || !peerStatus.online) {
        appendMessage("System", `Peer ${targetPeer} is not online`);
        return;
      }

      // Send first message with handshake
      const success = await sendFirstMessage(peerIp, peerPort, msg);
      if (!success) {
        appendMessage(
          "System",
          `Failed to establish connection with ${targetPeer}`
        );
        return;
      }
    } else {
      // Direct P2P message
      const result = await sendDirectMessage(peerIp, peerPort, msg);
      if (!result || result.status !== "ok") {
        appendMessage("System", `Failed to send message to ${targetPeer}`);
        return;
      }
    }

    appendMessage("Me", msg);
    msgInput.value = "";
  }

  // ============================================
  // POLL FOR MESSAGES: Check for incoming messages
  // Queries local P2P server for messages received from other peers
  // Runs every 2 seconds to keep chat updated
  // ============================================
  async function pollForMessages() {
    const url = `http://${myIp}:${myPort}/messages`;

    try {
      const res = await fetch(url);
      const data = await res.json();

      // Display new messages
      if (data.messages && data.messages.length > 0) {
        data.messages.forEach((msg) => {
          const senderId = `${msg.from_ip}:${msg.from_port}`;
          appendMessage(`Peer ${senderId}`, msg.message);
        });
      }
    } catch (e) {
      // Ignore errors (e.g., server not ready), polling will retry automatically
      console.warn("Polling error:", e.message);
    }
  }

  // ============================================
  // APPEND MESSAGE: Display message in chat UI
  // ============================================
  function appendMessage(sender, text) {
    const box = $("messages");
    const el = document.createElement("div");
    const time = new Date().toLocaleTimeString();
    el.className = "message";
    el.innerHTML = `
      <span class="time">[${time}]</span>
      <span class="sender">${sender}</span>: 
      <span class="text">${text}</span>
    `;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
  }

  // ============================================
  // UPDATE PEER LIST: Fetch active peers from tracker
  // Auto-detects tracker restart and re-registers if needed
  // Runs every 5 seconds to keep peer list current
  // ============================================
  async function updatePeerList() {
    try {
      const res = await fetch(`${trackerBase}/get-list`);
      const data = await res.json();
      if (data.status === "ok") {
        const peersObject = data.peers || {};
        const peerIdList = Object.keys(peersObject);

        // Check if we think we're registered
        const isRegistered = $("btnRegister").disabled;
        const myPeerId = `${myIp}:${myPort}`;

        // Auto re-registration: If we're registered but not in tracker list,
        // tracker must have restarted. Re-register automatically.
        if (isRegistered && myPeerId && !peersObject.hasOwnProperty(myPeerId)) {
          console.warn(
            `Tracker list does not contain me (${myPeerId}). Re-registering...`
          );
          appendMessage("System", "Tracker reset detected. Re-connecting...");

          // Unlock UI for re-registration
          $("btnRegister").disabled = false;
          $("port").disabled = false;
          $("username").disabled = false;

          // Auto re-register
          await register();
          return;
        }

        // Update peer select dropdown
        const select = $("peerSelect");
        const previous = select ? select.value : ""; // Preserve selection
        select.innerHTML =
          '<option value="">Select a peer to chat with...</option>';

        const sortedPeers = peerIdList
          .map((id) => ({ id, ...peersObject[id] }))
          .sort((a, b) => b.last_seen - a.last_seen);

        // Add broadcast option
        const broadcastOpt = document.createElement("option");
        broadcastOpt.value = "broadcast";
        broadcastOpt.textContent = "== BROADCAST TO ALL ==";
        select.appendChild(broadcastOpt);

        // Add peers (excluding ourselves)
        sortedPeers.forEach((peer) => {
          if (peer.id !== myPeerId) {
            const opt = document.createElement("option");
            opt.value = peer.id;
            opt.textContent = `Peer at ${peer.id}`;
            select.appendChild(opt);
          }
        });

        // Restore previous selection if still available
        if (previous) {
          const found = Array.from(select.options).some(
            (o) => o.value === previous
          );
          if (found) select.value = previous;
        }
      }
    } catch (e) {
      console.error("Update peer list failed:", e);
    }
  }

  // ============================================
  // EVENT LISTENERS: Set up UI interactions
  // ============================================
  window.addEventListener("load", () => {
    $("btnRegister").addEventListener("click", register);
    $("btnSend").addEventListener("click", sendMessage);
    $("messageInput").addEventListener("keypress", (e) => {
      if (e.key === "Enter") sendMessage();
    });
  });
})();
