from celery import shared_task
from celery.contrib import rdb

from api.models import ProfileStats
import cassiopeia as cass

@shared_task()
def aggregate_users(summoner_id, region):
    summoner_id = int(summoner_id)
    profile = ProfileStats.objects.get(user_id=summoner_id, region=region)
    summoner = cass.get_summoner(id=summoner_id, region=region)

    index = 0;
    updated = False
    count = 0

    while True:
        recent_matches = cass.get_match_history(summoner=summoner, region=region, begin_index=index, end_index=index+100)
        try:
            profile.last_match_updated = recent_matches[0].id
        except: #player does not have any matches
            pass
            
        for match in recent_matches:
            count += 1

            if profile.last_match_updated == match.id:
                updated = True
                break

            #is_ranked = match.queue == 420 or match.queue == 440

            #aggregate_user_match(summoner, match)
            #aggregate_global_stats(match)
            
        if updated or index > 100:
            break

        index += 100

    profile.save()

    return f"Aggregated {summoner_id}, {region}, {count} matches"

def aggregate_user_match(summoner, match):
    if match.win:
        profile.wins += 1
    else:
        profile.losses += 1

    Matches.objects.create(
        user_id=summoner.id,
        match_id=match.id,
        region=match.region
    )

    champion = UserChampionStats.objects.get_or_create(user_id=summoner.id, region=region, champ_id=champion.id)
    if match.win:
        champion.wins += 1
    else:
        champion.losses += 1
    champion.total_games += 1


def aggregate_global_stats(match):
    pass