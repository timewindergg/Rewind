from celery import shared_task
from celery.contrib import rdb

from api.models import ProfileStats, Matches, UserChampionStats, ChampionItems, ChampionRunes
import cassiopeia as cass
from cassiopeia import data

import json

@shared_task()
def aggregate_users(summoner_id, region, max_aggregations=-1):
    summoner_id = int(summoner_id)
    profile = ProfileStats.objects.get(user_id=summoner_id, region=region)
    summoner = cass.get_summoner(id=summoner_id, region=region)

    index = 0;
    updated = False
    count = 0

    while True:
        recent_matches = cass.get_match_history(summoner=summoner, region=region, begin_index=index, end_index=index+100)
        
        for match in recent_matches:
            if profile.last_match_updated == match.id:
                updated = True
                break

            try:
                is_ranked = match.queue == cass.Queue.depreciated_ranked_solo_fives or match.queue == cass.Queue.ranked_flex_fives
            except:
                is_ranked = False

            if is_ranked:
                aggregate_user_match(region=region, summoner=summoner, match=match, profile=profile)
                aggregate_global_stats(match=match)
            count += 1
            
        if updated or index > max_aggregations and max_aggregations != -1:
            break

        index += 100

    try:
        profile.last_match_updated = recent_matches[0].id
    except: # Player does not have any matches
        pass
    profile.save()

    return f"Aggregated {summoner_id}, {region}, {count} matches"

def aggregate_user_match(region, summoner, match, profile):
    profile.time_played += match.duration.total_seconds()

    for participant in match.participants:
        if participant.summoner.id == summoner.id:
            user = participant
            break

    if user.stats.win:
        profile.wins += 1
    else:
        profile.losses += 1

    try:
        wards_placed = user.stats.wards_placed
        wards_killed = user.stats.wards_killed
    except:
        wards_placed = 0
        wards_killed = 0

    season_id = data.SEASON_IDS[match.season]

    items = [item.id if item else 0 for item in user.stats.items]
    
    red_team = [p.summoner.name for p in match.red_team.participants]
    blue_team = [p.summoner.name for p in match.blue_team.participants]

    Matches.objects.get_or_create(
        user_id=summoner.id,
        match_id=match.id,
        region=match.region.value,
        season_id=season_id,
        queue_id=data.QUEUE_IDS[match.queue],
        timestamp=round(match.creation.timestamp()),
        duration=match.duration.total_seconds(),
        champion_id=user.champion.id,
        item0=items[0],
        item1=items[1],
        item2=items[2],
        item3=items[3],
        item4=items[4],
        item5=items[5],
        item6=items[6],
        spell0=user.summoner_spell_d.id,
        spell1=user.summoner_spell_f.id,
        deaths=user.stats.deaths,
        assists=user.stats.assists,
        cs=user.stats.total_minions_killed,
        gold=user.stats.gold_earned,
        level=user.stats.level,
        wards_placed=wards_placed,
        wards_killed=wards_killed,
        vision_wards_bought=user.stats.vision_wards_bought_in_game,
        game_type=match.mode.value,
        lane=user.lane.value,
        role=user.role,
        winner=100 if match.blue_team.win else 200,
        is_remake=match.is_remake,
        red_team=json.dumps(red_team),
        blue_team=json.dumps(blue_team),
    )

    champion, created = UserChampionStats.objects.get_or_create(user_id=summoner.id, region=region, season_id=season_id, champ_id=user.champion.id)
    if user.stats.win:
        champion.wins += 1
    else:
        champion.losses += 1
    champion.total_games += 1
    champion.pentas += user.stats.penta_kills
    champion.quadras += user.stats.quadra_kills
    champion.triples += user.stats.triple_kills
    champion.doubles += user.stats.double_kills
    champion.kills += user.stats.kills
    champion.deaths += user.stats.deaths
    champion.assists += user.stats.assists
    if hasattr(user.stats, "first_blood_kill") and user.stats.first_blood_kill:
        champion.first_bloods += 1
    champion.total_cs += user.stats.total_minions_killed
    champion.game_length += match.duration.total_seconds()
    champion.save()


def aggregate_global_stats(match):
    for participant in match.participants:
        champ_id = participant.champion.id
        for item in participant.stats.items:
            if item:
                champ_item, created = ChampionItems.objects.get_or_create(champ_id=champ_id, item_id=item.id)
                champ_item.occurence += 1
                champ_item.save()
        try: # Legacy runes will break this. Cassiopeia only supports runes reforged atm.
            for rune in participant.runes:
                champ_rune, created = ChampionRunes.objects.get_or_create(champ_id=champ_id, rune_id=rune[0].id)
                champ_rune.occurence += 1
                champ_rune.save()
        except:
            pass


