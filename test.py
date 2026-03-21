import os
import json
from base import SectionMiner

def main():
	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise SystemExit(
			"OPENAI_API_KEY nao encontrada. Exporte a variavel e rode novamente."
		)

	section_miner = SectionMiner("files/Artigo_Provatis.pdf", api_key=api_key)
	try:
		# estrutura + tokens
		structure, tokens = section_miner.extract_structure(return_tokens=True)

		print(tokens)
		print(json.dumps(structure, indent=4, ensure_ascii=False))

		# pegar texto da introducao
		intro = section_miner.get_section("Introducao")
		print("Introducao", intro)
	finally:
		section_miner.close()


if __name__ == "__main__":
	main()
