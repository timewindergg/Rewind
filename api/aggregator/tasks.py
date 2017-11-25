from celery import shared_task
import time

@shared_task
def aggregate_users(summoner_name, region):
    time.sleep(5)
    return "derp"