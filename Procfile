web: gunicorn rewind.wsgi --log-file -
worker: celery -A rewind worker -l warning