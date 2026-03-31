import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any

from decouple import config

from sectionminer import SectionMiner
from sectionminer.miner import _compact_text


def _parse_presets(values: list[str] | None) -> list[str]:
    presets: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        parts = re.split(r"[;,\n]", raw)
        for part in parts:
            cleaned = _compact_text(part)
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            presets.append(cleaned)
    return presets


def _resolve_api_key(cli_api_key: str | None) -> str:
    if cli_api_key:
        return cli_api_key
    return config("OPENAI_API_KEY", default="")


def _resolve_litellm_api_key(cli_api_key: str | None) -> str:
    """Resolve LiteLLM API key: CLI > LITELLM_API_KEY > OPENAI_API_KEY."""
    if cli_api_key:
        return cli_api_key
    return config("LITELLM_API_KEY", default="") or config("OPENAI_API_KEY", default="")


def _resolve_gemini_api_key(cli_api_key: str | None) -> str:
    if cli_api_key:
        return cli_api_key
    return config("GEMINI_API_KEY", default="")


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


def _build_miner(args: argparse.Namespace, presets: list[str]) -> SectionMiner:
    """Factory that builds a SectionMiner respecting --use-litellm and related flags."""
    use_litellm = getattr(args, "use_litellm", False)

    if use_litellm:
        api_key = _resolve_litellm_api_key(getattr(args, "litellm_api_key", None))
        model = getattr(args, "litellm_model", None) or config("LITELLM_MODEL", default="openai/gpt-4o-mini")
    else:
        api_key = _resolve_api_key(getattr(args, "api_key", None))
        model = getattr(args, "model", "gpt-4o-mini")

    return SectionMiner(
        args.pdf,
        api_key=api_key,
        model=model,
        extraction_backend=getattr(args, "extraction_backend", "pymupdf"),
        gemini_api_key=_resolve_gemini_api_key(getattr(args, "gemini_api_key", None)),
        gemini_model=getattr(args, "gemini_model", "gemini-2.0-flash"),
        preset_sections=presets,
        use_litellm=use_litellm,
    )


def _extract_command(args: argparse.Namespace) -> int:
    presets = _parse_presets(getattr(args, "preset_sections", None))
    miner = _build_miner(args, presets)
    try:
        if args.heuristic_only:
            miner.extract_blocks()
            miner.build_full_text()
            raw_sections = miner.build_sections()
            sections = []
            for section in raw_sections:
                sanitized = dict(section)
                sanitized["text"] = _compact_text(section.get("text", ""))
                sections.append(sanitized)
            payload = {
                "mode": "heuristic",
                "sections": sections,
            }
            _write_output(payload, args.output, args.pretty)
            if args.show_cost:
                _print_usage_summary({"cost_usd": 0.0, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0})
            return 0

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
    presets = _parse_presets(getattr(args, "preset_sections", None))
    miner = _build_miner(args, presets)
    try:
        if args.heuristic_only:
            miner.extract_blocks()
            miner.build_full_text()
            miner.build_sections()
            start, end = miner.get_section_start_and_end_chars(args.title)
            if start is None or end is None:
                raise SystemExit(f"Secao nao encontrada: {args.title}")
            text = _compact_text(miner.get_full_text()[start:end])
            print(text)
            if args.show_cost:
                _print_usage_summary({"cost_usd": 0.0, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0})
            return 0

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


