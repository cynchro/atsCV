import os
import uuid
import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from cv_processor import extract_text, optimize
from doc_generator import generate_docx, generate_pdf

load_dotenv()

app = FastAPI(title="ATS CV Optimizer")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)


@app.post("/optimize")
async def optimize_cv(file: UploadFile = File(...)):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY no configurada en .env")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande (máximo 15 MB)")

    try:
        cv_text = extract_text(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {e}")

    if len(cv_text.strip()) < 100:
        raise HTTPException(
            status_code=400,
            detail="El PDF parece estar escaneado o vacío. Necesita texto seleccionable.",
        )

    try:
        cv_data = optimize(cv_text, api_key)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="La IA devolvió una respuesta inválida. Intentá de nuevo.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de IA: {e}")

    file_id = str(uuid.uuid4())
    docx_path = TEMP_DIR / f"{file_id}.docx"
    pdf_path = TEMP_DIR / f"{file_id}.pdf"

    try:
        generate_docx(cv_data, str(docx_path))
        generate_pdf(cv_data, str(pdf_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando documentos: {e}")

    return JSONResponse({
        "file_id": file_id,
        "name": cv_data.get("name", "CV Optimizado"),
        "download_docx": f"/download/{file_id}/docx",
        "download_pdf": f"/download/{file_id}/pdf",
    })


@app.get("/download/{file_id}/{fmt}")
async def download_file(file_id: str, fmt: str):
    # Prevent path traversal
    if not all(c.isalnum() or c == "-" for c in file_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    if fmt == "docx":
        path = TEMP_DIR / f"{file_id}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = "cv_optimizado.docx"
    elif fmt == "pdf":
        path = TEMP_DIR / f"{file_id}.pdf"
        media_type = "application/pdf"
        filename = "cv_optimizado.pdf"
    else:
        raise HTTPException(status_code=400, detail="Formato inválido")

    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado o expirado")

    return FileResponse(path, media_type=media_type, filename=filename)


app.mount("/", StaticFiles(directory="static", html=True), name="static")
