from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.conf import settings

import cassiopeia as cass

import json
import datetime
from multiprocessing.dummy import Pool
from itertools import repeat
import time
import os
import gc

from api.models import ProfileStats, Matches, MatchLawn, UserChampionStats, ChampionStats, ChampionItems, ChampionRunes, UserChampionVersusStats, UserChampionItems, UserChampionRunes, UserChampionSummoners

import logging
log = logging.getLogger(__name__)


@shared_task(max_retries=5)
def aggregate_users(summoner_id, region, max_aggregations=-1):
    try:
        # init
        cass.get_realms(region=region).load()

        summoner_id = int(summoner_id)
        max_aggregations = int(max_aggregations)
        profile = ProfileStats.objects.get(user_id=summoner_id, region=region)
        summoner = cass.get_summoner(id=summoner_id, region=region)

        index = 0;
        updated = False
        count = 0

        while True:
            if updated or index >= max_aggregations and max_aggregations > 0:
                break

            recent_matches = cass.get_match_history(summoner=summoner, region=region, begin_index=index, end_index=index+100, seasons=[cass.data.Season.from_id(11)])

            batch = []
            for match in recent_matches:
                if profile.last_match_updated == match.id:
                    updated = True
                    break

                #aggregate_user_match.delay(region=region, summoner_id=summoner_id, match_id=match.id)
                batch.append(match.id)

                if len(batch) == settings.AGGREGATION_BATCH_SIZE:
                    aggregate_batched_matches.delay(batch, region, summoner_id)
                    batch = []
                count += 1

            index += 100

            if len(batch) > 0:
                aggregate_batched_matches.delay(batch, region, summoner_id)
                
            if len(recent_matches) == 0:
                break

        return f"Aggregated {summoner_id}, {region}, {count} matches"
    except Exception as e:
        log.warn("Failed to aggregate_user", stack_info=True)
        aggregate_users.retry(exc=e)


@shared_task(max_retries=5)
def aggregate_batched_matches(batch, region, summoner_id):
    try:
        old = time.time() * 1000

        # init
        cass.get_realms(region=region).load()

        matchlist = []
        for m_id in batch:
            match_id = int(m_id)
            matchlist.append(cass.get_match(id=match_id, region=region))

        pool = Pool(len(matchlist))
        pool.map(load_match, matchlist)
        pool.close()
        pool.join()

        #print("fetch:", time.time()*1000 - old)

        for match in matchlist:
            aggregate_user_match(match, summoner_id, region)

        #pool = Pool(len(matchlist))
        #pool.starmap(aggregate_user_match, zip(matchlist, repeat(summoner_id), repeat(region)))
        #pool.close()
        #pool.join()

    except Exception as e:
        log.warn("Failed to aggregate batched matches", e, stack_info=True)
        aggregate_batched_matches.retry(exc=e)


def load_match(match):
    match.load()

