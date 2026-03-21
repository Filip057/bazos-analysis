# Aliases map variant spellings → canonical model name
# Czech declension, typos, spacing variants, suffixes
MODEL_ALIASES = {
    # Škoda — Czech declension
    'octavii': 'octavia', 'octavie': 'octavia', 'octávii': 'octavia', 'octávie': 'octavia',
    'fabii': 'fabia', 'fabie': 'fabia', 'fábie': 'fabia',
    'superbem': 'superb', 'superbu': 'superb',
    'kodiaqem': 'kodiaq', 'kodiaqů': 'kodiaq',
    'karoqem': 'karoq',
    'scalu': 'scala',
    'roomsteru': 'roomster',
    'yetiho': 'yeti',
    'enyaqu': 'enyaq',

    # Peugeot — suffixed variants (308sw, 207cc etc.)
    '106sw': '106', '206sw': '206', '206cc': '206', '206+': '206',
    '207sw': '207', '207cc': '207',
    '307sw': '307', '307cc': '307',
    '308sw': '308', '308cc': '308', '308gt': '308',
    '407sw': '407', '407coupe': '407',
    '508sw': '508', '508gt': '508',
    '607sw': '607',

    # Mazda — spacing/dash variants
    'cx 3': 'cx-3', 'cx 5': 'cx-5', 'cx 7': 'cx-7', 'cx 9': 'cx-9',
    'cx 30': 'cx-30', 'cx 8': 'cx-8', 'cx 4': 'cx-4',
    'cx3': 'cx-3', 'cx5': 'cx-5', 'cx7': 'cx-7', 'cx9': 'cx-9',
    'cx30': 'cx-30', 'cx8': 'cx-8', 'cx4': 'cx-4',
    'mx 5': 'mx-5', 'mx5': 'mx-5',
    'rx 8': 'rx-8', 'rx8': 'rx-8',

    # Ford — spacing/dash
    'c max': 'c-max', 'cmax': 'c-max',
    'grand c max': 'grand c-max', 'grand cmax': 'grand c-max',
    'b max': 'b-max', 'bmax': 'b-max',
    's max': 's-max', 'smax': 's-max',
    'ka+': 'ka',
    'tourneo custom': 'tourneo custom',

    # Volkswagen — spacing/dot variants
    'id 3': 'id.3', 'id3': 'id.3',
    'id 4': 'id.4', 'id4': 'id.4',
    'id 5': 'id.5', 'id5': 'id.5',
    't roc': 't-roc', 'troc': 't-roc',
    't cross': 't-cross', 'tcross': 't-cross',
    'tiguan allspace': 'tiguan allspace',

    # BMW — common ways people write series
    'rada 1': '1 series', 'řada 1': '1 series', '1er': '1 series', '1 rada': '1 series',
    'rada 2': '2 series', 'řada 2': '2 series', '2er': '2 series', '2 rada': '2 series',
    'rada 3': '3 series', 'řada 3': '3 series', '3er': '3 series', '3 rada': '3 series',
    'rada 4': '4 series', 'řada 4': '4 series', '4er': '4 series', '4 rada': '4 series',
    'rada 5': '5 series', 'řada 5': '5 series', '5er': '5 series', '5 rada': '5 series',
    'rada 6': '6 series', 'řada 6': '6 series', '6er': '6 series',
    'rada 7': '7 series', 'řada 7': '7 series', '7er': '7 series',
    'rada 8': '8 series', 'řada 8': '8 series', '8er': '8 series',

    # Mercedes — people write "trida" instead of "-class"
    'trida a': 'a-class', 'třída a': 'a-class', 'a class': 'a-class',
    'trida b': 'b-class', 'třída b': 'b-class', 'b class': 'b-class',
    'trida c': 'c-class', 'třída c': 'c-class', 'c class': 'c-class',
    'trida e': 'e-class', 'třída e': 'e-class', 'e class': 'e-class',
    'trida s': 's-class', 'třída s': 's-class', 's class': 's-class',
    'trida v': 'v-class', 'třída v': 'v-class', 'v class': 'v-class',
    'trida r': 'r-class', 'třída r': 'r-class', 'r class': 'r-class',

    # Hyundai — spacing
    'ix 20': 'ix20', 'ix 35': 'ix35',
    'i 10': 'i10', 'i 20': 'i20', 'i 30': 'i30', 'i 40': 'i40',
    'santa': 'santa fe',  # people often write just "santa"

    # Opel — dash/spacing
    'crossland': 'crossland x', 'grandland': 'grandland x',

    # Citroen — dash/spacing
    'c elysee': 'c-elysee', 'celysee': 'c-elysee',
    'grand c4': 'grand c4 spacetourer',
    'c4 spacetourer': 'grand c4 spacetourer',
    'grand c4 picasso': 'grand c4 picasso',
    'c3 picasso': 'c3 picasso',
    'c4 picasso': 'c4 picasso',
    'xsara picasso': 'xsara picasso',
    'c 4x': 'c4x',

    # Suzuki — dash/spacing
    'sx4 s cross': 'sx4 s-cross', 'sx4 scross': 'sx4 s-cross',
    's cross': 's-cross', 'scross': 's-cross',
    'grand vitara': 'grand vitara', 'grandvitara': 'grand vitara',

    # Honda — dash
    'cr v': 'cr-v', 'crv': 'cr-v',
    'hr v': 'hr-v', 'hrv': 'hr-v',
    'zr v': 'zr-v', 'zrv': 'zr-v',
    'cr z': 'cr-z', 'crz': 'cr-z',

    # Renault — accent variants
    'mégane': 'megane', 'mégané': 'megane',
    'scénic': 'scenic', 'grand scénic': 'grand scenic',
    'grand scenic': 'grand scenic',
    'zoé': 'zoe',

    # Nissan — dash
    'x trail': 'x-trail', 'xtrail': 'x-trail',
    'gt r': 'gt-r', 'gtr': 'gt-r',

    # Toyota
    'c-hr': 'chr', 'c hr': 'chr',
    'rav 4': 'rav4',
    'land cruiser': 'land cruiser', 'landcruiser': 'land cruiser',

    # Chevrolet — typos
    'matis': 'matiz', 'mattiz': 'matiz',
    'lacceti': 'lacetti', 'laceti': 'lacetti',
    'olando': 'orlando',

    # Volvo — dash
    'xc 40': 'xc40', 'xc 60': 'xc60', 'xc 90': 'xc90', 'xc 70': 'xc70',

    # Seat — cupra variants
    'cupra': 'cupra formentor',
    'formentor': 'cupra formentor',
    'born': 'cupra born',

    # Fiat
    'grande': 'grande punto',

    # Audi — dash
    'e tron': 'e-tron', 'etron': 'e-tron',
    'q4 etron': 'q4 e-tron', 'q4e-tron': 'q4 e-tron',
}

