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
        except: # Player does not have any matches
            pass

        for match in recent_matches:
            if profile.last_match_updated == match.id:
                updated = True
                break

            is_ranked = match.queue == cass.Queue.depreciated_ranked_solo_fives or match.queue == cass.Queue.ranked_flex_fives

            aggregate_user_match(summoner, match, profile)
            aggregate_global_stats(match)

            count += 1
            
        if updated or index > 100:
            break

        index += 100

    profile.save()

    return f"Aggregated {summoner_id}, {region}, {count} matches"

def aggregate_user_match(summoner, match, profile):
    if match.win:
        profile.wins += 1
    else:
        profile.losses += 1

    profile.time_played += match.duration.total_seconds()

    for participant in match.participants:
        if participant.summoner.id == summoner.id:
            user = participant
            user_stats = participant.stats._data[cass.core.match.ParticipantStatsData]
            break

    Matches.objects.create(
        user_id=summoner.id,
        match_id=match.id,
        region=match.region,
        season_id=match.season,
        timestamp=round(match.creation.timestamp()),
        duration=match.duration.total_seconds(),
        item0=user_stats.item0,
        item1=user_stats.item1,
        item2=user_stats.item2,
        item3=user_stats.item3,
        item4=user_stats.item4,
        item5=user_stats.item5,
        item6=user_stats.item6,
        spell0=user.summoner_spell_d.id,
        spell1=user.summoner_spell_f.id,
        kills=user.stats.kills,
        deaths=user.stats.deaths,
        assists=user.stats.assists,
        cs=user.stats.total_minions_killed,
        gold=user.stats.gold_earned,
        level=user.stats.level,
        wards_placed=user.stats.wards_placed,
        wards_killed=user.stats.wards_killed,
        vision_wards_bought=user.stats.vision_wards_bought_in_game,
        game_type=match.mode.value,
        lane=user.lane.value,
    )

    champion = UserChampionStats.objects.get_or_create(user_id=summoner.id, region=region, champ_id=champion.id)
    if match.win:
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
    if user.stats.first_blood_kill:
        champion.first_bloods += 1
    champion.total_cs += user.stats.total_minions_killed
    champion.game_length += match.duration.total_seconds()
    champion.save()


def aggregate_global_stats(match):
    for participant in match.participants:
        champ_id = participant.champion.id
        for item in participant.stats.items:
            champ_item = ChampionItems.objects.get_or_create(champ_id=champ_id, item_id=item.id)
            champ_item.occurence += 1
            champ_item.save()
        for rune in participant.runes:
            champ_rune = ChampionRunes.objects.get_or_create(champ_id=champ_id, rune_id=rune[0].id)
            champ_rune.occurence += 1
            champ_rune.save()


