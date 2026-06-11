#!/bin/bash
set -e

# Ensure DB is initialised before dashboard starts
python -c "from database.connection import init_db; init_db()"

# Start Streamlit dashboard only — scheduler runs via Railway Cron (separate service)
exec streamlit run dashboard/app.py --server.port=${PORT:-8501} --server.address=0.0.0.0
