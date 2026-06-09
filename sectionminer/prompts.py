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
Keeping noise is far less harmful than discarding a real section.
NEVER invent sections absent from the input. This is absolute.

---

## MULTILINGUAL PROTECTION — Rule 0 (NEW — evaluated BEFORE all other rules)
Documents may mix Portuguese and English headings freely.
A heading is protected if it matches a canonical section name (rule 11)
in ANY language — Portuguese or English.
Never discard a heading solely because its language differs from the
predominant language of the document.
Examples that are always kept regardless of language:
  "Abstract" in an otherwise Portuguese document.
  "Introdução" in an otherwise English document.
  "Methodology" alongside "Resultados".
  "Discussion" alongside "Metodologia".

---

## NUMBERING PROTECTION — Rule 0b (NEW — evaluated BEFORE all other rules)
Any heading may carry a numbering prefix in ANY of these formats:
  Simple:      "1 Introdução", "2. Metodologia", "3 Resultados"
  Decimal:     "1.1 Contexto", "2.3.1 Amostra", "3.1.2 Análise"
  Deep:        "1.1.1.1 Subitem" (any depth, up to 5 levels)
  Roman:       "I. Introdução", "II Metodologia", "IV. Resultados"
  Alphabetic:  "A. Introdução", "B) Metodologia"
  Parenthesised: "(1) Contexto", "(a) Definições"
  Mixed:       "1a. Introdução", "2b Metodologia"

Strip the prefix mentally before applying any rule.
A heading that matches a canonical name after prefix removal is
canonical and must be kept (rule 11 + rule 12).
A heading that does NOT match canonical after prefix removal must
still pass through the full decision flow — but the prefix alone
is never a reason to discard.

SUBSECTION NUMBERING: headings with two or more numeric segments
(e.g. "2.1", "3.4.2") are subsections (level 2) by definition and
must be kept unless a specific noise rule clearly applies.
Deep decimal prefixes ("1.1.2 Análise de Dados") indicate subsections
of subsections — collapse them to level 2 in the output tree rather
than discarding.

---

## DECISION FLOW (apply in order, stop at first match)

1. RULE 0 / 0b? Multilingual or numbering protection → KEEP unconditionally.
2. CANONICAL? (Rule 11) → KEEP unconditionally. Skip steps 3–4.
3. NOISE? (Rules A–H) → DISCARD. If rule 11b variant, resolve doubt as KEEP.
4. GENERAL FILTER? (Rules 4–9) → DISCARD if clear match; else KEEP.
5. Default → KEEP.

---

## CANONICAL SECTIONS — Rule 11
These are PROTECTED. Match = skip all other rules and keep.
Match is case-insensitive, ignores numbering prefixes (rule 0b) and accents.
All-caps forms are canonical: "RESULTADOS E DISCUSSÃO", "MATERIAIS E MÉTODOS".
Bilingual forms are canonical: "Abstract" AND "Resumo" are both kept if both present.

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
Apply only to NON-CANONICAL headings (after prefix stripping per rule 0b).
Rule 0 (multilingual protection) overrides all noise rules.

A. Table header / column label / data identifier:
   A1. Single word/phrase that is a scale, benchmark, or data category (not a section word).
       Discard: ETAPA, GMFCS, BLEU, IEEE. Never discard canonical names even if all-caps.
   A2. Number or number+unit read as data value: "4 ou Mais", "1 Salário", "≥ 2 anos".
       EXCEPTION: do NOT apply A2 to numbered headings that, after prefix removal,
       yield a natural-language title (e.g. "2.1 Análise de Dados" → title is
       "Análise de Dados", not a data value — keep it).
   A3. Comma-separated math variables: "Q, K, V", "d_k, d_v".
   A4. Benchmark / language-pair ID (2–12 chars, uppercase+digits+hyphens): "EN-DE", "WSJ 23 F1".
       Never discard all-caps canonical names or compound canonical forms.

