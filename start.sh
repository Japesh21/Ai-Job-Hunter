#!/bin/bash
set -e

# Ensure DB is initialised before anything else starts
python -c "from database.connection import init_db; init_db()"

# Start scheduler in background (runs daily at 8 AM)
python main.py schedule &

# Start Streamlit dashboard in foreground (Railway keeps process alive via this)
exec streamlit run dashboard/app.py --server.port=${PORT:-8501} --server.address=0.0.0.0
