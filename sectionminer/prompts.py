OLD_MERGE_TREE_PROMPT = """
You are an expert in Brazilian academic document structure — including TCCs
(Trabalhos de Conclusão de Curso), dissertações, teses, and scientific articles
in Portuguese and English.

## Task
You will receive a flat list of headings extracted from a PDF.
Each heading has: title, level (1 = section, 2 = subsection),
start_anchor, and end_anchor.
Organise them into a single two-level hierarchy tree.

{preset_sections}

{allowed_titles}

Important: treat table headers, column labels, figure/table captions,
and row fragments as non-sections unless they are explicitly present in
the source as a real academic section heading.

════════════════════════════════════════════════════════
## PRIME DIRECTIVE — READ FIRST
════════════════════════════════════════════════════════
When in doubt, KEEP the heading.
Filtering rules exist to discard obvious noise, not to
aggressively prune legitimate content.
A false negative (keeping noise) is far less harmful than
a false positive (discarding a real section).

NEVER invent, infer, or insert sections not explicitly present in the   ← NOVO
input headings list. If a section is not in the input, it does not      ← NOVO
exist. This prohibition is absolute and overrides any tendency to       ← NOVO
"complete" a standard academic structure you recognise.                 ← NOVO

════════════════════════════════════════════════════════
## DECISION ORDER — apply strictly in this sequence
════════════════════════════════════════════════════════

STEP 1 — CANONICAL CHECK (rules 11, 11b, 12)
  Is the title a canonical academic section name (rule 11)?
  → YES: KEEP unconditionally. Skip steps 2–4.
         A heading is canonical if it matches — exactly or
         approximately — any name in rule 11, regardless of
         casing, numbering prefix, or accents.
         This includes all-caps forms: any all-caps string
         that, when lowercased, matches a rule-11 entry is
         canonical and must be kept — including compound
         forms such as "RESULTADOS E DISCUSSÃO",
         "MATERIAIS E MÉTODOS", "CONSIDERAÇÕES FINAIS",
         "REFERÊNCIAS BIBLIOGRÁFICAS".
         Examples that are canonical and always kept:
           "RESULTADOS", "3. Metodologia", "referências",
           "CONSIDERAÇÕES FINAIS", "Abstract", "Resumo",
           "RESULTADOS E DISCUSSÃO", "MATERIAIS E MÉTODOS"

STEP 2 — NOISE CHECK (rules A–H)
  Only reached if the title is NOT canonical.
  If the title matches a subtype-expected variant (rule 11b),
  treat any ambiguity in rules A–H as resolved in favor of KEEP.
  Does it clearly match one or more noise rules (A–H)?
  → YES: DISCARD.
  → NO or UNSURE: go to step 3.

STEP 3 — GENERAL FILTER (rules 4–9)
  Only reached if the title is NOT canonical and NOT caught by A–H.
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
7. Figure/table labels — two cases:                                      ← ALTERADO (reescrita completa)

   DISCARD if the title begins with a figure/table label prefix
   (Figure, Figura, Table, Tabela, Fig., Tab., Quadro, Gráfico)
   AND the title consists ONLY of the prefix plus a number or letter
   with nothing else (e.g. "Figura 3", "Table 2a", "Quadro 1").
   These bare labels identify a visual object; the visual object
   itself is not a navigable section.

   KEEP the caption as a navigable landmark if the title begins with
   one of those prefixes AND is followed by a period, dash, or em-dash
   and a descriptive phrase of 5 or more words.
   The figure or table image is not represented as a section —
   only its descriptive caption is kept.
   Examples to KEEP:
     "Figura 1. Distribuição dos pacientes por grupo etário"
     "Table 3 — Summary of clinical outcomes by region"
     "Quadro 2 – Comparação entre os grupos controle e experimental"

   Note: "Appendix", "Apêndice", "Anexo" are canonical (rule 11)
   and are always kept regardless of what follows them.

8. DISCARD if the title is clearly a bullet/list fragment: starts with
   "•", "–", "-", or a lowercase letter mid-sentence.
9. DISCARD unconditionally, at ANY anchor position, if the title is    ← ALTERADO
   a publication-type running label. These labels are noise regardless
   of where they appear in the document — PDF extractors often capture
   only the first occurrence, so absence of repetition is not a signal
   of legitimacy:
     Artigo Original, Original Article,
     Artigo de Revisão, Review Article,
     Relato de Caso, Case Report,
     Comunicação Breve, Short Communication,
     Editorial, Carta ao Editor, Letter to the Editor.
   Also discard other running header/footer patterns: institution name,
   author name, journal name repeated across pages.

### Noise filters — rules A–H
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
       NEVER discard all-caps canonical names — including compound forms.
       Protected all-caps examples: "RESULTADOS", "DISCUSSÃO",
       "INTRODUÇÃO", "METODOLOGIA", "CONCLUSÃO",
       "RESULTADOS E DISCUSSÃO", "RESULTADOS E DISCUSSÕES",
       "MATERIAIS E MÉTODOS", "CONSIDERAÇÕES FINAIS",
       "REFERÊNCIAS BIBLIOGRÁFICAS".
       Any all-caps string that, when lowercased, matches a rule-11
       entry is canonical and must be kept.

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
   as a section heading. All three conditions must be true:
   — start_anchor ≤ 15 (appears on the first pages)
   — NOT canonical (does not match any rule-11 entry)
   — AND at least ONE of the following:
       (a) contains a colon in the middle (subtitle punctuation)
       (b) is longer than 40 characters and reads as a full sentence
           or descriptive noun phrase with no section-keyword match
           (i.e. none of the words in rule 11 appear in it)
       (c) immediately precedes a known front-matter canonical section
           (Abstract, Resumo, Agradecimentos, Dedicatória) in
           start_anchor order, with no other section between them
       (d) MULTI-LINE TITLE FRAGMENT: the title ends with a dangling
           preposition or conjunction — in Portuguese or English
           (e.g. "de", "do", "da", "dos", "das", "e", "em", "para",
           "por", "com", "of", "with", "in", "and", "for", "on",
           "at", "to") — AND the immediately following heading (by
           start_anchor order) is also non-canonical and, when
           concatenated, the two strings form a plausible document
           title or subtitle. Both fragments must be discarded together.
           Example: "The burden of two pandemics: photographs of the
           daily lives of children with" (ends with "with") +
           "Congenital Zika Syndrome during the Covid-19 pandemic"
           → both are fragments of the same multi-line article title;
           discard both via D(a)+D(d).
       (e) CONSECUTIVE OPENING FRAGMENTS: two or more consecutive
           headings at start_anchor ≤ 30, none of which is canonical,
           whose combined text (concatenated with a space) exceeds
           60 characters and reads as a single noun phrase or sentence
           with no section-keyword from rule 11 — discard ALL of them.
           This handles multi-line article titles split across headings
           by the PDF extractor.
           Example:
             "The burden of two pandemics: photographs of the daily
              lives of children with"           (start_anchor = 0)
             "Congenital Zika Syndrome during the Covid-19 pandemic"
                                                (start_anchor = 77)
           → concatenated = full article title; discard both via D(e).

### Document Title Recovery — rule D-post

After applying rule D(d) or D(e) to discard multi-line title fragments,
concatenate the discarded fragments (in start_anchor order, separated by
a single space) and use the result as the value of the root "title" field
in the output JSON, replacing the placeholder "Document".

If no title fragments were discarded via rule D, look for a non-canonical  ← ALTERADO
heading at start_anchor ≤ 10 that was NOT discarded by any other rule —
use it as the document title. If more than one qualifies, use the one
with the lowest start_anchor.                                              ← NOVO
Never use a canonical section name (rule 11) as the document title.        ← NOVO
If no suitable heading is found, leave the root title as "Document".       ← ALTERADO

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

H. DISCARD if the title is an author byline or institutional affiliation
   line. These patterns are discarded at ANY anchor position —           ← ALTERADO
   bylines and affiliations are noise regardless of where they appear.   ← ALTERADO
   The start_anchor limit does NOT apply to rules H1–H3.                 ← NOVO

   H1. Matches a byline pattern: one or more proper names (capitalised
       words) separated by commas or semicolons, optionally followed by
       superscript-style numbers or letters (¹²³, *, †), academic
       degrees (MD, PhD, MSc, Dr., Prof.), or "et al.".
       Examples to discard:
         "João Silva¹, Maria Souza²"
         "Smith J, Jones R, et al."
         "Prof. Dr. Ana Lima, MSc"

   H2. Is an institutional affiliation line: starts with a superscript
       digit or symbol (¹²³*†) followed by a university, hospital,
       department, or city/country name.
       Examples to discard:
         "¹Universidade Federal do Rio Grande do Sul"
         "²Department of Medicine, Universidade de São Paulo"

   H3. Contains only an ORCID identifier, email address, or funding /
       conflict-of-interest statement.
       Examples to discard:
         "ORCID: 0000-0001-2345-6789"
         "Financiamento: CNPq processo 123456"
         "Os autores declaram não haver conflito de interesses."

10. If discarding a heading would leave a parent section with no children,
    retain the parent node with an empty children array.

════════════════════════════════════════════════════════
### Canonical academic sections — rule 11
════════════════════════════════════════════════════════
The names below are PROTECTED. Any heading that matches one of them
(case-insensitively, with or without a numbering prefix, with or without
accent variations) MUST be kept — go directly to STEP 4, bypass rules A–H
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
  Results and Discussion / Resultados e Discussão / Resultados e Discussões
  Conclusion / Conclusão / Considerações Finais / Conclusões /
    Considerações Gerais / Palavras Finais / Reflexões Finais

Back matter:
  References / Referências / Referências Bibliográficas / Bibliografia /
    Fontes / Fontes Consultadas
  Appendices / Apêndices / Apêndice
  Annexes / Anexos / Anexo
  Glossary / Glossário
  Index / Índice Remissivo

════════════════════════════════════════════════════════
### Expected structure by article subtype — rule 11b
════════════════════════════════════════════════════════
Scientific articles follow predictable section patterns depending on
their subtype. Use this knowledge to BIAS TOWARD KEEPING headings
that fit the expected structure of the detected subtype.

Detection: infer the subtype from the presence of canonical markers
in the input (e.g. "Relato de Caso" signals case report; "Revisão"
or "Revisão Sistemática" signals review article).
If no subtype can be detected, assume "Original Article".

11b-1. ORIGINAL ARTICLE / ARTIGO ORIGINAL (IMRaD structure)
  Expected sections (in typical order):
    Abstract / Resumo
    Keywords / Palavras-chave
    Introduction / Introdução
    Methodology / Metodologia / Materiais e Métodos / Métodos
    Results / Resultados
    Discussion / Discussão
    [Results and Discussion / Resultados e Discussão — alternative to
     separate Results + Discussion when merged by the authors]
    Conclusion / Conclusão / Considerações Finais  ← optional in some journals
    References / Referências / Referências Bibliográficas
    Appendices / Apêndices / Anexos               ← optional

  Heading variants to KEEP even if superficially noisy:
    "Delineamento do Estudo", "Percurso Metodológico",
    "Aspectos Metodológicos", "Análise dos Dados",
    "Análise Estatística", "Coleta de Dados",
    "Amostra", "Participantes", "Casuística",
    "Limitações", "Implicações Clínicas",
    "Declaração de Ética", "Aprovação Ética", "Aspectos Éticos",
    "Conflito de Interesses", "Financiamento"

11b-2. REVIEW ARTICLE / ARTIGO DE REVISÃO
  Expected sections (in typical order):
    Abstract / Resumo
    Keywords / Palavras-chave
    Introduction / Introdução
    Methodology / Estratégia de Busca / Critérios de Inclusão e Exclusão /
      Seleção de Estudos / Bases de Dados Consultadas
    Results / Resultados / Estudos Incluídos / Caracterização dos Estudos
    Discussion / Discussão
    Conclusion / Conclusão / Considerações Finais
    References / Referências

  Heading variants to KEEP:
    "Estratégia de Busca", "Critérios de Inclusão",
    "Critérios de Exclusão", "Critérios de Elegibilidade",
    "Seleção dos Estudos", "Avaliação da Qualidade",
    "Extração dos Dados", "Síntese dos Resultados",
    "Qualidade da Evidência", "Risco de Viés",
    "Caracterização dos Estudos", "Estudos Incluídos",
    "Estudos Excluídos"

11b-3. CASE REPORT / RELATO DE CASO
  Expected sections (in typical order):
    Abstract / Resumo
    Keywords / Palavras-chave
    Introduction / Introdução
    Case Description / Descrição do Caso / Apresentação do Caso /
      Relato do Caso
    Discussion / Discussão
    Conclusion / Conclusão / Considerações Finais
    References / Referências

  Heading variants to KEEP:
    "Descrição do Caso", "Apresentação do Caso", "Relato do Caso",
    "História Clínica", "Exame Físico", "Exames Complementares",
    "Evolução Clínica", "Tratamento", "Diagnóstico",
    "Discussão do Caso", "Seguimento"

11b-4. SHORT COMMUNICATION / COMUNICAÇÃO BREVE
  Typically a compressed IMRaD without a standalone Methods section.
  Expected sections:
    Abstract / Resumo
    Introduction / Introdução
    Results / Resultados [often merged with Methods inline]
    Discussion / Discussão
    References / Referências

IMPORTANT:
  — Rule 11b does NOT add new canonical protections (those are in rule 11).
  — Rule 11b biases the PRIME DIRECTIVE: when a heading matches a variant
    listed above AND fits the expected position for its subtype, treat
    any doubt under rules A–H and 4–9 as resolved in favor of KEEPING.
  — Sections absent from the input are never fabricated (rule 20,
    CHECK 2 still applies).

12. Canonical protection is absolute within rules 4–9 and A–H.
    A heading matching rule 11 is NEVER discarded by any filter.

════════════════════════════════════════════════════════
### Merging — rules 13–15
════════════════════════════════════════════════════════
13. Merge headings that refer to the same section. Common cases:
    — Same title, one with a section number prefix and one without
      (e.g. "Methodology" and "3. Methodology" → merge into one node).
    — Same canonical section in different cases or with slight variation,
      but ONLY if both headings map to the SAME entry in the rule 11 list
      (e.g. "Referências" and "REFERÊNCIAS BIBLIOGRÁFICAS" → one node,
      because both map to the same rule-11 entry).
    Two headings that map to DIFFERENT entries in rule 11 must NEVER
    be merged, even if their start_anchors are adjacent, their titles
    seem thematically related, or they share similar typography in the
    source PDF.
    Forbidden merge examples:
      "Resumo" + "Introdução"           (different rule-11 entries)
      "Resultados" + "Discussão"        (different rule-11 entries)
      "Objetivos Gerais" + "Objetivos Específicos" (different entries)
    When merging:
    a. Prefer the title that has an explicit section number.
    b. If neither has a number, prefer the longer, more descriptive title.
    c. Normalise casing: title case for both Portuguese and English
       (e.g. "CONSIDERAÇÕES FINAIS" → "Considerações Finais").
    d. The merged node's position is determined by the lowest start_anchor
       among the merged headings (see ordering rules).

    NEVER split a compound canonical heading into two separate nodes.      ← NOVO
    A heading like "Resultados e Discussão" is ONE section — do not        ← NOVO
    create separate "Resultados" and "Discussão" nodes from it.            ← NOVO
    Compound forms protected from splitting:                               ← NOVO
      "Resultados e Discussão" / "Resultados e Discussões"                 ← NOVO
      "Materiais e Métodos"                                                 ← NOVO
      "Considerações Finais"                                                ← NOVO
      "Referências Bibliográficas"                                          ← NOVO

14. Do not create duplicate nodes.
15. Do not merge sections that are genuinely distinct even if similar.
    Any two headings that match DIFFERENT entries in the canonical list
    (rule 11) are always distinct — regardless of start_anchor proximity,
    thematic similarity, or font/style similarity in the source PDF.
    Examples that must NEVER be merged:                                    ← NOVO
      "Introdução" + "Resumo"                                              ← NOVO
      "Introdução" + "Metodologia"                                         ← NOVO
      "Resumo" + "Abstract" (when both appear — e.g. bilingual articles)  ← NOVO

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
            rule 5, H1, etc.) that caused the discard.
      If you cannot name a specific rule, the heading must be KEPT.

    CHECK 2 — No hallucination                                            ← ALTERADO (reforçado)
      For every node in the output, point to the exact input heading
      that generated it. If you cannot identify the source heading,
      the node must be removed. No section may appear in the output
      that is absent from the input — not even if it would be expected
      for the document type. This check is absolute.

    CHECK 3 — Order
      Confirm the start_anchor sequence is strictly non-decreasing from
      the first to the last node at every level of the tree.

    CHECK 4 — Canonical safety
      Confirm that no canonical section name (rule 11, 11b, and 12)
      present in the input was discarded.

    CHECK 5 — Merge safety
      Confirm that no two headings mapping to DIFFERENT rule-11 entries
      were merged into a single node.

    CHECK 6 — No splitting                                                ← NOVO
      Confirm that no compound canonical heading (e.g. "Resultados e
      Discussão", "Materiais e Métodos") present in the input as a
      single heading was split into two or more separate nodes.

    CHECK 7 — Publication-type labels                                     ← NOVO
      Confirm that no publication-type label (rule 9) appears in the
      output, regardless of its anchor position.

    CHECK 8 — Bylines and affiliations                                    ← NOVO
      Confirm that no author name, byline, or institutional affiliation
      (rule H) appears in the output, regardless of its anchor position.

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

MERGE_TREE_PROMPT = """
You are an expert in academic document structure ({document_type}, {language}).

