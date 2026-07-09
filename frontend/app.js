const state = {
  userType: "visitor",
  ingestRole: "none",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

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
      const response = await fetch("/api/ingest", { method: "POST", body: form });
      data = await response.json();
      if (!response.ok) throw new Error(data.message || data.error || "上传失败");
    } else {
      data = await api("/api/ingest", {
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
$("#askBtn").addEventListener("click", ask);
$("#searchBtn").addEventListener("click", search);
$("#ingestBtn").addEventListener("click", ingest);

syncIngestVisibility();
api("/api/health").then(() => loadDocuments()).catch(console.error);
