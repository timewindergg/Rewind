from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.forms.models import model_to_dict
from django.db import transaction
from django.db.models import Sum, Q

import cassiopeia as cass
from cassiopeia import Champion
from cassiopeia.core import CurrentMatch

import os
import datetime
import time
import ujson
from functools import reduce
from multiprocessing.dummy import Pool
import operator

from .aggregator.tasks import aggregate_users
from .models import ProfileStats, ChampionItems, ChampionStats, ChampionMatchups, UserChampionStats, Matches, MatchLawn, UserLeagues, UserChampionMasteries, UserChampionVersusStats, UserChampionItems, UserChampionRunes, UserChampionSummoners
from . import items as Items
from . import consts as Consts

import logging
log = logging.getLogger(__name__)

cass.apply_settings({
  "global": {
    "default_region": None
  },

  "pipeline": {
    "Cache": {
      "expirations": {
        "ChampionStatusData": 0,
        "ChampionStatusListData": 0,
        "Realms": datetime.timedelta(hours=6),
        "Versions": datetime.timedelta(hours=6),
        "Champion": 0,
        "Rune": 0,
        "Item": 0,
        "SummonerSpell": 0,
        "Map": 0,
        "ProfileIcon": 0,
        "Locales": datetime.timedelta(days=20),
        "LanguageStrings": datetime.timedelta(days=20),
        "SummonerSpells": 0,
        "Items": 0,
        "Champions": 0,
        "Runes": 0,
        "Maps": 0,
        "ProfileIcons": 0,
        "ChampionMastery": 0,
        "ChampionMasteries": 0,
        "LeagueEntries": 0,
        "League": 0,
        "ChallengerLeague": 0,
        "MasterLeague": 0,
        "Match": 0,
        "Timeline": 0,
        "Summoner": 0,
        "ShardStatus": datetime.timedelta(hours=1),
        "CurrentMatch": 0,
        "FeaturedMatches": datetime.timedelta(hours=0.5),
      }
    },

    "DDragon": {},

    "RiotAPI": {
      "api_key": os.environ["RIOT_API_KEY"],
      "request_error_handling": {
        "404": {
          "strategy": "throw"
        },
        "429": {
          "service": {
            "strategy": "exponential_backoff",
            "initial_backoff": 1.0,
            "backoff_factor": 2.0,
            "max_attempts": 4
          },
          "method": {
            "strategy": "retry_from_headers",
            "max_attempts": 5
          },
          "application": {
            "strategy": "retry_from_headers",
            "max_attempts": 5
          }
        },
        "500": {
          "strategy": "exponential_backoff",
          "initial_backoff": 1.0,
          "backoff_factor": 2.0,
          "max_attempts": 4
        },
        "502": {
          "strategy": "exponential_backoff",
          "initial_backoff": 1.0,
          "backoff_factor": 2.0,
          "max_attempts": 4
        },
        "503": {
          "strategy": "exponential_backoff",
          "initial_backoff": 1.0,
          "backoff_factor": 2.0,
          "max_attempts": 8
        },
        "504": {
          "strategy": "exponential_backoff",
          "initial_backoff": 1.0,
          "backoff_factor": 2.0,
          "max_attempts": 4
        },
        "timeout": {
          "strategy": "throw"
        }
      }
    }
  },

  "logging": {
    "print_calls": False,
    "print_riot_api_key": False,
    "default": "WARNING",
    "core": "WARNING"
  }
})

cass_cache = cass.configuration.settings.pipeline._cache

#
# HELPER FUNCTIONS
#
def normalize_region(region):
    try:
        return region.upper()
    except:
        return region