B. Body-text fragment:
   B1. Ends with open/close quote or close parenthesis (mid-sentence cut).
   B2. 1–4 characters and not a known section abbreviation.
       EXCEPTION: do NOT apply B2 to Roman numerals or single-letter prefixes
       that are numbering tokens (e.g. a heading "I" followed by a title word
       on the same line is a numbered heading, not a fragment — keep it).
   B3. Starts with comma, closing parenthesis, or math operator.
   B4. Single parenthesised letter/number sub-item label: "(A)", "(1)".
       EXCEPTION: if the parenthesised token is followed by a natural-language
       title phrase, treat it as a numbered heading (rule 0b) — keep it.

C. Bibliographic entry:
   C1. Contains ISBN:, ISSN:, DOI, doi:, http://, https://.
   C2. Ends with "Edited by", "et al.", "org.", "eds.".
   C3. Numbered-reference pattern: digits + "." or ")" + author surname in title case.
       EXCEPTION: do NOT apply C3 to section headings with decimal numbering
       where the text after the number is a natural-language phrase, not a surname.
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

CRITICAL — NO DOUBLE APPEARANCE:
A heading used as the root title MUST NOT also appear as a child node in "children".
The title heading is consumed entirely by the root; remove it from the section list.
This applies whether the heading was discarded via rule D or promoted via step 2 above.

  WRONG — title duplicated as first child:
  {{
    "title": "Impacto da Tecnologia na Educação Básica",
    "children": [
      {{"title": "Impacto da Tecnologia na Educação Básica", "children": []}},  ← REMOVE
      {{"title": "Resumo", "children": []}},
      ...
    ]
  }}

  CORRECT — title only at root, absent from children:
  {{
    "title": "Impacto da Tecnologia na Educação Básica",
    "children": [
      {{"title": "Resumo", "children": []}},
      ...
    ]
  }}

---

## GENERAL FILTERS — Rules 4–9
Apply only to NON-CANONICAL headings that passed rules A–H.

4. Longer than 100 characters → DISCARD.
5. Ends with period, colon, or semicolon → DISCARD.
   EXCEPTION: do NOT apply rule 5 to headings where the period is part of
   a decimal numbering prefix (e.g. "2.1." where the trailing period is a
   separator, not sentence-ending punctuation). Strip the prefix first.
6. Standalone number, page number, or bare Roman numeral WITH NO accompanying
   text → DISCARD. A Roman numeral followed by any word is rule 0b (numbered
   heading) and must be kept.
7. Figure/table labels:
   — Bare label (prefix + number only, e.g. "Figura 3", "Table 2a") → DISCARD.
   — Prefix + dash/period + descriptive phrase of ≥5 words → KEEP.
   — "Apêndice", "Anexo", "Appendix" are canonical → always KEEP.
8. Starts with bullet "•", "–", "-", or lowercase mid-sentence → DISCARD.
   EXCEPTION: "–" used as a numbering-style prefix before a capitalized
   section word (e.g. "– Introdução") is a numbered heading — keep it.
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
3b. Subsections are included when the input heading was level 2 OR when the
    heading carries a decimal numbering prefix with two or more segments
    (e.g. "2.1", "3.4.2"). Deep prefixes (3+ segments) are collapsed to level 2.
    Never fabricate subsections not present in the input.
10. If discarding a heading leaves a parent with no children, keep the parent (children: []).

---

## MERGING — Rules 13–15

13. Merge only headings that refer to the SAME section:
    — Same title ± numbering prefix ("Methodology" + "3. Methodology" → one node).
    — Same canonical section in different cases, ONLY if both map to the SAME rule-11 entry.
    When merging: prefer numbered title; prefer longer if no number; normalise to title case;
    use lowest start_anchor for position.
    NEVER merge headings that map to DIFFERENT rule-11 entries (e.g. Resumo + Introdução).
    NEVER merge bilingual equivalents that both appear in the document
    (e.g. "Abstract" + "Resumo" when both are present → keep as two separate nodes).
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
9. Subsection source: every level-2 child comes from an input level-2 heading
   OR a heading with a decimal prefix of two or more segments (rule 0b).
10. Title check: root "title" is the recovered document title, NOT "Document",
    unless no title could be identified.
11. Multilingual check (NEW): confirm no heading was discarded solely because
    its language differs from the predominant document language (rule 0).
12. Numbering check (NEW): confirm no heading was discarded because of its
    numbering prefix format — all prefix formats in rule 0b are valid.
