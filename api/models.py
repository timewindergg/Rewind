from django.db import models


class UserChampionStats(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    champ_id = models.IntegerField()
    kills = models.IntegerField()
    deaths = models.IntegerField()
    assists = models.IntegerField()
    first_bloods = models.IntegerField()
    wins = models.IntegerField()
    losses = models.IntegerField()
    total_games = models.IntegerField()
    total_cs = models.IntegerField()
    total_cs10 = models.IntegerField()
    total_cs20 = models.IntegerField()
    total_cs30 = models.IntegerField()
    game_length = models.IntegerField()
    pentas = models.IntegerField()

    class Meta:
        unique_together = (("user_id", "region", "champ_id"),)


class ProfileStats(models.Model):
    user_id = models.IntegerField()
    region = models.CharField(max_length=10)
    name = models.CharField(max_length=16)
    last_updated = models.DateField().auto_now
    last_match_updated = models.IntegerField()
    rank_s8 = models.CharField(max_length=25)
    rank_s7 = models.CharField(max_length=25)
    wins = models.IntegerField()
    losses = models.IntegerField()
    level = models.IntegerField()
    icon = models.IntegerField()

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
    match_id = models.IntegerField()
    region = models.CharField(max_length=10)
    season_id = models.IntegerField()
    timestamp = models.DateField()
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
