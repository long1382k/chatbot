const API_BASE = "http://localhost:8000/v1";
const userId = "longlong";
let currentSessionId = null;
let messages = [];

async function fetchModels() {
  try {
    const res = await fetch(`${API_BASE}/models`);
    const { models } = await res.json();
    const sel = document.getElementById("modelSelect");
    sel.innerHTML = "";
    models.forEach(m => {
      const o = document.createElement("option");
      o.value = m.model_name;
      o.textContent = `${m.description} (${m.type})`;
      sel.appendChild(o);
    });
  } catch {
    alert("Không tải được danh sách models");
  }
}

async function loadConversations() {
  try {
    const res = await fetch(`${API_BASE}/chat/conversations?user_id=${userId}`);
    const convs = await res.json();
    renderConversations(convs);

  } catch (err) {
    console.error("Lỗi load conversations:", err);
  }
}

function renderConversations(convs) {
  const list = document.getElementById("conversationList");
  list.innerHTML = "";
  convs.forEach(c => {
    console.log(c);
    const div = document.createElement("div");
    div.className = "conversation-item";
    if (c.session_id === currentSessionId) div.classList.add("active");
    const date = new Date(c.created_at).toLocaleString();
    div.textContent = `${c.title}`;
    div.onclick = () => selectConversation(c.session_id);
    list.appendChild(div);
  });
}

async function selectConversation(sessionId) {
  currentSessionId = sessionId;
  messages = [];
  document.getElementById("chatBox").innerHTML = "";
  document.querySelectorAll(".conversation-item").forEach(el => {
    el.classList.toggle("active", el.textContent.includes(sessionId));
  });
  try {
    const res = await fetch(`${API_BASE}/chat/conversations/${sessionId}/history?user_id=${userId}`);
    const history = await res.json();
    history.forEach(m => {
      messages.push({ role: m.role, content: m.content });
      renderMessage(m.role, m.content);
    });
  } catch (err) {
    console.error("Lỗi load history:", err);
  }
}

function sendMessage() {
  const input = document.getElementById("userInput");
  const text = input.value.trim();
  if (!text) return;

  const model = document.getElementById("modelSelect").value;
  if (!currentSessionId) {
    currentSessionId = "sess_" + Date.now().toString(36) + "_" + Math.random().toString(36).substr(2, 6);
  }

  messages.push({ role: "user", content: text });
  renderMessage("user", text);
  input.value = "";

  const replyDivId = `reply_${Date.now()}`;
  const chatBox = document.getElementById("chatBox");
  const cont = document.createElement("div");
  cont.className = "message";
  cont.innerHTML = `<div class="assistant">AI:</div><div class="markdown" id="${replyDivId}"></div>`;
  chatBox.appendChild(cont);
  chatBox.scrollTop = chatBox.scrollHeight;

  const es = new EventSourcePolyfill(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": userId,
      "X-Session-ID": currentSessionId
    },
    payload: JSON.stringify({
      model,
      messages,
      temperature: 0.7
    })
  });

  let fullReply = "";
  es.onmessage((evt) => {
    if (evt.data === "[DONE]") {
      messages.push({ role: "assistant", content: fullReply });
      es.close();
      
      return;
    }
    try {
      const d = JSON.parse(evt.data);
      const delta = d.choices?.[0]?.delta?.content
        || d.choices?.[0]?.message?.content
        || d.content || "";
      if (delta) {
        fullReply += delta;
        document.getElementById(replyDivId).innerHTML = marked.parse(fullReply);
        chatBox.scrollTop = chatBox.scrollHeight;
      }
    } catch { }
  });

  es.onerror((err) => {
    console.error("SSE error", err);
    es.close();
  });
  loadConversations()
}

function renderMessage(role, text) {
  const chatBox = document.getElementById("chatBox");
  const div = document.createElement("div");
  div.className = "message";
  if (role === "user") {
    div.innerHTML = `<div class="user">Bạn:</div><div>${text}</div>`;
  } else {
    div.innerHTML = `<div class="assistant">AI:</div><div class="markdown">${marked.parse(text)}</div>`;
  }
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

class EventSourcePolyfill {
  constructor(url, { headers, payload, method }) {
    this.listeners = {};
    fetch(url, { method, headers, body: payload })
      .then(res => {
        const reader = res.body.getReader();
        const dec = new TextDecoder("utf-8");
        const read = () => reader.read().then(({ done, value }) => {
          if (done) return;
          const chunk = dec.decode(value);
          chunk.trim().split(/\n\n+/).forEach(line => {
            if (line.startsWith("data: ")) {
              const data = line.slice(6).trim();
              this.listeners.message?.({ data });
            }
          });
          return read();
        });
        return read();
      })
      .catch(err => this.listeners.error?.(err));
  }
  onmessage(fn) { this.listeners.message = fn; }
  onerror(fn) { this.listeners.error = fn; }
  close() { /* no-op */ }
}

window.addEventListener("DOMContentLoaded", () => {
  fetchModels();
  loadConversations();
});

document.getElementById("newConvBtn").addEventListener("click", () => {
  currentSessionId = "sess_" + Date.now().toString(36)
    + "_" + Math.random().toString(36).substr(2, 6);
  messages = [];
  document.getElementById("chatBox").innerHTML = "";
  document.querySelectorAll(".conversation-item").forEach(el => {
    el.classList.remove("active");
  });
  loadConversations();
  document.getElementById("userInput").focus();
});
