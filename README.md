# SectionMiner

Extrator de estrutura de artigos em PDF (secoes e subsecoes) com apoio de LLM.

O projeto le o PDF, detecta candidatos a titulos com heuristicas (fonte/tamanho/estilo), e consolida uma arvore hierarquica em JSON.

## O que este projeto faz

- Extrai blocos de texto e metadados de fonte via PyMuPDF.
- Detecta headings provaveis (titulo de secao/subsecao).
- Monta secoes com intervalos de texto (`start`, `end`).
- Usa LLM para unificar a estrutura final em arvore JSON.
- Permite recuperar o texto de uma secao pelo titulo.

## Requisitos

- Python 3.10+
- Chave da OpenAI valida

Dependencias (arquivo `requirements.txt`):

- `pymupdf`
- `langchain`
- `langchain-openai`
- `langchain-text-splitters`
- `langchain-community`

## Instalacao

```bash
cd /Users/ehodiogo/PycharmProjects/SectionMiner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuracao da API Key

Evite hardcode de chave no codigo.
No macOS/Linux, exporte como variavel de ambiente:

```bash
export OPENAI_API_KEY="sua-chave-aqui"
```

## Uso rapido

Exemplo minimo:

```python
import os
import json
from base import SectionMiner

pdf_path = "files/Artigo_Provatis.pdf"
api_key = os.getenv("OPENAI_API_KEY")

miner = SectionMiner(pdf_path, api_key=api_key)

structure, tokens = miner.extract_structure(return_tokens=True)
print(tokens)
print(json.dumps(structure, indent=2, ensure_ascii=False))

intro = miner.get_section("Introducao")
if intro:
    print(intro["text"][:800])

miner.close()
```

Se quiser executar o script de teste atual:

```bash
python3 test.py
```

## Estrutura de arquivos

```text
SectionMiner/
  base.py          # pipeline principal (PDF -> secoes)
  client.py        # cliente LLM e consolidacao de arvores
  prompts.py       # reservado para prompts compartilhados
  test.py          # exemplo de execucao
  files/           # PDFs de entrada
```

## Formato da saida

A estrutura principal retornada por `extract_structure()` segue o formato de arvore JSON:

```json
{
  "title": "Document",
  "children": [
    {
      "title": "Introducao",
      "children": [
        {
          "title": "Contexto",
          "children": []
        }
      ]
    }
  ]
}
```

Cada secao interna gerada em `base.py` possui tambem metadados de texto:

- `title`: titulo detectado
- `level`: 1 (secao) ou 2 (subsecao)
- `start`: offset inicial no texto completo
- `end`: offset final no texto completo
- `text`: conteudo bruto entre `start` e `end`

## Limitacoes atuais

- PDFs com layout muito irregular podem gerar heading quebrado.
- Qualidade depende da consistencia tipografica do documento.
- O merge via LLM pode variar com o modelo e prompts.

## TODO (coisas a fazer)

- [X] Migrar carregamento da API key para `.env` (hoje usa `OPENAI_API_KEY` por variavel de ambiente).
- [ ] Criar testes automatizados para `detect_headings` e `merge_trees`.
- [ ] Melhorar filtro de ruido para reduzir titulos quebrados em PDFs complexos.
- [ ] Criar uma CLI simples (`sectionminer extract arquivo.pdf`).

## FAQ rapido

**1) Estou recebendo erro de autenticacao da OpenAI. O que verificar?**

- Confirme se `OPENAI_API_KEY` foi exportada no mesmo terminal da execucao.
- Verifique se a chave esta ativa e sem espacos extras.

**2) As secoes estao vindo quebradas. Como melhorar?**

- Ajuste as heuristicas de heading em `base.py` (filtros de ruido, tamanho minimo/maximo).
- Teste com outro PDF para comparar se o problema e do layout especifico.

**3) Nao aparece Introducao/Conclusao no JSON final.**

- Alguns documentos nao usam esses titulos de forma explicita.
- Revise o merge no `client.py` e, se necessario, refine o prompt de consolidacao.

**4) Posso rodar sem LLM?**

- Hoje o merge final depende de LLM.
- Um modo offline/local esta listado no TODO como melhoria futura.

## Proximos passos sugeridos

1. Rodar com 2-3 PDFs diferentes e comparar se as secoes principais saem limpas.
2. Ajustar regras de heading em `base.py` para o padrao de layout mais frequente dos seus artigos.
3. Depois, adicionar testes para evitar regressao nas heuristicas.

