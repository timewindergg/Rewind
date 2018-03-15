web: gunicorn rewind.wsgi -k gthread --threads 4 --log-file -
worker: celery -A rewind worker -l warning --concurrency=4 --max-memory-per-child=128000 --max-tasks-per-child=1000
