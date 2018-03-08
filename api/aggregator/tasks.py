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
from api import consts as Consts

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

            recent_matches = cass.get_match_history(summoner=summoner, begin_index=index, end_index=index+100, seasons=[cass.data.Season.from_id(11)])

            batch = []
            for match in recent_matches:
                if profile.last_match_updated == match.id:
                    updated = True
                    break

                batch.append(match.id)

                if len(batch) == Consts.AGGREGATION_BATCH_SIZE:
                    
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
        log.warn("Failed to aggregate_user", e, stack_info=True)
        aggregate_users.retry(exc=e)


@shared_task(retry_backoff=True, max_retries=3, rate_limit='2/s')
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

    matches_data = {}
    champion_data = []

    for match in matchlist:
        #
        # Common data
        #
        try:
            is_ranked = match.queue == cass.Queue.ranked_solo_fives or match.queue == cass.Queue.ranked_flex_fives
        except:
            log.warn("Error checking is_ranked in aggregate_user_match")
            is_ranked = False

        participants = match.red_team.participants + match.blue_team.participants
        for participant in participants:
            if participant.summoner.id == summoner_id:
                user = participant
                break

        if user.lane is None:
            lane = 'NONE'
        else:
            lane = user.lane.value

        if user.role is None:
            role = 'NONE'
        else:
            role = getattr(user.role, 'value', user.role)

        wards_placed = getattr(user.stats, 'wards_placed', 0)
        wards_killed = getattr(user.stats, 'wards_killed', 0)

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

        match_data = {}
        match_data['match_id'] = match.id
        match_data['season_id'] = season_id
        match_data['queue_id'] = cass.data.QUEUE_IDS[match.queue]
        match_data['timestamp'] = match.creation.timestamp
        match_data['duration'] = match.duration.total_seconds()
        match_data['champ_id'] = user.champion.id
        match_data['participant_id'] = user.id
        match_data['item0'] = items[0]
        match_data['item1'] = items[1]
        match_data['item2'] = items[2]
        match_data['item3'] = items[3]
        match_data['item4'] = items[4]
        match_data['item5'] = items[5]
        match_data['item6'] = items[6]
        match_data['spell0'] = user.summoner_spell_d.id
        match_data['spell1'] = user.summoner_spell_f.id
        match_data['deaths'] = user.stats.deaths
        match_data['assists'] = user.stats.assists
        match_data['cs'] = user.stats.total_minions_killed
        match_data['gold'] = user.stats.gold_earned
        match_data['level'] = user.stats.level
        match_data['wards_placed'] = wards_placed
        match_data['wards_killed'] = wards_killed
        match_data['vision_wards_bought'] = user.stats.vision_wards_bought_in_game
        match_data['game_type'] = match.mode.value
        match_data['lane'] = lane
        match_data['role'] = role
        match_data['team'] = user.side.value
        match_data['winner'] = 100 if match.blue_team.win else 200
        match_data['won'] = user.stats.win
        match_data['is_remake'] = match.is_remake
        match_data['killing_spree'] = killing_spree
        match_data['red_team'] = match.red_team.to_json()
        match_data['blue_team'] = match.blue_team.to_json()
        matches_data[match.id] = match_data
            
        #
        # UserChampionStats
        #
        champ_stats = {
            'lane': lane,
            'champ_id': user.champion.id,
            'season_id': season_id,
            'win': user.stats.win,
            'duration': match.duration.seconds
        }
        if user.stats.win:
            champ_stats['wins'] = 1
            if match.duration.seconds <= 20 * 60:
                champ_stats['wins20'] = 1
            elif match.duration.seconds <= 30 * 60:
                champ_stats['wins30'] = 1
            elif match.duration.seconds <= 40 * 60:
                champ_stats['wins40'] = 1
            elif match.duration.seconds > 40 * 60:
                champ_stats['wins40p'] = 1
        else:
            champ_stats['losses'] = 1
        champ_stats['total_games'] = 1
        champ_stats['pentas'] = user.stats.penta_kills
        champ_stats['quadras'] = user.stats.quadra_kills
        champ_stats['triples'] = user.stats.triple_kills
        champ_stats['doubles'] = user.stats.double_kills
        champ_stats['kills'] = user.stats.kills
        champ_stats['deaths'] = user.stats.deaths
        champ_stats['assists'] = user.stats.assists
        champ_stats['fb'] = hasattr(user.stats, "first_blood_kill") and user.stats.first_blood_kill
        if champ_stats['fb']:
            champ_stats['first_bloods'] = 1
        champ_stats['total_cs'] = user.stats.total_minions_killed
        champ_stats['game_length'] = match.duration.total_seconds()
        champ_stats['gold'] = user.stats.gold_earned
        if match.duration.seconds <= 20 * 60:
            champ_stats['total_games20'] = 1
        elif match.duration.seconds <= 30 * 60:
            champ_stats['total_games30'] = 1
        elif match.duration.seconds <= 40 * 60:
            champ_stats['total_games40'] = 1
        elif match.duration.seconds > 40 * 60:
            champ_stats['total_games40p'] = 1
        has_diffs = hasattr(user.timeline, 'cs_diff_per_min_deltas')
        champ_stats['has_diffs'] = has_diffs
        if match.duration.seconds > 10 * 60:
            champ_stats['gpmd10'] = user.timeline.gold_per_min_deltas['0-10']
            champ_stats['cpmd10'] = user.timeline.creeps_per_min_deltas['0-10']
            champ_stats['xpmd10'] = user.timeline.xp_per_min_deltas['0-10']
            champ_stats['dpmd10'] = user.timeline.damage_taken_per_min_deltas['0-10']
            if has_diffs:
                champ_stats['cdpmd10'] = user.timeline.cs_diff_per_min_deltas['0-10']
                champ_stats['xdpmd10'] = user.timeline.xp_diff_per_min_deltas['0-10']
                champ_stats['ddpmd10'] = user.timeline.damage_taken_diff_per_min_deltas['0-10']
        if match.duration.seconds > 20 * 60:
            champ_stats['gpmd20'] = user.timeline.gold_per_min_deltas['10-20']
            champ_stats['cpmd20'] = user.timeline.creeps_per_min_deltas['10-20']
            champ_stats['xpmd20'] = user.timeline.xp_per_min_deltas['10-20']
            champ_stats['dpmd20'] = user.timeline.damage_taken_per_min_deltas['10-20']
            if has_diffs:
                champ_stats['cdpmd20'] = user.timeline.cs_diff_per_min_deltas['10-20']
                champ_stats['xdpmd20'] = user.timeline.xp_diff_per_min_deltas['10-20']
                champ_stats['ddpmd20'] = user.timeline.damage_taken_diff_per_min_deltas['10-20']
        if match.duration.seconds > 30 * 60:
            champ_stats['gpmd30'] = user.timeline.gold_per_min_deltas['20-30']
            champ_stats['cpmd30'] = user.timeline.creeps_per_min_deltas['20-30']
            champ_stats['xpmd30'] = user.timeline.xp_per_min_deltas['20-30']
            champ_stats['dpmd30'] = user.timeline.damage_taken_per_min_deltas['20-30']
            if has_diffs:
                champ_stats['cdpmd30'] = user.timeline.cs_diff_per_min_deltas['20-30']
                champ_stats['xdpmd30'] = user.timeline.xp_diff_per_min_deltas['20-30']
                champ_stats['ddpmd30'] = user.timeline.damage_taken_diff_per_min_deltas['20-30']
        champion_data.append(champ_stats)       


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
        

    update_profile.delay(summoner_id, region, profile_data)
    update_matchlawn.delay(summoner_id, region, lawn_data)
    create_matches.delay(summoner_id, region, matches_data)
    update_userchampionstats.delay(summoner_id, region, champion_data)
    update_userchampionversus.delay(summoner_id, region, versus_data)
    update_runes.delay(summoner_id, region, rune_data)
    update_spells.delay(summoner_id, region, spell_data)
    update_items.delay(summoner_id, region, items_data)
    update_global_items.delay(global_items_data)