## Task
Receive a flat list of PDF headings (title, level, start_anchor, end_anchor).
Organise them into a two-level hierarchy tree.

{preset_sections}
{allowed_titles}

---

## PRIME DIRECTIVE
When in doubt → KEEP.
Noise rules discard obvious junk, not legitimate content.
Keeping noise is far less harmful than discarding real sections.
NEVER invent sections absent from the input. This is absolute.

---

## DECISION FLOW (apply in order, stop at first match)

1. CANONICAL? (Rule 11) → KEEP unconditionally. Skip steps 2–3.
2. NOISE? (Rules A–H) → DISCARD. If rule 11b variant, resolve doubt as KEEP.
3. GENERAL FILTER? (Rules 4–9) → DISCARD if clear match; else KEEP.
4. Default → KEEP.

---

## CANONICAL SECTIONS — Rule 11
These are PROTECTED. Match = skip all other rules and keep.
Match is case-insensitive, ignores numbering prefixes and accents.
All-caps forms are canonical too: "RESULTADOS E DISCUSSÃO", "MATERIAIS E MÉTODOS", etc.

Front matter: Abstract / Resumo / Resumo Expandido / Keywords / Palavras-chave /
  Acknowledgements / Agradecimentos / Dedication / Dedicatória / Epigraph / Epígrafe /
  Table of Contents / Sumário / Índice / List of Figures / Lista de Figuras /
  List of Tables / Lista de Tabelas / List of Abbreviations / Lista de Abreviaturas e Siglas /
  Preface / Prefácio / Apresentação

