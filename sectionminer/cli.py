import argparse
import json
from pathlib import Path
import sys
from typing import Any

from decouple import config

from sectionminer import SectionMiner


def _resolve_api_key(cli_api_key: str | None) -> str:
    if cli_api_key:
        return cli_api_key
    return config("OPENAI_API_KEY", default="")


def _write_output(data: Any, output_path: str | None, pretty: bool) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)
    if output_path:
        Path(output_path).write_text(text + "\n", encoding="utf-8")
        return
    print(text)


def _print_usage_summary(usage: dict | None) -> None:
    if not usage:
        return
    sys.stderr.write(
        "Cost summary: "
        f"prompt_tokens={usage.get('prompt_tokens', 0)} "
        f"completion_tokens={usage.get('completion_tokens', 0)} "
        f"total_tokens={usage.get('total_tokens', 0)} "
        f"cost_usd={usage.get('cost_usd', 0):.8f}\n"
    )


def _extract_command(args: argparse.Namespace) -> int:
    api_key = _resolve_api_key(args.api_key)

    miner = SectionMiner(args.pdf, api_key=api_key, model=args.model)
    try:
        if args.heuristic_only:
            miner.extract_blocks()
            miner.build_full_text()
            sections = miner.build_sections()
            payload = {
                "mode": "heuristic",
                "sections": sections,
            }
            _write_output(payload, args.output, args.pretty)
            if args.show_cost:
                _print_usage_summary({"cost_usd": 0.0, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0})
            return 0

        if not api_key:
            raise SystemExit("OPENAI_API_KEY nao encontrada. Use --api-key ou variavel de ambiente.")

        if args.tokens or args.show_cost:
            structure, usage = miner.extract_structure(return_tokens=True)
            payload = {"structure": structure, "usage": usage} if args.tokens else structure
        else:
            payload = miner.extract_structure(return_tokens=False)
            usage = None

        _write_output(payload, args.output, args.pretty)
        if args.show_cost:
            _print_usage_summary(usage)
        return 0
    finally:
        miner.close()


def _section_text_command(args: argparse.Namespace) -> int:
    api_key = _resolve_api_key(args.api_key)

    miner = SectionMiner(args.pdf, api_key=api_key, model=args.model)
    try:
        if args.heuristic_only:
            miner.extract_blocks()
            miner.build_full_text()
            miner.build_sections()
            start, end = miner.get_section_start_and_end_chars(args.title)
            if start is None or end is None:
                raise SystemExit(f"Secao nao encontrada: {args.title}")
            text = miner.get_full_text()[start:end]
            print(text)
            if args.show_cost:
                _print_usage_summary({"cost_usd": 0.0, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0})
            return 0

        if not api_key:
            raise SystemExit("OPENAI_API_KEY nao encontrada. Use --api-key ou variavel de ambiente.")

        usage = None
        if args.show_cost:
            _, usage = miner.extract_structure(return_tokens=True)
        else:
            miner.extract_structure()
        text = miner.get_section_text(args.title)
        if text is None:
            raise SystemExit(f"Secao nao encontrada: {args.title}")

        print(text)
        if args.show_cost:
            _print_usage_summary(usage)
        return 0
    finally:
        miner.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sectionminer",
        description="CLI para extrair secoes e subsecoes de PDFs.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="Extrai a estrutura do PDF em JSON")
    extract.add_argument("pdf", help="Caminho do PDF de entrada")
    extract.add_argument("--api-key", help="Chave OpenAI (fallback: OPENAI_API_KEY)")
    extract.add_argument("--model", default="gpt-4o-mini", help="Modelo OpenAI")
    extract.add_argument("--tokens", action="store_true", help="Inclui uso de tokens no JSON")
    extract.add_argument("--show-cost", action="store_true", help="Mostra custo total da chamada no stderr")
    extract.add_argument("--heuristic-only", action="store_true", help="Nao usa LLM; retorna secoes heuristicas")
    extract.add_argument("--output", help="Arquivo de saida JSON")
    extract.add_argument("--pretty", action="store_true", help="Formata JSON com indentacao")
    extract.set_defaults(func=_extract_command)

    section_text = subparsers.add_parser("section-text", help="Retorna texto de uma secao por titulo")
    section_text.add_argument("pdf", help="Caminho do PDF de entrada")
    section_text.add_argument("title", help="Titulo da secao")
    section_text.add_argument("--api-key", help="Chave OpenAI (fallback: OPENAI_API_KEY)")
    section_text.add_argument("--model", default="gpt-4o-mini", help="Modelo OpenAI")
    section_text.add_argument("--heuristic-only", action="store_true", help="Nao usa LLM; busca na estrutura heuristica")
    section_text.add_argument("--show-cost", action="store_true", help="Mostra custo total da chamada no stderr")
    section_text.set_defaults(func=_section_text_command)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return args.func(args)

