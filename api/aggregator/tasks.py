from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.conf import settings

import cassiopeia as cass

import ujson
import datetime
from multiprocessing.dummy import Pool
import time
import os

from api.models import ProfileStats, Matches, MatchLawn, UserChampionStats, ChampionStats, ChampionItems, UserChampionVersusStats, UserChampionItems, UserChampionRunes, UserChampionSummoners

import logging
log = logging.getLogger(__name__)


@shared_task(retry_backoff=True, max_retries=3)
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

                batch.append(match.id)

                if len(batch) == 25:
                    
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


@shared_task(retry_backoff=True, max_retries=3)
def aggregate_batched_matches(batch, region, summoner_id):
    try:
        # init
        cass.get_realms(region=region).load()

        old = time.time() * 1000

        matchlist = []
        for m_id in batch:
            match_id = int(m_id)
            matchlist.append(cass.get_match(id=match_id, region=region))

        pool = Pool(len(matchlist))
        pool.map(load_match, matchlist)
        pool.close()
        pool.join()
        print("fetch:", time.time()*1000 - old)

        old = time.time() * 1000
        aggregate_user_matches(matchlist, summoner_id, region)
        print("total:", time.time()*1000 - old)

    except Exception as e:
        if pool is not None:
            pool.close()
        log.warn("Failed to aggregate batched matches", e, stack_info=True)
        aggregate_batched_matches.retry(exc=e)


def load_match(match):
    match.load()


