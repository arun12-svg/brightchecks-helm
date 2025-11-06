#!/bin/bash

# Activate venv if needed (not using here, since base image doesn't have it)

# Start the Uvicorn server in the background
echo "Starting Uvicorn..."
pip install -r requirements.txt
pip install websockets
pip install kubernetes
#uvicorn main:app --host 0.0.0.0 --port 5006 &
uvicorn main:app --host 0.0.0.0 --port 5006 --workers 4 > nohup.out 2>&1 &

# Start Celery worker
echo "Starting Celery..."
cd /em-etl-backend/src/celery_app
#pip install -r ../../requirements.txt
celery -A celery_app worker --loglevel=info --without-mingle --without-gossip