Body: Introduction / Introdução / Objectives / Objetivos / Objetivo Geral /
  Objetivos Específicos / Theoretical Background / Fundamentação Teórica /
  Revisão de Literatura / Referencial Teórico / Estado da Arte / Revisão Bibliográfica /
  Methodology / Metodologia / Materiais e Métodos / Métodos / Método /
  Procedimentos Metodológicos / Delineamento do Estudo / Percurso Metodológico /
  Aspectos Metodológicos / Results / Resultados / Discussion / Discussão /
  Análise dos Resultados / Análise e Discussão / Results and Discussion /
  Resultados e Discussão / Resultados e Discussões / Conclusion / Conclusão /
  Considerações Finais / Conclusões / Considerações Gerais / Palavras Finais /
  Reflexões Finais

Back matter: References / Referências / Referências Bibliográficas / Bibliografia /
  Appendices / Apêndices / Apêndice / Annexes / Anexos / Anexo / Glossary / Glossário

---

## NOISE RULES — Rules A–H
Apply only to NON-CANONICAL headings.

A. Table header / column label / data identifier:
   A1. Single word/phrase that is a scale, benchmark, or data category (not a section word).
       Discard: ETAPA, GMFCS, BLEU, IEEE. Never discard canonical names even if all-caps.
   A2. Number or number+unit read as data value: "4 ou Mais", "1 Salário", "≥ 2 anos".
   A3. Comma-separated math variables: "Q, K, V", "d_k, d_v".
   A4. Benchmark / language-pair ID (2–12 chars, uppercase+digits+hyphens): "EN-DE", "WSJ 23 F1".
       Never discard all-caps canonical names or compound canonical forms.

