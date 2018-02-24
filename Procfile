web: gunicorn rewind.wsgi --log-file -
worker: celery -A api.aggregator.tasks worker -l warning