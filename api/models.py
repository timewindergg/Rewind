from django.db import models

class Items(models.Model):
    item_id = models.IntegerField()
    item_type = models.IntegerField()


class ChampionStats(models.Model):
    champ_id = models.IntegerField()
    total_games = models.IntegerField()


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


class Matches(models.Model):
    user_id = models.IntegerField()
    match_id = models.BigIntegerField()
    region = models.CharField(max_length=10)
    season_id = models.IntegerField(default=0)
    queue_id = models.IntegerField(default=0)
    timestamp = models.IntegerField(default=0)
    duration = models.IntegerField(default=0)
    champion_id = models.IntegerField(default=0)
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
    winner = models.IntegerField(default=0)
    is_remake = models.BooleanField(default=False)
    red_team = models.CharField(max_length=300)
    blue_team = models.CharField(max_length=300)
    accolades = models.TextField()
    metadata = models.TextField()

    class Meta:
        unique_together = (("user_id", "match_id", "region"),)
