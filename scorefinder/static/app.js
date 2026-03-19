const state = {
  selectedImport: null,
};

const elements = {
  configForm: document.getElementById("config-form"),
  storageRoot: document.getElementById("storage-root"),
  configPath: document.getElementById("config-path"),
  bootstrapPath: document.getElementById("bootstrap-path"),
  databasePath: document.getElementById("database-path"),
  configMessage: document.getElementById("config-message"),
  importForm: document.getElementById("import-form"),
  importUrl: document.getElementById("import-url"),
  importMessage: document.getElementById("import-message"),
  importResult: document.getElementById("import-result"),
  imagePreview: document.getElementById("image-preview"),
  pdfPreview: document.getElementById("pdf-preview"),
  previewEmpty: document.getElementById("preview-empty"),
  previewMeta: document.getElementById("preview-meta"),
  saveForm: document.getElementById("save-form"),
  saveMessage: document.getElementById("save-message"),
  artist: document.getElementById("artist"),
  songTitle: document.getElementById("song-title"),
  scoreType: document.getElementById("score-type"),
  memo: document.getElementById("memo"),
  savedSearchForm: document.getElementById("saved-search-form"),
  savedMessage: document.getElementById("saved-message"),
  savedResults: document.getElementById("saved-results"),
};

function setMessage(target, text, type = "") {
  target.textContent = text || "";
  target.className = `message${type ? ` ${type}` : ""}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function mediaLabel(mediaKind) {
  if (mediaKind === "image") return "画像";
  if (mediaKind === "pdf") return "PDF";
  if (mediaKind === "html") return "HTML";
  return mediaKind;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    let detail = "リクエストに失敗しました";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json();
}

function showPreview({ mediaKind, metaHtml, url = "", srcdoc = "", local = false }) {
  elements.previewEmpty.classList.add("hidden");
  elements.previewMeta.classList.remove("hidden");
  elements.previewMeta.innerHTML = metaHtml;

  if (mediaKind === "image") {
    elements.pdfPreview.classList.add("hidden");
    elements.pdfPreview.removeAttribute("src");
    elements.pdfPreview.removeAttribute("srcdoc");
    elements.imagePreview.classList.remove("hidden");
    elements.imagePreview.src = url;
  } else {
    elements.imagePreview.classList.add("hidden");
    elements.imagePreview.removeAttribute("src");
    elements.pdfPreview.classList.remove("hidden");
    if (srcdoc) {
      elements.pdfPreview.srcdoc = srcdoc;
      elements.pdfPreview.removeAttribute("src");
    } else {
      elements.pdfPreview.removeAttribute("srcdoc");
      elements.pdfPreview.src = url;
    }
  }

  if (!local) {
    elements.saveForm.classList.remove("hidden");
  }
}

function hidePreview() {
  elements.imagePreview.classList.add("hidden");
  elements.pdfPreview.classList.add("hidden");
  elements.imagePreview.removeAttribute("src");
  elements.pdfPreview.removeAttribute("src");
  elements.pdfPreview.removeAttribute("srcdoc");
  elements.previewMeta.classList.add("hidden");
  elements.previewMeta.innerHTML = "";
  elements.previewEmpty.classList.remove("hidden");
  elements.saveForm.classList.add("hidden");
}

function selectImportedScore(item) {
  state.selectedImport = item;
  elements.artist.value = item.artist || "";
  elements.songTitle.value = item.song_title || "";
  if (item.score_type) {
    elements.scoreType.value = item.score_type;
  }
  setMessage(elements.saveMessage, "");

  const metaHtml = `
    <strong>${escapeHtml(item.song_title)} / ${escapeHtml(item.artist)}</strong><br />
    提供元: ${escapeHtml(item.provider || "unknown")}<br />
    種別: ${escapeHtml(item.score_type || mediaLabel(item.media_kind))}<br />
    行数: ${escapeHtml(item.line_count || "-")}<br />
    元ページ: <a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">開く</a>
  `;
  showPreview({
    mediaKind: item.media_kind,
    srcdoc: item.preview_html,
    metaHtml,
  });
}

function previewSavedScore(item) {
  state.selectedImport = null;
  elements.saveForm.classList.add("hidden");
  const metaHtml = `
    <strong>${escapeHtml(item.artist)} / ${escapeHtml(item.song_title)}</strong><br />
    譜面種別: ${escapeHtml(item.score_type)}<br />
    ファイル種別: ${escapeHtml(mediaLabel(item.media_kind))}<br />
    保存日: ${escapeHtml(item.saved_at)}<br />
    保存先: <code>${escapeHtml(item.storage_path)}</code><br />
    元ページ: <a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">開く</a>
  `;
  showPreview({
    mediaKind: item.media_kind,
    url: item.content_url,
    metaHtml,
    local: true,
  });
}

function renderImportResult(item) {
  if (!item) {
    elements.importResult.className = "result-grid empty-state";
    elements.importResult.textContent = "取り込み結果はここに表示されます。";
    return;
  }

  elements.importResult.className = "result-grid";
  elements.importResult.innerHTML = `
    <article class="result-card">
      <div class="content">
        <h3>${escapeHtml(item.song_title)} / ${escapeHtml(item.artist)}</h3>
        <div class="meta-row">
          <span>${escapeHtml(item.provider || "unknown")}</span>
          <span>${escapeHtml(item.score_type || mediaLabel(item.media_kind))}</span>
          <span>${escapeHtml(item.line_count || "-")} 行</span>
        </div>
        ${
          item.lyricist || item.composer
            ? `<div class="meta-row"><span>作詞: ${escapeHtml(item.lyricist || "-")} / 作曲: ${escapeHtml(item.composer || "-")}</span></div>`
            : ""
        }
      </div>
      <div class="actions">
        <button type="button" id="preview-imported-score">プレビュー</button>
        <a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">元ページ</a>
      </div>
    </article>
  `;

  document.getElementById("preview-imported-score").addEventListener("click", () => {
    selectImportedScore(item);
  });
}

function renderSavedResults(items) {
  if (!items.length) {
    elements.savedResults.className = "saved-results empty-state";
    elements.savedResults.textContent = "保存済みデータがありません。";
    return;
  }

  elements.savedResults.className = "saved-results";
  elements.savedResults.innerHTML = items
    .map(
      (item, index) => `
        <article class="saved-card">
          <div class="content">
            <h3>${escapeHtml(item.artist)} / ${escapeHtml(item.song_title)}</h3>
            <div class="meta-row">
              <span>${escapeHtml(item.score_type)}</span>
              <span>${escapeHtml(mediaLabel(item.media_kind))}</span>
              <span>${escapeHtml(item.saved_at)}</span>
            </div>
            <div class="meta-row">
              <span>登録キー: ${escapeHtml(item.query)}</span>
            </div>
            ${item.memo ? `<div class="meta-row"><span>メモ: ${escapeHtml(item.memo)}</span></div>` : ""}
          </div>
          <div class="actions">
            <button type="button" data-saved-index="${index}">プレビュー</button>
            <a href="${escapeHtml(item.content_url)}" target="_blank" rel="noreferrer">開く</a>
          </div>
        </article>
      `,
    )
    .join("");

  elements.savedResults.querySelectorAll("[data-saved-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = items[Number(button.dataset.savedIndex)];
      previewSavedScore(item);
    });
  });
}

async function loadConfig() {
  try {
    const payload = await fetchJson("/api/config");
    elements.storageRoot.value = payload.storage_root;
    elements.configPath.textContent = payload.config_path;
    elements.bootstrapPath.textContent = payload.bootstrap_path;
    elements.databasePath.textContent = payload.database_path;
  } catch (error) {
    setMessage(elements.configMessage, error.message, "error");
  }
}

async function searchSaved() {
  const params = new URLSearchParams();
  const formData = new FormData(elements.savedSearchForm);
  for (const [key, value] of formData.entries()) {
    if (value) {
      params.set(key, value);
    }
  }

  try {
    setMessage(elements.savedMessage, "保存済みデータを検索しています...");
    const payload = await fetchJson(`/api/scores?${params.toString()}`);
    renderSavedResults(payload.results);
    setMessage(elements.savedMessage, `${payload.results.length} 件見つかりました`, "success");
  } catch (error) {
    setMessage(elements.savedMessage, error.message, "error");
  }
}

elements.configForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = await fetchJson("/api/config", {
      method: "POST",
      body: JSON.stringify({ storage_root: elements.storageRoot.value }),
    });
    elements.storageRoot.value = payload.storage_root;
    elements.configPath.textContent = payload.config_path;
    elements.bootstrapPath.textContent = payload.bootstrap_path;
    elements.databasePath.textContent = payload.database_path;
    setMessage(
      elements.configMessage,
      `保存先を更新しました: ${payload.storage_root} / Config: ${payload.config_path} / DB: ${payload.database_path}`,
      "success",
    );
  } catch (error) {
    setMessage(elements.configMessage, error.message, "error");
  }
});

elements.importForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hidePreview();
  state.selectedImport = null;

  try {
    setMessage(elements.importMessage, "URL を解析しています...");
    const payload = await fetchJson(`/api/import?url=${encodeURIComponent(elements.importUrl.value.trim())}`);
    renderImportResult(payload);
    selectImportedScore(payload);
    setMessage(elements.importMessage, `${payload.provider} から ${payload.song_title} を取り込みました`, "success");
  } catch (error) {
    renderImportResult(null);
    setMessage(elements.importMessage, error.message, "error");
  }
});

elements.saveForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedImport) {
    setMessage(elements.saveMessage, "保存する取り込み結果を先に選択してください", "error");
    return;
  }

  const payload = {
    query: state.selectedImport.source_url,
    artist: elements.artist.value.trim(),
    song_title: elements.songTitle.value.trim(),
    score_type: elements.scoreType.value,
    media_kind: state.selectedImport.media_kind,
    source_url: state.selectedImport.source_url,
    source_page_url: state.selectedImport.source_page_url || state.selectedImport.source_url,
    source_title: state.selectedImport.source_title,
    provider: state.selectedImport.provider,
    memo: elements.memo.value.trim(),
  };

  try {
    const saved = await fetchJson("/api/scores", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setMessage(elements.saveMessage, `${saved.artist} / ${saved.song_title} を保存しました`, "success");
    await searchSaved();
  } catch (error) {
    setMessage(elements.saveMessage, error.message, "error");
  }
});

elements.savedSearchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await searchSaved();
});

async function bootstrap() {
  await loadConfig();
  await searchSaved();
}

bootstrap();
