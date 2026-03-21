import json

from decouple import config

from sectionminer import SectionMiner


def main() -> None:
    api_key = config("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY nao encontrada.")

    miner = SectionMiner("files/Artigo_Provatis.pdf", api_key)
    try:
        structure, usage = miner.extract_structure(return_tokens=True)
        print("=== TOKENS ===")
        print(usage)
        print("\n=== STRUCTURE ===")
        print(json.dumps(structure, indent=2, ensure_ascii=False))

        title = "introducao"
        print(f"\n=== TEXTO: {title} ===")
        print(miner.get_section_text(title))
    finally:
        miner.close()


if __name__ == "__main__":
    main()

