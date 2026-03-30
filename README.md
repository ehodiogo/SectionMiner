<div align="center">

<br/>

```
███████╗███████╗ ██████╗████████╗██╗ ██████╗ ███╗   ██╗
██╔════╝██╔════╝██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║
███████╗█████╗  ██║        ██║   ██║██║   ██║██╔██╗ ██║
╚════██║██╔══╝  ██║        ██║   ██║██║   ██║██║╚██╗██║
███████║███████╗╚██████╗   ██║   ██║╚██████╔╝██║ ╚████║
╚══════╝╚══════╝ ╚═════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
███╗   ███╗██╗███╗   ██╗███████╗██████╗
████╗ ████║██║████╗  ██║██╔════╝██╔══██╗
██╔████╔██║██║██╔██╗ ██║█████╗  ██████╔╝
██║╚██╔╝██║██║██║╚██╗██║██╔══╝  ██╔══██╗
██║ ╚═╝ ██║██║██║ ╚████║███████╗██║  ██║
╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
```

**Extract sections and subsections from academic PDFs — powered by layout heuristics and LLM consolidation.**

<br/>

[![PyPI version](https://img.shields.io/pypi/v/sectionminer?style=flat-square&color=0a0a0a&labelColor=f5f5f5)](https://pypi.org/project/sectionminer/)
[![Python](https://img.shields.io/pypi/pyversions/sectionminer?style=flat-square&color=0a0a0a&labelColor=f5f5f5)](https://pypi.org/project/sectionminer/)
[![License](https://img.shields.io/github/license/ehodiogo/SectionMiner?style=flat-square&color=0a0a0a&labelColor=f5f5f5)](LICENSE)
[![PyPI Downloads](https://img.shields.io/pypi/dm/sectionminer?style=flat-square&color=0a0a0a&labelColor=f5f5f5)](https://pypi.org/project/sectionminer/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

<br/>

[**Quickstart**](#-quickstart) · [**Installation**](#-installation) · [**Preset Sections**](#-preset-sections) · [**CLI**](#-cli) · [**API Reference**](#-api-reference) · [**Web UI**](#-web-ui) · [**Examples**](#-examples)

<br/>

</div>

---

## Overview

**SectionMiner** is a Python library for extracting structured sections and subsections from academic PDFs. It combines local layout analysis (font sizes, spans) with LLM-based tree consolidation to reliably identify section boundaries — even in complex, multi-column, or OCR-heavy documents.

```
PDF File  →  Text Extraction  →  Heading Detection  →  LLM Consolidation  →  Structured Tree
              (PyMuPDF / Gemini)   (font heuristics)    (OpenAI gpt-4o-mini)
```

### Extraction Backends

| Backend | Description | Best For |
|---------|-------------|----------|
| `pymupdf` *(default)* | Local text extraction using PDF layout spans | Clean, text-native PDFs |
| `gemini` | OCR and extraction via Google Gemini | Scanned docs, complex layouts |

> In both cases, LLM consolidation of the final section tree is handled by **OpenAI**.

---

## ✦ Quickstart

```python
import json
from sectionminer import SectionMiner

miner = SectionMiner("paper.pdf", api_key="sk-...")

try:
    structure, usage = miner.extract_structure(return_tokens=True)

    print(json.dumps(structure, indent=2, ensure_ascii=False))
    print(usage)  # { prompt_tokens, completion_tokens, cost_usd, ... }

    # Get text from a specific section
    print(miner.get_section_text("introduction"))

    # Or slice by character offsets
    start, end = miner.get_section_start_and_end_chars("introduction")
    print(miner.get_full_text()[start:end])
finally:
    miner.close()
```

---

## ⬇ Installation

**From PyPI:**

```bash
pip install sectionminer
```

**From source:**

```bash
git clone https://github.com/ehodiogo/SectionMiner.git
cd SectionMiner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Requirements

- Python **3.10+**
- `OPENAI_API_KEY` — required for LLM consolidation
- `GEMINI_API_KEY` — required only when using `extraction_backend="gemini"`

### API Keys

Via environment variable:

```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."      # optional, Gemini backend only
```

Or via `.env` in your project root:

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

---

## 🎯 Preset Sections

By default, SectionMiner extracts **all** sections it detects in the PDF. When you only need specific sections, use `preset_sections` to activate **filter mode** — the library will return only the sections whose titles match your list, ignoring everything else.

```python
miner = SectionMiner(
    "paper.pdf",
    api_key="sk-...",
    preset_sections=["Introdução", "Metodologia", "Conclusão"],
)

try:
    structure, usage = miner.extract_structure(return_tokens=True)
    print(miner.get_section_text("Introdução"))
finally:
    miner.close()
```

### How matching works

Matching is flexible and normalised — it strips leading numbering, folds casing, removes diacritics, and collapses whitespace before comparing. This means a preset of `"Introdução"` will match headings like `"-Introdução"`, `"1. INTRODUÇÃO"`, `"2.1 Introdução Geral"`, etc.

| Preset | Matches in PDF |
|--------|----------------|
| `"Introdução"` | `"-Introdução"`, `"1. INTRODUÇÃO"`, `"Introdução Geral"` |
| `"Metodologia"` | `"3. Metodologia"`, `"METODOLOGIA"`, `"2.3 Metodologia de Pesquisa"` |
| `"Conclusão"` | `"-CONCLUSÃO"`, `"Conclusão e Trabalhos Futuros"` |

### Key behaviours

- **No fabrication** — if a preset name has no match in the document, it is silently omitted. SectionMiner never invents sections.
- **Subsections follow their parent** — subsections are included only when their parent section was matched.
- **Document order preserved** — matched sections appear in the order they occur in the PDF, not in preset list order.
- **Double-filtered** — the LLM is instructed to filter, and a Python post-processing step removes any hallucinated nodes before results are returned.

### With Gemini backend

`preset_sections` works identically with both backends:

```python
miner = SectionMiner(
    "paper.pdf",
    api_key="sk-...",
    extraction_backend="gemini",
    gemini_api_key="AIza...",
    preset_sections=["Introdução"],
)

try:
    miner.extract_structure()
    print(miner.get_section_text("Introdução"))
finally:
    miner.close()
```

---

## ⌨ CLI

SectionMiner installs a `sectionminer` command.

```bash
sectionminer --help
```

### Extract section structure

```bash
# Full extraction with LLM consolidation
sectionminer extract paper.pdf --tokens --pretty

# Heuristic-only (no LLM / no API key needed)
sectionminer extract paper.pdf --heuristic-only --pretty

# Show cost estimate
sectionminer extract paper.pdf --show-cost --pretty

# Save output to JSON
sectionminer extract paper.pdf --output out.json --pretty
```

### Get text of a specific section

```bash
sectionminer section-text paper.pdf "introduction"

# With cost breakdown (printed to stderr, JSON unaffected)
sectionminer section-text paper.pdf "introduction" --show-cost

# Without LLM
sectionminer section-text paper.pdf "introduction" --heuristic-only
```

> **Note:** `--show-cost` outputs cost info to `stderr` so it never pollutes JSON output.

---

## 🌐 Web UI

SectionMiner includes a FastAPI-powered visual interface with real-time PDF rendering and section highlighting.

```bash
# Start with default PyMuPDF backend
sectionminer runserver --host 127.0.0.1 --port 8000 --reload

# Use Gemini for extraction
sectionminer runserver --extraction-backend gemini --gemini-model gemini-2.0-flash

# Heuristic-only (no LLM)
sectionminer runserver --heuristic-only
```

> Se o comando `sectionminer runserver` nao aparecer, atualize a instalacao local: `pip install -U .` ou `pip install -U sectionminer` dentro do seu ambiente virtual.

Open in your browser: **http://127.0.0.1:8000**

**Features:**
- Upload any PDF and view extracted sections in real time
- Click a section to highlight its exact location in the PDF viewer
- Dashboard shows: backend used, page count, section count, token usage, cost

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Visual UI |
| `POST` | `/api/extract` | Upload PDF, returns structured JSON |
| `GET` | `/api/files/{job_id}` | Stream the uploaded PDF for rendering |

<details>
<summary><strong>Sample <code>POST /api/extract</code> response</strong></summary>

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "paper.pdf",
  "pdf_url": "/api/files/3fa85f64-...",
  "extraction_backend": "pymupdf",
  "heuristic_only": false,
  "pages": 10,
  "metrics": {
    "pages": 10,
    "sections": 24,
    "prompt_tokens": 1800,
    "completion_tokens": 450,
    "total_tokens": 2250,
    "cost_usd": 0.00046
  },
  "sections": [
    {
      "title": "1. Introduction",
      "level": 1,
      "start_char": 0,
      "end_char": 1200,
      "text": "...",
      "locations": [
        { "page": 0, "bbox": [72.0, 120.0, 380.0, 138.0], "text": "..." }
      ]
    }
  ]
}
```

</details>

### Frontend styles (Tailwind)

The web UI CSS is built with Tailwind. Install the Node dev dependencies once, then build or watch:

```bash
npm install
npm run build:css   # one-off build
npm run dev:css     # watch mode
```

The entry stylesheet lives at `sectionminer/server/static/tailwind.css` and compiles to `sectionminer/server/static/styles.css` (served by FastAPI).

---

## 📖 API Reference

### `SectionMiner(path, api_key, **kwargs)`

```python
miner = SectionMiner(
    "paper.pdf",
    api_key="sk-...",                     # OpenAI API key
    extraction_backend="pymupdf",         # "pymupdf" | "gemini"
    gemini_api_key="...",                 # required if backend="gemini"
    gemini_model="gemini-2.5-flash-lite", # optional, default model
    preset_sections=["Introdução", "Metodologia"],  # optional filter
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str` | — | Path to the PDF file |
| `api_key` | `str` | — | OpenAI API key for LLM consolidation |
| `model` | `str` | `"gpt-4o-mini"` | OpenAI model to use |
| `extraction_backend` | `str` | `"pymupdf"` | `"pymupdf"` or `"gemini"` |
| `gemini_api_key` | `str` | `None` | Google Gemini API key |
| `gemini_model` | `str` | `"gemini-2.0-flash"` | Gemini model name |
| `preset_sections` | `list[str]` | `None` | If provided, return **only** sections matching these names |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `extract_structure(return_tokens=False)` | `dict` or `(dict, usage)` | Full extraction pipeline. Returns section tree. |
| `get_section_text(title)` | `str` | Retrieve text of a section by title (fuzzy match). |
| `get_section_start_and_end_chars(title)` | `(int, int)` | Character offsets for a section in the full text. |
| `get_full_text()` | `str` | Complete linearized text of the PDF. |
| `get_sections()` | `list[str]` | List of all detected section titles. |
| `close()` | `None` | Release the open PDF file handle. |

<details>
<summary><strong>Low-level pipeline methods</strong></summary>

| Method | Description |
|--------|-------------|
| `extract_blocks()` | Extract raw text spans from PDF |
| `build_full_text()` | Assemble linearized full text |
| `build_sections()` | Run heading detection heuristics |

Useful for debugging or custom pipelines.

</details>

---

## 🔌 Backends

### PyMuPDF *(default)*

```python
miner = SectionMiner("paper.pdf", api_key="sk-...")
```

Reads text directly from PDF layout data (font sizes, span positions). Fast, offline, no external API needed for extraction.

### Gemini

```python
miner = SectionMiner(
    "paper.pdf",
    api_key="sk-...",
    extraction_backend="gemini",
    gemini_api_key="...",
    gemini_model="gemini-2.5-flash-lite",
)
```

Sends the PDF to Google Gemini for OCR-based text extraction. Better for scanned documents or PDFs with unusual layouts.

---

## 💡 Examples

<details>
<summary><strong>Basic extraction</strong></summary>

```python
from sectionminer import SectionMiner

miner = SectionMiner("paper.pdf", api_key="sk-...")
try:
    structure, usage = miner.extract_structure(return_tokens=True)
    for section in miner.get_sections():
        print(f"→ {section}")
        print(miner.get_section_text(section)[:200])
        print()
finally:
    miner.close()
```

</details>

<details>
<summary><strong>Extract only specific sections (preset filter)</strong></summary>

```python
from sectionminer import SectionMiner

miner = SectionMiner(
    "paper.pdf",
    api_key="sk-...",
    preset_sections=["Introdução", "Metodologia", "Conclusão"],
)
try:
    miner.extract_structure()
    # Only matched sections are returned — no hallucination, no extras
    print(miner.get_section_text("Introdução"))
    print(miner.get_section_text("Metodologia"))
finally:
    miner.close()
```

</details>

<details>
<summary><strong>Preset sections with Gemini backend</strong></summary>

```python
from sectionminer import SectionMiner

miner = SectionMiner(
    "paper.pdf",
    api_key="sk-...",
    extraction_backend="gemini",
    gemini_api_key="AIza...",
    preset_sections=["Introdução"],
)
try:
    structure, usage = miner.extract_structure(return_tokens=True)
    print(usage)
    print(miner.get_section_text("Introdução"))
finally:
    miner.close()
```

</details>

<details>
<summary><strong>With Gemini backend (full extraction)</strong></summary>

```python
from sectionminer import SectionMiner

miner = SectionMiner(
    "paper.pdf",
    api_key="sk-...",
    extraction_backend="gemini",
    gemini_api_key="AIza...",
)
try:
    structure, usage = miner.extract_structure(return_tokens=True)
    print(usage)
    print(structure.get("title"))
finally:
    miner.close()
```

</details>

<details>
<summary><strong>Slice text by character offsets</strong></summary>

```python
miner = SectionMiner("paper.pdf", api_key="sk-...")
try:
    miner.extract_structure()
    start, end = miner.get_section_start_and_end_chars("conclusion")
    if start is not None:
        excerpt = miner.get_full_text()[start:end]
        print(excerpt[:500])
finally:
    miner.close()
```

</details>

---

## 💰 Cost Reference

Measured locally on `2026-03-21` using `gpt-4o-mini`:

| File           | Size | Pages | Tokens | Cost |
|----------------|------|-------|--------|------|
| `artigo_1.pdf` | 0.74 MB | 21 | 2,297 | `$0.000475` |
| `artigo_2.pdf` | 0.04 MB | 4 | 356 | `$0.000060` |

> Section text retrieval after extraction is **free** — it uses local character offsets.
> Using `preset_sections` reduces token usage further by limiting LLM output to matched sections only.

Reproduce with:
```bash
sectionminer extract paper.pdf --show-cost --pretty
```

---

## 🗂 Project Structure

```
SectionMiner/
├── sectionminer/
│   ├── __init__.py        # Public API
│   ├── miner.py           # SectionMiner class
│   ├── client.py          # LLM client + tree merge
│   ├── prompts.py         # Consolidation prompt
│   └── server/            # FastAPI + UI (routes, static, templates)
├── examples/
│   ├── basic_usage.py
│   └── api_smoke_test.py
├── files/                 # Sample PDFs
├── test.py                # PyMuPDF pipeline example
├── test_gemini.py         # Gemini pipeline example
└── requirements.txt
```

---

## 🐛 Troubleshooting

<details>
<summary><strong>"Invalid control character" when processing PDF</strong></summary>

The PDF contains invalid control characters that break JSON serialization.
The current version sanitizes these automatically. If the error persists, try a different PDF or validate it with a PDF reader.

</details>

<details>
<summary><strong>Sections are fragmented or broken</strong></summary>

- Review `_is_noise_heading` and `_looks_like_heading` in `sectionminer/miner.py`
- Adjust the threshold in `_detect_threshold` for your PDF's font pattern
- Two-column layouts, intrusive footers, and poor OCR quality increase detection errors

</details>

<details>
<summary><strong>Section not found by title</strong></summary>

- Try a variation without accents or in lowercase (search normalizes text)
- Inspect available titles with `miner.get_sections()`
- If using `preset_sections`, confirm the section actually exists in the PDF — presets with no match are silently omitted, never fabricated

</details>

<details>
<summary><strong>Preset section returns None text</strong></summary>

The section was matched by the LLM but `start_char` is null, meaning the title in `section_structures` differs from what the LLM returned. Debug with:

```python
miner.extract_structure()
for s in miner.section_structures:
    print(repr(s["title"]), s["start"])
```

Use the exact title shown there (or a close variation) in `preset_sections`.

</details>

<details>
<summary><strong>OpenAI key error</strong></summary>

- Confirm `OPENAI_API_KEY` is set in the same environment as your script
- If using `.env`, ensure it's in the project root

</details>

---

## 🗺 Roadmap

- [ ] Automated tests for `detect_headings`, `build_sections`, `get_section_text`
- [ ] Expose heuristic parameters via config (threshold, noise filters).
- [x] CLI: `sectionminer extract file.pdf --output out.json`
- [x] Heuristic-only mode (no LLM, fully offline)
- [x] Improved merge — keeps only valid sections/subsections without broken fragments
- [x] Web UI with PDF viewer and section highlighting
- [x] Preset sections filter — extract only named sections with flexible normalised matching

---

## 📄 License

[MIT](LICENSE) © [ehodiogo](https://github.com/ehodiogo)

---

<div align="center">

Made with ♥ for researchers who'd rather spend time reading papers than parsing them.

**[⬆ back to top](#)**

</div>