CAR_MODELS = {
    'alfa': ['giulia', 'stelvio', 'giulietta', 'mito', '147', '156', '159', 'brera', 'spider', 'tonale'],
    'audi': ['a1', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'q2', 'q3', 'q5', 'q7', 'q8', 'tt', 'r8', 's3', 's4', 's5', 's6', 's7', 's8', 'rs3', 'rs4', 'rs5', 'rs6', 'rs7', 'rsq3', 'e-tron', 'sq5', 'sq7', 'sq8', 'q4 e-tron'],
    'bmw': ['1 series', '2 series', '3 series', '4 series', '5 series', '6 series', '7 series', '8 series', 'i3', 'i4', 'i7', 'i8', 'ix', 'ix3', 'm2', 'm3', 'm4', 'm5', 'm6', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'z3', 'z4'],
    'citroen': ['c1', 'c2', 'c3', 'c3 picasso', 'c4', 'c4 picasso', 'c4x', 'c5', 'c-elysee', 'berlingo', 'cactus', 'ds3', 'ds4', 'ds5', 'grand c4 spacetourer', 'grand c4 picasso', 'jumpy', 'jumper', 'xsara', 'xsara picasso', 'saxo', 'c4 aircross'],
    'dacia': ['logan', 'sandero', 'duster', 'lodgy', 'dokker', 'spring', 'jogger'],
    'fiat': ['500', '500x', '500l', '500c', '500l living', '500e', 'panda', 'punto', 'tipo', 'bravo', 'doblo', 'ducato', 'grande punto', 'stilo', 'fiorino', 'linea', 'talento'],
    'ford': ['fiesta', 'focus', 'mondeo', 'mustang', 'ka', 'kuga', 'ecosport', 'edge', 'explorer', 's-max', 'galaxy', 'ranger', 'transit', 'puma', 'c-max', 'grand c-max', 'b-max', 'transit connect', 'tourneo', 'tourneo custom'],
    'honda': ['civic', 'accord', 'cr-v', 'hr-v', 'zr-v', 'jazz', 'nsx', 's2000', 'cr-z', 'insight', 'legend'],
    'hyundai': ['i10', 'i20', 'i30', 'i40', 'ioniq', 'kona', 'nexo', 'tucson', 'santa fe', 'ioniq electric', 'accent', 'getz', 'ix20', 'ix35', 'bayon', 'h1'],
    'chevrolet': ['spark', 'aveo', 'cruze', 'malibu', 'camaro', 'corvette', 'trax', 'equinox', 'captiva', 'orlando', 'blazer', 'tahoe', 'suburban', 'silverado', 'impala', 'lacetti', 'matiz', 'nubira', 'kalos'],
    'kia': ['picanto', 'rio', 'ceed', 'optima', 'stinger', 'sportage', 'sorento', 'niro', 'soul', 'stonic', 'carens', 'proceed', 'venga', 'xceed', 'ev6'],
    'mercedes': ['a-class', 'b-class', 'c-class', 'e-class', 's-class', 'r-class', 'cla', 'cls', 'gla', 'glb', 'glc', 'gle', 'glc coupe', 'gle coupe', 'gls', 'gl', 'ml', 'slc', 'slk', 'sl', 'amg gt', 'eqa', 'eqb', 'eqc', 'eqe', 'eqs', 'v-class', 'vito', 'sprinter'],
    'mitsubishi': ['space star', 'asx', 'eclipse cross', 'outlander', 'pajero', 'l200', 'carisma', 'colt', 'galant', 'lancer', 'grandis', 'fuso'],
    'nissan': ['micra', 'leaf', 'note', 'juke', 'qashqai', 'x-trail', 'pulsar', 'pathfinder', 'patrol', '370z', 'gt-r', 'nv200', 'almera', 'almera tino', 'navara', 'primera', 'murano', 'cube'],
    'opel': ['corsa', 'astra', 'insignia', 'mokka', 'crossland x', 'grandland x', 'zafira', 'adam', 'agila', 'combo', 'karl', 'meriva', 'vivaro', 'movano', 'cascada', 'ampera'],
    'peugeot': ['106', '107', '108', '206', '207', '208', '301', '306', '307', '308', '407', '408', '508', '607', '807', '2008', '3008', '4008', '5008', 'partner', 'traveller', 'rifter', 'expert', 'boxer', 'rcz'],
    'renault': ['twingo', 'clio', 'captur', 'megane', 'scenic', 'grand scenic', 'kadjar', 'espace', 'talisman', 'koleos', 'zoe', 'kangoo', 'laguna', 'master', 'trafic', 'fluence'],
    'seat': ['mii', 'ibiza', 'leon', 'toledo', 'arona', 'ateca', 'alhambra', 'tarraco', 'cordoba', 'cupra formentor', 'cupra born'],
    'suzuki': ['ignis', 'swift', 'baleno', 'vitara', 'sx4 s-cross', 's-cross', 'jimny', 'celerio', 'grand vitara', 'splash', 'alto', 'liana', 'sx4', 'kizashi'],
    'skoda': ['citigo', 'fabia', 'scala', 'octavia', 'superb', 'kamiq', 'karoq', 'kodiaq', 'rapid', 'yeti', 'enyaq', 'roomster', 'felicia'],
    'toyota': ['aygo', 'yaris', 'auris', 'corolla', 'prius', 'avensis', 'chr', 'rav4', 'highlander', 'land cruiser', 'hilux', 'camry', 'supra', 'proace', 'proace verso', 'verso', 'urban cruiser'],
    'volkswagen': ['up', 'polo', 'golf', 'passat', 'arteon', 't-roc', 't-cross', 'tiguan', 'tiguan allspace', 'touareg', 'touran', 'sharan', 'beetle', 'jetta', 'caddy', 'california', 'multivan', 'caravelle', 'amarok', 'cc', 'transporter', 'crafter', 'scirocco', 'lupo', 'id.3', 'id.4', 'id.5', 'bora', 'phaeton', 'eos', 'fox'],
    'volvo': ['v40', 'v50', 'v60', 'v70', 'v90', 's40', 's60', 's80', 's90', 'xc40', 'xc60', 'xc70', 'xc90', 'c30', 'c70'],
    'mazda': ['2', '3', '5', '6', '323', 'cx-3', 'cx-4', 'cx-5', 'cx-7', 'cx-8', 'cx-9', 'cx-30', 'mx-5', 'rx-8', 'mpv', 'premacy']
}
