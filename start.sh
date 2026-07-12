#!/bin/bash
cd frontend && npm run build
cd ..
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 4230
