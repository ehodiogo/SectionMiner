import fitz
from client import LLMClient
import unicodedata
import re


class SectionMiner:

    def __init__(self, pdf: str, api_key: str):
        self.pdf = pdf
        self.doc = fitz.open(pdf)
        self.client = LLMClient(api_key)

        self.full_text = None
        self.structure = None
        self.blocks = None
        self.offsets = None
        self.sections = None

    def normalize(self, text: str) -> str:
        return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()

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

    def _fix_unicode(self, text: str) -> str:
        return unicodedata.normalize("NFC", text)

    def _is_corrupted(self, text: str) -> bool:
        return "â€" in text or "\ufffd" in text

    def _looks_like_heading(self, offset: dict, threshold: float) -> bool:
        text = offset["text"].strip()
        if self._is_noise_heading(text):
            return False

        has_numbering = bool(re.match(r"^\d+(?:\.\d+)*\s+", text))
        style_hint = (
            offset["size"] >= threshold
            or "bold" in offset["font"].lower()
            or text.isupper()
        )

        return has_numbering or style_hint

    def extract_blocks(self):
        blocks = []

        for page_num, page in enumerate(self.doc):
            data = page.get_text("dict")

            for block in data["blocks"]:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        if "text" not in span:
                            continue

                        raw_text = span["text"]

                        if not raw_text or not raw_text.strip():
                            continue

                        text = self._fix_unicode(raw_text)

                        if self._is_corrupted(text):
                            continue

                        text = text.strip()

                        if not text:
                            continue

                        blocks.append({
                            "text": text,
                            "size": span["size"],
                            "font": span["font"],
                            "page": page_num
                        })

        self.blocks = blocks
        return blocks

    def build_full_text(self):
        full_text = ""
        offsets = []

        for b in self.blocks:
            start = len(full_text)
            full_text += b["text"] + "\n"
            end = len(full_text)

            offsets.append({
                "text": b["text"],
                "start": start,
                "end": end,
                "size": b["size"],
                "font": b["font"]
            })

        self.full_text = full_text
        self.offsets = offsets
        return full_text

    def _detect_threshold(self):
        sizes = [b["size"] for b in self.offsets]
        avg = sum(sizes) / len(sizes)
        return avg + 0.5

    def detect_headings(self):
        threshold = self._detect_threshold()
        headings = []
        seen = set()

        for o in self.offsets:
            if not self._looks_like_heading(o, threshold):
                continue

            key = self.normalize(o["text"])
            if key in seen:
                continue

            seen.add(key)
            headings.append(o)

        return headings

    def build_sections(self):
        headings = self.detect_headings()
        sections = []

        for i, h in enumerate(headings):
            start = h["start"]
            end = (
                headings[i + 1]["start"]
                if i + 1 < len(headings)
                else len(self.full_text)
            )

            title = h["text"].strip()
            has_numbering = re.match(r"^(\d+(?:\.\d+)*)", title)
            numbering_depth = len(re.findall(r"\.", has_numbering.group(1))) + 1 if has_numbering else 1
            level = 2 if numbering_depth >= 2 else 1

            sections.append({
                "title": title,
                "level": level,
                "start": start,
                "end": end,
                "text": self.full_text[start:end]
            })

        self.sections = sections
        return sections

    def extract_structure(self, return_tokens=False):
        self.extract_blocks()
        self.build_full_text()
        self.build_sections()

        heading_index = [
            {"title": s["title"], "level": s["level"]}
            for s in self.sections
        ]

        result, usage = self.client.merge_trees(heading_index)

        self._inject_positions_from_sections(result)

        self.structure = result
        return (self.structure, usage) if return_tokens else self.structure

    def _inject_positions_from_sections(self, node: dict):
        title = node.get("title", "")

        if title and title != "Document":
            sec = self._find_section_by_title(title)
            if sec:
                node["start_char"] = sec["start"]
                node["end_char"] = sec["end"]
            else:
                node["start_char"] = None
                node["end_char"] = None

        for child in node.get("children", []):
            self._inject_positions_from_sections(child)

    def _find_section_by_title(self, title: str) -> dict | None:
        norm = self.normalize(title)

        for s in self.sections:
            if self.normalize(s["title"]) == norm:
                return s

        for s in self.sections:
            s_norm = self.normalize(s["title"])
            if norm in s_norm or s_norm in norm:
                return s

        return None

    def get_section(self, title: str):
        if not self.sections:
            raise ValueError("Execute extract_structure primeiro")

        for s in self.sections:
            if self.normalize(s["title"]) == self.normalize(title):
                return s

        norm = self.normalize(title)
        for s in self.sections:
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

    def get_section_text(self, title: str) -> str | None:
        if not self.structure:
            raise ValueError("Execute extract_structure primeiro")

        node = self._find_in_tree(self.structure, title)
        if not node:
            def _find_partial(n, norm):
                n_norm = self.normalize(n.get("title", ""))
                if norm in n_norm or n_norm in norm:
                    return n
                for child in n.get("children", []):
                    found = _find_partial(child, norm)
                    if found:
                        return found
                return None

            node = _find_partial(self.structure, self.normalize(title))

        if not node:
            return None

        start = node.get("start_char")
        end = node.get("end_char")

        if start is None or end is None:
            return None

        return self.full_text[start:end]

    def close(self):
        self.doc.close()