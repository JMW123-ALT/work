const state = {
  userType: "visitor",
  ingestRole: "none",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.error || "请求失败");
  return data;
}

function canUpload() {
  return state.ingestRole !== "none";
}

function syncIngestVisibility() {
  const ingestNav = $("#ingestNav");
  if (ingestNav) ingestNav.hidden = !canUpload();
  if (!canUpload() && $("#view-ingest").classList.contains("active")) {
    setView("ask");
  }
}

function setView(view) {
  if (view === "ingest" && !canUpload()) view = "ask";
  $$(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  $$(".view").forEach((item) => item.classList.toggle("active", item.id === `view-${view}`));
  if (view === "docs") loadDocuments();
  if (view === "audit") loadAudit();
}

function renderSources(container, items) {
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = `<div class="result-card">暂无结果</div>`;
    return;
  }
  container.innerHTML = items.map((item) => `
    <article class="result-card">
      <strong>${item.title}</strong>
      <div>${item.snippet || item.content || ""}</div>
      <div class="meta">
        ${item.object_type} · ${item.permission_level} · ${item.modality || "text"} · ${item.source_id}
        ${item.chunk_index !== undefined ? ` · chunk ${item.chunk_index}` : ""}
        ${item.score ? ` · score ${item.score}` : ""}
      </div>
    </article>
  `).join("");
}

function renderAgentEvidence(items = []) {
  const container = $("#agentEvidenceList");
  if (!items.length) {
    container.innerHTML = `<div class="result-card">暂无引用资料</div>`;
    return;
  }
  container.innerHTML = items.map((item) => `
    <article class="result-card">
      <strong>${escapeHtml(item.culture_theme || item.category || item.source || "未命名资料")}</strong>
      <div>${escapeHtml(item.text || "").slice(0, 360)}</div>
      <div class="meta">
        ${escapeHtml(item.source || "unknown")}
        ${item.confidence !== undefined ? ` · confidence ${Number(item.confidence).toFixed(4)}` : ""}
        ${item.category ? ` · ${escapeHtml(item.category)}` : ""}
      </div>
    </article>
  `).join("");
}

function renderAgentWarnings(warnings = []) {
  const container = $("#agentWarnings");
  container.innerHTML = warnings.length
    ? warnings.map((warning) => `<div class="notice">${escapeHtml(warning)}</div>`).join("")
    : "";
}

function llmModeLabel(modes = {}) {
  const values = Object.values(modes);
  if (!values.length) return "-";
  const deepseekCount = values.filter((value) => value === "deepseek").length;
  return `${deepseekCount}/${values.length} DeepSeek`;
}

async function runAgent() {
  const query = $("#agentQuery").value.trim();
  const topK = Number($("#agentTopK").value || 5);
  const minConfidence = Number($("#agentMinConfidence").value || 0.7);
  if (!query) {
    $("#agentStatus").textContent = "请输入需求";
    $("#agentStatus").className = "status-pill warn";
    return;
  }

  $("#agentBtn").disabled = true;
  $("#agentStatus").textContent = "生成中";
  $("#agentStatus").className = "status-pill running";
  $("#agentAnswer").textContent = "检索资料并生成方案中...";
  $("#agentAnswer").classList.remove("empty");
  $("#agentEvidenceList").innerHTML = "";
  renderAgentWarnings([]);

  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        query,
        user_type: state.userType,
        top_k: topK,
        min_confidence: minConfidence,
      }),
    });

    $("#agentStatus").textContent = data.status || "ok";
    $("#agentStatus").className = `status-pill ${data.status || "ok"}`;
    $("#agentWorkflow").textContent = data.workflow || "-";
    $("#agentIntent").textContent = data.intent || "-";
    $("#agentEvidenceCount").textContent = String((data.evidence || []).length);
    $("#agentLlmState").textContent = llmModeLabel(data.llm_modes);
    $("#agentAnswer").textContent = data.final_answer || "暂无方案";
    renderAgentWarnings(data.warnings || []);
    renderAgentEvidence(data.evidence || []);
  } catch (error) {
    $("#agentStatus").textContent = "生成失败";
    $("#agentStatus").className = "status-pill blocked";
    $("#agentAnswer").textContent = error.message;
    renderAgentEvidence([]);
  } finally {
    $("#agentBtn").disabled = false;
  }
}

