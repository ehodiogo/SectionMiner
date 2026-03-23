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
        gemini_model="gemini-2.5-flash-lite"
    )

    try:
        structure, tokens = miner.extract_structure(return_tokens=True)

        print("\n=== TOKENS ===")
        print(tokens)

        print("\n=== STRUCTURE ===")
        print(json.dumps(structure, indent=2, ensure_ascii=False))

        print("\n=== INTRO ===")
        title = "introducao"

        start, end = miner.get_section_start_and_end_chars(title)
        print("start:", start, "end:", end)
        texto_completo = miner.get_full_text()
        print("Texto da secao:", texto_completo[start:end])

        for s in miner.get_sections():
            print("Extraindo texto da secao:", s)
            print(miner.get_section_text(s))

    finally:
        miner.close()


if __name__ == "__main__":
    main()