full_items = [
    3001, # Abyssal Mask
    3194, # Adaptive Helm
    3003, # Archangel's Staff
    3504, # Ardent Censer
    3174, # Athene's Unholy Grail
    3060, # Banner of Command
    3102, # Banshee's Veil
    3153, # Blade of the Ruined King
    3742, # Dead Man's Plate
    3812, # Death's Dance
    3147, # Duskblade
    3814, # Edge of Night
    3508, # Essence Reaver
    2303, # Eye of the Equinox
    2302, # Eye of the Oasis
    2301, # Eye of the Watchers
    3401, # Face of the Mountain
    3092, # Frost Queen's Claim
    3110, # Frozen Heart
    3022, # Frozen Mallet
    3193, # Gargoyle Stoneplate
    3026, # Guardian Angel
    3124, # Guinsoo's Rageblade
    3030, # Hextech GLP
    3146, # Hextech Gunblade
    3152, # Hextech Protobelt
    3025, # Iceborn Gauntlet
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
    3165, # Morellonomicon
    3033, # Mortal Reminder
    3042, # Muramana
    3115, # Nashor's Tooth
    3056, # Ohmwrecker
    3198, # Perfect Hex Core
    3046, # Phantom Dancer
    3089, # Rabadon's Deathcap
    3143, # Randuin's Omen
    3094, # Rapid Firecannon
    3074, # Ravenous Hydra
    3107, # Redemption
    3800, # Righteous Glory
    3027, # Rod of Ages
    2045, # Ruby Sightstone
    3085, # Runaan's Hurricane
    3116, # Rylai's Crystal Scepter
    3040, # Seraph's Embrace
    3065, # Spirit Visage
    3087, # Statikk Shiv
    3053, # Sterak's Gage
    3068, # Sunfire Cape
    3069, # Talisman of Ascension
    3071, # The Black Cleaver
    3072, # The Bloodthirster
    3075, # Thornmail
    3748, # Titanic Hydra
    3078, # Trinity Force
    3135, # Void Staff
    3083, # Warmog's Armor
    3091, # Wit's End
    3142, # Youmuu's Ghostblade
    3050, # Zeke's Convergence
    3157, # Zhonya's Hourglass
    3512  # Zz'Rot Portal
]

boots = [
    3006, # Berserkers
    3117, # Mobility
    3009, # Swiftness
    3158, # Lucidity
    3139, # Mercurials
    3047, # Tabi
    3020  # Sorcerer's
]

import consts as Consts
for item in full_items:
    Items.objects.get_or_create(item_id=item, item_type=Consts.ITEM_CORE)

for boot in boots:
    Items.objects.get_or_create(item_id=item, item_type=Consts.ITEM_BOOTS)




