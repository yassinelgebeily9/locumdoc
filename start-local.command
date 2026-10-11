#!/bin/bash
# Double-click this file on a Mac to run LocumDoc locally with demo data.
# It opens http://localhost:5050 in your browser. Close this window (or press Ctrl+C) to stop.

cd "$(dirname "$0")" || exit 1
PORT=5050

echo ""
echo "  LocumDoc — local test server"
echo "  ----------------------------"

if ! command -v python3 >/dev/null 2>&1; then
  echo "  Python 3 is not installed. Install it from https://www.python.org/downloads/ and run this again."
  read -r -p "  Press Return to close." _
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "  First run: setting up (takes about a minute)..."
  python3 -m venv .venv || { echo "  Could not create the Python environment."; read -r _; exit 1; }
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt || {
  echo "  Could not install requirements. Check your internet connection and try again."; read -r _; exit 1; }

export SECRET_KEY="local-test-only"
export SEED_DEMO=1
export ADMIN_EMAIL="admin@test.local"
export ADMIN_PASSWORD="admin-password-1"
export SITE_URL="http://localhost:$PORT"
export DATA_DIR="$PWD/instance"

echo ""
echo "  Running at http://localhost:$PORT"
echo ""
echo "  Logins (password for demo accounts: demo-password)"
echo "    Hospital: facility2@demo.locumdoc.me"
echo "    Doctor:   doctor1@demo.locumdoc.me"
echo "    Admin:    admin@test.local / admin-password-1"
echo ""
echo "  Close this window or press Ctrl+C to stop."
echo ""

(sleep 2 && open "http://localhost:$PORT") &
exec .venv/bin/python -m flask --app wsgi run --port "$PORT"
