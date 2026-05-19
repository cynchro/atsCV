# ATS CV Optimizer

Servicio web que toma un CV en PDF y devuelve una versión reescrita y optimizada para pasar filtros ATS (Applicant Tracking Systems), exportada en DOCX y PDF.

## Arquitectura

```
┌────────────────────────────────────────────────────────┐
│  Browser                                               │
│  static/index.html  →  POST /optimize (PDF upload)     │
│                     ←  { file_id, download_docx/pdf }  │
│                     →  GET /download/{id}/{fmt}         │
└────────────────────────────────────────────────────────┘
         │
┌────────▼───────────────────────────────────────────────┐
│  FastAPI  (main.py, port 8000)                         │
│                                                        │
│  cv_processor.py                                       │
│    extract_text()  →  PyMuPDF (fitz)                   │
│    optimize()      →  DeepSeek API (OpenAI-compat SDK) │
│                                                        │
│  doc_generator.py                                      │
│    generate_docx() →  python-docx                      │
│    generate_pdf()  →  ReportLab                        │
│                                                        │
│  temp_files/  (archivos generados, UUID como nombre)   │
└────────────────────────────────────────────────────────┘
```

## Módulos

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Rutas FastAPI: `/optimize` (POST), `/download/{id}/{fmt}` (GET), frontend estático |
| `cv_processor.py` | Extrae texto del PDF con PyMuPDF; llama a DeepSeek con el system prompt ATS y parsea el JSON de respuesta |
| `doc_generator.py` | Genera el DOCX (python-docx) y el PDF (ReportLab) a partir del dict estructurado devuelto por la IA |

### Flujo `/optimize`

1. Recibe el PDF (máx 15 MB).
2. Extrae el texto con PyMuPDF.
3. Envía el texto a `deepseek-chat` con un system prompt detallado que fuerza JSON estructurado.
4. Parsea el JSON y genera ambos archivos en `temp_files/`.
5. Devuelve los URLs de descarga.

### Estructura del JSON de la IA

```json
{
  "language": "es",
  "section_labels": { ... },
  "name": "...",
  "contact": { "email", "phone", "linkedin", "location", "website" },
  "summary": "...",
  "experience": [ { "company", "title", "location", "start_date", "end_date", "bullets": [] } ],
  "education": [ { "institution", "degree", "field", "location", "graduation_date", "gpa", "honors" } ],
  "skills": { "technical": [], "tools": [], "soft": [], "languages": [] },
  "certifications": [ { "name", "issuer", "date" } ]
}
```

## Configuración

Copiá `.env.example` a `.env` y completá tu clave:

```bash
cp .env.example .env
# editá .env y poné tu DEEPSEEK_API_KEY
```

Obtenés la API key en [platform.deepseek.com](https://platform.deepseek.com).

## Correr con Docker (recomendado)

```bash
# Build y arranque
docker compose up --build

# En background
docker compose up -d --build

# Ver logs
docker compose logs -f

# Detener
docker compose down
```

La app queda disponible en **http://localhost:8000**.

Los archivos generados se guardan en un volumen Docker (`temp_files`) que persiste entre reinicios.

## Correr sin Docker

```bash
pip install -r requirements.txt
./start.sh
```

Requiere Python 3.12+.

## Variables de entorno

| Variable | Descripción |
|---|---|
| `DEEPSEEK_API_KEY` | API key de DeepSeek (obligatoria) |

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/optimize` | Recibe PDF, devuelve JSON con `file_id` y URLs de descarga |
| `GET` | `/download/{file_id}/docx` | Descarga el DOCX generado |
| `GET` | `/download/{file_id}/pdf` | Descarga el PDF generado |
| `GET` | `/` | Frontend web (static/index.html) |

## Notas

- El PDF de entrada debe tener **texto seleccionable** (no escaneado).
- Los archivos en `temp_files/` no se limpian automáticamente; podés agregar una tarea cron o reiniciar el contenedor para limpiar.
- El modelo usa `temperature=0.2` para respuestas consistentes y hasta 8000 tokens de salida.
