web: newrelic-admin run-program gunicorn rewind.wsgi --log-file -
worker: celery -A rewind worker -l warning --concurrency=4
