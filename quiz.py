"""Educational quiz system shown between levels — Math & English.

Questions scale with level. Math tiers ramp from arithmetic up to
algebra, Pythagoras, quadratics and probability. English goes from
spelling/synonyms to advanced vocabulary, rhetoric and complex grammar.
"""

import math
import random
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    UI_BG, UI_BORDER, UI_TEXT, GOLD, WHITE,
    get_chapter
)


# ── Static space background (pre-rendered once, never moves) ──────────────────

def _make_space_bg() -> pygame.Surface:
    """Render a rich, completely-static deep-space background."""
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Deep-space gradient
    for y in range(SCREEN_HEIGHT):
        t = y / SCREEN_HEIGHT
        r = int(2  + t * 6)
        g = int(1  + t * 3)
        b = int(18 + t * 28)
        pygame.draw.line(s, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    # Nebula clouds
    _NEBULA_PALETTES = [
        (80, 0, 130), (0, 40, 140), (0, 90, 70),
        (130, 20, 0), (0, 60, 100), (90, 0, 80),
        (20, 70, 90), (0, 80, 120),
    ]
    ns = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    rng = random.Random(42)     # fixed seed so it looks the same every time
    for _ in range(9):
        hue = rng.choice(_NEBULA_PALETTES)
        cx  = rng.randint(0, SCREEN_WIDTH)
        cy  = rng.randint(0, SCREEN_HEIGHT)
        for _ in range(180):
            rx  = cx + rng.randint(-220, 220)
            ry  = cy + rng.randint(-140, 140)
            rr  = rng.randint(22, 72)
            al  = rng.randint(4, 18)
            c = (
                max(0, min(255, hue[0] + rng.randint(-30, 30))),
                max(0, min(255, hue[1] + rng.randint(-30, 30))),
                max(0, min(255, hue[2] + rng.randint(-30, 30))),
                al,
            )
            pygame.draw.ellipse(ns, c, (rx - rr, ry - rr//2, rr*2, rr))
    s.blit(ns, (0, 0))

    # Distant planets
    _PLANET_COLS = [
        (80, 50, 20), (30, 55, 110), (50, 28, 70),
        (20, 80, 50), (90, 30, 10), (10, 60, 90),
    ]
    for seed_off in range(2):
        pr2  = rng.randint(30, 75)
        px   = rng.randint(pr2 + 60, SCREEN_WIDTH - pr2 - 60)
        py   = rng.randint(pr2 + 40, SCREEN_HEIGHT - pr2 - 120)
        col  = rng.choice(_PLANET_COLS)
        ring = (seed_off == 0)
        for dr in range(pr2 + 12, pr2, -2):
            al = max(0, int(22 * (pr2 - dr + 12) / 12))
            ah = pygame.Surface((dr*2, dr*2), pygame.SRCALPHA)
            pygame.draw.circle(ah, (*col, al), (dr, dr), dr)
            s.blit(ah, (px - dr, py - dr))
        pygame.draw.circle(s, col, (px, py), pr2)
        hl = tuple(min(255, v + 65) for v in col)
        pygame.draw.circle(s, hl, (px - pr2//3, py - pr2//3), max(2, pr2//5))
        if ring:
            rw = pr2 * 4; rh = pr2 + 6
            rs = pygame.Surface((rw, rh), pygame.SRCALPHA)
            rc = tuple(min(255, v + 55) for v in col)
            pygame.draw.ellipse(rs, (*rc, 85), (0, rh//3, rw, rh//3), 3)
            s.blit(rs, (px - rw//2, py - rh//2))

    # Stars — 3 layers
    _STAR_TYPES = [
        (1.00, 1.00, 1.00), (0.85, 0.90, 1.00),
        (1.00, 0.85, 0.65), (1.00, 0.65, 0.55),
        (1.00, 0.50, 0.50), (0.75, 0.85, 1.00),
    ]
    for _ in range(110):   # far — dim tiny dots
        x = rng.randint(0, SCREEN_WIDTH)
        y = rng.randint(0, SCREEN_HEIGHT)
        b = rng.randint(38, 90)
        pygame.draw.circle(s, (b, b, b), (x, y), 1)
    for _ in range(65):    # mid
        x  = rng.randint(0, SCREEN_WIDTH)
        y  = rng.randint(0, SCREEN_HEIGHT)
        b  = rng.randint(90, 165)
        t_ = rng.choice(_STAR_TYPES[:3])
        c  = (min(255,int(b*t_[0])), min(255,int(b*t_[1])), min(255,int(b*t_[2])+20))
        pygame.draw.circle(s, c, (x, y), 1)
    for _ in range(38):    # near / bright
        x  = rng.randint(0, SCREEN_WIDTH)
        y  = rng.randint(0, SCREEN_HEIGHT)
        b  = rng.randint(160, 240)
        sz = 1 if rng.random() < 0.55 else (2 if rng.random() < 0.70 else 3)
        t_ = rng.choice(_STAR_TYPES)
        c  = (min(255,int(b*t_[0])), min(255,int(b*t_[1])), min(255,int(b*t_[2])+30))
        pygame.draw.circle(s, c, (x, y), sz)
        if sz >= 3 and b > 190:
            lc = (min(255,c[0]+60), min(255,c[1]+60), min(255,c[2]+60))
            pygame.draw.line(s, lc, (x-sz-2, y), (x+sz+2, y), 1)
            pygame.draw.line(s, lc, (x, y-sz-2), (x, y+sz+2), 1)

    return s


# ── Math question generator ───────────────────────────────────────────────────

def _distractors(correct, n, lo, hi):
    """Generate n plausible wrong answers near correct."""
    wrong = set()
    deltas = list(range(-18, 19))
    random.shuffle(deltas)
    for d in deltas:
        v = correct + d
        if v != correct and lo <= v <= hi:
            wrong.add(v)
        if len(wrong) >= n:
            break
    while len(wrong) < n:
        v = random.randint(lo, hi)
        if v != correct:
            wrong.add(v)
    return list(wrong)[:n]


def _make_math_question(level: int) -> tuple:
    """Return (question_str, answer_str, [choice_str, ...], correct_idx).

    Tiers 0-7 scale from multi-digit arithmetic up to quadratics,
    simultaneous equations, probability and circle theorems.
    """
    tier = min(7, (level - 1) // 3)

    if tier == 0:
        # Multi-digit add/subtract; basic multiply
        kind = random.choice(['add', 'sub', 'mul'])
        if kind == 'add':
            a, b = random.randint(25, 99), random.randint(25, 99)
            ans = a + b;  q = f'{a} + {b} = ?'
        elif kind == 'sub':
            a = random.randint(40, 130); b = random.randint(10, 50)
            if a < b: a, b = b, a
            ans = a - b;  q = f'{a} − {b} = ?'
        else:
            a, b = random.randint(4, 12), random.randint(4, 12)
            ans = a * b;  q = f'{a} × {b} = ?'

    elif tier == 1:
        # Times tables 2–15, BODMAS, negative numbers
        kind = random.choice(['times', 'bodmas', 'neg'])
        if kind == 'times':
            a, b = random.randint(7, 15), random.randint(7, 15)
            ans = a * b;  q = f'{a} × {b} = ?'
        elif kind == 'bodmas':
            a = random.randint(2, 8); b = random.randint(2, 7)
            c = random.randint(1, 12)
            ans = a * b + c;  q = f'{a} × {b} + {c} = ?'
        else:
            bigger = random.randint(6, 25)
            smaller= random.randint(1, bigger - 1)
            ans = smaller - bigger   # negative
            q   = f'{smaller} − {bigger} = ?'

    elif tier == 2:
        # Division remainder, long multiplication, LCM/HCF
        kind = random.choice(['div_rem', 'longmul', 'lcm', 'hcf'])
        if kind == 'div_rem':
            d = random.randint(3, 9); q_ = random.randint(2, 12)
            rem = random.randint(1, d-1); a = d*q_ + rem
            ans = rem;  q = f'{a} ÷ {d}: what is the remainder?'
        elif kind == 'longmul':
            a, b = random.randint(12, 35), random.randint(11, 22)
            ans = a * b;  q = f'{a} × {b} = ?'
        elif kind == 'lcm':
            pairs = [(4,6,12),(3,5,15),(6,8,24),(4,10,20),(6,9,18),(5,8,40),(4,12,12)]
            a, b, ans = random.choice(pairs)
            q = f'LCM of {a} and {b} = ?'
        else:
            h = random.randint(2, 7); p = random.randint(2, 5)
            r = random.randint(2, 5)
            while r == p: r = random.randint(2, 5)
            A, B = h*p, h*r;  ans = h
            q = f'HCF of {A} and {B} = ?'

    elif tier == 3:
        # Harder percentages, fractions, two-step algebra, perimeter
        kind = random.choice(['pct', 'frac', 'alg1', 'perim'])
        if kind == 'pct':
            pct = random.choice([15, 30, 35, 45, 60, 75])
            n   = random.choice([40, 60, 80, 120, 200, 240])
            ans = n * pct // 100;  q = f'{pct}% of {n} = ?'
        elif kind == 'frac':
            b = random.randint(1, 7); c = random.choice([2, 4, 5, 8, 10])
            b = min(b, c-1); n = random.randint(2, 7) * c
            ans = n * b // c;  q = f'{b}/{c} of {n} = ?'
        elif kind == 'alg1':
            x = random.randint(1, 14); a = random.randint(2, 6); b = random.randint(1, 18)
            c = a*x + b;  ans = x;  q = f'{a}x + {b} = {c}  →  x = ?'
        else:
            shape = random.choice(['rect_perim', 'triangle', 'circle_area'])
            if shape == 'rect_perim':
                w, h_ = random.randint(5,15), random.randint(5,15)
                ans = 2*(w+h_);  q = f'Perimeter of {w}×{h_} rectangle = ?'
            elif shape == 'triangle':
                a, b_, c_ = random.randint(5,14), random.randint(5,14), random.randint(5,14)
                ans = a+b_+c_;  q = f'Perimeter: sides {a}, {b_}, {c_} = ?'
            else:
                r = random.randint(3, 9)
                ans = int(round(math.pi * r * r))
                q   = f'Area of circle r={r} (π≈3.14), nearest whole = ?'

    elif tier == 4:
        # Square roots, cubes, powers, sequences, two-step algebra
        kind = random.choice(['sq_root', 'cube', 'seq', 'alg2'])
        if kind == 'sq_root':
            n = random.choice([4,9,16,25,36,49,64,81,100,121,144,169,196,225])
            ans = int(math.isqrt(n));  q = f'√{n} = ?'
        elif kind == 'cube':
            base = random.randint(2, 7); ans = base**3
            q    = f'{base}³ = ?'
        elif kind == 'seq':
            kind2 = random.choice(['quad', 'geo'])
            if kind2 == 'quad':
                k = random.randint(0, 6)
                seq = [n*n + k for n in range(1, 7)]
                q   = (f'Next term: {seq[0]}, {seq[1]}, {seq[2]}, '
                       f'{seq[3]}, {seq[4]}, __ ?')
                ans = seq[5]
            else:
                ratio = random.choice([2, 3]); start = random.randint(1, 4)
                seq   = [start * ratio**i for i in range(6)]
                q     = (f'Geometric: {seq[0]}, {seq[1]}, {seq[2]}, '
                         f'{seq[3]}, __ ?')
                ans   = seq[4]
        else:
            x = random.randint(2, 15); a = random.randint(2, 6); b = random.randint(2, 20)
            c = a*x - b;  ans = x;  q = f'{a}x − {b} = {c}  →  x = ?'

    elif tier == 5:
        # Pythagoras, probability, index laws, prime factorisation
        kind = random.choice(['pyth', 'prob', 'index', 'factor'])
        if kind == 'pyth':
            trips = [(3,4,5),(5,12,13),(8,15,17),(7,24,25),(6,8,10),(9,12,15),(20,21,29)]
            a, b, c = random.choice(trips)
            hide = random.choice([0,1,2]); vals = [a,b,c]; ans = vals[hide]
            lbl  = ['a','b','c']
            shown = [(lbl[i],vals[i]) for i in range(3) if i != hide]
            q = (f'Right triangle: {shown[0][0]}={shown[0][1]}, '
                 f'{shown[1][0]}={shown[1][1]}.  {lbl[hide]} = ?')
        elif kind == 'prob':
            total = random.choice([4,5,6,8,10,12,20])
            fav   = random.randint(1, total-1)
            g     = math.gcd(fav, total)
            numer = fav // g; denom = total // g
            ans   = numer
            q     = (f'Bag: {total} balls, {fav} red. '
                     f'P(red) as fraction: ? / {denom}  (give numerator)')
        elif kind == 'index':
            base = random.randint(2, 5); e1 = random.randint(2, 4); e2 = random.randint(2, 4)
            op   = random.choice(['mul','div'])
            if op == 'mul':
                ans = e1 + e2;  q = f'{base}^{e1} × {base}^{e2} = {base}^?'
            else:
                e1 = e2 + random.randint(1, 3); ans = e1 - e2
                q  = f'{base}^{e1} ÷ {base}^{e2} = {base}^?'
        else:
            primes = [2,3,5,7,11,13]
            p1, p2 = random.sample(primes[:5], 2)
            n  = p1 * p2;  ans = max(p1, p2)
            q  = f'Largest prime factor of {n} = ?'

    elif tier == 6:
        # Simultaneous equations, quadratic roots, statistics, polygon angles
        kind = random.choice(['simul', 'quad', 'stats', 'angle'])
        if kind == 'simul':
            x = random.randint(3, 15); y = random.randint(1, x-1)
            A = x + y; B = x - y
            q = f'x + y = {A},  x − y = {B}  →  x = ?';  ans = x
        elif kind == 'quad':
            r1 = random.randint(1, 9); r2 = random.randint(1, 9)
            s  = r1 + r2; p = r1 * r2;  ans = max(r1, r2)
            q  = f'x² − {s}x + {p} = 0.  Larger root = ?'
        elif kind == 'stats':
            nums = [random.randint(10, 30) for _ in range(5)]
            rem  = sum(nums) % len(nums);  nums[-1] -= rem
            ans  = sum(nums) // len(nums)
            q    = f'Mean of {nums} = ?'
        else:
            sides = random.choice([3,4,5,6,8])
            ans   = (sides - 2) * 180 // sides
            q     = f'Each interior angle of a regular {sides}-gon = ?°'

    else:
        # Tier 7 — ratio, percentage change, circumference, negative algebra
        kind = random.choice(['ratio', 'perc_change', 'circumference', 'neg_alg'])
        if kind == 'ratio':
            total = random.choice([20,24,30,36,40,48,60])
            parts = random.choice([(1,3),(1,4),(2,3),(3,5),(1,2),(3,7)])
            ans   = total * parts[0] // sum(parts)
            q     = f'Split {total} in ratio {parts[0]}:{parts[1]}.  Smaller share = ?'
        elif kind == 'perc_change':
            orig = random.choice([50,80,120,150,200,250])
            pct  = random.choice([10,20,25,30,40,50])
            up   = random.random() < 0.5
            ans  = orig + orig*pct//100 if up else orig - orig*pct//100
            sign = 'Increase' if up else 'Decrease'
            q    = f'{sign} {orig} by {pct}% = ?'
        elif kind == 'circumference':
            r   = random.choice([5,7,10,12,14,15])
            ans = int(round(2 * math.pi * r))
            q   = f'Circumference, r={r} (π≈3.14), nearest whole = ?'
        else:
            x = random.randint(1, 10); a = random.randint(2, 5)
            b = random.randint(a*x+1, a*x+22); c = b - a*x
            q = f'{b} − {a}x = {c}  →  x = ?';  ans = x

    lo    = max(-50, ans - 28)
    hi    = ans + 45
    wrong = _distractors(ans, 3, lo, hi)
    choices = [str(x) for x in wrong + [ans]]
    random.shuffle(choices)
    idx = choices.index(str(ans))
    return (q, str(ans), choices, idx)


# ── English question bank — 3 difficulty bands ────────────────────────────────

_ENG_EASY = [
    # Spelling
    ("Which is spelled correctly?", "beautiful",
     ["beautifull","beautyful","beautiful","beutiful"], 2),
    ("Which is spelled correctly?", "necessary",
     ["neccessary","necesary","neccesary","necessary"], 3),
    ("Which is spelled correctly?", "separate",
     ["seperate","seprate","separate","sepperate"], 2),
    ("Which is spelled correctly?", "rhythm",
     ["rythm","rhythym","rhythm","rythym"], 2),
    ("Which is spelled correctly?", "receive",
     ["recieve","recive","receive","receve"], 2),
    ("Which is spelled correctly?", "definitely",
     ["definately","definitly","definately","definitely"], 3),
    ("Which is spelled correctly?", "embarrass",
     ["embarass","embarras","embarrass","embaras"], 2),
    # Synonyms
    ("Synonym of 'happy'?", "joyful",
     ["angry","tired","joyful","sad"], 2),
    ("Synonym of 'large'?", "enormous",
     ["tiny","enormous","quick","dark"], 1),
    ("Synonym of 'brave'?", "courageous",
     ["cowardly","lazy","courageous","nervous"], 2),
    ("Synonym of 'fast'?", "swift",
     ["swift","heavy","quiet","tall"], 0),
    ("Synonym of 'sad'?", "melancholy",
     ["elated","melancholy","furious","serene"], 1),
    ("Synonym of 'begin'?", "commence",
     ["finish","ignore","prevent","commence"], 3),
    # Antonyms
    ("Opposite of 'ancient'?", "modern",
     ["old","historic","modern","classical"], 2),
    ("Opposite of 'generous'?", "stingy",
     ["kind","wealthy","stingy","giving"], 2),
    ("Opposite of 'expand'?", "contract",
     ["grow","contract","widen","enlarge"], 1),
    ("Opposite of 'transparent'?", "opaque",
     ["clear","glassy","sheer","opaque"], 3),
    ("Opposite of 'victory'?", "defeat",
     ["triumph","success","defeat","glory"], 2),
    ("Opposite of 'ascend'?", "descend",
     ["rise","descend","climb","soar"], 1),
    # Grammar basics
    ("Which is correct?", "She and I went to the store.",
     ["Me and her went.","She and I went to the store.",
      "Her and me went.","She and me went."], 1),
    ("Correct use of 'its'?", "The dog wagged its tail.",
     ["Its raining.","Its over there.",
      "The dog wagged its tail.","Its a beautiful day."], 2),
    ("Which is correct?", "I could have gone.",
     ["I could of gone.","I could have gone.",
      "I could of went.","I could have went."], 1),
    ("'Their / There / They're going home.' — which?", "They're",
     ["Their","There","They're","Thier"], 2),
    # Parts of speech
    ("'Quickly' is a …?", "adverb",
     ["noun","verb","adjective","adverb"], 3),
    ("'Happiness' is a …?", "noun",
     ["noun","verb","adverb","adjective"], 0),
    ("'Run' in 'I run every day' is a …?", "verb",
     ["noun","adjective","verb","preposition"], 2),
    # Definitions (basic)
    ("'Nocturnal' means …?", "active at night",
     ["active at night","very fast","underground","tiny"], 0),
    ("'Obsolete' means …?", "no longer used",
     ["brand new","very popular","no longer used","expensive"], 2),
    ("'Benevolent' means …?", "kind and generous",
     ["cruel","confused","kind and generous","angry"], 2),
    # Prefixes/suffixes
    ("Prefix 'pre-' means …?", "before",
     ["after","against","before","without"], 2),
    ("Suffix '-ful' means …?", "full of",
     ["without","full of","more than","opposite of"], 1),
    ("Prefix 'un-' means …?", "not or opposite",
     ["not or opposite","again","half","many"], 0),
]

_ENG_MEDIUM = [
    # Spelling
    ("Which is spelled correctly?", "occurrence",
     ["occurence","occurance","occurrence","occurrance"], 2),
    ("Which is spelled correctly?", "accommodation",
     ["accomodation","accommodaton","accommodation","acommodation"], 2),
    ("Which is spelled correctly?", "conscientious",
     ["consciencious","conscientious","consciontious","consientious"], 1),
    ("Which is spelled correctly?", "entrepreneur",
     ["entrepeneur","enterpreneur","entrepreneur","entreperneur"], 2),
    ("Which is spelled correctly?", "millennium",
     ["millenium","milenium","millennium","milleniom"], 2),
    ("Which is spelled correctly?", "bureaucracy",
     ["burocracy","beaurocracy","bureaucracy","buereaucracy"], 2),
    ("Which is spelled correctly?", "Lieutenant",
     ["Lieutennant","Leutenant","Lieutenant","Lietuenant"], 2),
    # Vocabulary
    ("'Ephemeral' means …?", "lasting a very short time",
     ["lasting a very short time","extremely large",
      "deeply confusing","brightly coloured"], 0),
    ("'Ubiquitous' means …?", "found everywhere",
     ["found nowhere","very unusual","found everywhere","deeply hidden"], 2),
    ("'Gregarious' means …?", "sociable and outgoing",
     ["lonely and sad","sociable and outgoing",
      "very intelligent","extremely quiet"], 1),
    ("'Pragmatic' means …?", "practical and realistic",
     ["very imaginative","perfectly honest",
      "practical and realistic","overly idealistic"], 2),
    ("'Tenacious' means …?", "persistent and determined",
     ["easily tired","very talkative",
      "persistent and determined","quick to give up"], 2),
    ("'Perfidious' means …?", "deceitful and untrustworthy",
     ["extremely loyal","deceitful and untrustworthy",
      "bravely courageous","endlessly kind"], 1),
    ("'Sycophant' is …?", "a flatterer seeking personal gain",
     ["a strong critic","an honest advisor",
      "a flatterer seeking personal gain","a fierce warrior"], 2),
    ("'Laconic' means …?", "using very few words",
     ["extremely talkative","using very few words",
      "completely illogical","full of anger"], 1),
    ("'Verbose' means …?", "using too many words",
     ["very quiet","using too many words","extremely fast","totally silent"], 1),
    # Literary terms
    ("A 'metaphor' is …?", "A comparison without 'like' or 'as'",
     ["A word that sounds like what it means",
      "A comparison without 'like' or 'as'",
      "An exaggeration for effect",
      "Words starting with the same sound"], 1),
    ("'Alliteration' is …?", "Repetition of initial consonant sounds",
     ["A comparison using 'like' or 'as'",
      "Words with opposite meanings",
      "Repetition of initial consonant sounds",
      "An extreme exaggeration"], 2),
    ("'Onomatopoeia' is …?", "A word that sounds like its meaning",
     ["A story's turning point",
      "A word that sounds like its meaning",
      "Repeating the same word",
      "Giving objects human traits"], 1),
    ("'Personification' is …?", "Giving human traits to non-human things",
     ["Using the same sound repeatedly","A moral story",
      "Giving human traits to non-human things",
      "Opposite of a metaphor"], 2),
    ("'Irony' is best described as …?", "Saying the opposite of what is meant",
     ["Saying the opposite of what is meant","A very sad event",
      "A sudden plot twist","Repetition for emphasis"], 0),
    ("'Hyperbole' is …?", "An extreme exaggeration for effect",
     ["A comparison using 'like'","An extreme exaggeration for effect",
      "Giving objects human traits","Repeating starting sounds"], 1),
    # Grammar
    ("Which is passive voice?", "The cake was eaten by the dog.",
     ["The dog ate the cake.","The cake was eaten by the dog.",
      "Eating cake is enjoyable.","The dog likes eating cake."], 1),
    ("'Fewer' vs 'less' — correct?", "Fewer students attended.",
     ["Less students attended.","Fewer students attended.",
      "Fewer amount attended.","Less number came."], 1),
    ("A 'compound sentence' has …?",
     "Two independent clauses joined by a conjunction",
     ["One main clause",
      "Two independent clauses joined by a conjunction",
      "A dependent and independent clause",
      "Three or more verbs"], 1),
    ("A 'subordinate clause' …?", "Cannot stand alone as a sentence",
     ["Stands alone as a complete sentence",
      "Cannot stand alone as a sentence",
      "Contains only a subject",
      "Is always a question"], 1),
    ("A 'gerund' is …?", "A verb form used as a noun",
     ["A verb form used as a noun","A word describing a verb",
      "A clause without a subject","A type of conjunction"], 0),
    ("A 'participle phrase' modifies …?", "A noun or pronoun",
     ["A verb","A noun or pronoun","A conjunction","An adverb"], 1),
    # Prefixes/roots
    ("Root 'port' means …?", "carry",
     ["walk","carry","speak","write"], 1),
    ("Prefix 'inter-' means …?", "between",
     ["inside","against","around","between"], 3),
    ("Prefix 'circum-' means …?", "around",
     ["below","around","against","inside"], 1),
    ("Prefix 'mal-' means …?", "bad or wrongly",
     ["good","many","bad or wrongly","again"], 2),
    ("Root 'aud-' means …?", "hear",
     ["see","speak","hear","touch"], 2),
    ("Root 'scrib-' means …?", "write",
     ["walk","write","carry","hold"], 1),
]

_ENG_HARD = [
    # Advanced vocabulary
    ("'Sanguine' means …?", "optimistic",
     ["pessimistic","optimistic","blood-red","very tired"], 1),
    ("'Recalcitrant' means …?", "stubbornly resistant to authority",
     ["eagerly obedient","stubbornly resistant to authority",
      "extremely calm","deeply thoughtful"], 1),
    ("'Loquacious' means …?", "very talkative",
     ["very talkative","very quiet","very clever","very brave"], 0),
    ("'Equivocate' means …?", "use vague language to avoid commitment",
     ["speak very clearly","use vague language to avoid commitment",
      "argue aggressively","tell a direct lie"], 1),
    ("'Inimical' means …?", "hostile or harmful",
     ["very friendly","extremely rare","hostile or harmful","deeply mysterious"], 2),
    ("'Verisimilitude' means …?", "the appearance of being true or real",
     ["complete falsehood","the appearance of being true or real",
      "excessive length","poetic beauty"], 1),
    ("'Pellucid' means …?", "very clear and easy to understand",
     ["deeply confusing","very clear and easy to understand",
      "extremely bright","faintly glowing"], 1),
    ("'Enervate' means …?", "weaken or drain of energy",
     ["strengthen greatly","weaken or drain of energy",
      "excite intensely","confuse completely"], 1),
    ("'Solipsism' is the view that …?", "only one's own mind is certain to exist",
     ["only one's own mind is certain to exist",
      "the world is fundamentally good",
      "mathematics underlies all reality",
      "knowledge is impossible"], 0),
    ("'Schadenfreude' means …?", "pleasure from another's misfortune",
     ["regret about one's own actions","deep romantic longing",
      "pleasure from another's misfortune","sudden overwhelming fear"], 2),
    ("'Sesquipedalian' describes …?", "long or polysyllabic words",
     ["short simple words","long or polysyllabic words",
      "foreign loanwords","words with silent letters"], 1),
    ("'Tendentious' means …?", "promoting a particular cause or point of view",
     ["completely unbiased","promoting a particular cause or point of view",
      "easily misunderstood","deliberately vague"], 1),
    # Rhetoric / persuasion
    ("An 'ad hominem' argument attacks …?", "The person rather than their argument",
     ["The logic of the argument","The evidence presented",
      "The person rather than their argument","The conclusion only"], 2),
    ("'Anaphora' in rhetoric is …?",
     "Repetition of a word at the start of successive clauses",
     ["A logical contradiction",
      "Repetition of a word at the start of successive clauses",
      "An appeal to authority","A comparison using 'like' or 'as'"], 1),
    ("A 'false dichotomy' presents …?", "Only two options when more exist",
     ["Only two options when more exist","A valid either/or choice",
      "An appeal to emotion","A circular argument"], 0),
    ("'Ethos' in rhetoric refers to …?", "Appeal to the speaker's credibility",
     ["Appeal to emotion","Appeal to logic",
      "Appeal to the speaker's credibility","Appeal to popular opinion"], 2),
    ("'Post hoc' fallacy assumes …?", "Because B followed A, A caused B",
     ["Because B followed A, A caused B","Two events always coincide",
      "Popular belief equals truth","Authority always implies correctness"], 0),
    ("'Chiasmus' is …?", "Reversing the order of words in parallel clauses",
     ["Reversing the order of words in parallel clauses",
      "Omitting conjunctions for speed",
      "Repeating a word at clause ends",
      "An appeal to shared values"], 0),
    # Advanced grammar
    ("The subjunctive mood expresses …?", "Hypothetical or wished-for situations",
     ["Definite past actions","Hypothetical or wished-for situations",
      "Commands only","Questions only"], 1),
    ("Which uses the subjunctive correctly?", "I wish he were here.",
     ["I wish he was here.","I wish he were here.",
      "I wished he is here.","I wish he is here."], 1),
    ("An 'absolute phrase' …?", "Modifies the whole sentence, not just one word",
     ["Modifies the whole sentence, not just one word",
      "Is always a verb phrase",
      "Must contain a preposition","Replaces the subject"], 0),
    ("A 'dangling modifier' …?", "Describes a word not clearly stated in the sentence",
     ["Is always a prepositional phrase",
      "Describes a word not clearly stated in the sentence",
      "Connects two independent clauses","Adds an extra adjective"], 1),
    ("'Asyndeton' is …?", "Omission of conjunctions for effect",
     ["Overuse of conjunctions","Omission of conjunctions for effect",
      "Extreme exaggeration","Comparison without 'like' or 'as'"], 1),
    ("'Polysyndeton' is …?", "Deliberate repetition of conjunctions",
     ["Deliberate repetition of conjunctions","Omission of conjunctions",
      "A type of rhyme scheme","A clause without a verb"], 0),
    # Etymology
    ("Greek root 'philo-' means …?", "love",
     ["love","fear","write","light"], 0),
    ("Latin root 'bene-' means …?", "good/well",
     ["bad","around","good/well","against"], 2),
    ("Greek root 'anthropo-' means …?", "human",
     ["star","human","earth","water"], 1),
    ("Latin root 'fract-' means …?", "break",
     ["make","break","carry","hold"], 1),
    ("Greek root 'chron-' means …?", "time",
     ["time","colour","body","sound"], 0),
    ("Latin root 'luc-' means …?", "light",
     ["dark","sound","light","truth"], 2),
    # Literary analysis
    ("In 'Lord of the Flies' the conch symbolises …?",
     "Order and democratic authority",
     ["Violence and chaos","Order and democratic authority",
      "Fear of the unknown","Religious faith"], 1),
    ("'Stream of consciousness' depicts …?",
     "A character's continuous flow of thoughts",
     ["Events in strict chronological order",
      "Multiple narrators simultaneously",
      "A character's continuous flow of thoughts",
      "Dialogue between characters"], 2),
    ("An 'unreliable narrator' …?", "Cannot be fully trusted to tell the truth",
     ["Always tells the objective truth",
      "Cannot be fully trusted to tell the truth",
      "Narrates from a third-person view",
      "Only describes physical events"], 1),
    ("'In medias res' means starting …?", "In the middle of the action",
     ["At the very beginning","After the climax",
      "In the middle of the action","With a character's death"], 2),
    ("The 'Bildungsroman' genre focuses on …?",
     "The moral and psychological growth of a protagonist",
     ["A love story with a happy ending",
      "The moral and psychological growth of a protagonist",
      "A society's political revolution",
      "A detective solving a crime"], 1),
    ("'Epistolary' novels are told through …?", "Letters or documents",
     ["Letters or documents","Flashbacks only",
      "Multiple omniscient narrators","Dream sequences"], 0),
]


# ── Chapter 2: Science questions ─────────────────────────────────────────────

_SCI_QUESTIONS = [
    # Physics
    ("What is the SI unit of force?", "Newton",
     ["Joule", "Newton", "Pascal", "Watt"], 1),
    ("What is the speed of light in a vacuum (approx)?", "3 × 10^8 m/s",
     ["3 × 10^6 m/s", "3 × 10^8 m/s", "3 × 10^10 m/s", "3 × 10^4 m/s"], 1),
    ("E = mc² — what does 'c' represent?", "Speed of light",
     ["Speed of sound", "Speed of light", "Energy constant", "Mass constant"], 1),
    ("Which law states F = ma?", "Newton's Second Law",
     ["Newton's First Law", "Newton's Second Law", "Newton's Third Law", "Hooke's Law"], 1),
    ("What type of energy does a moving object have?", "Kinetic energy",
     ["Potential energy", "Thermal energy", "Kinetic energy", "Chemical energy"], 2),
    ("What unit measures electrical resistance?", "Ohm",
     ["Volt", "Ampere", "Ohm", "Watt"], 2),
    ("Which electromagnetic waves have the shortest wavelength?", "Gamma rays",
     ["Radio waves", "X-rays", "Ultraviolet", "Gamma rays"], 3),
    ("What is the formula for pressure?", "Force ÷ Area",
     ["Mass × Acceleration", "Force ÷ Area", "Work ÷ Time", "Force × Distance"], 1),
    ("What phenomenon causes a rainbow?", "Refraction and dispersion",
     ["Reflection only", "Refraction and dispersion", "Diffraction", "Interference"], 1),
    ("What is absolute zero in Celsius?", "-273 °C",
     ["-100 °C", "-200 °C", "-273 °C", "-373 °C"], 2),
    # Chemistry
    ("What is the chemical symbol for gold?", "Au",
     ["Go", "Gd", "Au", "Ag"], 2),
    ("How many elements are in the periodic table?", "118",
     ["92", "100", "108", "118"], 3),
    ("What is the chemical formula for water?", "H₂O",
     ["HO", "H₂O", "H₂O₂", "OH"], 1),
    ("What type of bond shares electrons?", "Covalent",
     ["Ionic", "Covalent", "Metallic", "Hydrogen"], 1),
    ("What is the pH of a neutral solution?", "7",
     ["0", "5", "7", "14"], 2),
    ("Which gas makes up about 78% of Earth's atmosphere?", "Nitrogen",
     ["Oxygen", "Nitrogen", "Carbon dioxide", "Argon"], 1),
    ("What is the atomic number of carbon?", "6",
     ["4", "6", "8", "12"], 1),
    ("What is produced when an acid reacts with a base?", "Salt and water",
     ["Gas only", "Salt and water", "Oxide and acid", "Metal and gas"], 1),
    ("Which element has the symbol 'Fe'?", "Iron",
     ["Fluorine", "Francium", "Iron", "Fermium"], 2),
    ("What is the process of a liquid turning to gas called?", "Evaporation",
     ["Condensation", "Sublimation", "Evaporation", "Freezing"], 2),
    # Biology
    ("What is the powerhouse of the cell?", "Mitochondria",
     ["Nucleus", "Ribosome", "Mitochondria", "Vacuole"], 2),
    ("What molecule carries genetic information?", "DNA",
     ["RNA", "DNA", "ATP", "Protein"], 1),
    ("What process do plants use to make food?", "Photosynthesis",
     ["Respiration", "Photosynthesis", "Transpiration", "Germination"], 1),
    ("How many chromosomes do humans normally have?", "46",
     ["23", "44", "46", "48"], 2),
    ("What is the function of red blood cells?", "Carry oxygen",
     ["Fight infection", "Carry oxygen", "Clot blood", "Produce hormones"], 1),
    ("Which organ filters blood in the human body?", "Kidney",
     ["Liver", "Kidney", "Spleen", "Pancreas"], 1),
    ("What is the largest organ of the human body?", "Skin",
     ["Liver", "Brain", "Lungs", "Skin"], 3),
    ("What is the process where cells divide?", "Mitosis",
     ["Meiosis", "Mitosis", "Osmosis", "Diffusion"], 1),
    ("What gas do plants absorb during photosynthesis?", "Carbon dioxide",
     ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], 2),
    ("Which part of a flower produces pollen?", "Anther",
     ["Stigma", "Ovary", "Anther", "Sepal"], 2),
    # Earth Science
    ("What is the most abundant gas in Earth's atmosphere?", "Nitrogen",
     ["Oxygen", "Nitrogen", "Carbon dioxide", "Water vapour"], 1),
    ("What type of rock is formed from cooled lava?", "Igneous",
     ["Sedimentary", "Metamorphic", "Igneous", "Limestone"], 2),
    ("How long does Earth take to orbit the Sun?", "365.25 days",
     ["24 hours", "28 days", "365.25 days", "100 days"], 2),
    ("What causes day and night on Earth?", "Earth's rotation on its axis",
     ["Moon's orbit", "Earth's orbit around Sun",
      "Earth's rotation on its axis", "Sun's rotation"], 2),
    ("What is the deepest ocean trench on Earth?", "Mariana Trench",
     ["Puerto Rico Trench", "Mariana Trench", "Tonga Trench", "Java Trench"], 1),
    ("What is the name of the supercontinent that existed 300M years ago?", "Pangaea",
     ["Gondwana", "Pangaea", "Laurasia", "Rodinia"], 1),
    ("What scale measures earthquake magnitude?", "Richter scale",
     ["Beaufort scale", "Mohs scale", "Richter scale", "Decibel scale"], 2),
    ("What is the thin solid outer layer of Earth called?", "Crust",
     ["Mantle", "Core", "Crust", "Lithosphere"], 2),
    ("What phenomenon causes tides on Earth?", "Moon's gravitational pull",
     ["Sun's heat", "Earth's rotation", "Moon's gravitational pull", "Wind patterns"], 2),
    ("Which layer of the atmosphere contains the ozone layer?", "Stratosphere",
     ["Troposphere", "Stratosphere", "Mesosphere", "Thermosphere"], 1),
]


# ── Chapter 3: History questions ──────────────────────────────────────────────

_HIST_QUESTIONS = [
    # Ancient history
    ("In what year did World War II end?", "1945",
     ["1943", "1944", "1945", "1946"], 2),
    ("Who was the first Roman Emperor?", "Augustus",
     ["Julius Caesar", "Augustus", "Nero", "Hadrian"], 1),
    ("Which ancient wonder was located in Alexandria?", "The Great Lighthouse",
     ["The Colossus", "Hanging Gardens", "The Great Lighthouse", "The Mausoleum"], 2),
    ("What civilisation built the pyramids of Giza?", "Ancient Egyptians",
     ["Ancient Romans", "Ancient Greeks", "Ancient Egyptians", "Mesopotamians"], 2),
    ("Who was the first emperor of unified China?", "Qin Shi Huang",
     ["Genghis Khan", "Kublai Khan", "Qin Shi Huang", "Emperor Yao"], 2),
    ("In which year did the French Revolution begin?", "1789",
     ["1776", "1789", "1799", "1804"], 1),
    ("Who wrote 'The Art of War'?", "Sun Tzu",
     ["Confucius", "Sun Tzu", "Lao Tzu", "Mencius"], 1),
    ("What was the name of the ship Charles Darwin sailed on?", "HMS Beagle",
     ["HMS Victory", "Mayflower", "HMS Beagle", "Santa Maria"], 2),
    ("Which empire was the largest contiguous land empire in history?", "Mongol Empire",
     ["Roman Empire", "British Empire", "Mongol Empire", "Ottoman Empire"], 2),
    ("In which year did the Berlin Wall fall?", "1989",
     ["1985", "1987", "1989", "1991"], 2),
    # Medieval & Renaissance
    ("What were the Crusades?", "Religious military campaigns to the Holy Land",
     ["Trade routes to Asia", "Religious military campaigns to the Holy Land",
      "Viking raids on Europe", "Roman border wars"], 1),
    ("Who was known as 'The Maid of Orléans'?", "Joan of Arc",
     ["Eleanor of Aquitaine", "Joan of Arc", "Mary Queen of Scots", "Isabella of Castile"], 1),
    ("When did the Black Death peak in Europe?", "1347–1351",
     ["1066–1100", "1200–1250", "1347–1351", "1500–1550"], 2),
    ("What language did Isaac Newton write his Principia in?", "Latin",
     ["English", "French", "German", "Latin"], 3),
    ("What invention did Gutenberg introduce to Europe?", "The printing press",
     ["The compass", "The printing press", "Gunpowder", "The telescope"], 1),
    ("Which king signed the Magna Carta in 1215?", "King John",
     ["King Richard I", "King Henry II", "King John", "King Edward I"], 2),
    ("Who painted the Sistine Chapel ceiling?", "Michelangelo",
     ["Leonardo da Vinci", "Raphael", "Michelangelo", "Botticelli"], 2),
    ("Which explorer first reached India by sea around Africa?", "Vasco da Gama",
     ["Christopher Columbus", "Ferdinand Magellan", "Vasco da Gama", "Amerigo Vespucci"], 2),
    # Modern history
    ("Who was the first President of the United States?", "George Washington",
     ["John Adams", "Thomas Jefferson", "George Washington", "Benjamin Franklin"], 2),
    ("What event triggered World War I?", "Assassination of Archduke Franz Ferdinand",
     ["Invasion of Poland", "Sinking of the Lusitania",
      "Assassination of Archduke Franz Ferdinand", "German invasion of France"], 2),
    ("What was the name of the Soviet Union's space programme that put the first human in space?", "Vostok",
     ["Soyuz", "Vostok", "Mir", "Salyut"], 1),
    ("Who was the first woman to win a Nobel Prize?", "Marie Curie",
     ["Florence Nightingale", "Marie Curie", "Rosalind Franklin", "Emmy Noether"], 1),
    ("In which year did India gain independence from Britain?", "1947",
     ["1945", "1947", "1950", "1952"], 1),
    ("Who led the Cuban Revolution?", "Fidel Castro",
     ["Che Guevara", "Fidel Castro", "Fulgencio Batista", "Raúl Castro"], 1),
    ("What was the Marshall Plan?", "US aid to rebuild post-war Europe",
     ["A Cold War military alliance", "US aid to rebuild post-war Europe",
      "A nuclear arms treaty", "A trade embargo on USSR"], 1),
    ("When did the Cold War officially end?", "1991",
     ["1985", "1989", "1991", "1993"], 2),
    ("What ship sank on its maiden voyage in 1912?", "RMS Titanic",
     ["SS Lusitania", "RMS Titanic", "SS Britannic", "SS Normandie"], 1),
    ("Who delivered the 'I Have a Dream' speech?", "Martin Luther King Jr.",
     ["Malcolm X", "Nelson Mandela", "Martin Luther King Jr.", "Thurgood Marshall"], 2),
    ("What was the Holocaust?", "The systematic genocide of Jewish people by the Nazis",
     ["A WWI battle", "The systematic genocide of Jewish people by the Nazis",
      "Soviet gulags in Siberia", "Atomic bombing of Japan"], 1),
    ("In which year was the United Nations founded?", "1945",
     ["1919", "1939", "1945", "1948"], 2),
    ("Who was the first person to walk on the Moon?", "Neil Armstrong",
     ["Buzz Aldrin", "Yuri Gagarin", "Neil Armstrong", "Alan Shepard"], 2),
    ("What was the name of Nelson Mandela's political party?", "African National Congress",
     ["Pan Africanist Congress", "African National Congress",
      "Inkatha Freedom Party", "Democratic Alliance"], 1),
    ("Which war was fought between North and South Korea (starting 1950)?", "Korean War",
     ["Vietnam War", "Korean War", "Cold War", "Gulf War"], 1),
    ("What does 'D-Day' refer to?", "Allied invasion of Normandy, June 6 1944",
     ["Germany's invasion of Poland", "Allied invasion of Normandy, June 6 1944",
      "Japan's attack on Pearl Harbor", "VE Day celebration"], 1),
    ("Who was the first female Prime Minister of the UK?", "Margaret Thatcher",
     ["Teresa May", "Margaret Thatcher", "Barbara Castle", "Shirley Williams"], 1),
    ("The Silk Road connected China to which region?", "Mediterranean / Middle East",
     ["Africa only", "Mediterranean / Middle East", "South America", "Australia"], 1),
    ("What year did the Soviet Union launch Sputnik 1?", "1957",
     ["1955", "1957", "1961", "1963"], 1),
    ("Who was known as 'The Iron Chancellor' of Germany?", "Otto von Bismarck",
     ["Frederick the Great", "Otto von Bismarck", "Kaiser Wilhelm II", "Hindenburg"], 1),
    ("The Rwandan Genocide occurred in which year?", "1994",
     ["1990", "1992", "1994", "1996"], 2),
]


# ── Chapter 4: Geography questions ───────────────────────────────────────────

_GEO_QUESTIONS = [
    # Capitals
    ("What is the capital of Australia?", "Canberra",
     ["Sydney", "Melbourne", "Canberra", "Brisbane"], 2),
    ("What is the capital of Canada?", "Ottawa",
     ["Toronto", "Montreal", "Vancouver", "Ottawa"], 3),
    ("What is the capital of Brazil?", "Brasília",
     ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador"], 2),
    ("What is the capital of Japan?", "Tokyo",
     ["Osaka", "Kyoto", "Hiroshima", "Tokyo"], 3),
    ("What is the capital of South Africa?", "Pretoria",
     ["Cape Town", "Johannesburg", "Pretoria", "Durban"], 2),
    ("What is the capital of Argentina?", "Buenos Aires",
     ["Montevideo", "Santiago", "Buenos Aires", "Lima"], 2),
    ("What is the capital of Egypt?", "Cairo",
     ["Alexandria", "Luxor", "Cairo", "Giza"], 2),
    ("What is the capital of India?", "New Delhi",
     ["Mumbai", "Kolkata", "New Delhi", "Chennai"], 2),
    ("What is the capital of Russia?", "Moscow",
     ["St Petersburg", "Kiev", "Moscow", "Novosibirsk"], 2),
    ("What is the capital of Germany?", "Berlin",
     ["Munich", "Hamburg", "Frankfurt", "Berlin"], 3),
    # Rivers & Mountains
    ("What is the longest river in the world?", "Nile",
     ["Amazon", "Nile", "Yangtze", "Mississippi"], 1),
    ("What is the highest mountain in the world?", "Mount Everest",
     ["K2", "Mount Everest", "Kangchenjunga", "Makalu"], 1),
    ("In which country is the Amazon rainforest primarily located?", "Brazil",
     ["Colombia", "Peru", "Brazil", "Venezuela"], 2),
    ("What is the largest desert in the world?", "Antarctic Desert",
     ["Sahara", "Arabian Desert", "Gobi Desert", "Antarctic Desert"], 3),
    ("Which river flows through Egypt?", "Nile",
     ["Congo", "Niger", "Nile", "Zambezi"], 2),
    ("What is the longest mountain range in the world?", "Andes",
     ["Himalayas", "Rockies", "Andes", "Alps"], 2),
    ("What is the deepest lake in the world?", "Lake Baikal",
     ["Lake Superior", "Caspian Sea", "Lake Baikal", "Lake Tanganyika"], 2),
    ("What is the largest ocean on Earth?", "Pacific Ocean",
     ["Atlantic Ocean", "Indian Ocean", "Pacific Ocean", "Arctic Ocean"], 2),
    # Countries & Continents
    ("How many continents are there on Earth?", "7",
     ["5", "6", "7", "8"], 2),
    ("What is the largest country in the world by area?", "Russia",
     ["China", "Canada", "USA", "Russia"], 3),
    ("What is the smallest country in the world?", "Vatican City",
     ["Monaco", "San Marino", "Liechtenstein", "Vatican City"], 3),
    ("Which continent has the most countries?", "Africa",
     ["Asia", "Europe", "Africa", "Americas"], 2),
    ("Which is the most populous country in the world?", "India",
     ["China", "India", "USA", "Indonesia"], 1),
    ("What is the national language of Brazil?", "Portuguese",
     ["Spanish", "Portuguese", "English", "French"], 1),
    ("Which country has the most natural lakes?", "Canada",
     ["Russia", "Finland", "USA", "Canada"], 3),
    ("What country does the Sahara desert NOT pass through?", "Kenya",
     ["Algeria", "Libya", "Mali", "Kenya"], 3),
    ("Which ocean lies between Europe and North America?", "Atlantic Ocean",
     ["Pacific Ocean", "Indian Ocean", "Atlantic Ocean", "Arctic Ocean"], 2),
    ("In which continent is the Sahara Desert?", "Africa",
     ["Asia", "Australia", "Africa", "South America"], 2),
    ("What is the capital of China?", "Beijing",
     ["Shanghai", "Guangzhou", "Hong Kong", "Beijing"], 3),
    # Human Geography
    ("What is the most spoken language in the world (by native speakers)?", "Mandarin Chinese",
     ["English", "Spanish", "Mandarin Chinese", "Hindi"], 2),
    ("What is the International Date Line closest to?", "180° longitude",
     ["0° longitude", "90° longitude", "180° longitude", "45° longitude"], 2),
    ("What is the term for the imaginary line dividing Earth into North/South halves?", "Equator",
     ["Prime Meridian", "Tropic of Cancer", "Equator", "Arctic Circle"], 2),
    ("Which country has the most time zones?", "France",
     ["Russia", "USA", "France", "China"], 2),
    ("What is the name of the strait between Spain and Morocco?", "Strait of Gibraltar",
     ["Strait of Messina", "Strait of Gibraltar", "Strait of Hormuz", "Strait of Malacca"], 1),
    ("What is the world's largest island?", "Greenland",
     ["Australia", "Greenland", "Borneo", "Madagascar"], 1),
    ("What country has the most pyramids in the world?", "Sudan",
     ["Egypt", "Mexico", "Sudan", "Peru"], 2),
    ("Which country is both in Europe and Asia?", "Russia",
     ["Turkey", "Kazakhstan", "Russia", "Azerbaijan"], 2),
    ("What is the name of the world's largest coral reef system?", "Great Barrier Reef",
     ["Belize Barrier Reef", "Great Barrier Reef", "Mesoamerican Reef", "Red Sea Reef"], 1),
    ("What is the capital of Turkey?", "Ankara",
     ["Istanbul", "Izmir", "Ankara", "Bursa"], 2),
    ("The Nile Delta empties into which body of water?", "Mediterranean Sea",
     ["Red Sea", "Mediterranean Sea", "Arabian Sea", "Atlantic Ocean"], 1),
]


# ── Chapter 5: Space & Technology questions ───────────────────────────────────

_SPACE_QUESTIONS = [
    # Solar System
    ("How many planets are in our solar system?", "8",
     ["7", "8", "9", "10"], 1),
    ("What is the largest planet in our solar system?", "Jupiter",
     ["Saturn", "Jupiter", "Neptune", "Uranus"], 1),
    ("What is the smallest planet in our solar system?", "Mercury",
     ["Mars", "Mercury", "Venus", "Pluto"], 1),
    ("How far is the Moon from Earth (approximately)?", "384,400 km",
     ["38,400 km", "384,400 km", "3,844,000 km", "38,440 km"], 1),
    ("What is the name of Earth's natural satellite?", "The Moon",
     ["Europa", "Titan", "The Moon", "Phobos"], 2),
    ("How many moons does Mars have?", "2",
     ["0", "1", "2", "4"], 2),
    ("What is the Great Red Spot on Jupiter?", "A massive storm",
     ["A volcano", "A massive storm", "A crater", "An ocean"], 1),
    ("Which planet has the most moons?", "Saturn",
     ["Jupiter", "Saturn", "Uranus", "Neptune"], 1),
    ("What is the Asteroid Belt located between?", "Mars and Jupiter",
     ["Earth and Mars", "Mars and Jupiter", "Jupiter and Saturn", "Saturn and Uranus"], 1),
    ("How long does light from the Sun take to reach Earth?", "About 8 minutes",
     ["About 1 second", "About 8 minutes", "About 1 hour", "About 8 hours"], 1),
    # Stars & Universe
    ("What type of star is our Sun?", "Yellow dwarf",
     ["Red giant", "White dwarf", "Yellow dwarf", "Neutron star"], 2),
    ("What is a light-year?", "The distance light travels in one year",
     ["How long light lasts", "The speed of light", "The distance light travels in one year", "A unit of time"], 2),
    ("What is the name of our galaxy?", "Milky Way",
     ["Andromeda", "Milky Way", "Triangulum", "Centaurus A"], 1),
    ("What is a black hole?", "A region where gravity is so strong nothing can escape",
     ["A dark planet", "An exploded star", "A region where gravity is so strong nothing can escape", "A wormhole"], 2),
    ("What is a supernova?", "The explosion of a massive star",
     ["A new star forming", "The explosion of a massive star", "A comet impact", "A galaxy collision"], 1),
    ("What is the Big Bang theory?", "The universe began from a hot, dense state ~13.8 billion years ago",
     ["The universe is infinite and unchanging", "The universe began from a hot, dense state ~13.8 billion years ago",
      "Stars explode to create new universes", "The Milky Way was formed by a collision"], 1),
    ("What is a neutron star?", "The collapsed core of a massive star",
     ["A young star like the Sun", "The collapsed core of a massive star",
      "A star without a nucleus", "A failed star that never ignited"], 1),
    ("What are pulsars?", "Rapidly rotating neutron stars emitting radio waves",
     ["Black holes that pulse", "Rapidly rotating neutron stars emitting radio waves",
      "Bright variable stars", "Dwarf galaxies"], 1),
    ("What is the Hubble Space Telescope named after?", "Edwin Hubble",
     ["George Hubble", "Edwin Hubble", "Walter Hubble", "James Hubble"], 1),
    ("What is the approximate age of the universe?", "13.8 billion years",
     ["4.5 billion years", "10 billion years", "13.8 billion years", "20 billion years"], 2),
    # Space Exploration
    ("Who was the first human in space?", "Yuri Gagarin",
     ["Neil Armstrong", "Alan Shepard", "Yuri Gagarin", "Buzz Aldrin"], 2),
    ("In which year did humans first land on the Moon?", "1969",
     ["1965", "1967", "1969", "1971"], 2),
    ("What is the International Space Station?", "A habitable satellite orbiting Earth",
     ["A lunar base", "A habitable satellite orbiting Earth",
      "A space telescope", "A Mars rover"], 1),
    ("What is the name of NASA's most famous Mars rover (launched 2012)?", "Curiosity",
     ["Opportunity", "Spirit", "Curiosity", "Perseverance"], 2),
    ("What was the name of the first artificial satellite launched (1957)?", "Sputnik 1",
     ["Explorer 1", "Sputnik 1", "Vanguard 1", "Luna 1"], 1),
    ("Which spacecraft first left the solar system?", "Voyager 1",
     ["Pioneer 10", "Voyager 1", "New Horizons", "Cassini"], 1),
    ("What does NASA stand for?", "National Aeronautics and Space Administration",
     ["National Air and Space Agency", "National Aeronautics and Space Administration",
      "North American Space Association", "National Astronomy and Satellite Administration"], 1),
    ("What is the Hubble constant?", "The rate of expansion of the universe",
     ["The gravitational constant", "The speed of light in a vacuum",
      "The rate of expansion of the universe", "The age of the universe"], 2),
    ("What phenomenon was confirmed by LIGO in 2015?", "Gravitational waves",
     ["Black holes exist", "Dark matter particles", "Gravitational waves", "Parallel universes"], 2),
    # Technology
    ("Who invented the World Wide Web?", "Tim Berners-Lee",
     ["Bill Gates", "Steve Jobs", "Tim Berners-Lee", "Vint Cerf"], 2),
    ("What does 'AI' stand for?", "Artificial Intelligence",
     ["Automated Interface", "Artificial Intelligence", "Advanced Internet", "Algorithmic Innovation"], 1),
    ("What is Moore's Law?", "Transistor count on chips doubles roughly every two years",
     ["Internet speed doubles every year",
      "Transistor count on chips doubles roughly every two years",
      "Computer costs halve every decade",
      "Processing speed triples every five years"], 1),
    ("What does 'DNA computing' use?", "DNA molecules to perform calculations",
     ["Computer chips shaped like DNA", "DNA molecules to perform calculations",
      "Biological neural networks", "Quantum entanglement"], 1),
    ("Which programming language was created by Guido van Rossum?", "Python",
     ["Java", "C++", "Python", "Ruby"], 2),
    ("What is quantum computing's key advantage?", "Can process many states simultaneously",
     ["Faster clock speed", "Smaller physical size",
      "Can process many states simultaneously", "Uses less electricity"], 2),
    ("What is the binary representation of the decimal number 10?", "1010",
     ["1001", "1010", "1100", "1011"], 1),
    ("What does 'GPU' stand for?", "Graphics Processing Unit",
     ["General Processing Unit", "Graphics Processing Unit",
      "Global Processing Utility", "Graphical Program Utility"], 1),
    ("What year was the first iPhone released?", "2007",
     ["2005", "2007", "2009", "2011"], 1),
    ("What is machine learning?", "Systems that learn from data without explicit programming",
     ["Robots that repair themselves", "Systems that learn from data without explicit programming",
      "AI that mimics human movement", "Computers that design other computers"], 1),
]


def _make_english_question(level: int) -> tuple:
    """Pick from easy/medium/hard bank based on level."""
    if level <= 6:
        bank = _ENG_EASY
    elif level <= 13:
        bank = random.choices([_ENG_EASY, _ENG_MEDIUM, _ENG_HARD],
                               weights=[1, 3, 1])[0]
    else:
        bank = random.choices([_ENG_MEDIUM, _ENG_HARD, _ENG_HARD],
                               weights=[1, 3, 2])[0]
    q = random.choice(bank)
    return (q[0], q[1], list(q[2]), q[3])


# ── Quiz manager ──────────────────────────────────────────────────────────────

class QuizManager:
    CHOICE_LABELS = ['A', 'B', 'C', 'D']
    TIME_LIMIT    = 22 * 60   # 22 seconds — harder questions deserve more time
    REVEAL_FRAMES = 110

    _space_bg: pygame.Surface | None = None

    def __init__(self, game):
        self.game        = game
        self._question   = ''
        self._answer     = ''
        self._choices: list[str] = []
        self._correct_idx= 0
        self._timer      = 0
        self._answered   = False
        self._chosen_idx = -1
        self._result     = None
        self._reveal_t   = 0
        self._subject    = 'math'
        self._streak     = 0
        self._hover_idx  = -1
        self._anim_t     = 0
        self._btn_rects: list[pygame.Rect] = []
        self._fonts: dict[str, pygame.font.Font] = {}

    def _font(self, key: str) -> pygame.font.Font:
        if key not in self._fonts:
            sizes = {'xl': 48, 'lg': 32, 'md': 24, 'sm': 18, 'xs': 14}
            self._fonts[key] = pygame.font.SysFont('consolas', sizes[key], bold=True)
        return self._fonts[key]

    def start(self, level: int):
        chapter = get_chapter(level)

        # Each chapter has its own subject pool
        _CHAPTER_SUBJECTS = {
            1: ['math', 'math', 'english'],
            2: ['science', 'science', 'math'],
            3: ['history', 'history', 'english'],
            4: ['geography', 'geography', 'science'],
            5: ['space', 'space', 'history'],
        }
        pool = _CHAPTER_SUBJECTS.get(chapter, ['math', 'english'])
        self._subject = random.choice(pool)

        self._timer      = 0
        self._answered   = False
        self._chosen_idx = -1
        self._result     = None
        self._reveal_t   = 0
        self._anim_t     = 0
        self._hover_idx  = -1

        if self._subject == 'math':
            self._question, self._answer, self._choices, self._correct_idx = \
                _make_math_question(level)
        elif self._subject == 'english':
            self._question, self._answer, self._choices, self._correct_idx = \
                _make_english_question(level)
        elif self._subject == 'science':
            q = random.choice(_SCI_QUESTIONS)
            self._question, self._answer, self._choices, self._correct_idx = \
                q[0], q[1], list(q[2]), q[3]
        elif self._subject == 'history':
            q = random.choice(_HIST_QUESTIONS)
            self._question, self._answer, self._choices, self._correct_idx = \
                q[0], q[1], list(q[2]), q[3]
        elif self._subject == 'geography':
            q = random.choice(_GEO_QUESTIONS)
            self._question, self._answer, self._choices, self._correct_idx = \
                q[0], q[1], list(q[2]), q[3]
        else:  # space
            q = random.choice(_SPACE_QUESTIONS)
            self._question, self._answer, self._choices, self._correct_idx = \
                q[0], q[1], list(q[2]), q[3]

        # Build static background once
        if QuizManager._space_bg is None:
            QuizManager._space_bg = _make_space_bg()

    @property
    def done(self) -> bool:
        return self._result is not None and self._reveal_t <= 0

    def handle_event(self, event) -> str | None:
        if self._result is not None:
            return None
        if event.type == pygame.KEYDOWN:
            mapping = {pygame.K_a:0, pygame.K_b:1, pygame.K_c:2, pygame.K_d:3,
                       pygame.K_1:0, pygame.K_2:1, pygame.K_3:2, pygame.K_4:3}
            if event.key in mapping:
                self._submit(mapping[event.key])
            elif event.key == pygame.K_ESCAPE:
                self._result  = 'timeout'
                self._reveal_t= self.REVEAL_FRAMES
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self._hover_idx = -1
            for i, r in enumerate(self._btn_rects):
                if r.collidepoint(mx, my):
                    self._hover_idx = i
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self._btn_rects):
                if r.collidepoint(mx, my):
                    self._submit(i); break
        if event.type == pygame.FINGERDOWN:
            from settings import SCREEN_WIDTH, SCREEN_HEIGHT
            mx = int(event.x * SCREEN_WIDTH)
            my = int(event.y * SCREEN_HEIGHT)
            for i, r in enumerate(self._btn_rects):
                if r.collidepoint(mx, my):
                    self._submit(i); break
        return None

    def _submit(self, idx: int):
        if self._answered:
            return
        self._answered   = True
        self._chosen_idx = idx
        if idx == self._correct_idx:
            self._result = 'correct'
            self._streak += 1
            bonus = 200 + self.game.current_level * 20 + self._streak * 35
            self.game.player.coins += bonus
            self.game.save.add_coins(bonus)
            self.game.ui.show_message(
                f'+{bonus} COINS', SCREEN_WIDTH//2, 560, GOLD, 'lg')
            self.game.particles.stars_burst(SCREEN_WIDTH//2, 420, 50)
            self.game.screen_flash((50, 220, 80), 70)
            self.game.audio.play('coin')
        else:
            self._result = 'wrong'
            self._streak = 0
            self.game.screen_flash((200, 30, 30), 60)
        self._reveal_t = self.REVEAL_FRAMES

    def update(self):
        self._anim_t += 1
        if self._result is None:
            self._timer += 1
            if self._timer >= self.TIME_LIMIT:
                self._result  = 'timeout'
                self._streak  = 0
                self._reveal_t= self.REVEAL_FRAMES
        elif self._reveal_t > 0:
            self._reveal_t -= 1

    def draw(self, surface: pygame.Surface):
        # ── Static deep-space background ──────────────────────────────────────
        if QuizManager._space_bg:
            surface.blit(QuizManager._space_bg, (0, 0))
        else:
            surface.fill((5, 5, 25))

        # Corner vignette to focus the eye on the panel
        vgn = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for cx, cy in [(0,0),(SCREEN_WIDTH,0),(0,SCREEN_HEIGHT),(SCREEN_WIDTH,SCREEN_HEIGHT)]:
            for rad in range(330, 0, -18):
                a = int(85 * (1 - rad/330)**2)
                pygame.draw.circle(vgn, (0, 0, 0, a), (cx, cy), rad)
        surface.blit(vgn, (0, 0))

        # ── Animated corner brackets ──────────────────────────────────────────
        t = self._anim_t
        for col, pts in self._border_pts(t):
            c = (int(col[0]),int(col[1]),int(col[2]))
            pygame.draw.lines(surface, c, False, pts, 2)

        # ── Subject badge ─────────────────────────────────────────────────────
        _SUBJ_MAP = {
            'math':      ((50, 180, 255),  '  MATHEMATICS  '),
            'english':   ((80, 220, 100),  '  ENGLISH  '),
            'science':   ((0,  220, 200),  '  SCIENCE  '),
            'history':   ((255, 160, 50),  '  HISTORY  '),
            'geography': ((100, 220, 80),  '  GEOGRAPHY  '),
            'space':     ((180, 80, 255),  '  SPACE & TECH  '),
        }
        subj_col, subj_text = _SUBJ_MAP.get(self._subject, ((50, 180, 255), '  QUIZ  '))
        sb        = self._font('lg').render(subj_text, True, (8, 8, 28))
        sb_rect   = sb.get_rect(centerx=SCREEN_WIDTH//2, top=34)
        pygame.draw.rect(surface, subj_col, sb_rect.inflate(22,12), border_radius=9)
        glow_s = pygame.Surface((sb_rect.width+48, sb_rect.height+36), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_s, (*subj_col, 50), glow_s.get_rect())
        surface.blit(glow_s, glow_s.get_rect(center=sb_rect.inflate(22,12).center))
        surface.blit(sb, sb_rect)

        # Difficulty stars
        lvl  = self.game.current_level
        tier = min(7, (lvl-1)//3)
        diff_str = '★' * (tier+1) + '☆' * (7-tier)
        diff_t   = self._font('xs').render(f'Difficulty: {diff_str}', True, GOLD)
        surface.blit(diff_t, diff_t.get_rect(centerx=SCREEN_WIDTH//2, top=sb_rect.bottom+6))

        # Streak
        if self._streak >= 2:
            skt = self._font('sm').render(
                f'🔥 {self._streak} CORRECT IN A ROW!', True, (255,180,50))
            surface.blit(skt, skt.get_rect(centerx=SCREEN_WIDTH//2, top=sb_rect.bottom+24))

        # ── Timer ─────────────────────────────────────────────────────────────
        if self._result is None:
            ratio = 1 - self._timer / self.TIME_LIMIT
            self._draw_timer(surface, SCREEN_WIDTH-80, 80, 45, ratio)
        else:
            icon = '✓' if self._result=='correct' else ('✗' if self._result=='wrong' else '⏱')
            col  = (60,220,80) if self._result=='correct' else (220,60,60)
            itxt = self._font('xl').render(icon, True, col)
            surface.blit(itxt, itxt.get_rect(center=(SCREEN_WIDTH-80,80)))

        secs = max(0, (self.TIME_LIMIT - self._timer)//60 + 1)
        stxt = self._font('xs').render(f'{secs}s', True, (180,180,220))
        surface.blit(stxt, stxt.get_rect(center=(SCREEN_WIDTH-80, 134)))

        # ── Question box ──────────────────────────────────────────────────────
        qbox = pygame.Rect(68, 118, SCREEN_WIDTH-136, 150)
        qs   = pygame.Surface((qbox.width, qbox.height), pygame.SRCALPHA)
        qs.fill((10, 14, 44, 215))
        surface.blit(qs, qbox.topleft)
        pygame.draw.rect(surface, subj_col, qbox, 2, border_radius=12)
        pygame.draw.line(surface, subj_col,
                         (qbox.x+16, qbox.y+1),(qbox.right-16, qbox.y+1), 1)
        self._draw_wrapped(surface, self._question, qbox.inflate(-30,-22), 'lg', (240,240,255))

        # ── Answer choices ────────────────────────────────────────────────────
        bw  = (SCREEN_WIDTH - 180) // 2
        bh  = 72; gap = 14
        grid_top  = qbox.bottom + 24
        grid_left = 90

        self._btn_rects = []
        for i, choice in enumerate(self._choices):
            col_ = i % 2; row = i // 2
            bx = grid_left + col_*(bw+gap)
            by = grid_top  + row *(bh+gap)
            r  = pygame.Rect(bx, by, bw, bh)
            self._btn_rects.append(r)

            if self._result is not None:
                if i == self._correct_idx:
                    bg = (25,120,45); border = (70,245,95)
                elif i == self._chosen_idx and self._chosen_idx != self._correct_idx:
                    bg = (115,25,25); border = (255,70,70)
                else:
                    bg = (12,16,45); border = (45,45,75)
            elif i == self._hover_idx:
                bg = (38,58,130); border = subj_col
            else:
                bg = (16,24,72); border = (55,75,155)

            cs = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            cs.fill((*bg, 210)); surface.blit(cs, r.topleft)
            pygame.draw.rect(surface, border, r, 2, border_radius=10)
            sh = pygame.Surface((r.width-4, r.height//3), pygame.SRCALPHA)
            sh.fill((255,255,255,12)); surface.blit(sh, (r.x+2, r.y+2))

            label = self.CHOICE_LABELS[i]
            lsurf = self._font('md').render(label, True, border)
            surface.blit(lsurf, lsurf.get_rect(centery=r.centery, left=r.left+14))

            ctxt  = self._font('md').render(choice, True, (220,220,255))
            max_w = bw - 62
            if ctxt.get_width() > max_w:
                scale = max_w / ctxt.get_width()
                ctxt  = pygame.transform.smoothscale(
                    ctxt, (int(ctxt.get_width()*scale), int(ctxt.get_height()*scale)))
            surface.blit(ctxt, ctxt.get_rect(centery=r.centery, left=r.left+48))

        # ── Result ────────────────────────────────────────────────────────────
        ry = grid_top + 2*(bh+gap) + 48
        if self._result == 'correct':
            msgs = ['Brilliant!','Excellent!','Perfect!','Outstanding!','Genius!','Amazing!']
            msg  = random.choice(msgs) if self._reveal_t == self.REVEAL_FRAMES else msgs[0]
            self._draw_centered_text(surface, msg, (60,240,90), 'lg', SCREEN_WIDTH//2, ry)
        elif self._result == 'wrong':
            self._draw_centered_text(surface, f'Correct answer: {self._answer}',
                                     (255,120,80), 'md', SCREEN_WIDTH//2, ry)
        elif self._result == 'timeout':
            self._draw_centered_text(surface, f'Time up!  Answer: {self._answer}',
                                     (255,180,50), 'md', SCREEN_WIDTH//2, ry)

        # ── Hint ──────────────────────────────────────────────────────────────
        hint = 'Press A / B / C / D  or  click  ·  ESC = skip'
        htxt = self._font('xs').render(hint, True, (90,95,138))
        surface.blit(htxt, htxt.get_rect(centerx=SCREEN_WIDTH//2, bottom=SCREEN_HEIGHT-12))

    # ── Drawing helpers ───────────────────────────────────────────────────────
    def _draw_timer(self, surface, cx, cy, r, ratio):
        fill_col = (60,220,80) if ratio>0.45 else (255,180,0) if ratio>0.22 else (255,55,55)
        pygame.draw.circle(surface, (25,25,55), (cx,cy), r, 6)
        if ratio > 0:
            rect  = pygame.Rect(cx-r, cy-r, r*2, r*2)
            start = -math.pi/2
            end   = start + math.tau * ratio
            pygame.draw.arc(surface, fill_col, rect, start, end, 6)

    def _draw_wrapped(self, surface, text, rect, font_key, color):
        font  = self._font(font_key)
        words = text.split(); lines = []; line = ''
        for w in words:
            test = line + (' ' if line else '') + w
            if font.size(test)[0] <= rect.width: line = test
            else:
                if line: lines.append(line)
                line = w
        if line: lines.append(line)
        lh    = font.get_height() + 4
        total = lh * len(lines)
        y     = rect.centery - total // 2
        for l in lines:
            s = font.render(l, True, color)
            surface.blit(s, s.get_rect(centerx=rect.centerx, top=y))
            y += lh

    def _draw_centered_text(self, surface, text, color, font_key, cx, cy):
        s = self._font(font_key).render(text, True, color)
        surface.blit(s, s.get_rect(center=(cx, cy)))

    def _border_pts(self, t):
        m = 28; w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        a = int(140 + 80*math.sin(t*0.05))
        col = (50, 100, 255, a); size = 64
        corners = [
            [(m,m+size),(m,m),(m+size,m)],
            [(w-m-size,m),(w-m,m),(w-m,m+size)],
            [(m,h-m-size),(m,h-m),(m+size,h-m)],
            [(w-m-size,h-m),(w-m,h-m),(w-m,h-m-size)],
        ]
        return [(col, pts) for pts in corners]
