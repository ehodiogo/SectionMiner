import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/build/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/build/pdf.worker.min.mjs";

const form = document.getElementById("upload-form");
const input = document.getElementById("pdf-input");
const presetInput = document.getElementById("preset-sections");
const statusEl = document.getElementById("status");
const sectionsEl = document.getElementById("sections");
const pageInfoEl = document.getElementById("page-info");
const prevPageBtn = document.getElementById("prev-page");
const nextPageBtn = document.getElementById("next-page");
const backendBadgeEl = document.getElementById("backend-badge");
const metricPagesEl = document.getElementById("metric-pages");
const metricSectionsEl = document.getElementById("metric-sections");
const metricBackendEl = document.getElementById("metric-backend");
const canvas = document.getElementById("pdf-canvas");
const overlay = document.getElementById("pdf-overlay");
const exportActions = document.getElementById("export-actions");
const btnExportJson = document.getElementById("btn-export-json");
const btnExportPdf = document.getElementById("btn-export-pdf");
const detailModal = document.getElementById("detail-modal");
const detailTitle = document.getElementById("detail-title");
const detailText = document.getElementById("detail-text");
const detailClose = document.getElementById("detail-close");

const state = {
  pdfDoc: null,
  pageNumber: 1,
  pageCount: 0,
  viewport: null,
  sections: [],
  selectedSection: null,
  payload: null,
};

function compactText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .replace(/\s*\n\s*/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/\s+([,.;:!?])/g, "$1")
    .replace(/\(\s+/g, "(")
    .replace(/\s+\)/g, ")")
    .trim();
}

function formatBackendName(value) {
  if (value === "gemini") return "Gemini";
  if (value === "pymupdf") return "PyMuPDF";
  return value || "—";
}

function parsePresetValues(rawValue) {
  return Array.from(
    new Set(
      String(rawValue || "")
        .split(/[;,\n]/g)
        .map((item) => compactText(item))
        .filter(Boolean),
    ),
  );
}

function setStatus(message, tone = "slate") {
  statusEl.textContent = message;
  statusEl.className = "min-h-6 text-sm";
  const colors = {
    slate: "text-slate-300",
    blue: "text-blue-300",
    green: "text-emerald-300",
    red: "text-rose-300",
    amber: "text-amber-300",
  };
  statusEl.classList.add(colors[tone] || colors.slate);
}

function updateMetrics(payload) {
  const metrics = payload.metrics || {};
  const pages = metrics.pages ?? payload.pages ?? 0;
  const sections = metrics.sections ?? (payload.sections || []).length;
  const backend = formatBackendName(payload.extraction_backend);
  const modeLabel = payload.heuristic_only ? "Heurística" : "LLM";

  backendBadgeEl.textContent = `${backend} · ${modeLabel}`;
  metricPagesEl.textContent = String(pages);
  metricSectionsEl.textContent = String(sections);
  metricBackendEl.textContent = backend;
}

function resetMetrics() {
  backendBadgeEl.textContent = "aguardando";
  metricPagesEl.textContent = "—";
  metricSectionsEl.textContent = "—";
  metricBackendEl.textContent = "—";
}

function openModal(title, text) {
  detailTitle.textContent = title;
  detailText.textContent = text || "Sem texto disponível.";
  detailModal.classList.remove("hidden");
}

function closeModal() {
  detailModal.classList.add("hidden");
}

async function renderPage() {
  if (!state.pdfDoc) return;

  const page = await state.pdfDoc.getPage(state.pageNumber);
  const viewport = page.getViewport({ scale: 1.25 });
  const ctx = canvas.getContext("2d");

  canvas.width = viewport.width;
  canvas.height = viewport.height;
  overlay.style.width = `${viewport.width}px`;
  overlay.style.height = `${viewport.height}px`;
  overlay.style.position = "absolute";
  overlay.style.top = "0";
  overlay.style.left = "0";

  state.viewport = viewport;
  pageInfoEl.textContent = `Página ${state.pageNumber} / ${state.pageCount}`;

  await page.render({ canvasContext: ctx, viewport }).promise;
  drawHighlights();
}

