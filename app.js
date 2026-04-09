/**
 * PersonaBot — Frontend Application Logic
 * Full-featured SaaS chatbot with document AI capabilities
 */

/* ── Constants ─────────────────────────────────────────────── */
const API_BASE = "http://localhost:5000/api";
const SESSION_ID = generateSessionId();

/* ── State ──────────────────────────────────────────────────── */
const state = {
  isTyping: false,
  totalMessages: 0,
  uploadedDocs: [],
  config: {},
};

/* ── DOM References ─────────────────────────────────────────── */
const els = {
  app:             () => document.getElementById("app"),
  loadingScreen:   () => document.getElementById("loading-screen"),
  sidebar:         () => document.getElementById("sidebar"),
  sidebarToggle:   () => document.getElementById("sidebar-toggle"),
  menuBtn:         () => document.getElementById("menu-btn"),
  messagesContainer: () => document.getElementById("messages-container"),
  welcomeState:    () => document.getElementById("welcome-state"),
  messageInput:    () => document.getElementById("message-input"),
  sendBtn:         () => document.getElementById("send-btn"),
  charCount:       () => document.getElementById("char-count"),
  fileInput:       () => document.getElementById("file-input"),
  uploadBtn:       () => document.getElementById("upload-btn"),
  uploadZone:      () => document.getElementById("upload-zone"),
  uploadProgress:  () => document.getElementById("upload-progress"),
  progressFill:    () => document.getElementById("progress-fill"),
  progressText:    () => document.getElementById("progress-text"),
  docList:         () => document.getElementById("doc-list"),
  resetBtn:        () => document.getElementById("reset-btn"),
  clearChatBtn:    () => document.getElementById("clear-chat-btn"),
  contextChip:     () => document.getElementById("context-chip"),
  contextCount:    () => document.getElementById("context-count"),
  botRoleInput:    () => document.getElementById("bot-role-input"),
  businessNameInput: () => document.getElementById("business-name-input"),
  toastContainer:  () => document.getElementById("toast-container"),
  // Dynamic bot name displays
  botNameEl:       () => document.getElementById("bot-name"),
  botTaglineEl:    () => document.getElementById("bot-tagline"),
  headerBotName:   () => document.getElementById("header-bot-name"),
  headerAvatar:    () => document.getElementById("header-avatar"),
  welcomeBotName:  () => document.getElementById("welcome-bot-name"),
  welcomeAvatarIcon: () => document.getElementById("welcome-avatar-icon"),
  welcomeMessage:  () => document.getElementById("welcome-message"),
};

/* ═══════════════════════════════════════════════════
   INITIALIZATION
═══════════════════════════════════════════════════ */
async function init() {
  // Boot sequence
  await simulateLoad();
  hideLoadingScreen();

  await loadConfig();
  bindEvents();
  focusInput();
}

async function simulateLoad() {
  return new Promise(resolve => setTimeout(resolve, 2000));
}

function hideLoadingScreen() {
  const loader = els.loadingScreen();
  loader.classList.add("fade-out");
  setTimeout(() => {
    loader.style.display = "none";
    els.app().classList.remove("hidden");
    els.app().style.animation = "fade-up 0.5s ease";
  }, 500);
}

async function loadConfig() {
  try {
    const res  = await apiRequest("/config");
    const data = await res.json();
    state.config = data;
    applyConfig(data);
  } catch {
    // Fallback defaults if backend isn't running yet
    applyConfig({ bot_name: "PersonaBot", bot_tagline: "Intelligent Document AI", bot_avatar: "🤖", welcome_message: "Upload your documents and ask me anything!" });
  }
}

function applyConfig(cfg) {
  const { bot_name = "PersonaBot", bot_tagline = "Intelligent Document AI",
          bot_avatar = "🤖", welcome_message = "Upload your documents and ask me anything!" } = cfg;

  setTextSafe("bot-name", bot_name);
  setTextSafe("bot-tagline", bot_tagline);
  setTextSafe("header-bot-name", bot_name);
  setTextSafe("header-avatar", bot_avatar);
  setTextSafe("welcome-bot-name", bot_name);
  setTextSafe("welcome-avatar-icon", bot_avatar);
  setTextSafe("welcome-message", welcome_message);

  if (cfg.primary_color) {
    document.documentElement.style.setProperty("--accent", cfg.primary_color);
  }
}