B. Body-text fragment:
   B1. Ends with open/close quote or close parenthesis (mid-sentence cut).
   B2. 1–4 characters and not a known section abbreviation.
   B3. Starts with comma, closing parenthesis, or math operator.
   B4. Single parenthesised letter/number sub-item label: "(A)", "(1)".

C. Bibliographic entry:
   C1. Contains ISBN:, ISSN:, DOI, doi:, http://, https://.
   C2. Ends with "Edited by", "et al.", "org.", "eds.".
   C3. Numbered-reference pattern: digits + "." or ")" + author surname in title case.
   C4. Journal/book title fragment: "Journal of …", "Rev. Bras. …", edition/volume info.

D. Document title captured as heading (all three conditions required):
   — start_anchor ≤ 15
   — NOT canonical
   — AND at least one of:
     (a) Contains a colon in the middle (subtitle punctuation).
     (b) Longer than 40 chars, reads as a noun phrase, no rule-11 word in it.
     (c) Immediately precedes a front-matter canonical section with no section in between.
     (d) Ends with a dangling preposition/conjunction AND the next heading (by anchor),
         when concatenated, forms a plausible title. Discard both fragments.
     (e) Two or more consecutive non-canonical headings at start_anchor ≤ 30 whose
         combined text exceeds 60 chars and reads as one noun phrase. Discard all.