def aggregate_user_matches(matchlist, summoner_id, region):
    profile_data = {
        'wins': 0,
        'losses': 0,
        'last_match_updated': 0,
        'time_played': 0
    }
    lawn_data = {}
    versus_data = {}
    rune_data = {}
    spell_data = {}
    items_data = {}
    global_items_data = {}

    for match in matchlist:
        #
        # Common data
        #
        try:
            is_ranked = match.queue == cass.Queue.ranked_solo_fives or match.queue == cass.Queue.ranked_flex_fives or match.queue == cass.Queue.ranked_flex_threes
        except:
            log.warn("Error checking is_ranked in aggregate_user_match")
            is_ranked = False

        participants = match.participants
        for participant in participants:
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

        try:
            wards_placed = user.stats.wards_placed
            wards_killed = user.stats.wards_killed
        except:
            wards_placed = 0
            wards_killed = 0

        season_id = cass.data.SEASON_IDS[match.season]

        user_items = user.stats.items
        items = [item.id if item else 0 for item in user_items]


        #
        # ProfileStats
        #
        profile_data['time_played'] += match.duration.total_seconds()
        if profile_data['last_match_updated'] < match.id:
            profile_data['last_match_updated'] = match.id
        if user.stats.win:
            profile_data['wins'] += 1
        else:
            profile_data['losses'] += 1


        #
        # MatchLawn
        #
        date = str(datetime.datetime.fromtimestamp(match.creation.timestamp).date()) 
        if not date in lawn_data:
            lawn_data[date] = {
                'wins': 0,
                'losses': 0
            }
        if user.stats.win:
            lawn_data[date]['wins'] += 1
        else:
            lawn_data[date]['losses'] += 1

        
        with transaction.atomic():
            # 
            # Matches
            #
            killing_spree = 0
            if user.stats.penta_kills > 0:
                killing_spree = 5
            elif user.stats.quadra_kills > 0:
                killing_spree = 4
            elif user.stats.triple_kills > 0:
                killing_spree = 3
            elif user.stats.double_kills > 0:
                killing_spree = 2
            elif user.stats.kills > 0:
                killing_spree = 1
            try:
                m = Matches.objects.create(
                    user_id=summoner_id,
                    match_id=match.id,
                    region=match.region.value,
                    season_id=season_id,
                    queue_id=cass.data.QUEUE_IDS[match.queue],
                    timestamp=match.creation.timestamp,
                    duration=match.duration.total_seconds(),
                    champ_id=user.champion.id,
                    participant_id=user.id,
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
                    lane=lane,
                    role=role,
                    team=user.side.value,
                    winner=100 if match.blue_team.win else 200,
                    won=user.stats.win,
                    is_remake=match.is_remake,
                    killing_spree=killing_spree,
                    red_team = match.red_team.to_json(),
                    blue_team = match.blue_team.to_json()
                )
            except:
                log.warn("Duplicate match %d" % match_id)
                return

            
            #
            # UserChampionStats
            #
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
            has_diffs = hasattr(user.timeline, 'cs_diff_per_min_deltas')
            if match.duration.seconds > 10 * 60:
                ucs.gold10 = (ucs.gold10 * (ucs.total_games - 1) + user.timeline.gold_per_min_deltas['0-10']) / ucs.total_games
                ucs.cs10 = (ucs.cs10 * (ucs.total_games - 1) + user.timeline.creeps_per_min_deltas['0-10']) / ucs.total_games
                ucs.xp10 = (ucs.xp10 * (ucs.total_games - 1) + user.timeline.xp_per_min_deltas['0-10']) / ucs.total_games
                ucs.dmg_taken10 = (ucs.dmg_taken10 * (ucs.total_games - 1) + user.timeline.damage_taken_per_min_deltas['0-10']) / ucs.total_games
                if has_diffs:
                    ucs.cs_diff10 = (ucs.cs_diff10 * (ucs.total_games - 1) + user.timeline.cs_diff_per_min_deltas['0-10']) / ucs.total_games
                    ucs.xp_diff10 = (ucs.xp_diff10 * (ucs.total_games - 1) + user.timeline.xp_diff_per_min_deltas['0-10']) / ucs.total_games
                    ucs.dmg_taken_diff10 = (ucs.dmg_taken_diff10 * (ucs.total_games - 1) + user.timeline.damage_taken_diff_per_min_deltas['0-10']) / ucs.total_games
            if match.duration.seconds > 20 * 60:
                ucs.gold20 = (ucs.gold20 * (ucs.total_games - 1) + user.timeline.gold_per_min_deltas['10-20']) / ucs.total_games
                ucs.cs20 = (ucs.cs20 * (ucs.total_games - 1) + user.timeline.creeps_per_min_deltas['10-20']) / ucs.total_games
                ucs.xp20 = (ucs.xp20 * (ucs.total_games - 1) + user.timeline.xp_per_min_deltas['10-20']) / ucs.total_games
                ucs.dmg_taken20 = (ucs.dmg_taken20 * (ucs.total_games - 1) + user.timeline.damage_taken_per_min_deltas['10-20']) / ucs.total_games
                if has_diffs:
                    ucs.cs_diff20 = (ucs.cs_diff20 * (ucs.total_games - 1) + user.timeline.cs_diff_per_min_deltas['10-20']) / ucs.total_games
                    ucs.xp_diff20 = (ucs.xp_diff20 * (ucs.total_games - 1) + user.timeline.xp_diff_per_min_deltas['10-20']) / ucs.total_games
                    ucs.dmg_taken_diff20 = (ucs.dmg_taken_diff20 * (ucs.total_games - 1) + user.timeline.damage_taken_diff_per_min_deltas['10-20']) / ucs.total_games
            if match.duration.seconds > 30 * 60:
                ucs.gold30 = (ucs.gold30 * (ucs.total_games - 1) + user.timeline.gold_per_min_deltas['20-30']) / ucs.total_games
                ucs.cs30 = (ucs.cs30 * (ucs.total_games - 1) + user.timeline.creeps_per_min_deltas['20-30']) / ucs.total_games
                ucs.xp30 = (ucs.xp30 * (ucs.total_games - 1) + user.timeline.xp_per_min_deltas['20-30']) / ucs.total_games
                ucs.dmg_taken30 = (ucs.dmg_taken30 * (ucs.total_games - 1) + user.timeline.damage_taken_per_min_deltas['20-30']) / ucs.total_games
                if has_diffs:
                    ucs.cs_diff30 = (ucs.cs_diff30 * (ucs.total_games - 1) + user.timeline.cs_diff_per_min_deltas['20-30']) / ucs.total_games
                    ucs.xp_diff30 = (ucs.xp_diff30 * (ucs.total_games - 1) + user.timeline.xp_diff_per_min_deltas['20-30']) / ucs.total_games
                    ucs.dmg_taken_diff30 = (ucs.dmg_taken_diff30 * (ucs.total_games - 1) + user.timeline.damage_taken_diff_per_min_deltas['20-30']) / ucs.total_games
            ucs.save()
               

        #
        # UserChampionVersusStats
        #
        if user.side.value == 100:
            enemy_team = match.red_team.participants
        elif user.side.value == 200:
            enemy_team = match.blue_team.participants

        for enemy in enemy_team:
            if not user.champion.id in versus_data:
                versus_data[user.champion.id] = {}
            if not enemy.champion.id in versus_data[user.champion.id]:
                versus_data[user.champion.id][enemy.champion.id] = {
                    'wins': 0,
                    'losses': 0,
                    'total_games': 0
                }
            if user.stats.win:
                versus_data[user.champion.id][enemy.champion.id]['wins'] += 1
            else:
                versus_data[user.champion.id][enemy.champion.id]['losses'] += 1
            versus_data[user.champion.id][enemy.champion.id]['total_games'] += 1


        #
        # Runes
        #
        user_runes = user.runes
        sorted_runes = [r.id for r in user_runes]
        sorted_runes.sort()
        rune_string = ujson.dumps(sorted_runes)

        if not user.champion.id in rune_data:
            rune_data[user.champion.id] = {}
        if not lane in rune_data[user.champion.id]:
            rune_data[user.champion.id][lane] = {}
        if rune_string in rune_data[user.champion.id][lane]:
            rune_data[user.champion.id][lane][rune_string] += 1
        else:
            rune_data[user.champion.id][lane][rune_string] = 1


        #
        # Summoner Spells
        #
        sorted_summs = [user.summoner_spell_d.id, user.summoner_spell_f.id]
        sorted_summs.sort()
        sum_string = ujson.dumps(sorted_summs)

        if not user.champion.id in spell_data:
            spell_data[user.champion.id] = {}
        if not lane in spell_data[user.champion.id]:
            spell_data[user.champion.id][lane] = {}
        if sum_string in spell_data[user.champion.id][lane]:
            spell_data[user.champion.id][lane][sum_string] += 1
        else:
            spell_data[user.champion.id][lane][sum_string] = 1


        #
        # Items
        #
        user_items = user.stats.items[0:6]
        user_items = {item.id for item in user_items if item}
        for item in user_items:
            if not user.champion.id in items_data:
                items_data[user.champion.id] = {}
            if not lane in items_data[user.champion.id]:
                items_data[user.champion.id][lane] = {}
            if item in items_data[user.champion.id][lane]:
                items_data[user.champion.id][lane][item] += 1
            else:
                items_data[user.champion.id][lane][item] = 1
        
        #
        # Global
        #
        if is_ranked:
            #for participant in match.participants:
            participant = user
            participant_items = {item.id for item in participant.stats.items[0:6] if item}
            for item in participant_items:
                if not participant.champion.id in global_items_data:
                    global_items_data[participant.champion.id] = {}
                if item in global_items_data[participant.champion.id]:
                    global_items_data[participant.champion.id][item] += 1
                else:
                    global_items_data[participant.champion.id][item] = 1
        

    update_profile(summoner_id, region, profile_data)
    update_matchlawn(summoner_id, region, lawn_data)
    update_userchampionversus.delay(summoner_id, region, versus_data)
    update_runes.delay(summoner_id, region, rune_data)
    update_spells.delay(summoner_id, region, spell_data)
    update_items.delay(summoner_id, region, items_data)
    update_global_items.delay(global_items_data)


