import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/build/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/build/pdf.worker.min.mjs";

const form = document.getElementById("upload-form");
const input = document.getElementById("pdf-input");
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

const state = {
  pdfDoc: null,
  pageNumber: 1,
  pageCount: 0,
  viewport: null,
  sections: [],
  selectedSection: null,
};

function compactText(value) {
  return (value || "")
    .replace(/\s+/g, " ")
    .replace(/\s*\n\s*/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function formatBackendName(value) {
  if (value === "gemini") {
    return "Gemini";
  }
  if (value === "pymupdf") {
    return "PyMuPDF";
  }
  return value || "-";
}

function updateMetrics(payload) {
  const metrics = payload.metrics || {};
  const pages = metrics.pages ?? payload.pages ?? 0;
  const sections = metrics.sections ?? (payload.sections || []).length;
  const backend = formatBackendName(payload.extraction_backend);
  const modeLabel = payload.heuristic_only ? "Heuristica" : "LLM";

  backendBadgeEl.textContent = `${backend} - ${modeLabel}`;
  metricPagesEl.textContent = String(pages);
  metricSectionsEl.textContent = String(sections);
  metricBackendEl.textContent = backend;
}

function resetMetrics() {
  backendBadgeEl.textContent = "-";
  metricPagesEl.textContent = "-";
  metricSectionsEl.textContent = "-";
  metricBackendEl.textContent = "-";
}

async function renderPage() {
  if (!state.pdfDoc) {
    return;
  }

  const page = await state.pdfDoc.getPage(state.pageNumber);
  const viewport = page.getViewport({ scale: 1.2 });
  const ctx = canvas.getContext("2d");

  canvas.width = viewport.width;
  canvas.height = viewport.height;
  overlay.style.width = `${viewport.width}px`;
  overlay.style.height = `${viewport.height}px`;
  overlay.style.position = "absolute";
  overlay.style.top = "0";
  overlay.style.left = "0";

  state.viewport = viewport;
  pageInfoEl.textContent = `Pagina ${state.pageNumber} / ${state.pageCount}`;

  await page.render({ canvasContext: ctx, viewport }).promise;
  drawHighlights();
}

function drawHighlights() {
  overlay.innerHTML = "";

  if (!state.selectedSection || !state.viewport) {
    return;
  }

  const locations = state.selectedSection.locations || [];
  const pageLocations = locations.filter((item) => item.page === state.pageNumber - 1);
  if (pageLocations.length === 0) return;

  for (const location of pageLocations) {
    if (!Array.isArray(location.bbox) || location.bbox.length !== 4) {
      continue;
    }
    const [x0, y0, x1, y1] = location.bbox;
    const [vx0, vy0, vx1, vy1] = state.viewport.convertToViewportRectangle([x0, y0, x1, y1]);
    const left = Math.min(vx0, vx1);
    const top = Math.min(vy0, vy1);
    const width = Math.abs(vx1 - vx0);
    const height = Math.abs(vy1 - vy0);

    const box = document.createElement("div");
    box.className = "highlight-box";
    box.style.left = `${left}px`;
    box.style.top = `${top}px`;
    box.style.width = `${Math.max(width, 2)}px`;
    box.style.height = `${Math.max(height, 2)}px`;
    overlay.appendChild(box);
  }
}

function buildSectionCard(section, index) {
  const card = document.createElement("article");
  card.className = "section-card";
  card.style.marginLeft = `${(section.level - 1) * 12}px`;

  const title = document.createElement("h3");
  title.textContent = `${index + 1}. ${compactText(section.title || "(Sem titulo)")}`;

  const text = document.createElement("pre");
  text.textContent = compactText(section.text) || "(Sem texto encontrado)";

  card.appendChild(title);
  card.appendChild(text);

  card.addEventListener("click", async () => {
    state.selectedSection = section;
    document.querySelectorAll(".section-card").forEach((el) => el.classList.remove("active"));
    card.classList.add("active");

    const firstLocation = (section.locations || [])[0];
    if (firstLocation && state.pdfDoc) {
      state.pageNumber = firstLocation.page + 1;
      await renderPage();
    } else {
      drawHighlights();
    }
  });

  return card;
}

function renderSections() {
  sectionsEl.innerHTML = "";

  if (!state.sections.length) {
    sectionsEl.innerHTML = `
      <div class="empty-state">
        <p class="text-sm font-semibold text-slate-800">Nenhuma secao ainda</p>
        <p class="text-sm text-slate-600">Envie um PDF para ver as secoes consolidadas sem espacamentos quebrados.</p>
      </div>
    `;
    return;
  }

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

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!input.files.length) {
    statusEl.textContent = "Selecione um PDF.";
    return;
  }

  statusEl.textContent = "Processando documento...";
  sectionsEl.innerHTML = "";
  overlay.innerHTML = "";
  resetMetrics();

  const formData = new FormData();
  formData.append("file", input.files[0]);

  try {
    const response = await fetch("/api/extract", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Erro ao extrair secoes");
    }

    const payload = await response.json();
    state.sections = payload.sections || [];
    state.selectedSection = null;

    renderSections();
    await loadPdf(payload.pdf_url);
    updateMetrics(payload);

    const backend = formatBackendName(payload.extraction_backend);
    statusEl.textContent = `OK: ${payload.filename} | backend=${backend}`;
  } catch (error) {
    statusEl.textContent = `Falha: ${error.message}`;
    resetMetrics();
  }
});

prevPageBtn.addEventListener("click", async () => {
  if (!state.pdfDoc || state.pageNumber <= 1) {
    return;
  }
  state.pageNumber -= 1;
  await renderPage();
});

nextPageBtn.addEventListener("click", async () => {
  if (!state.pdfDoc || state.pageNumber >= state.pageCount) {
    return;
  }
  state.pageNumber += 1;
  await renderPage();
});