E. Publisher metadata / identifier string (ISBN, DOI strings).

F. Dataset description fragment: starts with a 4-digit year + training/corpus description.

G. Math expression or code fragment: operators, angle brackets, function-call syntax,
   no natural-language words; or main content is a citation bracket ([38], [1,2]).

H. Author byline or institutional affiliation (discard at ANY anchor position):
   H1. Proper names separated by commas/semicolons ± superscripts or degrees.
   H2. Superscript digit/symbol + university/hospital/city/country.
   H3. Only an ORCID, email, funding statement, or conflict-of-interest declaration.

---

## DOCUMENT TITLE RECOVERY
This determines the value of the root "title" field. Apply in order:

1. If headings were discarded via rule D(d) or D(e): concatenate them in start_anchor order
   (separated by a single space) → use as root title.
2. Else if there is a non-canonical heading at start_anchor ≤ 10 that was NOT discarded
   by any rule: use the one with the lowest start_anchor as root title.
3. Never use a canonical section name (rule 11) as root title.
4. Fallback: root title = "Document".

---

## GENERAL FILTERS — Rules 4–9
Apply only to NON-CANONICAL headings that passed rules A–H.

4. Longer than 100 characters → DISCARD.
5. Ends with period, colon, or semicolon → DISCARD.
6. Standalone number, page number, or bare Roman numeral → DISCARD.
7. Figure/table labels:
   — Bare label (prefix + number only, e.g. "Figura 3", "Table 2a") → DISCARD.
   — Prefix + dash/period + descriptive phrase of ≥5 words → KEEP.
   — "Apêndice", "Anexo", "Appendix" are canonical → always KEEP.
