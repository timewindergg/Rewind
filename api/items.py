full_items = [
    3001, # Abyssal Mask
    3194, # Adaptive Helm
    3003, # Archangel's Staff
    3504, # Ardent Censer
    3174, # Athene's Unholy Grail
    3060, # Banner of Command
    3102, # Banshee's Veil
    3153, # Blade of the Ruined King
    3383, # Circlet of the Iron Solari
    3742, # Dead Man's Plate
    3812, # Death's Dance
    3147, # Duskblade
    3814, # Edge of Night
    3508, # Essence Reaver
    #2303, # Eye of the Equinox
    #2302, # Eye of the Oasis
    #2301, # Eye of the Watchers
    3373, # Forgefire Cape
    3110, # Frozen Heart
    3022, # Frozen Mallet
    3193, # Gargoyle Stoneplate
    3026, # Guardian Angel
    3124, # Guinsoo's Rageblade
    3030, # Hextech GLP
    3146, # Hextech Gunblade
    3152, # Hextech Protobelt
    3025, # Iceborn Gauntlet
    3379, # Infernal Mask
    3031, # Infinity Edge
    3109, # Knight's Vow
    3151, # Liandry's Torment
    3100, # Lich Bane
    3190, # Locket of the Iron Solari
    3036, # Lord Dominik's
    3285, # Luden's Echo
    3004, # Manamune
    3156, # Maw of Malmortius
    3041, # Mejai's Soulstealer
    3139, # Mercurial Scimitar
    3222, # Mikael's Crucible
    3371, # Molten Edge
    3165, # Morellonomicon
    3033, # Mortal Reminder
    3042, # Muramana
    3115, # Nashor's Tooth
    3056, # Ohmwrecker
    3198, # Perfect Hex Core
    3046, # Phantom Dancer
    3089, # Rabadon's Deathcap
    3374, # Rabadon's Deathcrown
    3143, # Randuin's Omen
    3094, # Rapid Firecannon
    3074, # Ravenous Hydra
    3107, # Redemption
    3069, # Remnant of the Ascended
    3401, # Remnant of the Aspect
    3092, # Remnant of the Watchers
    3800, # Righteous Glory
    3027, # Rod of Ages
    #2045, # Ruby Sightstone
    3085, # Runaan's Hurricane
    3116, # Rylai's Crystal Scepter
    3382, # Salvation
    3040, # Seraph's Embrace
    3065, # Spirit Visage
    3087, # Statikk Shiv
    3053, # Sterak's Gage
    3068, # Sunfire Cape
    3071, # The Black Cleaver
    3072, # The Bloodthirster
    3380, # The Obsidian Cleaver
    3075, # Thornmail
    3748, # Titanic Hydra
    3078, # Trinity Force
    3384, # Trinity Fusion,
    3905, # Twin Shadows
    3135, # Void Staff
    3083, # Warmog's Armor
    3091, # Wit's End
    3142, # Youmuu's Ghostblade
    3050, # Zeke's Convergence
    3157, # Zhonya's Hourglass
    3386, # Zhonya's Paradox
    3512, # Zz'Rot Portal
]

ornnable = [
    3001, # Abyssal Mask
    3190, # Locket of the Iron Solari
    3068, # Sunfire Cape
    3031, # Infinity Edge
    3107, # Redemption
    3071, # Black Cleaver
    3078, # Trinity Force
    3090, # Wooglet's Witchcap
    3157, # Zhonya's Hourglass
]

boots = [
    3006, # Berserkers
    3117, # Mobility
    3009, # Swiftness
    3158, # Lucidity
    3111, # Mercury
    3047, # Tabi
    3020, # Sorcerer's
]

consumables = [
    2055, # Vision Ward
    2033, # Corrupting Potion
    2032, # Hunter's Potion
    2031, # Refillable Potion
]

def update_items():
    from . import consts as Consts
    from .models import Items
    import cassiopeia as cass

    items = cass.get_items(region='NA')

    for item in items:
        if item.id in ornnable or item.gold.total > 1200 and item.builds_into == []:
            Items.objects.get_or_create(item_id=item.id, item_type=Consts.ITEM_CORE)

    for boot in boots:
        Items.objects.get_or_create(item_id=boot, item_type=Consts.ITEM_BOOTS)