@shared_task()
def update_userchampionstats(summoner_id, region, data):
    t = time.time() * 1000
    for champ_data in data:
        with transaction.atomic():
            ucs, created = UserChampionStats.objects.select_for_update().get_or_create(
                user_id=summoner_id, 
                region=region, 
                season_id=champ_data['season_id'], 
                champ_id=champ_data['champ_id'], 
                lane=champ_data['lane']
            )

            dur = champ_data['duration']
            if champ_data['win']:
                ucs.wins += champ_data['wins']
                if dur <= 20 * 60:
                    ucs.wins20 += champ_data['wins20']
                elif dur <= 30 * 60:
                    ucs.wins30 += champ_data['wins30']
                elif dur <= 40 * 60:
                    ucs.wins40 += champ_data['wins40']
                elif dur > 40 * 60:
                    ucs.wins40p += champ_data['wins40p']
            else:
                ucs.losses += 1
            ucs.pentas += champ_data['pentas']
            ucs.quadras += champ_data['quadras']
            ucs.triples += champ_data['triples']
            ucs.doubles += champ_data['doubles']
            ucs.kills += champ_data['kills']
            ucs.deaths += champ_data['deaths']
            ucs.assists += champ_data['assists']
            if champ_data['fb']:
                ucs.first_bloods += champ_data['first_bloods']
            ucs.total_cs += champ_data['total_cs']
            ucs.game_length += champ_data['game_length']
            ucs.gold += champ_data['gold']
            if dur <= 20 * 60:
                ucs.total_games20 += champ_data['total_games20']
            elif dur <= 30 * 60:
                ucs.total_games30 += champ_data['total_games30']
            elif dur <= 40 * 60:
                ucs.total_games40 += champ_data['total_games40']
            elif dur > 40 * 60:
                ucs.total_games40p += champ_data['total_games40p']
            has_diffs = champ_data['has_diffs']
            if dur > 10 * 60:
                ucs.gold10 = (ucs.gold10 * ucs.total_games + champ_data['gpmd10']) / (ucs.total_games + 1)
                ucs.cs10 = (ucs.cs10 * ucs.total_games + champ_data['cpmd10']) / (ucs.total_games + 1)
                ucs.xp10 = (ucs.xp10 * ucs.total_games + champ_data['xpmd10']) / (ucs.total_games + 1)
                ucs.dmg_taken10 = (ucs.dmg_taken10 * ucs.total_games + champ_data['dpmd10']) / (ucs.total_games + 1)
                if has_diffs:
                    ucs.cs_diff10 = (ucs.cs_diff10 * ucs.total_games + champ_data['cdpmd10']) / (ucs.total_games + 1)
                    ucs.xp_diff10 = (ucs.xp_diff10 * ucs.total_games + champ_data['xdpmd10']) / (ucs.total_games + 1)
                    ucs.dmg_taken_diff10 = (ucs.dmg_taken_diff10 * ucs.total_games + champ_data['ddpmd10']) / (ucs.total_games + 1)
            if dur > 20 * 60:
                ucs.gold20 = (ucs.gold20 * ucs.total_games + champ_data['gpmd20']) / (ucs.total_games + 1)
                ucs.cs20 = (ucs.cs20 * ucs.total_games + champ_data['cpmd20']) / (ucs.total_games + 1)
                ucs.xp20 = (ucs.xp20 * ucs.total_games + champ_data['xpmd20']) / (ucs.total_games + 1)
                ucs.dmg_taken20 = (ucs.dmg_taken20 * ucs.total_games + champ_data['dpmd20']) / (ucs.total_games + 1)
                if has_diffs:
                    ucs.cs_diff20 = (ucs.cs_diff20 * ucs.total_games + champ_data['cdpmd20']) / (ucs.total_games + 1)
                    ucs.xp_diff20 = (ucs.xp_diff20 * ucs.total_games + champ_data['xdpmd20']) / (ucs.total_games + 1)
                    ucs.dmg_taken_diff20 = (ucs.dmg_taken_diff20 * ucs.total_games + champ_data['ddpmd20']) / (ucs.total_games + 1)
            if dur > 30 * 60:
                ucs.gold30 = (ucs.gold30 * ucs.total_games + champ_data['gpmd30']) / (ucs.total_games + 1)
                ucs.cs30 = (ucs.cs30 * ucs.total_games + champ_data['cpmd30']) / (ucs.total_games + 1)
                ucs.xp30 = (ucs.xp30 * ucs.total_games + champ_data['xpmd30']) / (ucs.total_games + 1)
                ucs.dmg_taken30 = (ucs.dmg_taken30 * ucs.total_games + champ_data['dpmd30']) / (ucs.total_games + 1)
                if has_diffs:
                    ucs.cs_diff30 = (ucs.cs_diff30 * ucs.total_games + champ_data['cdpmd30']) / (ucs.total_games + 1)
                    ucs.xp_diff30 = (ucs.xp_diff30 * ucs.total_games + champ_data['xdpmd30']) / (ucs.total_games + 1)
                    ucs.dmg_taken_diff30 = (ucs.dmg_taken_diff30 * ucs.total_games + champ_data['ddpmd30']) / (ucs.total_games + 1)
            ucs.total_games += 1
            ucs.save()
    print("ucs:", time.time() *1000 - t)


