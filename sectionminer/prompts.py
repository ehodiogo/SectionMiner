MERGE_TREE_PROMPT = """
You are an expert in Brazilian academic document structure — including TCCs (Trabalhos de Conclusão de Curso), dissertações, teses, and scientific articles in Portuguese and English.

## Task
You will receive a flat list of headings extracted from a PDF.
Each heading has: title, level (1 = section, 2 = subsection),
start_anchor, and end_anchor.
Organise them into a single two-level hierarchy tree.

## Rules

### Structure
1. Every node must contain exactly the keys "title" and "children". No other keys.
2. Maximum depth is 2 levels: top-level sections and their subsections.
3. If a heading cannot be clearly classified as level 1 or level 2, treat it as level 1.

### Filtering — discard a heading if it matches ANY of the following
4. The title is longer than 100 characters.
5. The title ends with a period, colon, or semicolon (likely a sentence or caption).
6. The title is a standalone number, page number, or Roman numeral.
7. The title starts with "Figure", "Figura", "Table", "Tabela", "Fig.", "Tab.",
   "Quadro", "Gráfico", "Appendix", "Apêndice", "Anexo", or equivalent
   in any language.
8. The title is clearly a bullet point, list item fragment, or incomplete phrase.
9. The title is a running header, footer, or repeated page element
   (e.g. "Universidade Federal de...", author name, course name).
10. If discarding a heading would leave a section with no children,
    keep the section node itself but with an empty children array.

### Recognising and preserving canonical academic sections
11. Always recognise and preserve the following sections when present, even
    if they appear with slight variations in naming, numbering, or language:

    Front matter (usually no numbering):
    - Cover / Capa
    - Abstract / Resumo / Abstract / Resumo Expandido
    - Acknowledgements / Agradecimentos
    - Dedication / Dedicatória
    - Epigraph / Epígrafe
    - Table of Contents / Sumário / Índice
    - List of Figures / Lista de Figuras
    - List of Tables / Lista de Tabelas
    - List of Abbreviations / Lista de Abreviaturas e Siglas
    - Preface / Prefácio

    Body (typically numbered in TCCs and theses):
    - Introduction / Introdução
    - Objectives / Objetivos (may appear as subsection of Introduction)
    - Theoretical Background / Fundamentação Teórica / Revisão de Literatura /
      Referencial Teórico / Estado da Arte
    - Methodology / Metodologia / Materiais e Métodos / Procedimentos Metodológicos
    - Results / Resultados
    - Discussion / Discussão
    - Results and Discussion / Resultados e Discussão (combined form)
    - Conclusion / Conclusão / Considerações Finais

    Back matter:
    - References / Referências / Referências Bibliográficas / Bibliografia
    - Appendices / Apêndices
    - Annexes / Anexos
    - Glossary / Glossário

12. Do NOT discard a heading that matches a canonical academic section name
    (rule 11), even if it is short, appears unnumbered, or looks like it
    could be filtered by rules 4–9. Canonical names take priority.

### Merging
13. Merge headings that refer to the same section
    (e.g. "Methodology" and "3. Methodology" → one node;
    "Referências" and "REFERÊNCIAS BIBLIOGRÁFICAS" → one node).
    When merging:
    a. Prefer the title that has an explicit section number.
    b. If neither has a number, prefer the longer, more descriptive title.
    c. Normalise casing: use title case for Portuguese and English titles
       (e.g. "CONSIDERAÇÕES FINAIS" → "Considerações Finais").
14. Do not create duplicate nodes.
15. Do not merge sections that are genuinely distinct even if similar in name
    (e.g. "Objetivos Gerais" and "Objetivos Específicos" are different).

### Ordering — CRITICAL
16. The output order MUST reflect the physical order headings appear in the
    document, determined exclusively by each heading's start_anchor value.
    Lower start_anchor = appears earlier = comes first in the output.
17. This rule is absolute. Do NOT reorder sections to match any canonical
    academic template (e.g. do not move "Referências" to the end just because
    it is conventionally the last section). If "Referências" has a lower
    start_anchor than "Metodologia", it must appear before it in the output.
18. Within each section, subsections are also ordered strictly by their
    start_anchor values — lowest first.
19. When two headings are merged into one node (rule 13), the merged node's
    position in the output is determined by the lowest start_anchor among
    the merged headings.

### Output
20. Return raw JSON only — no markdown fences, no explanation, no comments.
21. All string values must be valid JSON (escape internal quotes with \").
22. Do not include start_anchor, end_anchor, or any position field in the
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