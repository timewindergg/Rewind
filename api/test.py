import cassiopeia as cass
import datetime
import os

from multiprocessing.dummy import Pool
import gc

cass.apply_settings({
  "global": {
    "default_region": None
  },

  "pipeline": {
    "Cache": {
      "expirations": {
          "ChampionStatusData": datetime.timedelta(hours=6),
          "ChampionStatusListData": datetime.timedelta(hours=6),
          "Realms": datetime.timedelta(hours=6),
          "Versions": datetime.timedelta(hours=6),
          "Champion": datetime.timedelta(days=20),
          "Rune": datetime.timedelta(days=20),
          "Item": datetime.timedelta(days=20),
          "SummonerSpell": datetime.timedelta(days=20),
          "Map": datetime.timedelta(days=20),
          "ProfileIcon": datetime.timedelta(days=20),
          "Locales": datetime.timedelta(days=20),
          "LanguageStrings": datetime.timedelta(days=20),
          "SummonerSpells": datetime.timedelta(days=20),
          "Items": datetime.timedelta(days=20),
          "Champions": datetime.timedelta(days=20),
          "Runes": datetime.timedelta(days=20),
          "Maps": datetime.timedelta(days=20),
          "ProfileIcons": datetime.timedelta(days=20),
          "ChampionMastery": datetime.timedelta(days=7),
          "ChampionMasteries": datetime.timedelta(days=7),
          "LeagueEntries": datetime.timedelta(hours=6),
          "League": datetime.timedelta(hours=6),
          "ChallengerLeague": datetime.timedelta(hours=6),
          "MasterLeague": datetime.timedelta(hours=6),
          "Match": 0,
          "Timeline": 0,
          "Summoner": datetime.timedelta(minutes=2),
          "ShardStatus": datetime.timedelta(hours=1),
          "CurrentMatch": 0,
          "FeaturedMatches": 0
      }
    },

    "DDragon": {},

    "RiotAPI": {
      "api_key": os.environ["RIOT_API_KEY"]
    },
  },

  "logging": {
    "print_calls": True,
    "print_riot_api_key": False,
    "default": "WARNING",
    "core": "WARNING"
  }
})

def aggregate_batched_matches(batch, region, summoner_id):
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



def load_match(match):
    match.load()


#for i in range(0, 1000):
#  m = cass.get_match(2726687109, region='NA').load()
#  m = cass.get_match(2726091726, region='NA').load()

matches = []
for i in range(0, 25):
  matches.append(2726687109)

for i in range(0, 100):
  aggregate_batched_matches(matches, 'NA', "blah")