async function ask() {
  const question = $("#questionInput").value.trim();
  $("#answerBox").textContent = "检索和生成中...";
  $("#answerBox").classList.remove("empty");
  const data = await api("/api/ask", {
    method: "POST",
    body: JSON.stringify({ question, user_type: state.userType }),
  });
  $("#answerBox").textContent = `${data.answer}\n\nTrace ID: ${data.traceId}`;
  renderSources($("#sourceList"), data.sources);
}

async function search() {
  const query = $("#searchInput").value.trim();
  const data = await api("/api/search", {
    method: "POST",
    body: JSON.stringify({ query, user_type: state.userType }),
  });
  renderSources($("#searchList"), data.items);
}

async function ingest() {
  const files = [...$("#docFile").files];
  const modality = $("#docModality").value;
  const base = {
    title: $("#docTitle").value.trim(),
    content: $("#docContent").value.trim(),
    object_type: $("#docType").value,
    permission_level: $("#docPermission").value,
    ingest_role: state.ingestRole,
    operator: "local-admin",
  };
  if (modality !== "auto") base.modality = modality;

  try {
    let data;
    if (!files.length && ["pdf", "image", "office"].includes(modality)) {
      throw new Error("请选择实际文件后再入库。只选择模态不会上传文件。");
    }
    if (files.length) {
      const form = new FormData();
      Object.entries(base).forEach(([key, value]) => form.append(key, value));
      files.forEach((file) => form.append("files", file));
      const response = await fetch("/api/v1/ingest/file", { method: "POST", body: form });
      data = await response.json();
      if (!response.ok) throw new Error(data.message || data.error || "上传失败");
    } else {
      data = await api("/api/v1/ingest/text", {
        method: "POST",
        body: JSON.stringify({ ...base, modality: base.modality || "text" }),
      });
    }
    const items = data.items || [data.item];
    $("#ingestMessage").textContent = `已入库 ${items.length} 条资料：${items.map((item) => item.title).join("、")}`;
    $("#docFile").value = "";
    loadDocuments();
  } catch (error) {
    $("#ingestMessage").textContent = error.message;
  }
}

async function loadDocuments() {
  const data = await api("/api/documents");
  $("#docList").innerHTML = data.items.map((item) => `
    <div class="table-row">
      <strong>${item.title}</strong>
      <div>${item.content}</div>
      <div class="meta">
        ${item.object_type} · ${item.permission_level} · ${item.modality || "text"}
        · chunks ${item.chunk_count || 0}
        ${item.file_name ? ` · ${item.file_name}` : ""}
        · ${item.extraction_status || "parsed"}
      </div>
    </div>
  `).join("");
}

async function loadAudit() {
  const data = await api("/api/audit");
  $("#auditList").innerHTML = data.items.length ? data.items.map((item) => `
    <div class="table-row">
      <strong>${item.action} · ${item.user_type}</strong>
      <div class="meta">${item.time} · ${item.trace_id}</div>
      <pre>${JSON.stringify(item.detail, null, 2)}</pre>
    </div>
  `).join("") : `<div class="table-row">暂无审计记录</div>`;
}

$$(".nav-item").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
$("#userType").addEventListener("change", (event) => { state.userType = event.target.value; });
$("#ingestRole").addEventListener("change", (event) => {
  state.ingestRole = event.target.value;
  syncIngestVisibility();
});
$("#agentBtn").addEventListener("click", runAgent);
$("#askBtn").addEventListener("click", ask);
$("#searchBtn").addEventListener("click", search);
$("#ingestBtn").addEventListener("click", ingest);

syncIngestVisibility();
api("/api/health").then(() => loadDocuments()).catch(console.error);
