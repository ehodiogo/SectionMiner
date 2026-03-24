import re
import unicodedata
import json
import fitz
from sectionminer.client import LLMClient


def _normalize_bbox(value) -> list[float] | None:
    if not value or len(value) != 4:
        return None
    return [float(value[0]), float(value[1]), float(value[2]), float(value[3])]


def _sanitize_text(text: str) -> str:
    """Remove control characters that break JSON serialization."""
    if not isinstance(text, str):
        return str(text)
    return "".join(c for c in text if ord(c) >= 32 or c in "\n\t\r")


def _compact_text(text: str) -> str:
    """Collapse excessive whitespace without losing paragraph breaks."""
    if not isinstance(text, str):
        text = str(text)
    text = _sanitize_text(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_json_array_text(raw_text: str) -> str:
    """Extract the first JSON array-like block from model output."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    start = text.find("[")
    if start == -1:
        return text

    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]

    return text[start:]


class SectionMiner:
    SUPPORTED_BACKENDS = ("pymupdf", "gemini")

    def __init__(
        self,
        pdf: str,
        api_key: str,
        model: str = "gpt-4o-mini",
        extraction_backend: str = "pymupdf",
        gemini_api_key: str | None = None,
        gemini_model: str = "gemini-2.0-flash",
    ):
        if extraction_backend not in self.SUPPORTED_BACKENDS:
            raise ValueError(
                f"extraction_backend deve ser um de {self.SUPPORTED_BACKENDS}, "
                f"recebido: {repr(extraction_backend)}"
            )

        self.pdf = pdf
        self.api_key = api_key
        self.model = model
        self.extraction_backend = extraction_backend
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.doc = fitz.open(pdf)
        self.client: LLMClient | None = None

        self.full_text: str | None = None
        self.structure: dict | None = None
        self.blocks: list | None = None
        self.offsets: list | None = None
        self.sections: list | None = None
        self.section_structures: dict | None = None

    def normalize(self, text: str) -> str:
        return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()

    def _fix_unicode(self, text: str) -> str:
        return unicodedata.normalize("NFC", text)

    def _is_corrupted(self, text: str) -> bool:
        return "\u00e2\u20ac" in text or "\ufffd" in text

    def _is_noise_heading(self, text: str) -> bool:
        t = text.strip()
        low = self.normalize(t)

        if len(t) < 3 or len(t) > 140:
            return True
        if t.endswith((".", ";", ":", "?", "!")):
            return True
        if len(t.split()) > 16:
            return True
        if re.match(r"^(figura|tabela|table|figure)\b", low):
            return True
        if re.match(r"^\d+$", t):
            return True

        return False

    def _looks_like_heading(self, offset: dict, threshold: float) -> bool:
        text = offset["text"].strip()
        if self._is_noise_heading(text):
            return False

        has_numbering = bool(re.match(r"^\d+(?:\.\d+)*\s+\w", text))
        has_dash_prefix = bool(re.match(r"^[-–—]\s*\w", text))
        is_allcaps = text.isupper() and len(text.split()) <= 5
        is_styled = offset["size"] >= threshold and "bold" in offset["font"].lower()

        return has_numbering or has_dash_prefix or is_allcaps or is_styled

    def extract_blocks(self) -> list:
        blocks = []

        for page_num in range(self.doc.page_count):
            page = self.doc[page_num]
            data = page.get_text("dict")

            for block in data["blocks"]:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        raw_text = span.get("text", "")
                        if not raw_text or not raw_text.strip():
                            continue

                        text = self._fix_unicode(raw_text)
                        text = _sanitize_text(text)
                        if self._is_corrupted(text):
                            continue

                        text = text.strip()
                        if not text:
                            continue

                        blocks.append(
                            {
                                "text": text,
                                "size": span["size"],
                                "font": span["font"],
                                "page": page_num,
                                "bbox": _normalize_bbox(span.get("bbox")),
                            }
                        )

        self.blocks = blocks
        return blocks

    def build_full_text(self) -> str:
        full_text = ""
        offsets = []

        for b in self.blocks:
            start = len(full_text)
            full_text += b["text"] + "\n"
            end = len(full_text)

            offsets.append(
                {
                    "text": b["text"],
                    "start": start,
                    "end": end,
                    "size": b["size"],
                    "font": b["font"],
                    "page": b.get("page"),
                    "bbox": b.get("bbox"),
                }
            )

        self.full_text = full_text
        self.offsets = offsets
        return full_text

    def _extract_text_gemini(self) -> list[dict]:
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise ImportError(
                "O backend 'gemini' requer o pacote google-genai. "
                "Instale com: pip install google-genai"
            ) from exc

        key = self.gemini_api_key or self.api_key
        client = genai.Client(api_key=key)

        with open(self.pdf, "rb") as fh:
            pdf_bytes = fh.read()

        response = client.models.generate_content(
            model=self.gemini_model,
            contents=[
                genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                """
                Analyse this PDF and return a JSON array of text spans.
                For each line of text, return an object with:
                - "text": the exact text content
                - "size": estimated font size as a float (body text ~= 10-12,
                          headings ~= 14-18, titles ~= 18+)
                - "font": inferred font style - use "Bold" if the text appears
                          bold, "Italic" if italic, "BoldItalic" if both,
                          or "Regular" otherwise
                - "page": page number (0-indexed)

                Rules:
                - Skip empty lines, page numbers, headers/footers.
                - Preserve document order exactly.
                - Return raw JSON array only.
                """,
            ],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "size": {"type": "number"},
                            "font": {"type": "string"},
                            "page": {"type": "integer"},
                            "bbox": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 4,
                                "maxItems": 4,
                            },
                        },
                        "required": ["text", "size", "font", "page"],
                    },
                },
            ),
        )

        # 1) Structured response when response_schema is honored
        parsed_response = getattr(response, "parsed", None)
        if parsed_response:
            if isinstance(parsed_response, list):
                return parsed_response
            if isinstance(parsed_response, dict) and isinstance(parsed_response.get("parsed"), list):
                return parsed_response["parsed"]

        # 2) Parsed parts inside candidates
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            if not content:
                continue
            for part in getattr(content, "parts", []) or []:
                part_parsed = getattr(part, "parsed", None)
                if isinstance(part_parsed, list):
                    return part_parsed

        # 3) Text-based fallback
        raw = getattr(response, "text", "") or ""
        raw = raw.strip()

        if not raw:
            chunks: list[str] = []
            for candidate in getattr(response, "candidates", []) or []:
                content = getattr(candidate, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", []) or []:
                    piece = getattr(part, "text", None)
                    if piece:
                        chunks.append(piece)
            raw = "\n".join(chunks).strip()

        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError as e:
            candidate_text = _extract_json_array_text(raw)
            raw_sanitized = _sanitize_text(candidate_text)
            try:
                parsed = json.loads(raw_sanitized)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError as inner:
                raise ValueError(
                    "Failed to parse Gemini response as JSON. "
                    f"Original error: {e}. Fallback error: {inner}."
                ) from inner

    def _build_full_text_from_gemini(self) -> str:
        try:
            spans = self._extract_text_gemini()
        except ValueError:
            # Fallback to local PyMuPDF extraction if Gemini returns malformed JSON.
            self.extract_blocks()
            self.build_full_text()
            return self.full_text
        full_text = ""
        offsets = []

        for span in spans:
            text = span.get("text", "").strip()
            text = _sanitize_text(text)
            if not text:
                continue

            start = len(full_text)
            full_text += text + "\n"
            end = len(full_text)

            offsets.append(
                {
                    "text": text,
                    "start": start,
                    "end": end,
                    "size": float(span.get("size", 12.0)),
                    "font": span.get("font", "Regular"),
                    "page": int(span.get("page", -1)),
                    "bbox": _normalize_bbox(span.get("bbox")),
                }
            )

        self.full_text = full_text
        self.offsets = offsets
        return full_text

    def _detect_threshold(self) -> float:
        sizes = [b["size"] for b in self.offsets]
        avg = sum(sizes) / len(sizes)
        return avg + 0.5

    def detect_headings(self) -> list:
        threshold = self._detect_threshold()
        headings = []
        seen: set[str] = set()

        for o in self.offsets:
            if not self._looks_like_heading(o, threshold):
                continue

            key = self.normalize(o["text"])
            if key in seen:
                continue

            seen.add(key)
            headings.append(o)

        return headings

    def build_sections(self) -> list:
        headings = self.detect_headings()
        sections = []

        for i, h in enumerate(headings):
            start = h["start"]
            end = headings[i + 1]["start"] if i + 1 < len(headings) else len(self.full_text)

            title = h["text"].strip()
            has_numbering = re.match(r"^(\d+(?:\.\d+)*)", title)
            numbering_depth = len(re.findall(r"\.", has_numbering.group(1))) + 1 if has_numbering else 1
            level = 2 if numbering_depth >= 2 else 1

            sections.append(
                {
                    "title": title,
                    "level": level,
                    "start": start,
                    "end": end,
                    "text": self.full_text[start:end],
                }
            )

        self.section_structures = sections
        return sections

    def extract_structure(self, return_tokens: bool = False):
        if self.extraction_backend == "gemini":
            self._build_full_text_from_gemini()
        else:
            self.extract_blocks()
            self.build_full_text()

        self.build_sections()
        self.client = LLMClient(api_key=self.api_key, model=self.model, max_tokens=4096)

        heading_index = []
        for s in self.section_structures:
            start_anchor = self.full_text[s["start"] : s["start"] + 60].strip()
            end_anchor = self.full_text[max(0, s["end"] - 60) : s["end"]].strip()
            heading_index.append(
                {
                    "title": s["title"],
                    "level": s["level"],
                    "start_anchor": start_anchor,
                    "end_anchor": end_anchor,
                }
            )

        result, usage = self.client.merge_trees(heading_index)
        self._inject_positions(result)

        self.structure = result
        self.sections = (self.structure, usage) if return_tokens else self.structure
        return (self.structure, usage) if return_tokens else self.structure

    def _inject_positions(self, node: dict) -> None:
        title = node.get("title", "")

        if title and title != "Document":
            sec = self._find_section_by_title(title)

            if sec is None:
                anchor = node.get("start_anchor", "")
                if anchor and self.full_text:
                    idx = self.full_text.find(anchor)
                    if idx != -1:
                        sec = min(
                            self.section_structures,
                            key=lambda s: abs(s["start"] - idx),
                        )

            if sec:
                node["start_char"] = sec["start"]
                node["end_char"] = sec["end"]
            else:
                node["start_char"] = None
                node["end_char"] = None

        children = node.get("children", [])
        for child in children:
            self._inject_positions(child)

        for i, child in enumerate(children):
            if child.get("end_char") is None:
                next_start = children[i + 1].get("start_char") if i + 1 < len(children) else len(self.full_text)
                child["end_char"] = next_start

        if children:
            last_child_end = children[-1].get("end_char")
            if last_child_end is not None:
                current_end = node.get("end_char")
                if current_end is None or last_child_end > current_end:
                    node["end_char"] = last_child_end

    def _find_section_by_title(self, title: str) -> dict | None:
        norm = self.normalize(title)

        for s in self.section_structures:
            if self.normalize(s["title"]) == norm:
                return s

        for s in self.section_structures:
            s_norm = self.normalize(s["title"])
            if norm in s_norm or s_norm in norm:
                return s

        return None

    def _find_in_tree(self, node: dict, title: str) -> dict | None:
        if self.normalize(node.get("title", "")) == self.normalize(title):
            return node
        for child in node.get("children", []):
            found = self._find_in_tree(child, title)
            if found:
                return found
        return None

    def _find_partial_in_tree(self, node: dict, norm: str) -> dict | None:
        n_norm = self.normalize(node.get("title", ""))
        if norm in n_norm or n_norm in norm:
            return node
        for child in node.get("children", []):
            found = self._find_partial_in_tree(child, norm)
            if found:
                return found
        return None

    def get_section(self, title: str) -> dict | None:
        if not self.section_structures:
            raise ValueError("Execute extract_structure primeiro")
        return self._find_section_by_title(title)

    def get_sections(self) -> list | None:
        if not self.section_structures:
            raise ValueError("Execute extract_structure primeiro")

        def extract_titles(node):
            result = {"title": node["title"]}
            if node.get("children"):
                result["children"] = [extract_titles(child) for child in node["children"]]
            if isinstance(result, dict):
                result = result["title"]
            return result

        self.sections = [extract_titles(s) for s in self.section_structures]
        return self.sections

    def get_section_text(self, title: str) -> str | None:
        if not self.structure:
            raise ValueError("Execute extract_structure primeiro")

        node = self._find_in_tree(self.structure, title)
        if node is None:
            node = self._find_partial_in_tree(self.structure, self.normalize(title))
        if node is None:
            return None

        start = node.get("start_char")
        end = node.get("end_char")

        if start is None or end is None:
            return None

        return _compact_text(self.full_text[start:end])

    def get_full_text(self, normalize_whitespace: bool = False) -> str:
        if self.full_text is None:
            raise ValueError("Execute extract_structure primeiro")
        return _compact_text(self.full_text) if normalize_whitespace else self.full_text

    def get_section_start_and_end_chars(self, title: str) -> tuple[int | None, int | None]:
        sec = self.get_section(title)
        if not sec:
            return None, None
        return sec["start"], sec["end"]

    def get_locations_by_char_range(self, start: int, end: int, max_spans: int = 300) -> list[dict]:
        matches: list[dict] = []

        for offset in self.offsets or []:
            o_start = offset.get("start")
            o_end = offset.get("end")
            if o_start is None or o_end is None:
                continue
            if o_end <= start or o_start >= end:
                continue

            page = offset.get("page")
            bbox = offset.get("bbox")
            if page is None or page < 0:
                continue
            if not bbox:
                continue

            matches.append(
                {
                    "page": int(page),
                    "bbox": [float(v) for v in bbox],
                    "text": offset.get("text", ""),
                    "start_char": int(o_start),
                    "end_char": int(o_end),
                }
            )
            if len(matches) >= max_spans:
                break

        return matches

    def get_section_locations(self, title: str, max_spans: int = 300) -> list[dict]:
        sec = self.get_section(title)
        if not sec:
            return []
        return self.get_locations_by_char_range(sec["start"], sec["end"], max_spans=max_spans)

    def close(self) -> None:
        self.doc.close()