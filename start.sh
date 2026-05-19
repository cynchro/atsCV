#!/bin/bash
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "⚠️  No encontré el archivo .env"
  echo "   Copiá .env.example a .env y agregá tu DEEPSEEK_API_KEY"
  exit 1
fi

echo "🚀 Iniciando ATS CV Optimizer en http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
