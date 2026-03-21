MERGE_TREE_PROMPT = """
You are an expert in academic document structure.

## Task
You will receive a flat list of headings extracted from a document.
Each heading has a title, a level (1 = section, 2 = subsection), a start_anchor,
and an end_anchor. Organise them into a single two-level hierarchy tree.

## Mandatory rules
1. Every node must contain exactly: "title", "children".
2. Maximum depth: 2 levels (sections -> subsections).
3. Discard any node whose title is a full paragraph, a sentence longer than
   100 characters, a page number, a figure/table caption, or a standalone
   bullet point.
4. Merge semantically equivalent headings (e.g. "Methodology" and
   "2. Method" -> single node with the more complete title).
5. Preserve canonical academic order when possible:
   Abstract -> Introduction -> Related Work -> Methodology -> Results ->
   Discussion -> Conclusion -> References.
6. Within each section, order subsections by their start_anchor appearance
   order in the document.
7. Do not duplicate nodes; do not omit any valid section present in the input.
8. Do NOT include start_anchor, end_anchor, or any position field in the
   output - positions are managed externally.

## Output format - raw JSON only, no markdown fences, no explanation
{{
  "title": "Document",
  "children": [
	{{
	  "title": "<Section>",
	  "children": [
		{{
		  "title": "<Subsection>",
		  "children": []
		}}
	  ]
	}}
  ]
}}

## Input headings
{trees}
"""

