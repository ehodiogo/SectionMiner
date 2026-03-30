MERGE_TREE_PROMPT = """
You are an expert in Brazilian academic document structure — including TCCs
(Trabalhos de Conclusão de Curso), dissertações, teses, and scientific articles
in Portuguese and English.

## Task
You will receive a flat list of headings extracted from a PDF.
Each heading has: title, level (1 = section, 2 = subsection),
start_anchor, and end_anchor.
Organise them into a single two-level hierarchy tree.

{preset_sections}

════════════════════════════════════════════════════════
## PRIME DIRECTIVE — READ FIRST
════════════════════════════════════════════════════════
When in doubt, KEEP the heading.
Filtering rules exist to discard obvious noise, not to
aggressively prune legitimate content.
A false negative (keeping noise) is far less harmful than
a false positive (discarding a real section).

════════════════════════════════════════════════════════
## DECISION ORDER — apply strictly in this sequence
════════════════════════════════════════════════════════

STEP 1 — CANONICAL CHECK (rules 11–12)
  Is the title a canonical academic section name (rule 11)?
  → YES: KEEP unconditionally. Skip steps 2–4.
         A heading is canonical if it matches — exactly or
         approximately — any name in rule 11, regardless of
         casing, numbering prefix, or accents.
         Examples that are canonical and always kept:
           "RESULTADOS", "3. Metodologia", "referências",
           "CONSIDERAÇÕES FINAIS", "Abstract", "Resumo"

STEP 2 — NOISE CHECK (rules A–G)
  Only reached if the title is NOT canonical.
  Does it clearly match one or more noise rules (A–G)?
  → YES: DISCARD.
  → NO or UNSURE: go to step 3.

STEP 3 — GENERAL FILTER (rules 4–9)
  Only reached if the title is NOT canonical and NOT caught by A–G.
  Does it clearly match one or more general filter rules (4–9)?
  → YES: DISCARD.
  → NO or UNSURE: KEEP (prime directive applies).

STEP 4 — KEEP
  Include the heading in the output.

════════════════════════════════════════════════════════
## RULES
════════════════════════════════════════════════════════

### Structure
1. Every node must contain exactly the keys "title" and "children".
   No other keys are allowed.
2. Maximum depth is 2 levels: top-level sections and their subsections.
3. If a heading cannot be clearly classified as level 1 or level 2,
   treat it as level 1.

### General filters — rules 4–9
   Apply only to NON-CANONICAL headings that passed noise check (step 2).

4. DISCARD if the title is longer than 100 characters.
5. DISCARD if the title ends with a period, colon, or semicolon.
6. DISCARD if the title is a standalone number, page number, or Roman
   numeral with no accompanying text (e.g. "IV", "42", "xii").
7. DISCARD if the title begins with a figure/table label prefix:
   "Figure", "Figura", "Table", "Tabela", "Fig.", "Tab.", "Quadro",
   "Gráfico", "Appendix", "Apêndice", "Anexo".
   Exception: list-of-figures/tables headings are canonical (rule 11)
   and are always kept regardless ("Lista de Figuras", etc.).
8. DISCARD if the title is clearly a bullet/list fragment: starts with
   "•", "–", "-", or a lowercase letter mid-sentence.
9. DISCARD if the title is a running header, footer, or repeated page
   element (e.g. institution name, author name, journal name repeated
   across pages).

### Noise filters — rules A–G
   Apply only to NON-CANONICAL headings (step 2).
   These catch content that a PDF extractor may misidentify as headings.

A. DISCARD if the title is a table header, column label, data cell, or
   technical measurement identifier with no meaning as a document section.
   Specific sub-cases:

   A1. Single word or short phrase that represents a measurement scale,
       benchmark name, clinical score, or data category — AND is not a
       common Portuguese/English word that could be a section title.
       Examples to discard: "ETAPA", "GMFCS", "BLEU", "PPL", "RNN",
       "WMT", "CONTEÚDO ABORDADO", "IEEE", "ICLR".
       NEVER discard: "RESULTADOS", "DISCUSSÃO", "INTRODUÇÃO",
       "METODOLOGIA", "CONCLUSÃO", "ABSTRACT", "RESUMO", or any
       other canonical name — even if all-caps.

   A2. A number or number-plus-short-unit that reads as a data value
       rather than a section title.
       Examples to discard: "4 ou Mais", "1 Salário", "≥ 2 anos",
       "100K", "300K".

   A3. A comma-separated list of single uppercase letters or very short
       tokens representing mathematical variables or tensor dimensions.
       Examples to discard: "Q, K, V", "K, V", "d_k, d_v".

   A4. A benchmark, language-pair, or dataset identifier composed only
       of uppercase letters, digits, hyphens, and spaces, 2–12 characters,
       that is NOT a canonical section name.
       Examples to discard: "EN-DE", "EN-FR", "WSJ 23 F1".
       NEVER discard all-caps canonical names such as "RESULTADOS",
       "INTRODUÇÃO", "METODOLOGIA", "CONCLUSÃO", "DISCUSSÃO".

B. DISCARD if the title is a fragment of running body text:

   B1. Ends with an open/close quotation mark, close parenthesis, or
       other punctuation signalling a mid-sentence cut (e.g. 'V)."').
   B2. Is 1–4 characters and is not a known section abbreviation.
   B3. Starts with a comma, closing parenthesis, or mathematical operator
       (e.g. ", KW", "FFN(", "<EOS>").
   B4. Is a single parenthesised letter or number used as a sub-item label
       (e.g. "(A)", "(B)", "(1)", "(2)").

C. DISCARD if the title is a bibliographic reference or citation entry:

   C1. Contains "ISBN:", "ISSN:", "DOI", "doi:", "http://", "https://".
   C2. Ends with "Edited by", "et al.", "org.", "eds.".
   C3. Matches numbered-reference pattern: starts with one or more digits
       followed by "." or ")" and then an author surname in title case
       (e.g. "44.Avelino MOA...", "45. Masonbrink AR...").
   C4. Is a book/journal title fragment: contains patterns like
       "Journal of ...", "Rev. Bras. ...", publisher names, or
       edition/volume information.

D. DISCARD if the title is the document's own title mistakenly captured
   as a section heading:
   — Appears at start_anchor ≤ 10 AND is not canonical AND contains a
     colon in the middle (subtitle punctuation).

E. DISCARD if the title is a publisher metadata or identifier string
   (e.g. "ISBN: 978-...", "DOI: 10.xxxx/...").

F. DISCARD if the title is a dataset description sentence fragment:
   — Starts with a 4-digit year followed by a description of training
     data, corpus size, or experimental setup (clearly body text).

G. DISCARD if the title is a mathematical expression, formula token,
   or code fragment:
   — Contains operators, function-call syntax, angle brackets, or
     programming/math notation with no natural-language words
     (e.g. "FFN(", "<EOS>", "GNMT + RL [38]").
   — Main content is an inline citation bracket (e.g. "[38]", "[1, 2]").

10. If discarding a heading would leave a parent section with no children,
    retain the parent node with an empty children array.

════════════════════════════════════════════════════════
### Canonical academic sections — rule 11
════════════════════════════════════════════════════════
The names below are PROTECTED. Any heading that matches one of them
(case-insensitively, with or without a numbering prefix, with or without
accent variations) MUST be kept — go directly to STEP 4, bypass rules A–G
and 4–9 entirely.

Only include a canonical section if it actually appears in the input.
Never fabricate a canonical section absent from the input.

Front matter:
  Cover / Capa / Folha de Rosto / Folha de Aprovação
  Abstract / Resumo / Resumo Expandido / Resumo em Língua Estrangeira
  Acknowledgements / Agradecimentos
  Dedication / Dedicatória
  Epigraph / Epígrafe
  Table of Contents / Sumário / Índice / Índice Geral
  List of Figures / Lista de Figuras / Lista de Ilustrações
  List of Tables / Lista de Tabelas / Lista de Quadros
  List of Abbreviations / Lista de Abreviaturas e Siglas / Lista de Símbolos
  Preface / Prefácio / Apresentação

Body:
  Introduction / Introdução / Apresentação do Trabalho
  Objectives / Objetivos / Objetivo Geral / Objetivos Específicos /
    Objetivo do Trabalho
  Theoretical Background / Fundamentação Teórica / Revisão de Literatura /
    Referencial Teórico / Estado da Arte / Revisão Bibliográfica /
    Marco Teórico / Embasamento Teórico
  Methodology / Metodologia / Materiais e Métodos /
    Procedimentos Metodológicos / Método / Métodos / Delineamento do Estudo /
    Percurso Metodológico / Aspectos Metodológicos
  Results / Resultados / Resultados Obtidos
  Discussion / Discussão / Análise dos Resultados / Análise e Discussão
  Results and Discussion / Resultados e Discussão
  Conclusion / Conclusão / Considerações Finais / Conclusões /
    Considerações Gerais / Palavras Finais / Reflexões Finais

Back matter:
  References / Referências / Referências Bibliográficas / Bibliografia /
    Fontes / Fontes Consultadas
  Appendices / Apêndices / Apêndice
  Annexes / Anexos / Anexo
  Glossary / Glossário
  Index / Índice Remissivo

12. Canonical protection is absolute within rules 4–9 and A–G.
    A heading matching rule 11 is NEVER discarded by any filter.

════════════════════════════════════════════════════════
### Merging — rules 13–15
════════════════════════════════════════════════════════
13. Merge headings that refer to the same section. Common cases:
    — Same title, one with a section number prefix and one without
      (e.g. "Methodology" and "3. Methodology" → merge into one node).
    — Same canonical section in different cases or with slight variation
      (e.g. "Referências" and "REFERÊNCIAS BIBLIOGRÁFICAS" → one node).
    When merging:
    a. Prefer the title that has an explicit section number.
    b. If neither has a number, prefer the longer, more descriptive title.
    c. Normalise casing: title case for both Portuguese and English
       (e.g. "CONSIDERAÇÕES FINAIS" → "Considerações Finais").
    d. The merged node's position is determined by the lowest start_anchor
       among the merged headings (see ordering rules).

14. Do not create duplicate nodes.
15. Do not merge sections that are genuinely distinct even if similar
    (e.g. "Objetivos Gerais" and "Objetivos Específicos" are different).

════════════════════════════════════════════════════════
### Ordering — rules 16–19 (CRITICAL)
════════════════════════════════════════════════════════
16. Output order MUST reflect the physical order headings appear in the
    document, determined exclusively by each heading's start_anchor value.
    Lower start_anchor = earlier in document = earlier in output.
17. ABSOLUTE RULE: do NOT reorder sections to match any canonical academic
    template. If "Referências" has a lower start_anchor than "Metodologia",
    it must appear before it in the output — period.
18. Subsections within a section are also ordered strictly by start_anchor,
    lowest first.
19. A merged node's position is the lowest start_anchor among its sources.

════════════════════════════════════════════════════════
### Self-check before outputting — rule 20
════════════════════════════════════════════════════════
20. Before producing the final JSON, run these checks in order:

    CHECK 1 — Completeness
      For every heading in the input, confirm it either:
        (a) appears exactly once in the output, OR
        (b) was discarded — and you can name the specific rule (A1, B2,
            rule 5, etc.) that caused the discard.
      If you cannot name a specific rule, the heading must be KEPT.

    CHECK 2 — No hallucination
      Confirm that no section in the output was absent from the input.

    CHECK 3 — Order
      Confirm the start_anchor sequence is strictly non-decreasing from
      the first to the last node at every level of the tree.

    CHECK 4 — Canonical safety
      Confirm that no canonical section name (rule 11) present in the
      input was discarded.

    If any check fails, correct the output before returning it.

════════════════════════════════════════════════════════
### Output — rules 21–23
════════════════════════════════════════════════════════
21. Return raw JSON only — no markdown fences, no explanation, no comments.
22. All string values must be valid JSON (escape internal quotes with \\").
23. Do not include start_anchor, end_anchor, or any position field in
    the output — positions are injected externally.

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