#!/bin/bash
set -e

echo "⚔️ Iniciando configuração do Aethelgard RPG..."

# 1. Configurando ambiente virtual Python
if [ ! -d "venv" ]; then
    echo "🐍 Criando ambiente virtual Python (venv)..."
    python3 -m venv venv
fi

echo "📦 Instalando dependências do Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2. Configurando Frontend React
echo "📦 Instalando dependências do Frontend (npm)..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi

echo "🏗️ Compilando assets do Frontend..."
npm run build
cd ..

# 3. Iniciando o servidor
echo "🚀 Iniciando servidor FastAPI na porta 4230..."
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 4230
