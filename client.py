from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.callbacks import get_openai_callback


class LLMClient:

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0
        )
        self.parser = JsonOutputParser()

    def _run(self, chain, inputs):
        with get_openai_callback() as cb:
            result = chain.invoke(inputs)
            usage = {
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_tokens": cb.total_tokens,
                "cost_usd": cb.total_cost
            }
        return result, usage

    def _resolve_positions(self, node: dict, text: str) -> dict:
        result = {"title": node.get("title", ""), "start_char": None, "end_char": None}

        start_anchor = node.get("start_anchor", "")
        end_anchor = node.get("end_anchor", "")

        if start_anchor:
            idx = text.find(start_anchor)
            result["start_char"] = idx if idx != -1 else None

        if end_anchor:
            idx = text.rfind(end_anchor)
            result["end_char"] = (idx + len(end_anchor)) if idx != -1 else None

        result["children"] = [
            self._resolve_positions(child, text)
            for child in node.get("children", [])
        ]
        return result

    def _resolve_siblings(self, children: list, text: str, search_from: int = 0) -> list:
        resolved = []
        cursor = search_from

        for node in children:
            result = {
                "title": node.get("title", ""),
                "start_char": None,
                "end_char": None,
            }

            start_anchor = node.get("start_anchor", "").strip()
            if start_anchor:
                idx = text.find(start_anchor, cursor)
                if idx != -1:
                    result["start_char"] = idx
                    cursor = idx + len(start_anchor)

            result["children"] = self._resolve_siblings(
                node.get("children", []),
                text,
                result["start_char"] or cursor,
            )
            resolved.append(result)

        for i, r in enumerate(resolved):
            if i + 1 < len(resolved) and resolved[i + 1]["start_char"] is not None:
                r["end_char"] = resolved[i + 1]["start_char"]
            else:
                r["end_char"] = len(text)

        return resolved

    def _sanitize_tree(self, data, text: str = ""):
        if not isinstance(data, dict):
            return {"title": "Document", "start_char": 0, "end_char": len(text), "children": []}

        def clean_title(value):
            if not isinstance(value, str):
                return None
            t = " ".join(value.split()).strip()
            if len(t) < 2 or len(t) > 140:
                return None
            return t

        def clean_nodes(nodes, depth):
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
                cleaned.append({
                    "title": title,
                    "start_char": node.get("start_char"),
                    "end_char": node.get("end_char"),
                    "children": children,
                })
            return cleaned

        root_title = clean_title(data.get("title")) or "Document"
        return {
            "title": root_title,
            "start_char": 0,
            "end_char": len(text) if text else data.get("end_char"),
            "children": clean_nodes(data.get("children", []), 1),
        }

    def extract_sections(self, text: str):
        prompt = ChatPromptTemplate.from_template("""
You are an expert in structural analysis of academic documents.
The input text may be written in any language — preserve all headings exactly as they appear.

## Task
Identify every section and subsection in the text below.
For each node return two short verbatim anchors copied character-for-character from the text:
  - start_anchor: the first 40–60 characters of the section heading (or opening line if no heading).
  - end_anchor:   the last 40–60 characters of that section's content, immediately before the next sibling section begins (or the end of the text).

## Strict rules
- Detect canonical academic sections when present: Abstract, Introduction, Related Work, Methodology, Results, Discussion, Conclusion, References — and any other explicitly named section.
- Identify numbered subsections (e.g. "2.1 Data collection") or subsections with an explicit heading.
- Use semantic inference only when a heading is not explicit; never fabricate content.
- Ignore figure/table captions, footnotes, and repeated page headers.
- Maximum 2 hierarchy levels: sections → subsections.
- Anchors must be copied verbatim from the text — do not paraphrase, translate, or summarise.
- Anchors must be unique enough to locate the position unambiguously (include surrounding punctuation or numbers if needed).
- Sibling sections must not share overlapping anchors.

## Output format — raw JSON only, no markdown fences, no explanation
{{
  "title": "Document",
  "children": [
    {{
      "title": "<Section heading>",
      "start_anchor": "<verbatim text>",
      "end_anchor": "<verbatim text>",
      "children": [
        {{
          "title": "<Subsection heading>",
          "start_anchor": "<verbatim text>",
          "end_anchor": "<verbatim text>",
          "children": []
        }}
      ]
    }}
  ]
}}

## Text (first 15 000 characters)
{texto}
""")

        chain = prompt | self.llm | self.parser

        def _run_and_resolve(inputs):
            raw, usage = self._run(chain, inputs)
            resolved = self._resolve_positions(raw, inputs["texto"])
            sanitized = self._sanitize_tree(resolved, inputs["texto"])
            return sanitized, usage

        return _run_and_resolve({"texto": text[:15000]})

    def merge_trees(self, trees: list):
        prompt = ChatPromptTemplate.from_template("""
You are an expert in academic document structure.

## Task
You will receive multiple section trees extracted from non-overlapping chunks of the same document.
Merge them into a single consolidated tree, deduplicating equivalent sections and preserving the original anchors.

## Mandatory rules
1. Every node must contain exactly: "title", "start_anchor", "end_anchor", "children".
2. Maximum depth: 2 levels (sections and subsections).
3. Discard any node whose title is a full paragraph, a sentence longer than 100 characters, a page number, a figure/table caption, or a standalone bullet point.
4. Merge semantically equivalent headings (e.g. "Methodology" and "2. Method" → single node with the more complete title).
   - Merged start_anchor = the anchor with the smaller position in the document (i.e. from the earlier chunk).
   - Merged end_anchor   = the anchor with the larger position in the document (i.e. from the later chunk).
5. Preserve canonical academic order when possible: Abstract → Introduction → Related Work → Methodology → Results → Discussion → Conclusion → References.
6. Within each section, order subsections by their start_anchor appearance order in the document.
7. Do not duplicate nodes; do not omit any section present in the inputs.

## Output format — raw JSON only, no markdown fences, no explanation
{{
  "title": "Document",
  "children": [
    {{
      "title": "<Section>",
      "start_anchor": "<verbatim text>",
      "end_anchor": "<verbatim text>",
      "children": [
        {{
          "title": "<Subsection>",
          "start_anchor": "<verbatim text>",
          "end_anchor": "<verbatim text>",
          "children": []
        }}
      ]
    }}
  ]
}}

## Input trees
{trees}
""")

        chain = prompt | self.llm | self.parser
        result, usage = self._run(chain, {"trees": trees})
        return result, usage