function setTextSafe(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

/* ═══════════════════════════════════════════════════
   EVENT BINDINGS
═══════════════════════════════════════════════════ */
function bindEvents() {
  // Send message
  els.sendBtn().addEventListener("click", handleSend);
  els.messageInput().addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  // Input auto-resize + char counter
  els.messageInput().addEventListener("input", handleInputChange);

  // Sidebar toggle
  els.sidebarToggle().addEventListener("click", closeSidebar);
  els.menuBtn().addEventListener("click", openSidebar);

  // File upload
  els.uploadBtn().addEventListener("click", () => els.fileInput().click());
  els.fileInput().addEventListener("change", handleFileSelect);
  els.uploadZone().addEventListener("click", (e) => {
    if (e.target === els.uploadZone() || e.target.classList.contains("upload-content")
        || e.target.classList.contains("upload-text") || e.target.classList.contains("upload-sub")
        || e.target.classList.contains("upload-icon")) {
      els.fileInput().click();
    }
  });

  // Drag & drop
  els.uploadZone().addEventListener("dragover", (e) => {
    e.preventDefault();
    els.uploadZone().classList.add("drag-over");
  });
  els.uploadZone().addEventListener("dragleave", () => els.uploadZone().classList.remove("drag-over"));
  els.uploadZone().addEventListener("drop", handleDrop);

  // Reset session
  els.resetBtn().addEventListener("click", handleReset);
  els.clearChatBtn().addEventListener("click", clearChat);

  // Quick actions
  document.querySelectorAll(".quick-action").forEach(btn => {
    btn.addEventListener("click", () => {
      const msg = btn.dataset.msg;
      if (msg) sendMessage(msg);
    });
  });
}

/* ═══════════════════════════════════════════════════
   CHAT LOGIC
═══════════════════════════════════════════════════ */
async function handleSend() {
  const input = els.messageInput();
  const msg   = input.value.trim();
  if (!msg || state.isTyping) return;

  input.value = "";
  updateCharCount(0);
  resizeTextarea(input);
  sendMessage(msg);
}

async function sendMessage(text) {
  if (!text.trim()) return;

  // Remove welcome state on first message
  if (state.totalMessages === 0) {
    const ws = els.welcomeState();
    if (ws) ws.style.display = "none";
  }

  // Render user message
  appendMessage("user", text);
  state.isTyping = true;
  updateSendBtn(false);

  // Show typing indicator
  const typingId = showTyping();

  try {
    const res = await apiRequest("/chat", {
      method: "POST",
      body: JSON.stringify({
        message: text,
        bot_role: els.botRoleInput().value || "professional business assistant",
        business_name: els.businessNameInput().value || "Our Company",
      })
    });

    const data = await res.json();
    removeTyping(typingId);

    if (res.ok && data.success) {
      appendMessage("bot", data.response);
    } else {
      // Show the real error message from backend
      const errMsg = data.error || "Something went wrong. Please try again.";
      const hint   = data.hint ? `\n\n💡 ${data.hint}` : "";
      appendMessage("bot", `⚠️ ${errMsg}${hint}`, true);
      showToast(errMsg.length > 80 ? errMsg.slice(0, 80) + "..." : errMsg, "error", 6000);
    }
  } catch (err) {
    removeTyping(typingId);
    appendMessage("bot", "⚠️ Cannot reach the server. Make sure the backend is running on port 5000.", true);
  }

  state.isTyping = false;
  updateSendBtn(true);
  focusInput();
}

/* ── Message Rendering ────────────────────────────── */
function appendMessage(role, text, isError = false) {
  const container = els.messagesContainer();
  const isUser    = role === "user";

  const msgEl = document.createElement("div");
  msgEl.classList.add("message", isUser ? "user-message" : "bot-message");
  if (isError) msgEl.classList.add("error-message");

  const avatar   = document.createElement("div");
  avatar.classList.add("msg-avatar");
  avatar.textContent = isUser ? "U" : (state.config.bot_avatar || "🤖");

  const bubble   = document.createElement("div");
  bubble.classList.add("msg-bubble");

  const content  = document.createElement("div");
  content.classList.add("msg-content");
  content.innerHTML = isUser ? escapeHtml(text) : formatBotMessage(text);

  const timeEl   = document.createElement("span");
  timeEl.classList.add("msg-time");
  timeEl.textContent = formatTime(new Date());

  bubble.appendChild(content);
  bubble.appendChild(timeEl);
  msgEl.appendChild(avatar);
  msgEl.appendChild(bubble);
  container.appendChild(msgEl);

  state.totalMessages++;
  scrollToBottom();
}

function formatBotMessage(text) {
  // Convert markdown-lite to HTML
  return text
    .split("\n")
    .map(line => {
      // Bold: **text**
      line = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      // Italic: *text*
      line = line.replace(/\*(.*?)\*/g, "<em>$1</em>");
      // Inline code: `code`
      line = line.replace(/`([^`]+)`/g, "<code>$1</code>");
      // Bullet points
      if (line.trim().startsWith("- ") || line.trim().startsWith("• ")) {
        return `<div class="msg-bullet">• ${line.trim().slice(2)}</div>`;
      }
      return line;
    })
    .join("<br>");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

/* ── Typing Indicator ─────────────────────────────── */
function showTyping() {
  const id        = `typing-${Date.now()}`;
  const container = els.messagesContainer();

  const typingEl  = document.createElement("div");
  typingEl.classList.add("message", "bot-message", "typing-message");
  typingEl.id     = id;

  const avatar    = document.createElement("div");
  avatar.classList.add("msg-avatar");
  avatar.textContent = state.config.bot_avatar || "🤖";

  const indicator = document.createElement("div");
  indicator.classList.add("typing-indicator");
  indicator.innerHTML = `
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  `;

  typingEl.appendChild(avatar);
  typingEl.appendChild(indicator);
  container.appendChild(typingEl);
  scrollToBottom();
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

/* ═══════════════════════════════════════════════════
   FILE UPLOAD
═══════════════════════════════════════════════════ */
function handleFileSelect(e) {
  const files = Array.from(e.target.files);
  if (files.length) uploadFiles(files);
  e.target.value = ""; // Reset so same file can be uploaded again
}

function handleDrop(e) {
  e.preventDefault();
  els.uploadZone().classList.remove("drag-over");
  const files = Array.from(e.dataTransfer.files);
  if (files.length) uploadFiles(files);
}

async function uploadFiles(files) {
  for (const file of files) {
    await uploadSingleFile(file);
  }
}

async function uploadSingleFile(file) {
  const ALLOWED = ["pdf", "csv", "txt", "xlsx", "xls"];
  const ext     = file.name.split(".").pop().toLowerCase();

  if (!ALLOWED.includes(ext)) {
    showToast(`❌ .${ext} files are not supported`, "error");
    return;
  }

  if (file.size > 16 * 1024 * 1024) {
    showToast("❌ File too large. Maximum size is 16MB", "error");
    return;
  }

  // Show progress
  showProgress(`Uploading ${file.name}...`);
  animateProgress(0, 40, 600);

  const formData = new FormData();
  formData.append("file", file);

  try {
    animateProgress(40, 80, 800);
    const res  = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      headers: { "X-Session-ID": SESSION_ID },
      body: formData
    });

    animateProgress(80, 100, 400);
    const data = await res.json();

    if (res.ok && data.success) {
      addDocToList(file.name, data.chunks, ext);
      updateContextCount();
      showToast(`✅ ${file.name} — ${data.chunks} chunks extracted`, "success");

      // Welcome chat message about uploaded doc
      setTimeout(() => {
        appendMessage("bot",
          `📄 I've processed **${file.name}** (${data.chunks} chunks, ${data.characters.toLocaleString()} characters).\n\n${data.preview}\n\nYou can now ask me questions about this document!`
        );
      }, 500);
    } else {
      showToast(`❌ ${data.error || "Upload failed"}`, "error");
    }
  } catch (err) {
    showToast("❌ Upload failed — server not reachable", "error");
  } finally {
    setTimeout(hideProgress, 600);
  }
}