13. Subsection completeness (NEW): for every decimal-prefixed heading with
    two or more segments, confirm it appears as a level-2 child in the output
    or has a named discard rule (excluding rule 0b itself).
14. No-duplicate-title check (NEW): confirm the root "title" value does NOT
    appear anywhere inside "children" at any level. If it does, remove it.

---

## REAL-WORLD EXAMPLES BY DOCUMENT TYPE

These examples show correct KEEP/DISCARD decisions for headings that are
frequently lost. Study them before processing the input.

────────────────────────────────────────────────────────────────
### TCC / Monografia (Portuguese, numbered sections)
────────────────────────────────────────────────────────────────

Input headings (flat, as extracted from PDF):
  {{"title": "Uso de Aplicativos Móveis no Ensino de Matemática", "level": 1, "start_anchor": 0}}
  {{"title": "Resumo", "level": 1, "start_anchor": 45}}
  {{"title": "Abstract", "level": 1, "start_anchor": 120}}          ← English in PT doc
  {{"title": "1 Introdução", "level": 1, "start_anchor": 200}}
  {{"title": "1.1 Contextualização", "level": 2, "start_anchor": 310}}
  {{"title": "1.2 Justificativa", "level": 2, "start_anchor": 420}}
  {{"title": "1.3 Objetivos", "level": 2, "start_anchor": 530}}
  {{"title": "1.3.1 Objetivo Geral", "level": 2, "start_anchor": 590}}   ← deep decimal
  {{"title": "1.3.2 Objetivos Específicos", "level": 2, "start_anchor": 650}}
  {{"title": "2 Referencial Teórico", "level": 1, "start_anchor": 800}}
  {{"title": "2.1 Tecnologia na Educação", "level": 2, "start_anchor": 900}}
  {{"title": "2.2 Gamificação", "level": 2, "start_anchor": 1050}}
  {{"title": "3 Metodologia", "level": 1, "start_anchor": 1200}}
  {{"title": "3.1 Tipo de Pesquisa", "level": 2, "start_anchor": 1280}}
  {{"title": "3.2 Participantes", "level": 2, "start_anchor": 1360}}
  {{"title": "3.3 Instrumentos de Coleta de Dados", "level": 2, "start_anchor": 1440}}
  {{"title": "4 Resultados e Discussão", "level": 1, "start_anchor": 1600}}
  {{"title": "4.1 Análise Quantitativa", "level": 2, "start_anchor": 1700}}
  {{"title": "4.2 Análise Qualitativa", "level": 2, "start_anchor": 1820}}
  {{"title": "5 Considerações Finais", "level": 1, "start_anchor": 2000}}
  {{"title": "Referências", "level": 1, "start_anchor": 2100}}
  {{"title": "Apêndice A – Questionário Aplicado", "level": 1, "start_anchor": 2200}}

Correct output (abbreviated):
{{
  "title": "Uso de Aplicativos Móveis no Ensino de Matemática",
  "children": [
    {{"title": "Resumo", "children": []}},
    {{"title": "Abstract", "children": []}},           ← KEEP: canonical in any language (rule 0)
    {{"title": "1 Introdução", "children": [
      {{"title": "1.1 Contextualização", "children": []}},
      {{"title": "1.2 Justificativa", "children": []}},
      {{"title": "1.3 Objetivos", "children": [
        {{"title": "1.3.1 Objetivo Geral", "children": []}},      ← KEEP: deep decimal → level 2
        {{"title": "1.3.2 Objetivos Específicos", "children": []}}
      ]}}
    ]}},
    {{"title": "2 Referencial Teórico", "children": [
      {{"title": "2.1 Tecnologia na Educação", "children": []}},
      {{"title": "2.2 Gamificação", "children": []}}
    ]}},
    {{"title": "3 Metodologia", "children": [
      {{"title": "3.1 Tipo de Pesquisa", "children": []}},
      {{"title": "3.2 Participantes", "children": []}},
      {{"title": "3.3 Instrumentos de Coleta de Dados", "children": []}}
    ]}},
    {{"title": "4 Resultados e Discussão", "children": [
      {{"title": "4.1 Análise Quantitativa", "children": []}},
      {{"title": "4.2 Análise Qualitativa", "children": []}}
    ]}},
    {{"title": "5 Considerações Finais", "children": []}},
    {{"title": "Referências", "children": []}},
    {{"title": "Apêndice A – Questionário Aplicado", "children": []}}
  ]
}}