#
# STATIC DATA
#
@cache_page(60 * 60 * 12)
@require_http_methods(["GET"])
def get_static_data(request, region):
    region = normalize_region(region)

    response = {}
    try:
        response['version'] = cass.get_version(region=region)

        items_response = {}
        items = cass.get_items(region=region)
        for item in items:
            item_response = {}
            item_response['name'] = item.name
            item_response['totalGold'] = item.gold.total
            item_response['sellGold'] = item.gold.sell
            item_response['description'] = item.description
            item_response['plaintext'] = item.plaintext
            item_response['from'] = [it.id for it in item.builds_from]
            items_response[str(item.id)] = item_response

        runes_response = {}
        runes = cass.get_runes(region=region)
        for rune in runes:
            rune_response = {}
            rune_response['name'] = rune.name
            rune_response['path'] = rune.path.value
            rune_response['shortDescription'] = rune._data[cass.core.staticdata.rune.RuneData].shortDescription #rune.short_description
            rune_response['isKeystone'] = rune.is_keystone
            runes_response[str(rune.id)] = rune_response

        skills_response = {}
        champion_response = {}
        champions = cass.get_champions(region=region)
        for champion in champions:
            ch = {}
            ch['name'] = champion.name
            ch['title'] = champion.title
            ch['img'] = champion.image.full
            champion_response[str(champion.id)] = ch

            skills = ['q', 'w', 'e', 'r']
            skill_response = {
                'p': {},
                'q': {},
                'w': {},
                'e': {},
                'r': {}
            }
            skill_response['p']['img'] = champion.passive.image_info.full
            skill_response['p']['name'] = champion.passive.name
            skill_response['p']['description'] = champion.passive.sanitized_description
            for i, skill in enumerate(skills):
                skill_response[skill]['img'] = champion.spells[i].image_info.full
                skill_response[skill]['name'] = champion.spells[i].name
                skill_response[skill]['description'] = champion.spells[i].sanitized_description
                skill_response[skill]['cooldowns'] = champion.spells[i].cooldowns
                skill_response[skill]['costs'] = champion.spells[i].costs
            skills_response[str(champion.id)] = skill_response

        response['items'] = items_response
        response['runes'] = runes_response
        response['championSkills'] = skills_response
        response['champions'] = champion_response

    except Exception as e:
        log.warn("failed to get static data", stack_info=True)
        log.warn(e)
        return HttpResponse(status=500)

    return JsonResponse(response)

#
# UPDATE SUMMONER
#
def update_summoner_helper(s, region):
    update = False

    with transaction.atomic():
        summoner, created = ProfileStats.objects.select_for_update().get_or_create(user_id=s.id, region=region)
        last_updated = summoner.last_updated
        if created or last_updated < time.time() - Consts.SECONDS_BETWEEN_UPDATES:
            update = True
            summoner.last_updated = round(time.time())
            summoner.name = s.name
            summoner.icon = s.profile_icon.id
            summoner.level = s.level
            summoner.save()

        transaction.on_commit(lambda: aggregate_users.delay(summoner.user_id, region, Consts.AGGREGATION_SIZE))

    with transaction.atomic():
        if update:
            leagues = cass.get_league_positions(summoner=s, region=region)
            for league in leagues:
                user_league, created = UserLeagues.objects.select_for_update().get_or_create(user_id=s.id, region=region, queue=league.queue.value)
                user_league.tier = league.tier.value
                user_league.division = league.division.value
                user_league.points = league.league_points
                user_league.save()

            if last_updated < time.time() - Consts.SECONDS_BETWEEN_CHAMPION_MASTERY_UPDATES:
                cmasteries = cass.get_champion_masteries(summoner=s, region=region)
                for cmastery in cmasteries:
                    user_champion, created = UserChampionMasteries.objects.select_for_update().get_or_create(user_id=s.id, region=region, champ_id=cmastery.champion.id)
                    user_champion.level = cmastery.level
                    user_champion.total_points = cmastery.points
                    user_champion.points_since_last = cmastery.points_since_last_level
                    user_champion.points_to_next = cmastery.points_until_next_level
                    user_champion.chest_granted = cmastery.chest_granted
                    user_champion.save()


@csrf_exempt
@require_http_methods(["POST"])
def update_summoner(request):
    summoner_name = request.POST['summoner_name']
    region = normalize_region(request.POST['region'])

    s = cass.get_summoner(name=summoner_name, region=region)
    if s.exists:
        update_summoner_helper(s, region)
    else:
        return HttpResponse(status=404)

    return HttpResponse(status=200)

