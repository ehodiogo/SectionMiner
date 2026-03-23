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
const metricTokensEl = document.getElementById("metric-tokens");
const metricCostEl = document.getElementById("metric-cost");
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
  const tokens = metrics.total_tokens ?? payload.usage?.total_tokens ?? 0;
  const cost = metrics.cost_usd ?? payload.usage?.cost_usd ?? 0;
  const backend = formatBackendName(payload.extraction_backend);
  const modeLabel = payload.heuristic_only ? "Heuristica" : "LLM";

  backendBadgeEl.textContent = `${backend} - ${modeLabel}`;
  metricPagesEl.textContent = String(pages);
  metricSectionsEl.textContent = String(sections);
  metricTokensEl.textContent = String(tokens);
  metricCostEl.textContent = `$${Number(cost).toFixed(6)}`;
}

function resetMetrics() {
  backendBadgeEl.textContent = "-";
  metricPagesEl.textContent = "-";
  metricSectionsEl.textContent = "-";
  metricTokensEl.textContent = "-";
  metricCostEl.textContent = "-";
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
    console.log("No section selected or viewport not ready");
    return;
  }

  const locations = state.selectedSection.locations || [];
  console.log(
    `[Highlight] Section: "${state.selectedSection.title}"`,
    `| Current page (viewer): ${state.pageNumber}`,
    `| Total locations: ${locations.length}`,
    `| Locations:`,
    locations
  );

  const pageLocations = locations.filter((item) => item.page === state.pageNumber - 1);
  console.log(`[Highlight] Matches for page ${state.pageNumber - 1}: ${pageLocations.length}`);

  if (pageLocations.length === 0) {
    console.log(`[Highlight] No highlights on this page. Section appears on pages:`, 
      locations.map(l => l.page + 1).filter((v, i, a) => a.indexOf(v) === i));
    return;
  }

  for (const location of pageLocations) {
    const [x0, y0, x1, y1] = location.bbox;
    const left = x0 * state.viewport.scale;
    const top = y0 * state.viewport.scale;
    const width = (x1 - x0) * state.viewport.scale;
    const height = (y1 - y0) * state.viewport.scale;

    console.log(
      `[Highlight] Creating box: left=${left.toFixed(1)}, top=${top.toFixed(1)}, ` +
      `width=${width.toFixed(1)}, height=${height.toFixed(1)}, scale=${state.viewport.scale}`
    );

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
  title.textContent = `${index + 1}. ${section.title}`;

  const text = document.createElement("pre");
  text.textContent = section.text || "(Sem texto encontrado)";

  card.appendChild(title);
  card.appendChild(text);

  card.addEventListener("click", async () => {
    state.selectedSection = section;
    document.querySelectorAll(".section-card").forEach((el) => el.classList.remove("active"));
    card.classList.add("active");

    console.log(`[Click] Selected section: "${section.title}"`);

    const firstLocation = (section.locations || [])[0];
    if (firstLocation && state.pdfDoc) {
      console.log(`[Click] Jumping to page ${firstLocation.page + 1}`);
      state.pageNumber = firstLocation.page + 1;
      await renderPage();
    } else {
      console.log(`[Click] No locations found, just drawing highlights on current page`);
      drawHighlights();
    }
  });

  return card;
}

function renderSections() {
  sectionsEl.innerHTML = "";

  if (!state.sections.length) {
    sectionsEl.textContent = "Nenhuma secao encontrada.";
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

