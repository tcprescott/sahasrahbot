import random

MRB_FLAG_CHOICES = {
    'Base flags': 'iyhqh$j9g7@$ZqTBT!BhOAdES$vA',
    'Nerfed Boots, no vanilla': 'iyhqh$j9g7@$ZqTBT!BhOA!0Pv@A',
    'Restrict caves, no vanilla': 'iyhJh$j9g7@$ZqTBT!BhOAu0P@@A',
    'Hidden Palace and Kasuto ON': 'iyhqh$j9g7@$ZZSBT!BhOAdES$vA',
    'No vanilla OW': 'iyhqh$j9g7@$ZqTBT!BhOA!0P@@A',
    'No community Rooms': 'iyhqh$j9g7@$ZqTBT!BhOAdES$rA',
    'Long GP': 'iyhqh$j9Q7@$ZqTBT!BhOAdES$vA',
    'Long GP, No community rooms': 'iyhqh$j9Q7@$ZqTBT!BhOAdES$rA',
    'Disable MC Requirements': 'iyhqh$j9g7@gZqTBT!BhOAdES$vA',
    'No Hints, Disable MC Requirements': 'iyhqh$j9g7@gZqTBTyBAOAdES$vA',
    'The "Finals" Experience': 'iyAqh$j9Q7@gZZSBTyBAOAdES0vA',
}

Z2R_PRESETS = {
    'maxrando': 'iyhqh$j9g7@$ZqTBT!BhOAdES$vA',
    'groups1': 'jhAhD0L#$Za$LpTBT!AhOA!0P@@A',
    'groups2': 'jhAhD0L#$Z8$LpTBT!AhOA!0P@@A',
    'groups3': 'hhAhD0L#$Za$LpTBT!AhOA!0P@@A',
    'groups4': 'hhAhD0L#$Z8$LpTBT!AhOA!0P@@A',
    'brackets': 'hhAhD0j#$78$Jp5HgRAhOA!0P8@A',
    'nit': 'hhAhD0j#$78$Jp5Q$dAhOA!0Pz@A',
    'sgl4': 'jhhhD0j9x78$JpTBT!BhSA!0P@@A',
    'sgl': 'jhhhD0j9$78$JpTBT!BhSA!0P@@A',
}

def preset(preset):
    seed = random.randint(0, 1000000000)
    flags = Z2R_PRESETS[preset]
    return seed, flags

def mrb():
    seed = random.randint(0, 1000000000)
    description, flags = random.choice(list(MRB_FLAG_CHOICES.items()))
    return seed, flags, description