8. Starts with bullet "•", "–", "-", or lowercase mid-sentence → DISCARD.
9. Publication-type running label → DISCARD unconditionally at any anchor:
   Artigo Original, Original Article, Artigo de Revisão, Review Article,
   Relato de Caso, Case Report, Comunicação Breve, Short Communication,
   Editorial, Carta ao Editor, Letter to the Editor.
   Also: repeated institution/author/journal running headers/footers.

---

## SUBTYPE BIAS — Rule 11b
Infer subtype from canonical markers (e.g. "Relato de Caso" → case report).
Default: Original Article (IMRaD).
When a heading matches a subtype-expected variant below AND fits its expected position,
resolve any doubt in rules A–H and 4–9 as KEEP.

Original Article variants: Delineamento do Estudo, Percurso Metodológico,
  Aspectos Metodológicos, Análise dos Dados, Análise Estatística, Coleta de Dados,
  Amostra, Participantes, Casuística, Limitações, Implicações Clínicas,
  Declaração de Ética, Aprovação Ética, Aspectos Éticos, Conflito de Interesses,
  Financiamento.

Review Article variants: Estratégia de Busca, Critérios de Inclusão/Exclusão,
  Critérios de Elegibilidade, Seleção dos Estudos, Avaliação da Qualidade,
  Extração dos Dados, Síntese dos Resultados, Qualidade da Evidência, Risco de Viés,
  Caracterização dos Estudos, Estudos Incluídos/Excluídos.