#
# GET SUMMONER
#
@require_http_methods(["GET"])
def get_summoner(request):
    region = normalize_region(request.GET['region'])
    try:
        summoner_name = request.GET['summoner_name']
        s = cass.get_summoner(name=summoner_name, region=region)
    except:
        summoner_id = request.GET['summoner_id']
        s = cass.get_summoner(id=summoner_id, region=region)

    if not s.exists:
        return HttpResponse('Summoner does not exist', status=404)

    update_summoner_helper(s, region)

    try:
        summoner = ProfileStats.objects.get(user_id=s.id, region=region)
    except:
        log.warn("ProfileStats not found after update in get_summoner")
        return HttpResponse("Error retrieving profile stats", status=500)

    try:
        cmasteries = UserChampionMasteries.objects.filter(user_id=s.id, region=region).order_by('-total_points')[:3]
    except:
        log.warn("UserChampionMasteries not found after update in get_summoner")
        return HttpResponse("Error retrieving champion masteries", status=500)

    try:
        user_leagues = UserLeagues.objects.filter(user_id=s.id, region=region)
    except:
        log.warn("ProfileStats not found after update in get_summoner")
        return HttpResponse("Error retrieving leagues", status=500)

    try:
        lawn = MatchLawn.objects.filter(user_id=s.id, region=region).order_by('-date')[:90]
    except:
        log.warn("Lawn not found after update in get_summoner")
        return HttpResponse("Error retrieving matchlawn", status=500)

    try:
        champ_stats = UserChampionStats.objects.filter(user_id=s.id, region=region)
    except:
        log.warn("Champ stats not found after update in get_summoner")
        return HttpResponse(status=500)

    response = model_to_dict(summoner)
    response['championMasteries'] = list(cmasteries.values())
    response['leagues'] = list(user_leagues.values())
    response['lawn'] = list(lawn.values())
    response['championStats'] = list(champ_stats.values())

    return JsonResponse(response)


#
# USER LEAGUES
#
@require_http_methods(["GET"])
def get_user_leagues(request):
    try:
        region = normalize_region(request.GET['region'])
        summoners = request.GET['summoner_ids']
        summoner_list = summoners.split(',')
        summoner_list = [int(s) for s in summoner_list]

        league_list = []
        for s in summoner_list:
            summ = cass.get_summoner(id=s, region=region) 
            league_list.append(cass.get_league_positions(summoner=s, region=region))

        try:
            pool = Pool(10)
            pool.map(load_league, league_list)
            pool.close()
            pool.join()
        except:
            pool.close()
            log.warn('failed to load league list')

        response = {}

        for i, summoner_leagues in enumerate(league_list):
            response[summoner_list[i]] = {}
            for league in l:
                league_response = {}
                league_response['tier'] = league.tier.value
                league_response['division'] = league.division.value
                league_response['points'] = league.league_points
                response[summoner_list[i]][league] = league_response
    except Exception as e:
        log.warn('failed to get user leagues', e, stack_info=True)
        return HttpResponse(status=500)

    return JsonResponse(response)
    

def load_league(league):
    league.load()


#
# MATCH HISTORY
#
@require_http_methods(["GET"])
def get_match_history(request):
    region = normalize_region(request.GET['region'])
    offset = int(request.GET['offset'])
    size = int(request.GET['size'])
    try:
        summoner_name = request.GET['summoner_name']
        s = cass.get_summoner(name=summoner_name, region=region)
    except:
        summoner_id = request.GET['summoner_id']
        s = cass.get_summoner(id=summoner_id, region=region)

    if not s.exists:
        return HttpResponse('Summoner does not exist', status=404)

    try:
        matches = Matches.objects.filter(user_id=s.id, region=region).order_by('-timestamp')[offset:size]
    except:
        return HttpResponse(status=404)

    response = list(matches.values())

    return JsonResponse(response, safe=False)

