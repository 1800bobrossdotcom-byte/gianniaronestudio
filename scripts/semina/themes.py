"""Which footage each lyric line reaches for. Keyword -> theme tags; first match order matters little,
every matching theme joins the pool for that line."""
import re

KEY = [
    (r'\broom|rooms|building|built|destroyed', 'building stage'),
    (r'soundtrack|scenes|stage|spotlight|film|poems|endings', 'stage film'),
    (r'time zoo|zoo|anima\b|animalia|creatures|wildlife', 'zoo animals'),
    (r'\blight\b|lights|luminal', 'light sun'),
    (r'swim|tides|ocean|submerged|water|hydrat|thirst|sea', 'ocean water'),
    (r'reins|pulse', 'horse'),
    (r'hide and seek|mirror|ghost|shadow', 'ghost'),
    (r'morse|code|touch|chain letters|little languages|language', 'morse'),
    (r'vibrat|electric|equanimity|understanding', 'electric'),
    (r'numbers|words|idea|burden', 'numbers record'),
    (r'moon|eyes', 'moon'),
    (r'raven', 'birds'),
    (r'tattoo|sleep|forehead|memory|remember|tired|awaken|dream', 'sleep'),
    (r'fabric|silk|fibers', 'dance light'),
    (r'piano|note|chord|melody|record|needle|silence', 'piano record'),
    (r'glanc|stillness', 'moon light'),
    (r'dice|cosmic|stars|star|space|dark', 'stars'),
    (r'circus|ringmaster|trapeze|pirouette|dancing|dance', 'circus dance'),
    (r'painting|still life|abstraction|picture frame|desk|majestic|mundane', 'stage film'),
    (r'8 shape|infinity|spiral|circling', 'electric dance'),
    (r'hourglass|time of|o.clock|timeless|moment|ages', 'clock'),
    (r'death|grave|totems|crises|horror|pain|tortures|erotic|programs', 'grave horror'),
    (r'snake', 'dance'),
    (r'horizon|vanishing|mountain|canyon|river|wind|shores', 'mountain water'),
    (r'wolves|howling', 'wolf'),
    (r'sunflower', 'flowers sun'),
    (r'gods|consciousness', 'stars light'),
    (r'switchblade|drawer|father|mother|underwear', 'sleep ghost'),
    (r'school|child', 'school'),
    (r'cat|midnight|fur|petting|bag', 'cat'),
    (r'car ran|car\b', 'car'),
    (r'buried|backyard', 'grave'),
    (r'door|walked', 'ghost cat'),
    (r'tears|blood', 'water'),
    (r'strobing|technicolor|uncanny', 'horror dance'),
    (r'black and white|color', 'film'),
    (r'shepherd', 'sheep'),
    (r'systems|organizing', 'numbers electric'),
]

def tags_for(text):
    t = text.lower(); out = []
    for pat, tg in KEY:
        if re.search(pat, t): out += tg.split()
    return list(dict.fromkeys(out))
