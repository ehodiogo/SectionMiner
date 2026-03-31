from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatLiteLLM
from typing import Any, cast
from sectionminer.prompts import MERGE_TREE_PROMPT
import re

class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", max_tokens: int = 8000, use_litellm: bool = False):
        print("Model ", model)
        if not use_litellm:
            self.llm = ChatOpenAI(
                model=model,
                api_key=cast(Any, api_key),
                temperature=0,
                max_tokens=max_tokens,
            )
        else:
            self.llm = ChatLiteLLM(
                model=model,
                api_key=api_key,
                temperature=0,
                max_tokens=max_tokens,
            )

        self.parser = JsonOutputParser()

    def _normalise(self, text: str) -> str:
        """Strip numbering, lowercase, remove diacritics, collapse spaces."""
        import unicodedata
        # strip leading numbering like "3.", "2.1", "III. "
        text = re.sub(r"^[\dIVXivx]+(?:[\.\d]*)\s*[-–—]?\s*", "", text.strip())
        text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", " ", text).lower().strip()

    def _matches_preset(self, title: str, preset_norms: list[str]) -> bool:
        norm = self._normalise(title)
        return any(norm == p or norm.startswith(p) for p in preset_norms)

    def _filter_by_presets(self, node: dict, preset_norms: list[str]) -> dict:
        """Post-LLM safety net: remove any node not matching a preset."""
        filtered_children = []
        for child in node.get("children", []):
            if self._matches_preset(child["title"], preset_norms):
                # keep, and filter its own children too
                filtered_child = dict(child)
                filtered_child["children"] = [
                    gc for gc in child.get("children", [])
                    if self._matches_preset(gc["title"], preset_norms)
                ]
                filtered_children.append(filtered_child)
            # else: silently drop
        return {**node, "children": filtered_children}

    def _run(self, chain, inputs: dict) -> tuple[dict, dict]:
        with get_openai_callback() as cb:
            result = chain.invoke(inputs)
            usage = {
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_tokens": cb.total_tokens,
                "cost_usd": cb.total_cost,
            }
        return result, usage

    def _sanitize_tree(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return {"title": "Document", "children": []}

        def clean_title(value) -> str | None:
            if not isinstance(value, str):
                return None
            t = " ".join(value.split()).strip()
            if len(t) < 2 or len(t) > 140:
                return None
            return t

        def clean_nodes(nodes: list, depth: int) -> list:
            if not isinstance(nodes, list):
                return []
            cleaned = []
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                title = clean_title(node.get("title"))
                if not title:
                    continue
                children = clean_nodes(node.get("children", []), depth + 1) if depth < 2 else []
                cleaned.append({"title": title, "children": children})
            return cleaned

        root_title = clean_title(data.get("title")) or "Document"
        return {
            "title": root_title,
            "children": clean_nodes(data.get("children", []), 1),
        }

    def merge_trees(
        self,
        heading_index: list,
        preset_sections: list[str] | None = None,
        allowed_titles: list[str] | None = None,
    ) -> tuple[dict, dict]:
        preset_sections = preset_sections or []
        allowed_titles = allowed_titles or []
        preset_instructions = "(No preset filter — include all headings using the standard rules below.)"
        if preset_sections:
            bullet_list = "\n".join(f"- {item}" for item in preset_sections)
            preset_instructions = (
                "════════════════════════════════════════════════════════\n"
                "## PRESET FILTER — OVERRIDES ALL OTHER RULES\n"
                "════════════════════════════════════════════════════════\n"
                "This block takes absolute priority over the PRIME DIRECTIVE,\n"
                "DECISION ORDER, and all rules below.\n\n"
                "PRESET LIST (the ONLY sections allowed in the output):\n"
                f"{bullet_list}\n\n"
                "BEFORE applying any other rule, apply these steps:\n\n"
                "F0. For EVERY heading in the input, run the preset match test:\n"
                "    Normalise the heading title by:\n"
                "      (a) stripping leading numbering ('3.', '2.1 —', 'III.')\n"
                "      (b) folding to lowercase\n"
                "      (c) removing diacritics ('Introdução'→'introducao')\n"
                "      (d) collapsing whitespace\n"
                "    Then normalise each preset name the same way.\n"
                "    A heading MATCHES if its normalised title:\n"
                "      — equals a normalised preset name, OR\n"
                "      — starts with a normalised preset name\n\n"
                "F1. If a heading MATCHES → include it (still apply merging rules 13–15\n"
                "    and ordering rules 16–19, but skip all discard rules).\n\n"
                "F2. If a heading does NOT match ANY preset → EXCLUDE it unconditionally.\n"
                "    Do not apply PRIME DIRECTIVE or any KEEP rule to non-matching headings.\n\n"
                "F3. If a preset name has no match in the input → omit it entirely.\n"
                "    NEVER fabricate a section absent from the input headings.\n\n"
                "F4. Subsections are included ONLY when their parent matched via F0.\n\n"
                "F5. SELF-CHECK (replaces rule 20 entirely when preset is active):\n"
                "    — Every node in the output matches at least one preset name.\n"
                "    — No node is absent from the input headings list.\n"
                "    — Nodes are ordered by start_anchor (rules 16–19).\n"
                "    — No preset name that had a match was omitted.\n"
                "    If any check fails, fix the output before returning.\n"
            )

        allowed_block = ""
        if allowed_titles:
            allowed_list = "\n".join(f"- {t}" for t in allowed_titles)
            allowed_block = (
                "\n\n### Allowed source headings (do not invent new ones)\n"
                "You MUST choose titles only from this list, or a preset title that clearly matches one of these headings. Never output a section that is not represented here.\n"
                f"{allowed_list}\n"
            )

        prompt = ChatPromptTemplate.from_template(MERGE_TREE_PROMPT)
        chain = prompt | self.llm | self.parser
        raw, usage = self._run(
            chain,
            {
                "trees": heading_index,
                "preset_sections": preset_instructions,
                "allowed_titles": allowed_block,
            },
        )
        sanitized = self._sanitize_tree(raw)
        if preset_sections:
            preset_norms = [self._normalise(p) for p in preset_sections]
            sanitized = self._filter_by_presets(sanitized, preset_norms)

        return sanitized, usage