#
# USER CHAMPION STATS
#
def get_user_champion_stats(summoner, region, champion_id):
    response = {}

    try:
        champ_stats_response = {}
        champ_stats = UserChampionStats.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id)
        for stat in champ_stats:
            champ_stats_response[stat.lane] = model_to_dict(stat)
    except:
        log.warn("failed to get champ_stats", stack_info=True)
        return HttpResponse(status=500)

    try:
        champ_versus = UserChampionVersusStats.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id)
    except:
        log.warn("failed to get champ_versus", stack_info=True)
        return HttpResponse(status=500)

    try:
        championItems = {}
        uci = UserChampionItems.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id)
        
        for uci_lane in uci:
            boots = {}
            core = {}
            situational = {}
            all_items = {}
            items_blob = ujson.loads(uci_lane.item_blob)

            blob_items = items_blob.items()
            for item, occurence in blob_items:
                if int(item) in Items.boots:
                    boots[item] = occurence
                elif int(item) in Items.full_items:
                    all_items[item] = occurence

            sorted_all = sorted(all_items, key=all_items.get, reverse=True) 
            core_arr = sorted_all[:3]
            situational_arr = sorted_all[3:]

            for item in core_arr:
                core[item] = all_items[item]

            for item in situational_arr:
                situational[item] = all_items[item]

            itemset = {
                'core': core,
                'situational': situational,
                'boots': boots
            }

            if uci_lane.lane == cass.data.Lane.top_lane.value:
                championItems['TOP_LANE'] = itemset
            elif uci_lane.lane == cass.data.Lane.jungle.value:
                championItems['JUNGLE'] = itemset
            elif uci_lane.lane == cass.data.Lane.mid_lane.value:
                championItems['MID_LANE'] = itemset
            elif uci_lane.lane == cass.data.Lane.bot_lane.value:
                championItems['BOT_LANE'] = itemset
            else: # lane = NONE
                pass
    except:
        log.warn("failed to get champ_items", stack_info=True)
        return HttpResponse(status=500)

    try:
        champ_runes = UserChampionRunes.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id).order_by('-occurence')
    except:
        log.warn("failed to get champ_runes", stack_info=True)
        return HttpResponse(status=500)

    try:
        champ_summs = UserChampionSummoners.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id).order_by('-occurence')
    except:
        log.warn("failed to get champ_summs", stack_info=True)
        return HttpResponse(status=500)

    try:
        matches = Matches.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id).order_by('-timestamp')[:5]
    except:
        log.warn("failed to get recent matches", stack_info=True)
        return HttpResponse(status=500)

    response['championId'] = champion_id
    response['championStats'] = champ_stats_response
    response['championMatchups'] = list(champ_versus.values())
    response['championItems'] = championItems
    response['championRunes'] = list(champ_runes.values())
    response['championSummoners'] = list(champ_summs.values())
    response['recentMatches'] = list(matches.values())

    return JsonResponse(response)


@require_http_methods(["GET"])
def get_user_champion_stats_by_id(request):
    region = normalize_region(request.GET['region'])
    champion_id = int(request.GET['champion_id'])
    try:
        summoner_name = request.GET['summoner_name']
        s = cass.get_summoner(name=summoner_name, region=region)
    except:
        summoner_id = request.GET['summoner_id']
        s = cass.get_summoner(id=summoner_id, region=region)

    if not s.exists:
        return HttpResponse('Summoner does not exist', status=404)

    return get_user_champion_stats(s, region, champion_id)


