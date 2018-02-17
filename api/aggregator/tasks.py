from celery import shared_task
from celery.contrib import rdb

from django.db import transaction

import cassiopeia as cass
from cassiopeia import data

import json
import datetime

from api.models import ProfileStats, Matches, MatchLawn, UserChampionStats, ChampionItems, ChampionRunes, UserChampionVersusStats, UserChampionItems, UserChampionRunes, UserChampionSummoners

import logging
log = logging.getLogger(__name__)

@shared_task()
def aggregate_users(summoner_id, region, max_aggregations=-1):
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

        for match in recent_matches:
            if profile.last_match_updated == match.id:
                updated = True
                break

            aggregate_user_match.delay(region=region, summoner_id=summoner_id, match_id=match.id)
            count += 1

        index += 100

        if len(recent_matches) == 0:
            break

    return f"Aggregated {summoner_id}, {region}, {count} matches"


@shared_task()
def aggregate_user_match(region, summoner_id, match_id):
    summoner_id = int(summoner_id)
    match_id = int(match_id)
    summoner = cass.get_summoner(id=summoner_id, region=region)
    match = cass.get_match(id=match_id, region=region)

    try: # match.queue will call riot api
        is_ranked = match.queue == cass.Queue.ranked_solo_fives or match.queue == cass.Queue.ranked_flex_fives or match.queue == cass.Queue.ranked_flex_threes
    except:
        log.warn("Error checking is_ranked in aggregate_user_match")
        is_ranked = False

    with transaction.atomic():
        try:
            profile = ProfileStats.objects.select_for_update().get(user_id=summoner_id, region=region)
        except Exception as e:
            log.error("Summoner not created in database")
            return

        profile.time_played += match.duration.total_seconds()

        for participant in match.participants:
            if participant.summoner.id == summoner.id:
                user = participant
                break

        try:
            wards_placed = user.stats.wards_placed
            wards_killed = user.stats.wards_killed
        except:
            wards_placed = 0
            wards_killed = 0

        season_id = data.SEASON_IDS[match.season]

        items = [item.id if item else 0 for item in user.stats.items]
        
        #red_team = [p.to_json() for p in match.red_team.participants]
        #blue_team = [p.to_json() for p in match.blue_team.participants]
        
        m, created = Matches.objects.select_for_update().get_or_create(
            user_id=summoner.id,
            match_id=match.id,
            region=match.region.value
        )
        m.season_id = season_id
        m.queue_id = data.QUEUE_IDS[match.queue]
        m.timestamp = match.creation.timestamp
        m.duration = match.duration.total_seconds()
        m.champ_id = user.champion.id
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
        m.lane = user.lane.value
        m.role = user.role
        m.team = user.side.value
        m.winner = 100 if match.blue_team.win else 200
        m.won = user.stats.win
        m.is_remake = match.is_remake
        #m.red_team = json.dumps(red_team)
        #m.blue_team = json.dumps(blue_team)
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

        lawn, created = MatchLawn.objects.select_for_update().get_or_create(user_id=summoner.id, region=region, date=datetime.datetime.fromtimestamp(match.creation.timestamp))
        if user.stats.win:
            lawn.wins += 1
        else:
            lawn.losses += 1
        lawn.save()

        ucs, created = UserChampionStats.objects.select_for_update().get_or_create(user_id=summoner.id, region=region, season_id=season_id, champ_id=user.champion.id, lane=user.lane.value)
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
        ucs.lane = user.lane.value
        '''
        if user.lane == cass.data.Lane.top_lane:
            ucs.lane_top += 1
        elif user.lane == cass.data.Lane.jungle:
            ucs.lane_jg += 1
        elif user.lane == cass.data.Lane.mid_lane:
            ucs.lane_mid += 1
        elif user.lane == cass.data.Lane.bot_lane:
            ucs.lane_bot += 1
        '''
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
            championv, created = UserChampionVersusStats.objects.select_for_update().get_or_create(user_id=summoner.id, region=region, season_id=season_id, champ_id=user.champion.id, enemy_champ_id=enemy.champion.id)
            championv.total_games += 1
            if user.stats.win:
                championv.wins += 1
            else:
                championv.losses += 1
            championv.save()

        try:
            sorted_runes = [r.id for r in user.runes]
            sorted_runes.sort()
            rune_string = json.dumps(sorted_runes)
            ucr, created = UserChampionRunes.objects.select_for_update().get_or_create(user_id=summoner.id, region=region, season_id=season_id, lane=user.lane.value, champ_id=user.champion.id, rune_set=rune_string)
            ucr.occurence += 1
            ucr.save()
        except:
            log.warn("legacy runes")

        sorted_summs = [user.summoner_spell_d.id, user.summoner_spell_f.id]
        sorted_summs.sort()
        summoner_string = json.dumps(sorted_summs)
        ucs, created = UserChampionSummoners.objects.select_for_update().get_or_create(user_id=summoner.id, region=region, season_id=season_id, lane=user.lane.value, champ_id=user.champion.id, summoner_set=summoner_string)
        ucs.occurence += 1
        ucs.save()

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

    for item in user.stats.items:
        if item:
            with transaction.atomic():
                uci, created = UserChampionItems.objects.select_for_update().get_or_create(user_id=summoner.id, region=region, season_id=season_id, lane=user.lane.value, champ_id=user.champion.id, item_id=item.id)
                uci.occurence += 1
                uci.save()

    if is_ranked:
        aggregate_global_stats(match=match)
    else:
        return


def aggregate_global_stats(match):
    for participant in match.participants:
        champ_id = participant.champion.id
        for item in participant.stats.items:
            if item:
                with transaction.atomic():
                    champ_item, created = ChampionItems.objects.select_for_update().get_or_create(champ_id=champ_id, item_id=item.id)
                    champ_item.occurence += 1
                    champ_item.save()
        try: # Legacy runes will break this. Cassiopeia only supports runes reforged atm.
            for rune in participant.runes:
                with transaction.atomic():
                    champ_rune, created = ChampionRunes.objects.select_for_update().get_or_create(champ_id=champ_id, rune_id=rune.id)
                    champ_rune.occurence += 1
                    champ_rune.save()
        except:
            pass
