#!/usr/bin/env bash
# Pornire Panou de Control Web & Scheduler automat

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "=========================================================="
echo " 🏢 Pornire Platformă Imobiliare Sector 6"
echo " Dashboard Web: http://localhost:8000"
echo " Scheduler integrat activ: rulare zilnică la ora 08:00"
echo "=========================================================="

python3 -m uvicorn web.server:app --host 0.0.0.0 --port 8000 --reload
