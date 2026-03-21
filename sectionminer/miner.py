import re
import unicodedata

import fitz

from sectionminer.client import LLMClient


class SectionMiner:
    def __init__(self, pdf: str, api_key: str, model: str = "gpt-4o-mini"):
        self.pdf = pdf
        self.api_key = api_key
        self.model = model
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
        # Common mojibake markers seen in PDFs with broken encoding.
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

        return self.full_text[start:end]

    def get_full_text(self) -> str:
        if self.full_text is None:
            raise ValueError("Execute extract_structure primeiro")
        return self.full_text

    def get_section_start_and_end_chars(self, title: str) -> tuple[int | None, int | None]:
        sec = self.get_section(title)
        if not sec:
            return None, None
        return sec["start"], sec["end"]

    def close(self) -> None:
        self.doc.close()