#
# CURRENT MATCH
#
@require_http_methods(["GET"])
def get_current_match(request):
    region = normalize_region(request.GET['region'])
    try:
        summoner_name = request.GET['summoner_name']
        s = cass.get_summoner(name=summoner_name, region=region)
    except:
        summoner_id = request.GET['summoner_id']
        s = cass.get_summoner(id=summoner_id, region=region)

    if not s.exists:
        return HttpResponse("Summoner does not exist", status=404)

    try:
        m = cass.get_current_match(summoner=s, region=region)
        if not m.exists:
            return HttpResponse("Match does not exist", status=404)
    except:
        return HttpResponse("Match does not exist", status=404)


    response = {}
    winrates = {}
    skill_orders_response = {}

    blue_participants = m.teams[0].participants
    blue_team_champs = [p.champion.id for p in blue_participants]
    red_participants = m.teams[1].participants
    red_team_champs = [p.champion.id for p in red_participants]
    participants = m.participants

    # champion winrates
    wr_matrix = {}
    for btc in blue_team_champs:
        champ_wrs = {}
        for mtc in red_team_champs:
            cid = min(btc, mtc)
            eid = max(btc, mtc)
            matchup = ChampionMatchups.objects.filter(champ_id=cid, enemy_champ_id=eid)
            if len(matchup) > 0:
                wrs = [mu.win_rate for mu in matchup]
                awr = sum(wrs) / len(wrs)

                if btc < mtc:
                    champ_wrs[eid] = awr
                else:
                    champ_wrs[cid] = awr
                
        wr_matrix[btc] = champ_wrs
                
    red_team = []
    blue_team = []
    for participant in participants:
        p = {}
        p['id'] = participant.summoner.id
        p['champion_id'] = participant.champion.id
        p['name'] = participant.summoner.name
        p['summoner_spell0'] = participant.summoner_spell_d.id
        p['summoner_spell1'] = participant.summoner_spell_f.id
        runes = []
        for rune in participant.runes:
            runes.append(rune.id)
        p['runes'] = runes
        if participant.side.value == 100:
            blue_team.append(p)
        elif participant.side.value == 200:
            red_team.append(p)

        # champion skill order
        champ_stats = ChampionStats.objects.filter(champ_id=participant.champion.id).values('skill_orders')
        best_order = []
        top_wr_so = 0
        for stat in champ_stats:
            so = ujson.loads(stat['skill_orders'])
            if so['winrate'] > top_wr_so:
                top_wr_so = so['winrate']
                order = so['hash'].split('-')[1:]
                best_order = order
        skill_orders_response[participant.champion.id] = best_order

    bans = m.teams[0].bans.items()
    blue_bans = [v.id for k, v in bans]
    bans = m.teams[1].bans.items()
    red_bans = [v.id for k, v in bans]

    queue = {}
    queue['id'] = m.queue.id
    queue['value'] = m.queue.value

    response['red_team'] = red_team
    response['blue_team'] = blue_team
    response['red_bans'] = red_bans
    response['blue_bans'] = blue_bans
    response['creation'] = m.creation.timestamp
    response['queue'] = queue
    response['winrates'] = wr_matrix
    response['skill_orders'] = skill_orders_response

    return JsonResponse(response)


def load_match(match):
    try:
        match.load()
        match.timeline.load()
    except Exception as e:
        log.warn("Failed to load match", e, stack_info=True)


def load_cass_obj(obj):
    try:
        obj.load()
    except Exception as e:
        log.warn("Failed to load cass obj", e, stack_info=True)


