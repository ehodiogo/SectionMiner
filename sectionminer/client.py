from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback
from langchain_openai import ChatOpenAI
from typing import Any, cast

from sectionminer.prompts import MERGE_TREE_PROMPT


class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", max_tokens: int = 8000):
        self.llm = ChatOpenAI(
            model=model,
            api_key=cast(Any, api_key),
            temperature=0,
            max_tokens=max_tokens,
        )
        self.parser = JsonOutputParser()

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

    def merge_trees(self, heading_index: list) -> tuple[dict, dict]:
        prompt = ChatPromptTemplate.from_template(MERGE_TREE_PROMPT)
        chain = prompt | self.llm | self.parser
        raw, usage = self._run(chain, {"trees": heading_index})
        sanitized = self._sanitize_tree(raw)
        return sanitized, usage

