from django.db import models


class UserChampionStats(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    season_id = models.IntegerField()
    champ_id = models.IntegerField()
    kills = models.IntegerField(default=0)
    deaths = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    first_bloods = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    total_games = models.IntegerField(default=0)
    total_cs = models.IntegerField(default=0)
    total_cs10 = models.IntegerField(default=0)
    total_cs20 = models.IntegerField(default=0)
    total_cs30 = models.IntegerField(default=0)
    game_length = models.IntegerField(default=0)
    pentas = models.IntegerField(default=0)
    quadras = models.IntegerField(default=0)
    triples = models.IntegerField(default=0)
    doubles = models.IntegerField(default=0)

    class Meta:
        unique_together = (("user_id", "region", "season_id", "champ_id"),)


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


class Matches(models.Model):
    user_id = models.IntegerField()
    match_id = models.BigIntegerField()
    region = models.CharField(max_length=10)
    season_id = models.IntegerField()
    timestamp = models.IntegerField()
    duration = models.IntegerField()
    item0 = models.IntegerField()
    item1 = models.IntegerField()
    item2 = models.IntegerField()
    item3 = models.IntegerField()
    item4 = models.IntegerField()
    item5 = models.IntegerField()
    item6 = models.IntegerField()
    spell0 = models.IntegerField()
    spell1 = models.IntegerField()
    kills = models.IntegerField()
    deaths = models.IntegerField()
    assists = models.IntegerField()
    cs = models.IntegerField()
    level = models.IntegerField()
    wards_placed = models.IntegerField()
    wards_killed = models.IntegerField()
    vision_wards_bought = models.IntegerField()
    game_type = models.CharField(max_length=50)
    red_players = models.CharField(max_length=300)
    blue_players = models.CharField(max_length=300)
    accolades = models.TextField()
    metadata = models.TextField()

    class Meta:
        unique_together = (("user_id", "match_id", "region"),)