Key decisions:
  "Abstract" → KEEP (rule 0: canonical in English, document is Portuguese — language never disqualifies)
  "1.3 Objetivos" + "1.3.1" + "1.3.2" → KEEP all (rule 0b: numbered headings; deep decimal → level 2)
  "3.2 Participantes" → KEEP (rule 0b + rule 11b: subtype variant for Original Article)
  "Apêndice A – Questionário Aplicado" → KEEP (rule 11: canonical back matter)

────────────────────────────────────────────────────────────────
### Artigo Científico (mixed PT/EN, unnumbered subsections)
────────────────────────────────────────────────────────────────

Input headings (flat):
  {{"title": "Efeitos do Treinamento Resistido em Idosos com Sarcopenia", "level": 1, "start_anchor": 0}}
  {{"title": "Resumo", "level": 1, "start_anchor": 30}}
  {{"title": "Abstract", "level": 1, "start_anchor": 90}}
  {{"title": "Palavras-chave", "level": 1, "start_anchor": 150}}
  {{"title": "Keywords", "level": 1, "start_anchor": 170}}          ← English in PT doc
  {{"title": "Introdução", "level": 1, "start_anchor": 200}}
  {{"title": "Materiais e Métodos", "level": 1, "start_anchor": 500}}
  {{"title": "Delineamento do Estudo", "level": 2, "start_anchor": 560}}   ← unnumbered subsection
  {{"title": "Amostra", "level": 2, "start_anchor": 620}}                  ← unnumbered subsection
  {{"title": "Critérios de Inclusão e Exclusão", "level": 2, "start_anchor": 700}}
  {{"title": "Protocolo de Treinamento", "level": 2, "start_anchor": 780}}
  {{"title": "Análise Estatística", "level": 2, "start_anchor": 860}}
  {{"title": "Resultados", "level": 1, "start_anchor": 1000}}
  {{"title": "Características da Amostra", "level": 2, "start_anchor": 1080}}
  {{"title": "Desfechos Funcionais", "level": 2, "start_anchor": 1200}}
  {{"title": "Discussão", "level": 1, "start_anchor": 1400}}
  {{"title": "Limitações", "level": 2, "start_anchor": 1600}}
  {{"title": "Conclusão", "level": 1, "start_anchor": 1700}}
  {{"title": "Referências", "level": 1, "start_anchor": 1800}}

Correct output (abbreviated):
{{
  "title": "Efeitos do Treinamento Resistido em Idosos com Sarcopenia",
  "children": [
    {{"title": "Resumo", "children": []}},
    {{"title": "Abstract", "children": []}},
    {{"title": "Palavras-chave", "children": []}},
    {{"title": "Keywords", "children": []}},           ← KEEP: canonical in English (rule 0)
    {{"title": "Introdução", "children": []}},
    {{"title": "Materiais e Métodos", "children": [
      {{"title": "Delineamento do Estudo", "children": []}},   ← KEEP: unnumbered level-2 (rule 11b)
      {{"title": "Amostra", "children": []}},                  ← KEEP: unnumbered level-2 (rule 11b)
      {{"title": "Critérios de Inclusão e Exclusão", "children": []}},
      {{"title": "Protocolo de Treinamento", "children": []}},
      {{"title": "Análise Estatística", "children": []}}
    ]}},
    {{"title": "Resultados", "children": [
      {{"title": "Características da Amostra", "children": []}},
      {{"title": "Desfechos Funcionais", "children": []}}
    ]}},
    {{"title": "Discussão", "children": [
      {{"title": "Limitações", "children": []}}
    ]}},
    {{"title": "Conclusão", "children": []}},
    {{"title": "Referências", "children": []}}
  ]
}}

Key decisions:
  "Keywords" → KEEP (rule 0: canonical in English regardless of document language)
  "Delineamento do Estudo", "Amostra", "Análise Estatística" → KEEP (rule 11b: Original Article variants;
    input level was 2 → subsections)
  "Limitações" → KEEP (rule 11b: Original Article variant)