function showProgress(text) {
  els.uploadProgress().classList.remove("hidden");
  els.progressText().textContent = text;
  els.progressFill().style.width = "0%";
}

function hideProgress() {
  els.uploadProgress().classList.add("hidden");
}

function animateProgress(from, to, duration) {
  const fill  = els.progressFill();
  const start = performance.now();
  const diff  = to - from;

  function step(now) {
    const elapsed = now - start;
    const prog    = Math.min(elapsed / duration, 1);
    fill.style.width = (from + diff * prog) + "%";
    if (prog < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function addDocToList(filename, chunks, ext) {
  if (!state.uploadedDocs.includes(filename)) {
    state.uploadedDocs.push(filename);
  }

  // Check if already in DOM
  if (document.getElementById(`doc-${filename}`)) {
    document.getElementById(`doc-${filename}`).remove();
  }

  const iconMap = { pdf: "ph-file-pdf", csv: "ph-table", xlsx: "ph-microsoft-excel-logo", txt: "ph-file-text" };
  const icon    = iconMap[ext] || "ph-file";

  const item = document.createElement("div");
  item.classList.add("doc-item");
  item.id = `doc-${filename}`;
  item.innerHTML = `
    <div class="doc-icon ${ext}">
      <i class="ph ${icon}"></i>
    </div>
    <span class="doc-name" title="${filename}">${filename}</span>
    <button class="doc-delete" onclick="removeDocument('${filename}')" title="Remove document">
      <i class="ph ph-x"></i>
    </button>
  `;

  els.docList().appendChild(item);
}

window.removeDocument = async function(filename) {
  try {
    const res = await apiRequest(`/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
    const data = await res.json();

    if (res.ok) {
      const el = document.getElementById(`doc-${filename}`);
      if (el) {
        el.style.animation = "slide-in 0.2s ease reverse";
        setTimeout(() => el.remove(), 200);
      }
      state.uploadedDocs = state.uploadedDocs.filter(d => d !== filename);
      updateContextCount();
      showToast(`🗑️ "${filename}" removed`, "info");
    }
  } catch {
    showToast("Failed to remove document", "error");
  }
};

function updateContextCount() {
  const count = state.uploadedDocs.length;
  els.contextCount().textContent = `${count} doc${count !== 1 ? "s" : ""}`;
  els.contextChip().style.opacity = count > 0 ? "1" : "0.5";
}

/* ═══════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════ */
function openSidebar() {
  const sb = els.sidebar();
  if (window.innerWidth <= 768) {
    sb.classList.add("mobile-open");
  } else {
    sb.classList.remove("collapsed");
  }
}

function closeSidebar() {
  const sb = els.sidebar();
  if (window.innerWidth <= 768) {
    sb.classList.remove("mobile-open");
  } else {
    sb.classList.add("collapsed");
  }
}

/* ═══════════════════════════════════════════════════
   SESSION MANAGEMENT
═══════════════════════════════════════════════════ */
async function handleReset() {
  if (!confirm("Reset the session? This will clear all chat history and uploaded documents.")) return;

  try {
    await apiRequest("/reset", { method: "POST" });
    clearChat();
    els.docList().innerHTML = "";
    state.uploadedDocs      = [];
    updateContextCount();
    showToast("🔄 Session reset successfully", "success");
  } catch {
    showToast("Failed to reset session", "error");
  }
}

function clearChat() {
  const container = els.messagesContainer();
  // Remove all message elements (not welcome state)
  const messages = container.querySelectorAll(".message, .date-separator");
  messages.forEach(m => m.remove());

  // Show welcome state again
  const ws = els.welcomeState();
  if (ws) ws.style.display = "";

  state.totalMessages = 0;
}

/* ═══════════════════════════════════════════════════
   UI HELPERS
═══════════════════════════════════════════════════ */
function handleInputChange() {
  const input = els.messageInput();
  const len   = input.value.length;
  updateCharCount(len);
  resizeTextarea(input);
  updateSendBtn(len > 0 && !state.isTyping);
}

function updateCharCount(len) {
  const el   = els.charCount();
  el.textContent = `${len}/2000`;
  el.classList.remove("warn", "danger");
  if (len > 1800) el.classList.add("danger");
  else if (len > 1500) el.classList.add("warn");
}

function resizeTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 160) + "px";
}

function updateSendBtn(enabled) {
  els.sendBtn().disabled = !enabled;
}

function scrollToBottom() {
  const container = els.messagesContainer();
  setTimeout(() => {
    container.scrollTop = container.scrollHeight;
  }, 50);
}

function focusInput() {
  setTimeout(() => els.messageInput().focus(), 100);
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function generateSessionId() {
  const stored = sessionStorage.getItem("personabot_session_id");
  if (stored) return stored;
  const id = "sess_" + Math.random().toString(36).slice(2) + "_" + Date.now();
  sessionStorage.setItem("personabot_session_id", id);
  return id;
}

/* ═══════════════════════════════════════════════════
   TOAST NOTIFICATION SYSTEM
═══════════════════════════════════════════════════ */
function showToast(message, type = "info", duration = 4000) {
  const iconMap = {
    success: "ph-check-circle",
    error:   "ph-x-circle",
    warning: "ph-warning",
    info:    "ph-info"
  };

  const toast       = document.createElement("div");
  toast.classList.add("toast", type);
  toast.innerHTML   = `
    <i class="ph ${iconMap[type] || "ph-info"} toast-icon"></i>
    <span>${message}</span>
  `;

  els.toastContainer().appendChild(toast);

  setTimeout(() => {
    toast.classList.add("removing");
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ═══════════════════════════════════════════════════
   API HELPER
═══════════════════════════════════════════════════ */
async function apiRequest(endpoint, options = {}) {
  const defaults = {
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": SESSION_ID,
    }
  };

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (options.body instanceof FormData) {
    delete defaults.headers["Content-Type"];
  }

  const config = {
    ...defaults,
    ...options,
    headers: {
      ...defaults.headers,
      ...(options.headers || {})
    }
  };

  return fetch(`${API_BASE}${endpoint}`, config);
}

/* ── Boot ───────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", init);
