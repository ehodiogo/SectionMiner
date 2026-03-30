from decouple import config
import json
from sectionminer import SectionMiner


def main():
    openai_api_key = config("OPENAI_API_KEY")
    gemini_api_key = config("GEMINI_API_KEY")

    if not openai_api_key:
        raise SystemExit("OPENAI_API_KEY nao encontrada.")
    if not gemini_api_key:
        raise SystemExit("GEMINI_API_KEY nao encontrada.")

    miner = SectionMiner(
        "files/Artigo_Provatis.pdf",
        api_key=openai_api_key,
        extraction_backend="gemini",
        gemini_api_key=gemini_api_key,
        gemini_model="gemini-2.5-flash-lite",
        preset_sections=["Introdução"],
    )

    try:
        structure, tokens = miner.extract_structure(return_tokens=True)

        print("\n=== TOKENS ===")
        print(tokens)

        print("\n=== STRUCTURE ===")
        print(json.dumps(structure, indent=2, ensure_ascii=False))

        print("\n=== INTRODUÇÃO ===")
        text = miner.get_section_text("Introdução")
        print(text)

    finally:
        miner.close()


if __name__ == "__main__":
    main()