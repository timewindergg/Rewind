web: gunicorn rewind.wsgi --log-file -
worker: celery -A rewind worker -l warning
worker2: celery -A rewind worker -l warning