@shared_task()
def create_matches(summoner_id, region, data):
    try:
        t = time.time() * 1000
        matches = []
        data_items = data.items()
        for m_id, match_data in data_items:
            m = Matches(
                user_id=summoner_id,
                match_id=m_id,
                region=region,
                season_id=match_data['season_id'],
                queue_id=match_data['queue_id'],
                timestamp=match_data['timestamp'],
                duration=match_data['duration'],
                champ_id=match_data['champ_id'],
                participant_id=match_data['participant_id'],
                item0=match_data['item0'],
                item1=match_data['item1'],
                item2=match_data['item2'],
                item3=match_data['item3'],
                item4=match_data['item4'],
                item5=match_data['item5'],
                item6=match_data['item6'],
                spell0=match_data['spell0'],
                spell1=match_data['spell1'],
                deaths=match_data['deaths'],
                assists=match_data['assists'],
                cs=match_data['cs'],
                gold=match_data['gold'],
                level=match_data['level'],
                wards_placed=match_data['wards_placed'],
                wards_killed=match_data['wards_killed'],
                vision_wards_bought=match_data['vision_wards_bought'],
                game_type=match_data['game_type'],
                lane=match_data['lane'],
                role=match_data['role'],
                team=match_data['team'],
                winner=match_data['winner'],
                won=match_data['won'],
                is_remake=match_data['is_remake'],
                killing_spree=match_data['killing_spree'],
                red_team=match_data['red_team'],
                blue_team=match_data['blue_team']
            )
            matches.append(m)

        Matches.objects.bulk_create(matches)
        print("m:", time.time() *1000 - t)
    except:
        log.warn("Could not bulk create matches", stack_info=True)
        return


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
