MERGE_TREE_PROMPT = """
You are an expert in academic document structure analysis.

## Task
You will receive a flat list of headings extracted from a PDF.
Each heading has: title, level (1 = section, 2 = subsection),
start_anchor, and end_anchor.
Organise them into a single two-level hierarchy tree.

## Rules

### Structure
1. Every node must contain exactly the keys "title" and "children". No other keys.
2. Maximum depth is 2 levels: top-level sections and their subsections.
3. If a heading cannot be clearly classified as level 1 or level 2,
   treat it as level 1.

### Filtering — discard a heading if it matches ANY of the following
4. The title is longer than 100 characters.
5. The title ends with a period, colon, or semicolon (likely a sentence).
6. The title is a standalone number, page number, or Roman numeral.
7. The title starts with "Figure", "Table", "Fig.", "Tab." or equivalent
   in any language.
8. The title is clearly a bullet point or list item fragment.
9. If discarding a heading would leave a section with no children,
   keep the section node itself but with an empty children array.

### Merging
10. Merge headings that refer to the same section
    (e.g. "Methodology" and "2. Methodology" -> one node).
    When merging, prefer the title that has an explicit section number;
    if neither has a number, prefer the longer, more descriptive title.
11. Do not create duplicate nodes.

### Ordering
12. Preserve the original document order of sections as indicated by
    start_anchor positions. Do NOT reorder sections to match a canonical
    academic template.
13. Within each section, order subsections by their start_anchor
    appearance order in the document.

### Output
14. Return raw JSON only — no markdown fences, no explanation, no comments.
15. All string values must be valid JSON (escape internal quotes with \").
16. Do not include start_anchor, end_anchor, or any position field in the
    output — positions are injected externally.

## Output format
{{
  "title": "Document",
  "children": [
    {{
      "title": "<Section A>",
      "children": []
    }},
    {{
      "title": "<Section B>",
      "children": [
        {{
          "title": "<Subsection B.1>",
          "children": []
        }},
        {{
          "title": "<Subsection B.2>",
          "children": []
        }}
      ]
    }}
  ]
}}

## Input headings
{trees}
"""