# SectionMiner

Biblioteca Python para extrair secoes e subsecoes de PDFs academicos com heuristicas de layout + consolidacao por LLM.

Este README foi organizado com foco nas funcoes principais que sao usadas em `test.py`.

## Visao geral

O fluxo do projeto e:

1. Ler spans do PDF com fonte/tamanho (`PyMuPDF`).
2. Detectar titulos provaveis (heading).
3. Montar secoes com intervalos de caracteres (`start`, `end`).
4. Enviar um indice de headings para LLM consolidar a arvore final.
5. Buscar texto de uma secao pelo titulo.

## Requisitos

- Python 3.10+
- `OPENAI_API_KEY` valida
- Dependencias em `requirements.txt`:
  - `pymupdf`
  - `langchain`
  - `langchain-openai`
  - `langchain-text-splitters`
  - `langchain-community`
  - `python-decouple`

## Instalacao (modo biblioteca)

```bash
cd /Users/ehodiogo/PycharmProjects/SectionMiner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Depois disso, voce pode importar com `from sectionminer import SectionMiner` em qualquer script do ambiente.

Tambem instala a CLI `sectionminer`.

## Configuracao da chave

O `test.py` usa `python-decouple` para ler `OPENAI_API_KEY`.

Opcao 1 (rapida, terminal atual):

```bash
export OPENAI_API_KEY="sua-chave-aqui"
```

Opcao 2 (`.env` na raiz do projeto):

```env
OPENAI_API_KEY=sua-chave-aqui
```

## Fluxo principal (o que o `test.py` faz)

Arquivo: `test.py` (exemplo usando a biblioteca)

1. Le a chave com `config("OPENAI_API_KEY")`.
2. Cria `SectionMiner("files/Artigo_Provatis.pdf", api_key)`.
3. Executa `extract_structure(return_tokens=True)` para obter:
   - arvore de secoes/subsecoes
   - uso de tokens/custo
4. Consulta uma secao (ex.: `introducao`) por offsets com `get_section_start_and_end_chars`.
5. Recupera texto completo com `get_full_text()` e fatia por `[start:end]`.
6. Reexecuta pipeline manual (`extract_blocks`, `build_full_text`, `build_sections`) e imprime secoes com `get_sections()` e `get_section_text()`.
7. Fecha o PDF com `close()` no `finally`.

Executar:

```bash
python3 test.py
```

Exemplo alternativo (arquivo dedicado em `examples/`):

```bash
python3 examples/basic_usage.py
```

## CLI inicial

Comando raiz:

```bash
sectionminer --help
```

Extrair estrutura (com LLM):

```bash
sectionminer extract files/Artigo_Provatis.pdf --tokens --pretty
```

Extrair estrutura heuristica (sem LLM/OpenAI):

```bash
sectionminer extract files/Artigo_Provatis.pdf --heuristic-only --pretty
```

Salvar saida JSON em arquivo:

```bash
sectionminer extract files/Artigo_Provatis.pdf --heuristic-only --output out.json --pretty
```

Buscar texto de secao por titulo:

```bash
sectionminer section-text files/Artigo_Provatis.pdf "introducao"
```

Buscar texto de secao sem LLM (heuristica):

```bash
sectionminer section-text files/Artigo_Provatis.pdf "introducao" --heuristic-only
```

## Funcoes principais da API (`SectionMiner`)

Arquivo: `sectionminer/miner.py`

- `extract_structure(return_tokens=False)`
  - Pipeline completo (extracao, deteccao, merge com LLM).
  - Retorna a arvore final; com `return_tokens=True`, retorna `(arvore, usage)`.

- `get_section_start_and_end_chars(title)`
  - Retorna `(start, end)` da secao localizada por titulo.
  - Bom para recortar diretamente em `get_full_text()`.

- `get_full_text()`
  - Retorna o texto linear completo do PDF processado.

- `get_section_text(title)`
  - Busca no tree consolidado e devolve o texto da secao.

- `get_sections()`
  - Retorna lista de titulos detectados a partir das estruturas internas.

- `extract_blocks()`, `build_full_text()`, `build_sections()`
  - Etapas internas do pipeline usadas no `test.py` para depuracao/inspecao.

- `close()`
  - Fecha o documento PDF aberto em memoria.

## Exemplo minimo (mesma ideia do teste)

```python
import json
from decouple import config
from sectionminer import SectionMiner

api_key = config("OPENAI_API_KEY")
miner = SectionMiner("files/Artigo_Provatis.pdf", api_key)

try:
    structure, tokens = miner.extract_structure(return_tokens=True)
    print(tokens)
    print(json.dumps(structure, indent=2, ensure_ascii=False))

    start, end = miner.get_section_start_and_end_chars("introducao")
    if start is not None and end is not None:
        print(miner.get_full_text()[start:end][:800])

    print(miner.get_section_text("conclusao"))
finally:
    miner.close()
```

## Estrutura do projeto

```text
SectionMiner/
  sectionminer/
    __init__.py  # API publica da biblioteca
    miner.py     # classe SectionMiner
    client.py    # cliente LLM e merge da arvore
    prompts.py   # prompt de consolidacao
  base.py        # compatibilidade com import legado
  client.py      # compatibilidade com import legado
  prompts.py     # compatibilidade com import legado
  test.py        # fluxo de uso principal
  examples/      # exemplos prontos de execucao
  files/         # PDFs de exemplo
```

## Problemas comuns

### 1) "As secoes estao vindo quebradas"

- Revise filtros em `_is_noise_heading` e `_looks_like_heading` em `sectionminer/miner.py`.
- Ajuste threshold em `_detect_threshold` para o padrao do seu PDF.
- PDFs com layout irregular (duas colunas, rodape intrusivo, OCR ruim) tendem a piorar a deteccao.

### 2) Secao nao encontrada por titulo

- Tente variacao sem acento/caixa (a busca normaliza texto).
- Verifique os titulos retornados por `get_sections()`.

### 3) Erro de chave OpenAI

- Confirme `OPENAI_API_KEY` no mesmo ambiente da execucao.
- Se usar `.env`, confirme que esta na raiz do projeto.

## TODO (coisas a fazer)

- [ ] Criar testes automatizados para `detect_headings`, `build_sections` e `get_section_text`.
- [ ] Adicionar modo sem LLM (somente heuristica local) para uso offline.
- [x] Criar CLI inicial: `sectionminer extract arquivo.pdf --output out.json`.
- [ ] Expor parametros de heuristica por configuracao (threshold, filtros de ruido).
- [ ] Melhorar merge para manter apenas secoes/subsecoes validas (sem fragmentos quebrados).

## Publicacao (preparo inicial)

O projeto ja possui `pyproject.toml`, `LICENSE` e entrypoint de CLI.

Gerar artefatos:

```bash
python3 -m pip install --upgrade build twine
python3 -m build
python3 -m twine check dist/*
```

Teste local do wheel:

```bash
python3 -m pip install dist/*.whl
sectionminer --help
```

Publicar (TestPyPI primeiro, recomendado):

```bash
python3 -m twine upload --repository testpypi dist/*
```

Publicar no PyPI oficial:

```bash
python3 -m twine upload dist/*
```

## Licenca

MIT (arquivo `LICENSE`).