#
# CURRENT_MATCH_DETAILS
#
def get_current_match_details(s, region, champion_id):
    matchlist = cass.get_match_history(summoner=s, champions=[champion_id], begin_index=0, end_index=10)
    len(matchlist) # to fill matchlist

    try:
        pool = Pool(10)
        pool.map(load_match, matchlist)
        pool.close()
        pool.join()
    except:
        pool.close()
        return HttpResponse(status=500)

    response = {}

    q = {}
    leagues = cass.get_league_positions(summoner=s, region=region)
    for league in leagues:
        q[league.queue.value] = {
            'tier': league.tier.value,
            'division': league.division.value,
            'points': league.league_points
        }
        if league.promos != None:
            q[league.queue.value]['promos'] = league.promos.progress

    # summoner stats for past 20 matches on a champion
    stats = {
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "totalCs": 0,
        "cs10": 0,
        "cs20": 0,
        "cs30": 0,
        "gold10": 0,
        "gold20": 0,
        "gold30": 0,
        "wins": 0,
        "losses": 0
    }
    match_history = []

    games10 = 0
    games20 = 0
    games30 = 0
    cs10 = 0
    cs20 = 0
    cs30 = 0
    gold10 = 0
    gold20 = 0
    gold30 = 0
    for match in matchlist:
        participants = match.participants
        for participant in participants:
            if participant.summoner.id == s.id and hasattr(participant, "timeline"):
                user = participant
                break

        stats["kills"] += user.stats.kills
        stats["deaths"] += user.stats.deaths
        stats["assists"] += user.stats.assists
        stats["totalCs"] += user.stats.total_minions_killed

        if user.stats.win:
            stats["wins"] += 1
            match_history.append(1)
        else:
            stats["losses"] += 1
            match_history.append(0)

        try:
            cs10 += match.timeline.frames[10].participant_frames[user.id].creep_score
            gold10 += match.timeline.frames[10].participant_frames[user.id].gold_earned
            games10 += 1

            cs20 += match.timeline.frames[20].participant_frames[user.id].creep_score
            gold20 += match.timeline.frames[20].participant_frames[user.id].gold_earned
            games20 += 1

            cs30 += match.timeline.frames[30].participant_frames[user.id].creep_score
            gold30 += match.timeline.frames[30].participant_frames[user.id].gold_earned
            games30 += 1
        except:
            pass

    stats["kills"] /= 10
    stats["deaths"] /= 10
    stats["assists"] /= 10
    stats["totalCs"] /= 10

    try:
        stats["cs10"] = round(cs10 / games10, 2)
        stats["cs20"] = round(cs20 / games20, 2)
        stats["cs30"] = round(cs30 / games30, 2)
        stats["gold10"] = round(gold10 / games10, 2)
        stats["gold20"] = round(gold20 / games20, 2)
        stats["gold30"] = round(gold30 / games30, 2)
    except:
        # divide by 0
        pass

    build = {}

    # get recommended build
    champ_items = ChampionItems.objects.get(champ_id=user.champion.id)
    items_blob = ujson.loads(champ_items.item_blob)

    boots = {}
    core = {}
    situational = {}
    all_items = {}

    blob_items = items_blob.items()
    for item, occurence in blob_items:
        if int(item) in Items.boots:
            boots[item] = occurence
        elif int(item) in Items.full_items:
            all_items[item] = occurence

    sorted_all = sorted(all_items, key=all_items.get, reverse=True) 
    core_arr = sorted_all[:3]
    situational_arr = sorted_all[3:8]

    for item in core_arr:
        core[item] = all_items[item]

    for item in situational_arr:
        situational[item] = all_items[item]

    build['boots'] = boots
    build['core'] = core
    build['situational'] = situational

    response['stats'] = stats
    response['build'] = build
    response['leagues'] = q

    return response


@require_http_methods(["GET"])
def get_current_match_details_by_id(request):
    region = normalize_region(request.GET['region'])
    champion_id = int(request.GET['champion_id'])
    try:
        summoner_name = request.GET['summoner_name']
        s = cass.get_summoner(name=summoner_name, region=region)
    except:
        summoner_id = request.GET['summoner_id']
        s = cass.get_summoner(id=summoner_id, region=region)

    if not s.exists:
        return HttpResponse("Summoner does not exist", status=404)

    response = get_current_match_details(s, region, champion_id)

    return JsonResponse(response)

#
# MATCH TIMELINE
#
@require_http_methods(["GET"])
def get_match_timeline(request):
    region = normalize_region(request.GET['region'])
    match_id = int(request.GET['match_id'])

    try:
        match = cass.get_match(id=match_id, region=region)
        pool = Pool(2)
        pool.map(load_cass_obj, [match, match.timeline])
        pool.close()
        pool.join()
    except:
        pool.close()
        return HttpResponse("Match does not exist", status=404)

    response = {}
    response['timeline'] = ujson.loads(match.timeline.to_json())
    response['match'] = ujson.loads(match.to_json())

    return JsonResponse(response)