def aggregate_user_match(match, summoner_id, region):
    old = time.time() * 1000

    #summoner_id = int(match['summoner_id'])
    #match_id = int(match['match_id'])
    #region = match['region']

    #match = cass.get_match(id=match_id, region=region)

    try:
        is_ranked = match.queue == cass.Queue.ranked_solo_fives or match.queue == cass.Queue.ranked_flex_fives or match.queue == cass.Queue.ranked_flex_threes
    except:
        log.warn("Error checking is_ranked in aggregate_user_match")
        is_ranked = False

    for participant in match.participants:
        if participant.summoner.id == summoner_id:
            user = participant
            break

    try:
        lane = user.lane.value
    except:
        lane = 'NONE'

    if user.role is None:
        role = 'NONE'
    else:
        try:
            role = user.role.value
        except:
            role = user.role

    with transaction.atomic():
        try:
            profile = ProfileStats.objects.select_for_update().get(user_id=summoner_id, region=region)
        except Exception as e:
            log.error("Summoner not created in database")
            raise e

        profile.time_played += match.duration.total_seconds()

        try:
            if profile.last_match_updated < match.id:
                profile.last_match_updated = match.id
        except: # Player does not have any matches
            pass

        if user.stats.win:
            profile.wins += 1
        else:
            profile.losses += 1
        profile.save()

    try:
        wards_placed = user.stats.wards_placed
        wards_killed = user.stats.wards_killed
    except:
        wards_placed = 0
        wards_killed = 0

    season_id = cass.data.SEASON_IDS[match.season]

    items = [item.id if item else 0 for item in user.stats.items]

    with transaction.atomic():
        m, created = Matches.objects.select_for_update().get_or_create(
            user_id=summoner_id,
            match_id=match.id,
            region=match.region.value
        )
        m.season_id = season_id
        m.queue_id = cass.data.QUEUE_IDS[match.queue]
        m.timestamp = match.creation.timestamp
        m.duration = match.duration.total_seconds()
        m.champ_id = user.champion.id
        m.participant_id = user.id
        m.item0 = items[0]
        m.item1 = items[1]
        m.item2 = items[2]
        m.item3 = items[3]
        m.item4 = items[4]
        m.item5 = items[5]
        m.item6 = items[6]
        m.spell0 = user.summoner_spell_d.id
        m.spell1 = user.summoner_spell_f.id
        m.deaths = user.stats.deaths
        m.assists = user.stats.assists
        m.cs = user.stats.total_minions_killed
        m.gold = user.stats.gold_earned
        m.level = user.stats.level
        m.wards_placed = wards_placed
        m.wards_killed = wards_killed
        m.vision_wards_bought = user.stats.vision_wards_bought_in_game
        m.game_type = match.mode.value
        m.lane = lane
        m.role = role
        m.team = user.side.value
        m.winner = 100 if match.blue_team.win else 200
        m.won = user.stats.win
        m.is_remake = match.is_remake
        m.red_team = match.red_team.to_json()
        m.blue_team = match.blue_team.to_json()
        if user.stats.penta_kills > 0:
            m.killing_spree = 5
        elif user.stats.quadra_kills > 0:
            m.killing_spree = 4
        elif user.stats.triple_kills > 0:
            m.killing_spree = 3
        elif user.stats.double_kills > 0:
            m.killing_spree = 2
        elif user.stats.kills > 0:
            m.killing_spree = 1
        m.save()

    lawn, created = MatchLawn.objects.get_or_create(user_id=summoner_id, region=region, date=datetime.datetime.fromtimestamp(match.creation.timestamp))
    if user.stats.win:
        lawn.wins = F('wins') + 1
    else:
        lawn.losses = F('losses') + 1
    lawn.save()

    with transaction.atomic():
        ucs, created = UserChampionStats.objects.select_for_update().get_or_create(user_id=summoner_id, region=region, season_id=season_id, champ_id=user.champion.id, lane=lane)
        if user.stats.win:
            ucs.wins += 1
            if match.duration.seconds <= 20 * 60:
                ucs.wins20 += 1
            elif match.duration.seconds <= 30 * 60:
                ucs.wins30 += 1
            elif match.duration.seconds <= 40 * 60:
                ucs.wins40 += 1
            elif match.duration.seconds > 40 * 60:
                ucs.wins40p += 1
        else:
            ucs.losses += 1
        ucs.total_games += 1
        ucs.pentas += user.stats.penta_kills
        ucs.quadras += user.stats.quadra_kills
        ucs.triples += user.stats.triple_kills
        ucs.doubles += user.stats.double_kills
        ucs.kills += user.stats.kills
        ucs.deaths += user.stats.deaths
        ucs.assists += user.stats.assists
        if hasattr(user.stats, "first_blood_kill") and user.stats.first_blood_kill:
            ucs.first_bloods += 1
        ucs.total_cs += user.stats.total_minions_killed
        ucs.game_length += match.duration.total_seconds()
        ucs.gold += user.stats.gold_earned
        if match.duration.seconds <= 20 * 60:
            ucs.total_games20 += 1
        elif match.duration.seconds <= 30 * 60:
            ucs.total_games30 += 1
        elif match.duration.seconds <= 40 * 60:
            ucs.total_games40 += 1
        elif match.duration.seconds > 40 * 60:
            ucs.total_games40p += 1
        try:
            if match.duration.seconds >= 10 * 60:
                ucs.gold10 = (ucs.gold10 * (ucs.total_games - 1) + user.timeline.gold_per_min_deltas['0-10']) / ucs.total_games
                ucs.cs10 = (ucs.cs10 * (ucs.total_games - 1) + user.timeline.creeps_per_min_deltas['0-10']) / ucs.total_games
                ucs.xp10 = (ucs.xp10 * (ucs.total_games - 1) + user.timeline.xp_per_min_deltas['0-10']) / ucs.total_games
                ucs.dmg_taken10 = (ucs.dmg_taken10 * (ucs.total_games - 1) + user.timeline.damage_taken_per_min_deltas['0-10']) / ucs.total_games
                ucs.cs_diff10 = (ucs.cs_diff10 * (ucs.total_games - 1) + user.timeline.cs_diff_per_min_deltas['0-10']) / ucs.total_games
                ucs.xp_diff10 = (ucs.xp_diff10 * (ucs.total_games - 1) + user.timeline.xp_diff_per_min_deltas['0-10']) / ucs.total_games
                ucs.dmg_taken_diff10 = (ucs.dmg_taken_diff10 * (ucs.total_games - 1) + user.timeline.damage_taken_diff_per_min_deltas['0-10']) / ucs.total_games
            if match.duration.seconds >= 20 * 60:
                ucs.gold20 = (ucs.gold20 * (ucs.total_games - 1) + user.timeline.gold_per_min_deltas['10-20']) / ucs.total_games
                ucs.cs20 = (ucs.cs20 * (ucs.total_games - 1) + user.timeline.creeps_per_min_deltas['10-20']) / ucs.total_games
                ucs.xp20 = (ucs.xp20 * (ucs.total_games - 1) + user.timeline.xp_per_min_deltas['10-20']) / ucs.total_games
                ucs.dmg_taken20 = (ucs.dmg_taken20 * (ucs.total_games - 1) + user.timeline.damage_taken_per_min_deltas['10-20']) / ucs.total_games
                ucs.cs_diff20 = (ucs.cs_diff20 * (ucs.total_games - 1) + user.timeline.cs_diff_per_min_deltas['10-20']) / ucs.total_games
                ucs.xp_diff20 = (ucs.xp_diff20 * (ucs.total_games - 1) + user.timeline.xp_diff_per_min_deltas['10-20']) / ucs.total_games
                ucs.dmg_taken_diff20 = (ucs.dmg_taken_diff20 * (ucs.total_games - 1) + user.timeline.damage_taken_diff_per_min_deltas['10-20']) / ucs.total_games
            if match.duration.seconds >= 30 * 60:
                ucs.gold30 = (ucs.gold30 * (ucs.total_games - 1) + user.timeline.gold_per_min_deltas['20-30']) / ucs.total_games
                ucs.cs30 = (ucs.cs30 * (ucs.total_games - 1) + user.timeline.creeps_per_min_deltas['20-30']) / ucs.total_games
                ucs.xp30 = (ucs.xp30 * (ucs.total_games - 1) + user.timeline.xp_per_min_deltas['20-30']) / ucs.total_games
                ucs.dmg_taken30 = (ucs.dmg_taken30 * (ucs.total_games - 1) + user.timeline.damage_taken_per_min_deltas['20-30']) / ucs.total_games
                ucs.cs_diff30 = (ucs.cs_diff30 * (ucs.total_games - 1) + user.timeline.cs_diff_per_min_deltas['20-30']) / ucs.total_games
                ucs.xp_diff30 = (ucs.xp_diff30 * (ucs.total_games - 1) + user.timeline.xp_diff_per_min_deltas['20-30']) / ucs.total_games
                ucs.dmg_taken_diff30 = (ucs.dmg_taken_diff30 * (ucs.total_games - 1) + user.timeline.damage_taken_diff_per_min_deltas['20-30']) / ucs.total_games
        except:
            pass
        ucs.save()

    if user.side.value == 100:
        enemy_team = match.red_team.participants
    elif user.side.value == 200:
        enemy_team = match.blue_team.participants

    for enemy in enemy_team:
        championv, created = UserChampionVersusStats.objects.get_or_create(user_id=summoner_id, region=region, season_id=season_id, champ_id=user.champion.id, enemy_champ_id=enemy.champion.id)
        championv.total_games = F('total_games') + 1
        if user.stats.win:
            championv.wins = F('wins') + 1
        else:
            championv.losses = F('losses') + 1
        championv.save()

    sorted_runes = [r.id for r in user.runes]
    sorted_runes.sort()
    rune_string = json.dumps(sorted_runes)
    ucr, created = UserChampionRunes.objects.get_or_create(user_id=summoner_id, region=region, season_id=season_id, lane=lane, champ_id=user.champion.id, rune_set=rune_string)
    ucr.occurence = F('occurence') + 1
    ucr.save()

    sorted_summs = [user.summoner_spell_d.id, user.summoner_spell_f.id]
    sorted_summs.sort()
    summoner_string = json.dumps(sorted_summs)
    ucs, created = UserChampionSummoners.objects.get_or_create(user_id=summoner_id, region=region, season_id=season_id, lane=lane, champ_id=user.champion.id, summoner_set=summoner_string)
    ucs.occurence = F('occurence') + 1
    ucs.save()

    items = {}
    for item in user.stats.items:
        if item:
            if not item.id in items:
                items[item.id] = 1

    for item in items.keys():
        uci, created = UserChampionItems.objects.get_or_create(user_id=summoner_id, region=region, season_id=season_id, lane=lane, champ_id=user.champion.id, item_id=item)
        uci.occurence = F('occurence') + 1
        uci.save()

    if is_ranked:
        data = []
        for participant in match.participants:
            p_data = {}
            p_data['champ_id'] = participant.champion.id
            p_data['items'] = [item.id for item in participant.stats.items[0:6] if item]
            data.append(p_data)

        aggregate_global_stats.delay(data)
    else:
        return

    print("aggr",time.time() * 1000 - old)


