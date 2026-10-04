const API = "http://localhost:8000";
const statusEl = document.getElementById("status");
const chatEl = document.getElementById("chat");
const input = document.getElementById("q");
const sendBtn = document.getElementById("send");
let videoId = null;

function getVideoId(url) {
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtu.be")) return u.pathname.slice(1);
    if (u.pathname === "/watch") return u.searchParams.get("v");
    const m = u.pathname.match(/^\/(shorts|embed)\/([\w-]{11})/);
    if (m) return m[2];
  } catch (e) {}
  return null;
}

function addMsg(text, cls) {
  const d = document.createElement("div");
  d.className = "msg " + cls;
  d.textContent = text;
  chatEl.appendChild(d);
  chatEl.scrollTop = chatEl.scrollHeight;
  return d;
}

async function post(path, body) {
  const r = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Request failed (" + r.status + ")");
  return data;
}

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  videoId = getVideoId(tab.url || "");
  if (!videoId) {
    statusEl.textContent = "Open a YouTube video, then click the extension.";
    return;
  }
  statusEl.textContent = "Reading transcript and indexing... (first time takes a while)";
  try {
    const res = await post("/index", { video_id: videoId });
    statusEl.textContent = "Ready (" + res.status + ") - video " + videoId;
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  } catch (e) {
    statusEl.textContent = "Error: " + e.message + " (is the backend running?)";
  }
}

async function ask() {
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  addMsg(q, "user");
  const thinking = addMsg("Thinking...", "bot");
  sendBtn.disabled = true;
  try {
    const res = await post("/ask", { video_id: videoId, question: q });
    thinking.textContent = res.answer;
  } catch (e) {
    thinking.textContent = "Error: " + e.message;
  }
  sendBtn.disabled = false;
}

sendBtn.addEventListener("click", ask);
input.addEventListener("keydown", (e) => { if (e.key === "Enter") ask(); });
init();