────────────────────────────────────────────────────────────────
### Dissertação / Tese (numbered, deep hierarchy, PT)
────────────────────────────────────────────────────────────────

Input headings (flat, problem cases highlighted):
  {{"title": "Sumário", "level": 1, "start_anchor": 10}}
  {{"title": "Lista de Figuras", "level": 1, "start_anchor": 30}}
  {{"title": "Lista de Tabelas", "level": 1, "start_anchor": 50}}
  {{"title": "Lista de Abreviaturas e Siglas", "level": 1, "start_anchor": 70}}
  {{"title": "1 Introdução", "level": 1, "start_anchor": 100}}
  {{"title": "1.1 Problemática", "level": 2, "start_anchor": 180}}
  {{"title": "1.2 Hipóteses", "level": 2, "start_anchor": 260}}
  {{"title": "1.3 Estrutura da Dissertação", "level": 2, "start_anchor": 340}}
  {{"title": "2 Revisão de Literatura", "level": 1, "start_anchor": 500}}
  {{"title": "2.1 Conceitos Fundamentais", "level": 2, "start_anchor": 600}}
  {{"title": "2.1.1 Definição de Variável X", "level": 2, "start_anchor": 660}}   ← deep decimal
  {{"title": "2.1.2 Definição de Variável Y", "level": 2, "start_anchor": 720}}   ← deep decimal
  {{"title": "2.2 Estado da Arte", "level": 2, "start_anchor": 800}}
  {{"title": "3 Metodologia", "level": 1, "start_anchor": 1000}}
  {{"title": "3.1 Percurso Metodológico", "level": 2, "start_anchor": 1080}}
  {{"title": "3.2 Coleta de Dados", "level": 2, "start_anchor": 1160}}
  {{"title": "3.3 Análise dos Dados", "level": 2, "start_anchor": 1240}}
  {{"title": "4 Resultados", "level": 1, "start_anchor": 1400}}
  {{"title": "4.1 Resultados Quantitativos", "level": 2, "start_anchor": 1500}}
  {{"title": "4.2 Resultados Qualitativos", "level": 2, "start_anchor": 1650}}
  {{"title": "5 Discussão", "level": 1, "start_anchor": 1800}}
  {{"title": "6 Conclusões", "level": 1, "start_anchor": 2000}}
  {{"title": "Referências Bibliográficas", "level": 1, "start_anchor": 2100}}
  {{"title": "Apêndices", "level": 1, "start_anchor": 2200}}
  {{"title": "Anexos", "level": 1, "start_anchor": 2300}}

Key decisions:
  "2.1.1 Definição de Variável X" → KEEP, place as level-2 child of "2 Revisão de Literatura"
    (rule 0b: deep decimal collapsed to level 2; do NOT discard for having 3 numeric segments)
  "3.1 Percurso Metodológico" → KEEP (rule 11b: Original Article variant + rule 0b)
  "1.3 Estrutura da Dissertação" → KEEP (rule 0b: numbered subsection; prime directive)
  "Referências Bibliográficas" → KEEP (rule 11: canonical back matter)

────────────────────────────────────────────────────────────────
### Relatório Técnico (mixed numbering styles, English subsections)
────────────────────────────────────────────────────────────────

