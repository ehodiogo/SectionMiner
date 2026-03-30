from decouple import config
import json
from sectionminer import SectionMiner


def main():
    api_key = config("OPENAI_API_KEY")

    if not api_key:
        raise SystemExit("OPENAI_API_KEY nao encontrada.")

    miner = SectionMiner(
        "files/Artigo_Provatis.pdf",
        api_key,
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