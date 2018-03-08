import os

SECONDS_BETWEEN_UPDATES = 15 * 60
SECONDS_BETWEEN_CHAMPION_MASTERY_UPDATES = 60 * 60 * 3

# Aggregation settings
AGGREGATION_BATCH_SIZE = os.environ['AGGREGATION_BATCH_SIZE']
AGGREGATION_SIZE = os.environ['AGGREGATION_SIZE']

ITEM_CORE = 0
ITEM_BOOTS = 1
