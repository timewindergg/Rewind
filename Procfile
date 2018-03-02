web: gunicorn rewind.wsgi --log-file -
worker: celery -A rewind worker -l warning --concurrency=10
worker2: celery -A rewind worker -l warning --concurrency=10
