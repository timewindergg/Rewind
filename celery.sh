celery -A rewind worker -l warning --concurrency=6 --max-memory-per-child=256000 --max-tasks-per-child=1000