function drawHighlights() {
  overlay.innerHTML = "";

  if (!state.selectedSection || !state.viewport) return;

  const locations = Array.isArray(state.selectedSection.locations) ? state.selectedSection.locations : [];
  const pageLocations = locations.filter((item) => item.page === state.pageNumber - 1);

  for (const location of pageLocations) {
    if (!Array.isArray(location.bbox) || location.bbox.length !== 4) continue;

    const [x0, y0, x1, y1] = location.bbox;
    const [vx0, vy0] = state.viewport.convertToViewportPoint(x0, y0);
    const [vx1, vy1] = state.viewport.convertToViewportPoint(x1, y1);

    const box = document.createElement("div");
    box.className = "highlight-box";
    box.style.left = `${Math.min(vx0, vx1)}px`;
    box.style.top = `${Math.min(vy0, vy1)}px`;
    box.style.width = `${Math.max(Math.abs(vx1 - vx0), 2)}px`;
    box.style.height = `${Math.max(Math.abs(vy1 - vy0), 2)}px`;
    overlay.appendChild(box);
  }
}

function renderEmptySections() {
  sectionsEl.innerHTML = `
    <div class="rounded-2xl border border-dashed border-white/10 bg-slate-950/50 p-6 text-center">
      <p class="text-sm font-semibold text-slate-200">Nenhuma seção ainda</p>
      <p class="mt-2 text-sm leading-6 text-slate-400">Envie um PDF para ver as seções em cards limpos, com botão de ver detalhe e sem poluição visual.</p>
    </div>
  `;
  exportActions.classList.add("hidden");
}

function activateSectionCard(activeCard) {
  document.querySelectorAll(".section-card").forEach((node) => node.classList.remove("active"));
  activeCard.classList.add("active");
}

async function selectSection(section, card) {
  state.selectedSection = section;
  activateSectionCard(card);

  const firstLocation = Array.isArray(section.locations) ? section.locations[0] : null;
  if (firstLocation && typeof firstLocation.page === "number") {
    state.pageNumber = firstLocation.page + 1;
    await renderPage();
    return;
  }

  drawHighlights();
}

function buildSectionCard(section, index) {
  const card = document.createElement("article");
  card.className = "section-card rounded-2xl border border-white/10 bg-slate-950/70 p-4 transition hover:border-blue-400/60 hover:bg-slate-900/80";

  const level = Number(section.level || 1);
  const title = section.title || `Seção ${index + 1}`;
  const fullText = compactText(section.text || "Sem texto extraído.");
  const preview = fullText.length > 420 ? `${fullText.slice(0, 420)}…` : fullText;
  const page = Array.isArray(section.locations) && section.locations.length ? section.locations[0].page + 1 : null;

  card.style.marginLeft = `${Math.max(level - 1, 0) * 12}px`;

  const header = document.createElement("div");
  header.className = "flex items-start justify-between gap-3";
  header.innerHTML = `
    <div class="min-w-0">
      <div class="flex flex-wrap items-center gap-2">
        <span class="rounded-full border border-blue-400/20 bg-blue-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.25em] text-blue-200">${level === 1 ? "Seção" : "Subseção"}</span>
        ${page ? `<span class="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">Pág. ${page}</span>` : ""}
      </div>
      <h3 class="mt-3 truncate text-base font-semibold text-white">${index + 1}. ${title}</h3>
    </div>
  `;

  const text = document.createElement("p");
  text.className = "mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-300";
  text.textContent = preview;

  const actions = document.createElement("div");
  actions.className = "mt-4 flex flex-wrap gap-2";
  actions.innerHTML = `
    <button type="button" class="btn-select rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10">Selecionar</button>
    <button type="button" class="btn-detail rounded-xl border border-blue-400/20 bg-blue-400/10 px-3 py-2 text-sm font-medium text-blue-100 transition hover:bg-blue-400/15">Ver detalhe</button>
  `;

  card.appendChild(header);
  card.appendChild(text);
  card.appendChild(actions);

  card.addEventListener("click", async () => {
    await selectSection(section, card);
  });

  card.querySelector(".btn-select").addEventListener("click", async (event) => {
    event.stopPropagation();
    await selectSection(section, card);
  });

  card.querySelector(".btn-detail").addEventListener("click", (event) => {
    event.stopPropagation();
    openModal(title, fullText);
  });

  return card;
}

