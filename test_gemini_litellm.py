from decouple import config
import json
from sectionminer import SectionMiner


def main():
    litellm_api_key = config("OPENAI_API_KEY", default=None)
    litellm_model = config("LITELLM_MODEL", default="openai/gpt-4o-mini")
    gemini_api_key = config("GEMINI_API_KEY", default=None)
    gemini_model = config("GEMINI_MODEL", default="gemini-2.0-flash")

    if not litellm_api_key:
        raise SystemExit("OPENAI_API_KEY (ou chave do provider LiteLLM) não encontrada.")

    if not gemini_api_key:
        raise SystemExit("GEMINI_API_KEY não encontrada.")

    miner = SectionMiner(
        "files/Artigo_Provatis.pdf",
        litellm_api_key,
        model=litellm_model,
        extraction_backend="gemini",
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        use_litellm=True,
        preset_sections=["Introdução"],
    )

    try:
        structure, tokens = miner.extract_structure(return_tokens=True)

        print("\n=== TOKENS ===")
        print(tokens)

        # DEBUG: ver todos os títulos extraídos antes do LLM
        print("\n=== SECTION STRUCTURES (títulos brutos extraídos do PDF) ===")
        for s in miner.section_structures:
            print(f"  title={repr(s['title'])}  start={s['start']}  end={s['end']}")

        print("\n=== STRUCTURE ===")
        print(json.dumps(structure, indent=2, ensure_ascii=False))

        print("\n=== RESUMO ===")
        text = miner.get_section_text("Introdução")
        print(text)

    finally:
        miner.close()


if __name__ == "__main__":
    main()