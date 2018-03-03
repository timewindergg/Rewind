web: gunicorn rewind.wsgi --log-file -
worker: celery -A rewind worker -l warning --concurrency=4 --max-memory-per-child=120000
worker2: celery -A rewind worker -l warning --concurrency=4 --max-memory-per-child=120000