function renderSections() {
  sectionsEl.innerHTML = "";

  if (!state.sections.length) {
    renderEmptySections();
    return;
  }

  exportActions.classList.remove("hidden");
  exportActions.classList.add("flex");

  state.sections.forEach((section, index) => {
    sectionsEl.appendChild(buildSectionCard(section, index));
  });
}

async function loadPdf(url) {
  const loadingTask = pdfjsLib.getDocument(url);
  state.pdfDoc = await loadingTask.promise;
  state.pageCount = state.pdfDoc.numPages;
  state.pageNumber = 1;
  await renderPage();
}

function downloadJSON() {
  if (!state.payload) return;
  const blob = new Blob([JSON.stringify(state.payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "sectionminer-result.json";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function downloadPDF() {
  if (!state.sections.length) return;

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  const margin = 15;
  const pageHeight = doc.internal.pageSize.height;
  let y = 16;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("Relatório de Seções Extraídas", margin, y);
  y += 12;

  state.sections.forEach((section, index) => {
    const title = `${index + 1}. ${compactText(section.title || "Sem título")}`;
    const body = compactText(section.text || "Nenhum texto encontrado.");
    const lines = doc.splitTextToSize(body, 180);

    if (y > pageHeight - 40) {
      doc.addPage();
      y = 16;
    }

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text(title, margin, y);
    y += 7;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    lines.forEach((line) => {
      if (y > pageHeight - 15) {
        doc.addPage();
        y = 16;
      }
      doc.text(line, margin, y);
      y += 5;
    });

    y += 6;
  });

  doc.save("sectionminer-result.pdf");
}

function applyDefaultPresetValue() {
  const presetDefault = presetInput.dataset.default || "";
  if (presetDefault.trim()) {
    presetInput.value = presetDefault;
  }
}

applyDefaultPresetValue();
renderEmptySections();

btnExportJson.addEventListener("click", downloadJSON);
btnExportPdf.addEventListener("click", downloadPDF);
detailClose.addEventListener("click", closeModal);
detailModal.addEventListener("click", (event) => {
  if (event.target === detailModal.firstElementChild) {
    closeModal();
  }
});
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeModal();
});

prevPageBtn.addEventListener("click", async () => {
  if (!state.pdfDoc || state.pageNumber <= 1) return;
  state.pageNumber -= 1;
  await renderPage();
});

nextPageBtn.addEventListener("click", async () => {
  if (!state.pdfDoc || state.pageNumber >= state.pageCount) return;
  state.pageNumber += 1;
  await renderPage();
});

window.addEventListener("resize", () => {
  if (state.pdfDoc) {
    renderPage().catch(() => {});
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!input.files.length) {
    setStatus("Selecione um PDF.", "amber");
    return;
  }

  const file = input.files[0];
  const presetValues = parsePresetValues(presetInput.value);

  resetMetrics();
  renderEmptySections();
  setStatus("Processando documento…", "blue");
  state.sections = [];
  state.selectedSection = null;
  state.payload = null;

  const formData = new FormData();
  formData.append("file", file);
  if (presetInput.value.trim()) {
    formData.append("preset_sections", presetInput.value.trim());
  }
  presetValues.forEach((item) => formData.append("preset_section", item));

  try {
    const response = await fetch("/api/extract", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let message = "Falha na extração.";
      try {
        const payload = await response.json();
        message = payload.detail || message;
      } catch {
        message = await response.text();
      }
      throw new Error(message);
    }

    const payload = await response.json();
    state.payload = payload;
    state.sections = payload.sections || [];
    state.selectedSection = null;

    updateMetrics(payload);
    renderSections();
    await loadPdf(payload.pdf_url);

    setStatus(`Extração concluída: ${payload.filename}`, "green");
  } catch (error) {
    console.error(error);
    setStatus(error.message || "Erro durante a extração.", "red");
    resetMetrics();
  }
});

