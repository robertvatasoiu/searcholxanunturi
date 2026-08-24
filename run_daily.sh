#!/usr/bin/env bash
# Script pentru scanare imobiliară și trimitere alerte email (ora 08:00 sau on-demand)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "=========================================================="
echo " [$(date '+%Y-%m-%d %H:%M:%S')] Rulare Căutare Apartamente Sector 6"
echo "=========================================================="

python3 -m backend.scheduler --now

echo "=========================================================="
echo " Finalizat cu succes."
echo "=========================================================="