Input headings (flat, problem cases highlighted):
  {{"title": "Relatório de Avaliação de Impacto Ambiental – Fase II", "level": 1, "start_anchor": 0}}
  {{"title": "Executive Summary", "level": 1, "start_anchor": 50}}    ← English in PT doc
  {{"title": "1. Introdução", "level": 1, "start_anchor": 200}}
  {{"title": "2. Caracterização da Área de Estudo", "level": 1, "start_anchor": 400}}
  {{"title": "2.1. Localização Geográfica", "level": 2, "start_anchor": 480}}
  {{"title": "2.2. Aspectos Físicos e Bióticos", "level": 2, "start_anchor": 560}}
  {{"title": "2.2.1. Solo e Relevo", "level": 2, "start_anchor": 610}}       ← deep decimal
  {{"title": "2.2.2. Hidrografia", "level": 2, "start_anchor": 660}}          ← deep decimal
  {{"title": "3. Methodology", "level": 1, "start_anchor": 800}}              ← English section
  {{"title": "3.1. Sampling Design", "level": 2, "start_anchor": 870}}        ← English subsection
  {{"title": "3.2. Data Analysis", "level": 2, "start_anchor": 950}}          ← English subsection
  {{"title": "4. Resultados", "level": 1, "start_anchor": 1100}}
  {{"title": "4.1 Indicadores Ambientais", "level": 2, "start_anchor": 1200}}
  {{"title": "4.2 Indicadores Socioeconômicos", "level": 2, "start_anchor": 1350}}
  {{"title": "5. Conclusão e Recomendações", "level": 1, "start_anchor": 1500}}
  {{"title": "Referências", "level": 1, "start_anchor": 1600}}
  {{"title": "Anexo I – Mapas", "level": 1, "start_anchor": 1700}}
  {{"title": "Anexo II – Dados Brutos", "level": 1, "start_anchor": 1800}}

Key decisions:
  "Executive Summary" → KEEP (rule 0: canonical equivalent of "Resumo" in English;
    do NOT discard because document is primarily Portuguese)
  "3. Methodology" → KEEP (rule 0: canonical in English; rule 0b: numbered prefix stripped)
  "3.1. Sampling Design" → KEEP (rule 0: English subsection; rule 0b: decimal prefix)
  "3.2. Data Analysis" → KEEP (rule 0: English subsection; rule 0b: decimal prefix)
  "2.2.1. Solo e Relevo" → KEEP (rule 0b: deep decimal collapsed to level 2)
  "Anexo I – Mapas" → KEEP (rule 11: canonical back matter; numbering suffix ignored)
  "Conclusão e Recomendações" → KEEP (prime directive: matches spirit of canonical "Conclusão";
    not a noise pattern)

────────────────────────────────────────────────────────────────
### Common traps — always KEEP these, never discard
────────────────────────────────────────────────────────────────

  "Abstract"            → canonical EN (rule 0), even in a PT document
  "Keywords"            → canonical EN (rule 0), even in a PT document
  "Executive Summary"   → canonical EN equivalent of Resumo (rule 0)
  "Discussion"          → canonical EN (rule 0)
  "Methodology"         → canonical EN (rule 0)
  "Results"             → canonical EN (rule 0)
  "Conclusion"          → canonical EN (rule 0)
  "2.1 Algo"            → numbered subsection (rule 0b); "Algo" is the real title
  "1.1.2 Algo"          → deep decimal subsection (rule 0b); collapse to level 2
  "I. Introdução"       → Roman numeral prefix (rule 0b); canonical after stripping
  "A) Metodologia"      → alphabetic prefix (rule 0b); canonical after stripping
  "– Introdução"        → dash prefix (rule 0b + rule 8 exception); canonical after stripping
  "Delineamento do Estudo"  → rule 11b Original Article variant; keep as subsection
  "Amostra"             → rule 11b Original Article variant; keep as subsection
  "Estratégia de Busca" → rule 11b Review Article variant; keep as subsection
  "Descrição do Caso"   → rule 11b Case Report variant; keep as subsection
  "Caracterização da Área de Estudo" → non-canonical but legitimate section (prime directive)
  "Conclusão e Recomendações"        → non-canonical variant of Conclusão (prime directive)
  "Estrutura da Dissertação"         → non-canonical but legitimate subsection (prime directive)

────────────────────────────────────────────────────────────────
### Common traps — always DISCARD these
────────────────────────────────────────────────────────────────

  "Artigo Original"      → rule 9 (publication-type label)
  "Original Article"     → rule 9
  "João Silva¹, Maria Souza²"  → rule H1 (byline)
  "¹Universidade Federal do RS" → rule H2 (affiliation)
  "EN-DE"               → rule A4 (benchmark ID)
  "Q, K, V"             → rule A3 (math variables)
  "44. Avelino MOA..."  → rule C3 (bibliographic reference)
  "Figura 3"            → rule 7 (bare figure label)
  "42"                  → rule 6 (standalone number)

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