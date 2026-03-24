from datetime import datetime, timedelta, timezone
import os
import tempfile
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from sectionminer import SectionMiner
from sectionminer.miner import _compact_text

router = APIRouter()


def _build_heuristic_tree(sections: list[dict]) -> dict:
    return {
        "title": "Document",
        "children": [
            {
                "title": section["title"],
                "children": [],
                "start_char": section.get("start"),
                "end_char": section.get("end"),
            }
            for section in sections
        ],
    }


def _iter_nodes(tree: dict) -> list[tuple[dict, int]]:
    nodes: list[tuple[dict, int]] = []

    def visit(node: dict, depth: int) -> None:
        title = node.get("title")
        if title and title != "Document":
            nodes.append((node, depth))
        for child in node.get("children", []):
            visit(child, depth + 1)

    visit(tree, 1)
    return nodes


def _cleanup_old_jobs(request: Request, ttl_hours: int = 6) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    jobs = request.app.state.jobs
    stale_ids = [job_id for job_id, data in jobs.items() if data["created_at"] < cutoff]

    for job_id in stale_ids:
        del jobs[job_id]


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    templates = Jinja2Templates(directory=request.app.state.templates_dir)
    return templates.TemplateResponse(request, "index.html")


@router.post("/api/extract")
async def extract_sections(request: Request, file: UploadFile = File(...)) -> dict:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF.")

    _cleanup_old_jobs(request)

    job_id = str(uuid.uuid4())

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    temp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp_pdf.write(content)
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()

    settings = request.app.state.settings
    miner = None
    usage = None
    try:
        miner = SectionMiner(
            temp_pdf_path,
            api_key=settings.api_key,
            model=settings.model,
            extraction_backend=settings.extraction_backend,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
        )

        if settings.heuristic_only:
            miner.extract_blocks()
            miner.build_full_text()
            raw_sections = miner.build_sections()
            tree = _build_heuristic_tree(raw_sections)
        else:
            if not settings.api_key:
                raise HTTPException(
                    status_code=400,
                    detail="OPENAI_API_KEY nao encontrada. Rode com --api-key ou configure o ambiente.",
                )
            tree, usage = miner.extract_structure(return_tokens=True)

        sections = []
        for node, depth in _iter_nodes(tree):
            title = _compact_text(node.get("title", ""))
            start = node.get("start_char")
            end = node.get("end_char")
            text = ""
            locations = []
            if start is not None and end is not None:
                text = _compact_text(miner.get_full_text()[start:end])
                locations = miner.get_locations_by_char_range(start, end)
            sections.append(
                {
                    "title": title,
                    "level": depth,
                    "start_char": start,
                    "end_char": end,
                    "text": text,
                    "locations": locations,
                }
            )

        request.app.state.jobs[job_id] = {
            "pdf_bytes": content,
            "filename": file.filename,
            "created_at": datetime.now(timezone.utc),
        }

        pages = miner.doc.page_count
        section_count = len(sections)
        prompt_tokens = int((usage or {}).get("prompt_tokens", 0))
        completion_tokens = int((usage or {}).get("completion_tokens", 0))
        total_tokens = int((usage or {}).get("total_tokens", 0))
        cost_usd = float((usage or {}).get("cost_usd", 0.0))

        return {
            "job_id": job_id,
            "filename": file.filename,
            "pdf_url": f"/api/files/{job_id}",
            "pages": pages,
            "extraction_backend": settings.extraction_backend,
            "heuristic_only": settings.heuristic_only,
            "metrics": {
                "pages": pages,
                "sections": section_count,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
            },
            "usage": usage,
            "tree": tree,
            "sections": sections,
        }
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Falha ao processar PDF: {exc}") from exc
    finally:
        if miner is not None:
            miner.close()
        try:
            os.unlink(temp_pdf_path)
        except OSError:
            pass


@router.get("/api/files/{job_id}")
def serve_pdf(request: Request, job_id: str) -> Response:
    data = request.app.state.jobs.get(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Documento nao encontrado ou expirado.")

    return Response(content=data["pdf_bytes"], media_type="application/pdf")