def _runserver_command(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("uvicorn nao instalado. Rode: pip install uvicorn") from exc

    from sectionminer.server.app import ServerSettings, create_app

    use_litellm = getattr(args, "use_litellm", False)
    if use_litellm:
        api_key = _resolve_litellm_api_key(getattr(args, "litellm_api_key", None))
        model = getattr(args, "litellm_model", None) or config("LITELLM_MODEL", default="openai/gpt-4o-mini")
    else:
        api_key = _resolve_api_key(args.api_key)
        model = args.model

    settings = ServerSettings(
        api_key=api_key,
        model=model,
        extraction_backend=args.extraction_backend,
        gemini_api_key=_resolve_gemini_api_key(args.gemini_api_key),
        gemini_model=args.gemini_model,
        heuristic_only=args.heuristic_only,
        preset_sections=_parse_presets(getattr(args, "preset_sections", None)),
        use_litellm=use_litellm,
    )

    app = create_app(settings)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


def _add_litellm_args(parser: argparse.ArgumentParser) -> None:
    """Add LiteLLM-related arguments to a subcommand parser."""
    group = parser.add_argument_group("LiteLLM (alternativa ao OpenAI)")
    group.add_argument(
        "--use-litellm",
        action="store_true",
        help="Usa LiteLLM como backend LLM (suporta OpenAI, Anthropic, Groq, Azure, etc.)",
    )
    group.add_argument(
        "--litellm-model",
        default=None,
        help=(
            "Modelo LiteLLM com prefixo de provider. "
            "Ex: openai/gpt-4o-mini, anthropic/claude-3-haiku-20240307, groq/llama3-8b-8192. "
            "Fallback: variavel de ambiente LITELLM_MODEL."
        ),
    )
    group.add_argument(
        "--litellm-api-key",
        default=None,
        help="Chave do provider LiteLLM (fallback: LITELLM_API_KEY ou OPENAI_API_KEY).",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sectionminer",
        description="CLI para extrair secoes e subsecoes de PDFs.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── extract ──────────────────────────────────────────────────────────────
    extract = subparsers.add_parser("extract", help="Extrai a estrutura do PDF em JSON")
    extract.add_argument("pdf", help="Caminho do PDF de entrada")
    extract.add_argument("--api-key", help="Chave OpenAI (fallback: OPENAI_API_KEY)")
    extract.add_argument("--model", default="gpt-4o-mini", help="Modelo OpenAI")
    extract.add_argument("--tokens", action="store_true", help="Inclui uso de tokens no JSON")
    extract.add_argument("--show-cost", action="store_true", help="Mostra custo total da chamada no stderr")
    extract.add_argument("--heuristic-only", action="store_true", help="Nao usa LLM; retorna secoes heuristicas")
    extract.add_argument("--output", help="Arquivo de saida JSON")
    extract.add_argument("--pretty", action="store_true", help="Formata JSON com indentacao")
    extract.add_argument(
        "--extraction-backend",
        default="pymupdf",
        choices=SectionMiner.SUPPORTED_BACKENDS,
        help="Backend de extracao de texto (default: pymupdf)",
    )
    extract.add_argument("--gemini-api-key", help="Chave Gemini (fallback: GEMINI_API_KEY)")
    extract.add_argument("--gemini-model", default="gemini-2.0-flash", help="Modelo Gemini")
    extract.add_argument(
        "--preset-section",
        action="append",
        dest="preset_sections",
        help="Titulo de secao esperado. Pode repetir ou separar por virgula/ponto-e-virgula.",
    )
    _add_litellm_args(extract)
    extract.set_defaults(func=_extract_command)

    # ── section-text ─────────────────────────────────────────────────────────
    section_text = subparsers.add_parser("section-text", help="Retorna texto de uma secao por titulo")
    section_text.add_argument("pdf", help="Caminho do PDF de entrada")
    section_text.add_argument("title", help="Titulo da secao")
    section_text.add_argument("--api-key", help="Chave OpenAI (fallback: OPENAI_API_KEY)")
    section_text.add_argument("--model", default="gpt-4o-mini", help="Modelo OpenAI")
    section_text.add_argument("--heuristic-only", action="store_true", help="Nao usa LLM; busca na estrutura heuristica")
    section_text.add_argument(
        "--extraction-backend",
        default="pymupdf",
        choices=SectionMiner.SUPPORTED_BACKENDS,
        help="Backend de extracao de texto (default: pymupdf)",
    )
    section_text.add_argument("--gemini-api-key", help="Chave Gemini (fallback: GEMINI_API_KEY)")
    section_text.add_argument("--gemini-model", default="gemini-2.0-flash", help="Modelo Gemini")
    section_text.add_argument(
        "--preset-section",
        action="append",
        dest="preset_sections",
        help="Titulo de secao esperado para guiar o agrupamento (opcional)",
    )
    section_text.add_argument("--show-cost", action="store_true", help="Mostra custo total da chamada no stderr")
    _add_litellm_args(section_text)
    section_text.set_defaults(func=_section_text_command)

    # ── runserver ─────────────────────────────────────────────────────────────
    runserver = subparsers.add_parser("runserver", help="Sobe API FastAPI com interface visual")
    runserver.add_argument("--host", default="127.0.0.1", help="Host do servidor")
    runserver.add_argument("--port", type=int, default=8000, help="Porta do servidor")
    runserver.add_argument("--reload", action="store_true", help="Ativa auto-reload de desenvolvimento")
    runserver.add_argument("--api-key", help="Chave OpenAI (fallback: OPENAI_API_KEY)")
    runserver.add_argument("--model", default="gpt-4o-mini", help="Modelo OpenAI")
    runserver.add_argument(
        "--extraction-backend",
        default="pymupdf",
        choices=SectionMiner.SUPPORTED_BACKENDS,
        help="Backend de extracao de texto",
    )
    runserver.add_argument("--gemini-api-key", help="Chave Gemini (fallback: GEMINI_API_KEY)")
    runserver.add_argument("--gemini-model", default="gemini-2.0-flash", help="Modelo Gemini")
    runserver.add_argument("--heuristic-only", action="store_true", help="Nao usa LLM; retorna secoes heuristicas")
    runserver.add_argument(
        "--preset-section",
        action="append",
        dest="preset_sections",
        help="Titulo de secao esperado para pre-preencher a UI e a API (pode repetir ou separar por virgula)",
    )
    _add_litellm_args(runserver)
    runserver.set_defaults(func=_runserver_command)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return args.func(args)