from decouple import config
import json
from base import SectionMiner


def main():
    api_key = config("OPENAI_API_KEY")

    if not api_key:
        raise SystemExit("OPENAI_API_KEY nao encontrada.")

    miner = SectionMiner("files/Artigo_Provatis.pdf", api_key)

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
        #
        # text = miner.get_section_text(title)
        # print(text)
        #
        miner.extract_blocks()
        miner.build_full_text()
        miner.build_sections()

        for s in miner.get_sections():
            print("Extraindo texto da secao:", s)
            print(miner.get_section_text(s))

    finally:
        miner.close()


if __name__ == "__main__":
    main()