@shared_task()
def update_global_items(data):
    t = time.time() * 1000
    for champ_id, items in data.items():
        with transaction.atomic():
            champ_item, created = ChampionItems.objects.select_for_update().get_or_create(
                champ_id=champ_id
            )
            cur_data = ujson.loads(champ_item.item_blob)
            for item_id, occurence in items.items():
                if item_id in cur_data:
                    cur_data[item_id] += occurence
                else:
                    cur_data[item_id] = occurence
            new_data = ujson.dumps(cur_data)
            champ_item.item_blob = new_data
            champ_item.save()
    print("ugi:", time.time() *1000 - t)


@shared_task()
def update_items(summoner_id, region, data):
    t = time.time() * 1000
    for champ_id, lanes in data.items():
        for lane, items in lanes.items():
            with transaction.atomic():
                uci, created = UserChampionItems.objects.select_for_update().get_or_create(
                    user_id=summoner_id, 
                    region=region,
                    lane=lane, 
                    champ_id=champ_id
                )
                cur_data = ujson.loads(uci.item_blob)
                for item_id, occurence in items.items():
                    if item_id in cur_data:
                        cur_data[item_id] += occurence
                    else:
                        cur_data[item_id] = occurence
                new_data = ujson.dumps(cur_data)
                uci.item_blob = new_data
                uci.save()
    print("ui:", time.time() *1000 - t)