Case Report variants: Descrição do Caso, Apresentação do Caso, Relato do Caso,
  História Clínica, Exame Físico, Exames Complementares, Evolução Clínica,
  Tratamento, Diagnóstico, Discussão do Caso, Seguimento.

---

## STRUCTURE RULES

1. Each node: exactly {{"title": "…", "children": […]}}.
2. Max 2 levels (sections and subsections).
3. Ambiguous level → treat as level 1.
3b. Subsections are optional. Only include a child if its heading was explicitly level 2.
    Never infer or fabricate subsections.
10. If discarding a heading leaves a parent with no children, keep the parent (children: []).

---

## MERGING — Rules 13–15

13. Merge only headings that refer to the SAME section:
    — Same title ± numbering prefix ("Methodology" + "3. Methodology" → one node).
    — Same canonical section in different cases, ONLY if both map to the SAME rule-11 entry.
    When merging: prefer numbered title; prefer longer if no number; normalise to title case;
    use lowest start_anchor for position.
    NEVER merge headings that map to DIFFERENT rule-11 entries (e.g. Resumo + Introdução).
    NEVER split compound canonical headings into separate nodes:
      "Resultados e Discussão", "Materiais e Métodos",
      "Considerações Finais", "Referências Bibliográficas".
14. No duplicate nodes.
15. Genuinely distinct sections are never merged.

---

## ORDERING — Rules 16–19 (CRITICAL)

16. Output order = physical document order = ascending start_anchor.
17. NEVER reorder to match a canonical template.
18. Subsections also ordered by ascending start_anchor.
19. Merged node position = lowest start_anchor among sources.

---

## SELF-CHECK (run before outputting)

1. Completeness: every input heading either appears once in output OR has a named discard rule.
   Cannot name a rule → KEEP.
2. No hallucination: every output node traces to an exact input heading.
   No source → REMOVE.
3. Order: start_anchors strictly non-decreasing at every level.
4. Canonical safety: no rule-11 heading was discarded.
5. Merge safety: no two different rule-11 entries were merged.
6. No splitting: no compound canonical heading was split into multiple nodes.
7. No publication-type labels (rule 9) in output.
8. No bylines/affiliations (rule H) in output.
9. Subsection source: every level-2 child comes from an input level-2 heading.
10. Title check: root "title" is the recovered document title, NOT "Document",
    unless no title could be identified.

---

## OUTPUT FORMAT

Return raw JSON only — no markdown fences, no comments.
The root "title" must be the actual document title recovered per the Title Recovery rules above.

{{
  "title": "<actual document title recovered from headings>",
  "children": [
    {{"title": "<Section A>", "children": []}},
    {{"title": "<Section B>", "children": [
      {{"title": "<Subsection B.1>", "children": []}}
    ]}}
  ]
}}

## Input headings
{trees}
"""