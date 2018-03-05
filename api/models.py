from django.db import models

class Items(models.Model):
    item_id = models.IntegerField(primary_key=True)
    item_type = models.IntegerField()


class ChampionStats(models.Model):
    champ_id = models.IntegerField()
    total_games = models.IntegerField(default=0)
    role = models.CharField(max_length=50)
    skill_orders = models.TextField()
    items = models.TextField()
    summoners = models.TextField()
    runes = models.TextField()

    class Meta:
        unique_together = (("champ_id", "role"),)


class ChampionMatchups(models.Model):
    champ_id = models.IntegerField()
    enemy_champ_id = models.IntegerField()
    role = models.CharField(max_length=50)
    win_rate = models.FloatField(default=0)
    kills = models.FloatField(default=0)
    losses = models.FloatField(default=0)
    assists = models.FloatField(default=0)

    class Meta:
        unique_together = (("champ_id", "role", "enemy_champ_id"),)

class ChampionItems(models.Model):
    champ_id = models.IntegerField()
    item_id = models.IntegerField()
    occurence = models.IntegerField(default=0)

    class Meta:
        unique_together = (("champ_id", "item_id"),)


class ChampionRunes(models.Model):
    champ_id = models.IntegerField()
    rune_id = models.IntegerField()
    occurence = models.IntegerField(default=0)

    class Meta:
        unique_together = (("champ_id", "rune_id"),)


class UserChampionItems(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    champ_id = models.IntegerField()
    season_id = models.IntegerField()
    lane = models.CharField(max_length=50)
    item_id = models.IntegerField()
    occurence = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "region", "season_id", "champ_id", "lane", "item_id"),)


class UserChampionRunes(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    champ_id = models.IntegerField()
    season_id = models.IntegerField()
    lane = models.CharField(max_length=50)
    rune_set = models.TextField()
    occurence = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "region", "season_id", "champ_id", "lane", "rune_set"),)


class UserChampionMasteries(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    champ_id = models.IntegerField()
    level = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    points_since_last = models.IntegerField(default=0)
    points_to_next = models.IntegerField(default=0)
    chest_granted = models.BooleanField(default=False)

    class Meta:
        unique_together = (("user_id", "region", "champ_id"),)


class UserChampionSummoners(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    champ_id = models.IntegerField()
    season_id = models.IntegerField()
    lane = models.CharField(max_length=50)
    summoner_set = models.TextField()
    occurence = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "region", "season_id", "champ_id", "lane", "summoner_set"),)


class UserChampionVersusStats(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    season_id = models.IntegerField()
    champ_id = models.IntegerField()
    enemy_champ_id = models.IntegerField()
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    total_games = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "region", "season_id", "champ_id", "enemy_champ_id"),)

class UserChampionStats(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    season_id = models.IntegerField()
    champ_id = models.IntegerField()
    lane = models.CharField(max_length=50)
    kills = models.IntegerField(default=0)
    deaths = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    first_bloods = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    wins20 = models.IntegerField(default=0)
    wins30 = models.IntegerField(default=0)
    wins40 = models.IntegerField(default=0)
    wins40p = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    total_games = models.IntegerField(default=0)
    total_games20 = models.IntegerField(default=0)
    total_games30 = models.IntegerField(default=0)
    total_games40 = models.IntegerField(default=0)
    total_games40p = models.IntegerField(default=0)
    total_cs = models.IntegerField(default=0)
    game_length = models.IntegerField(default=0)
    pentas = models.IntegerField(default=0)
    quadras = models.IntegerField(default=0)
    triples = models.IntegerField(default=0)
    doubles = models.IntegerField(default=0)
    gold = models.IntegerField(default=0)
    xp10 = models.FloatField(default=0)
    xp20 = models.FloatField(default=0)
    xp30 = models.FloatField(default=0)
    xp_diff10 = models.FloatField(default=0)
    xp_diff20 = models.FloatField(default=0)
    xp_diff30 = models.FloatField(default=0)
    gold10 = models.FloatField(default=0)
    gold20 = models.FloatField(default=0)
    gold30 = models.FloatField(default=0)
    cs10 = models.FloatField(default=0)
    cs20 = models.FloatField(default=0)
    cs30 = models.FloatField(default=0)
    cs_diff10 = models.FloatField(default=0)
    cs_diff20 = models.FloatField(default=0)
    cs_diff30 = models.FloatField(default=0)
    dmg_taken10 = models.FloatField(default=0)
    dmg_taken20 = models.FloatField(default=0)
    dmg_taken30 = models.FloatField(default=0)
    dmg_taken_diff10 = models.FloatField(default=0)
    dmg_taken_diff20 = models.FloatField(default=0)
    dmg_taken_diff30 = models.FloatField(default=0)

    class Meta:
        unique_together = (("user_id", "region", "season_id", "champ_id", "lane"),)


class UserLeagues(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    queue = models.CharField(max_length=30)
    tier = models.CharField(max_length=20)
    division = models.CharField(max_length=10)
    points = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "region", "queue"),)


class ProfileStats(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    name = models.CharField(max_length=16)
    last_updated = models.IntegerField(default=0)
    last_match_updated = models.BigIntegerField(default=0)
    rank_s8 = models.CharField(max_length=25)
    rank_s7 = models.CharField(max_length=25)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    icon = models.IntegerField(default=0)
    time_played = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "region"),)


class Accolades(models.Model):
    accolade_id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=300)


class UserAccolades(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    accolade_id = models.IntegerField()
    accolade_value = models.IntegerField()

    class Meta:
        unique_together = (("user_id", "region", "accolade_id"),)


class MatchLawn(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    date = models.DateField()
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "region", "date"),)


class Matches(models.Model):
    user_id = models.IntegerField()
    match_id = models.BigIntegerField()
    region = models.CharField(max_length=10)
    season_id = models.IntegerField(default=0)
    queue_id = models.IntegerField(default=0)
    timestamp = models.IntegerField(default=0)
    duration = models.IntegerField(default=0)
    champ_id = models.IntegerField(default=0)
    participant_id = models.IntegerField(default=0)
    item0 = models.IntegerField(default=0)
    item1 = models.IntegerField(default=0)
    item2 = models.IntegerField(default=0)
    item3 = models.IntegerField(default=0)
    item4 = models.IntegerField(default=0)
    item5 = models.IntegerField(default=0)
    item6 = models.IntegerField(default=0)
    spell0 = models.IntegerField(default=0)
    spell1 = models.IntegerField(default=0)
    kills = models.IntegerField(default=0)
    deaths = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    cs = models.IntegerField(default=0)
    gold = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    wards_placed = models.IntegerField(default=0)
    wards_killed = models.IntegerField(default=0)
    vision_wards_bought = models.IntegerField(default=0)
    game_type = models.CharField(max_length=50)
    lane = models.CharField(max_length=50)
    role = models.CharField(max_length=50, null=True)
    team = models.IntegerField(default=0)
    winner = models.IntegerField(default=0)
    won = models.BooleanField(default=False)
    is_remake = models.BooleanField(default=False)
    red_team = models.TextField()
    blue_team = models.TextField()
    accolades = models.TextField()
    metadata = models.TextField()
    killing_spree = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "match_id", "region"),)
