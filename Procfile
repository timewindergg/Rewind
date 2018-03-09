web: gunicorn rewind.wsgi --log-file -
worker: celery -A rewind worker -l warning --concurrency=5 --max-memory-per-child=200000 --max-tasks-per-child=1000
