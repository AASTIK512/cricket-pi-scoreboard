#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ -f .venv/bin/activate ]; then
  . .venv/bin/activate
fi
if [ -f newsapi.env ]; then
  set -a
  . ./newsapi.env
  set +a
fi
exec python3 app.py
