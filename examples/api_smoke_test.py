from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from sectionminer.server.app import ServerSettings, create_app


def main() -> int:
    app = create_app(ServerSettings(heuristic_only=True))
    client = TestClient(app)

    ui = client.get("/")
    print(f"GET / -> {ui.status_code}")

    pdf = Path("files/Artigo_Mae.pdf")
    if not pdf.exists():
        raise SystemExit("Arquivo de exemplo nao encontrado: files/Artigo_Mae.pdf")

    with pdf.open("rb") as fh:
        response = client.post(
            "/api/extract",
            files={"file": (pdf.name, fh, "application/pdf")},
        )

    print(f"POST /api/extract -> {response.status_code}")
    payload = response.json()
    metrics = payload.get("metrics", {})
    print(f"Backend: {payload.get('extraction_backend')}")
    print(f"Paginas: {metrics.get('pages', payload.get('pages'))}")
    print(f"Secoes encontradas: {metrics.get('sections', len(payload.get('sections', [])))}")
    print(f"Tokens usados: {metrics.get('total_tokens', 0)}")
    print(f"Custo total (USD): {metrics.get('cost_usd', 0.0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

