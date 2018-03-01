web: gunicorn rewind.wsgi --log-file -
worker: celery -A rewind worker -l warning --concurrency=15
worker2: celery -A rewind worker -l warning --concurrency=15