@shared_task()
def update_spells(summoner_id, region, data):
    t = time.time() * 1000
    for champ_id, lanes in data.items():
        for lane, sum_strings in lanes.items():
            for sum_string, occurence in sum_strings.items():
                ucs, created = UserChampionSummoners.objects.get_or_create(
                    user_id=summoner_id, 
                    region=region, 
                    lane=lane, 
                    champ_id=champ_id, 
                    summoner_set=sum_string,
                    defaults={'occurence': 0}
                )
                ucs.occurence = F('occurence') + occurence
                ucs.save()
    print("us:", time.time() *1000 - t)

@shared_task()
def update_runes(summoner_id, region, data):
    t = time.time() * 1000
    for champ_id, lanes in data.items():
        for lane, rune_strings in lanes.items():
            for rune_string, occurence in rune_strings.items():
                ucr, created = UserChampionRunes.objects.get_or_create(
                    user_id=summoner_id, 
                    region=region, 
                    lane=lane, 
                    champ_id=champ_id, 
                    rune_set=rune_string,
                    defaults={'occurence': 0}
                )
                ucr.occurence = F('occurence') + occurence
                ucr.save()
    print("ur:", time.time() *1000 - t)

@shared_task()
def update_userchampionversus(summoner_id, region, data):
    t = time.time() * 1000
    for champ_id, enemies_data in data.items():
        with transaction.atomic():
            championv, created = UserChampionVersusStats.objects.select_for_update().get_or_create(
                user_id=summoner_id, 
                region=region, 
                champ_id=champ_id
            )
            cur_data = ujson.loads(championv.versus_blob)
            for enemy_id, enemy_data in enemies_data.items():
                if enemy_id in cur_data:
                    cur_data[enemy_id]['wins'] += enemy_data['wins']
                    cur_data[enemy_id]['losses'] += enemy_data['losses']
                else:
                    cur_data[enemy_id] = {}
                    cur_data[enemy_id]['wins'] = enemy_data['wins']
                    cur_data[enemy_id]['losses'] = enemy_data['losses']
            new_data = ujson.dumps(cur_data)
            championv.versus_blob = new_data
            championv.save()
    print("ucv:", time.time() *1000 - t)

@shared_task()
def update_matchlawn(summoner_id, region, data):
    t = time.time() * 1000
    for date, stats in data.items():
        lawn, created = MatchLawn.objects.get_or_create(
            user_id=summoner_id,
            region=region, 
            date=date, 
            defaults={
                'wins': 0,
                'losses': 0
            }
        )
        lawn.wins = F('wins') + stats['wins']
        lawn.losses = F('losses') + stats['losses']
        lawn.save()
    print("ml:", time.time() *1000 - t)

@shared_task()
def update_profile(summoner_id, region, data):
    t = time.time() * 1000
    try:
        profile = ProfileStats.objects.get(user_id=summoner_id, region=region)
        profile.wins = F('wins') + data['wins']
        profile.losses = F('losses') + data['losses']
        profile.time_played = F('time_played') + data['time_played']
        if profile.last_match_updated < data['last_match_updated']:
            profile.last_match_updated = data['last_match_updated']
        profile.save()
    except Exception as e:
        log.error("Summoner not created in database")
        raise e
    print("p:", time.time() *1000 - t)