@shared_task(max_retries=3)
def aggregate_global_stats(data):
    try:
        for participant in data:
            champ_id = participant['champ_id']

            items = {}
            for item in participant['items']:
                if not item in items:
                    items[item] = 1

            for item in items.keys():
                champ_item, created = ChampionItems.objects.get_or_create(champ_id=champ_id, item_id=item)
                champ_item.occurence = F('occurence') + 1
                champ_item.save()
    except Exception as e:
        log.warn("Failed to aggregate global stats", stack_info=True)
        aggregate_global_stats.retry(exc=e)

'''
def aggregate_global_stats(match):
    for participant in match.participants:
        champ_id = participant.champion.id

        items = {}
        for item in participant.stats.items:
            if item:
                if not item.id in items:
                    items[item.id] = 1

        #champ_stats, created = ChampionStats.objects.get_or_create(champ_id=champ_id)
        #champ_stats.total_games = F('total_games') + 1
        #champ_stats.save()
    
        champ_item, created = ChampionItems.objects.get_or_create(champ_id=champ_id, item_id__in=items.keys())
        champ_item.occurence = F('occurence') + 1
        champ_item.save()

        #for rune in participant.runes:
        #    champ_rune, created = ChampionRunes.objects.get_or_create(champ_id=champ_id, rune_id=rune.id)
        #    champ_rune.occurence = F('occurence') + 1
        #    champ_rune.save()
'''
