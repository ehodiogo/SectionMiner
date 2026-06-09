import json
import re
from typing import Any, cast

from langchain_community.callbacks import get_openai_callback
from langchain_community.chat_models import ChatLiteLLM
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from sectionminer.prompts import MERGE_TREE_PROMPT


class LLMClient:

    def _get_model_config(self, model: str) -> dict:
        model = model.split("/")[-1]
        if model.startswith("gpt-5.1"):
            return {
                "temperature": 0,
                "reasoning_effort": "none",
            }
        elif model.startswith("gpt-5"):
            return {
                "temperature": 0,  # obrigatório
            }
        else:
            return {
                "temperature": 0,
            }

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", max_tokens: int = 8000, use_litellm: bool = False):
        print("Model ", model)
        config = self._get_model_config(model)
        print("Config ", config)

        if not use_litellm:
            self.llm = ChatOpenAI(
                model=model,
                api_key=cast(Any, api_key),
                max_tokens=max_tokens,
                **config,
            )
        else:
            self.llm = ChatLiteLLM(
                model=model,
                api_key=api_key,
                max_tokens=max_tokens,
                **config,
            )

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
        """Post-LLM safety net: keep only branches that match a preset."""

        def filter_node(current: dict, ancestor_kept: bool = False) -> dict | None:
            title = current.get("title", "")
            matches = self._matches_preset(title, preset_norms)
            keep_branch = ancestor_kept or matches

            children: list[dict] = []
            for child in current.get("children", []):
                filtered = filter_node(child, keep_branch)
                if filtered is not None:
                    children.append(filtered)

            if current.get("title") == "Document":
                return {**current, "children": children}

            if keep_branch or children:
                return {**current, "children": children}

            return None

        filtered = filter_node(node)
        return filtered or {"title": "Document", "children": []}

    def _extract_json_block(self, raw_text: str) -> str:
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```")
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        start_candidates = [idx for idx in (text.find("{"), text.find("[")) if idx != -1]
        if not start_candidates:
            return text

        start = min(start_candidates)
        opener = text[start]
        closer = "}" if opener == "{" else "]"

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
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]

        return text[start:]

    def _parse_tree_payload(self, raw_result: Any) -> dict:
        if isinstance(raw_result, dict):
            return raw_result

        if hasattr(raw_result, "content"):
            raw_result = getattr(raw_result, "content")

        if not isinstance(raw_result, str):
            raise ValueError(f"Unexpected LLM payload type: {type(raw_result)!r}")

        candidate = self._extract_json_block(raw_result)
        parsed = json.loads(candidate)
        if not isinstance(parsed, dict):
            raise ValueError("LLM output must be a JSON object")
        return parsed

    def _build_fallback_tree(self, heading_index: list[dict], preset_sections: list[str] | None = None) -> dict:
        root = {"title": "Document", "children": []}
        top_level: dict | None = None

        for item in heading_index:
            title = item.get("title")
            if not isinstance(title, str):
                continue
            title = title.strip()
            if not title:
                continue

            node = {"title": title, "children": []}
            level = int(item.get("level", 1) or 1)

            if level <= 1 or top_level is None:
                root["children"].append(node)
                top_level = node
            else:
                top_level.setdefault("children", []).append(node)

        if preset_sections:
            preset_norms = [self._normalise(p) for p in preset_sections]
            root = self._filter_by_presets(root, preset_norms)

        return root

    def _run(self, chain, inputs: dict) -> tuple[Any, dict]:
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
        document_type: str = "Artigo Científico",
        language: str = "PT-BR",
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
        chain = prompt | self.llm

        raw, usage = self._run(
            chain,
            {
                "trees": heading_index,
                "preset_sections": preset_instructions,
                "allowed_titles": allowed_block,
                "language": language,
                "document_type": document_type,
            },
        )
        try:
            parsed = self._parse_tree_payload(raw)
        except Exception:
            parsed = self._build_fallback_tree(heading_index, preset_sections=preset_sections)

        sanitized = self._sanitize_tree(parsed)
        if preset_sections:
            preset_norms = [self._normalise(p) for p in preset_sections]
            sanitized = self._filter_by_presets(sanitized, preset_norms)

        return sanitized, usage

