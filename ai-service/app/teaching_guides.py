"""Original discovery activities informed by Underhill's published teaching work.

These are teaching examples, separate from acoustic predictions. Artwork poses
are illustrative values, not coordinates inferred from a learner's audio.
"""
from .sound_catalog import VOWEL_FEATURES, CONSONANT_FEATURES, PRIMARY_TARGETS, MOVING_VOWELS, PROMPTS, R_SEQUENCES

UNDERHILL_SOURCES = {
    "method": {"label": "Adrian Underhill: physical pronunciation", "url": "https://adrianunderhill.com/2012/05/29/making-pronunciation-physical-finding-the-%E2%80%98muscle-buttons%E2%80%99/"},
    "vowels": {"label": "Underhill: discovering vowel movement", "url": "https://adrianpronchart.wordpress.com/2013/08/31/the-story-of-sounds-episode-17-discovering-i-and-%CA%8A/"},
    "front_vowel": {"label": "Underhill: noticing tongue movement", "url": "https://adrianpronchart.wordpress.com/2013/05/30/the-story-of-sounds-episode-16-using-i%CB%90-and-u%CB%90-to-locate-the-tongue-button/"},
    "lip_rounding": {"label": "Underhill: noticing lip movement", "url": "https://adrianpronchart.wordpress.com/2013/05/01/the-story-of-sounds-episode-15-starting-from-i%CB%90-and-u%CB%90/"},
    "open_vowel": {"label": "Underhill: discovering the bad vowel", "url": "https://adrianpronchart.wordpress.com/2015/10/06/the-story-of-sounds-episode-26-discovering-the-vowel-ae/"},
    "jaw": {"label": "Underhill: exploring the bed vowel", "url": "https://adrianunderhill.com/2014/04/15/the-story-of-sounds-episode-21-discovering-the-vowel-e/"},
    "friction": {"label": "Underhill: moving between s and sh", "url": "https://adrianpronchart.wordpress.com/2011/10/30/the-story-of-sounds-episode-6/"},
    "stops": {"label": "Underhill: exploring p and b", "url": "https://adrianpronchart.wordpress.com/2012/05/18/working-with-the-confusion-between-p-and-b/"},
    "videos": {"label": "American pronunciation demonstrations", "url": "https://soundsamerican.net/"},
    "method_videos": {"label": "Underhill physical teaching method", "url": "https://www.macmillanenglish.com/us/blog-resources/articles/article/pronunciation-skills-videos"},
    "american": {"label":"American sounds and r-colored vowels", "url":"https://opentext.ku.edu/amenglishpronunciation/chapter/chapter-1/"},
}
CONTROLS = [
    {"id": "lips", "label": "Lips", "hint": "Notice rounding or gentle spreading."},
    {"id": "tongue", "label": "Tongue", "hint": "Notice a small forward or backward change."},
    {"id": "jaw", "label": "Jaw", "hint": "Notice a comfortable opening or closing."},
    {"id": "voice", "label": "Voice", "hint": "Feel vibration gently at your throat."},
]


def lesson(anchor, word, anchor_word, move, steps, feel, controls, source, mode="glide", note=""):
    return {"anchor_phone": anchor, "word": word, "anchor_word": anchor_word,
            "move": move, "mode": mode,
            "steps": [{"title": title, "text": text, "focus": focus, "progress": progress}
                      for title, text, focus, progress in steps],
            "feel": feel, "controls": dict(zip([c["id"] for c in CONTROLS], controls)),
            "source": UNDERHILL_SOURCES[source], "note": note}


LESSONS = {
    "iː": lesson("ɪ", "seat", "sit", "A small lift and forward move", [
        ("Find", "Start with the vowel in sit. Notice its relaxed shape.", "tongue", 0),
        ("Move", "Bring the tongue a little higher and forward; keep the lips unrounded.", "tongue", 50),
        ("Feel", "Use a mirror: let the lips widen gently, without forcing a grin.", "lips", 100),
        ("Use", "Try seat, then sit. Notice the vowel quality as well as its timing.", "voice", 100)],
        "What small movement changed the vowel?", ["Gently wide, not tightly stretched.", "High and toward the front.", "A small, comfortable opening.", "Keep a gentle voice vibration."], "front_vowel"),
    "ɪ": lesson("iː", "sit", "seat", "Relax a little toward the centre", [
        ("Find", "Begin with the vowel in seat.", "lips", 0),
        ("Move", "Ease the lips and let the tongue move slightly back and down.", "tongue", 50),
        ("Feel", "Notice the change in sound as the mouth relaxes.", "jaw", 100),
        ("Use", "Try sit, then seat. Keep the vowel qualities distinct.", "voice", 100)],
        "Does the sound change when the tongue and lips relax?", ["Relax the spread; no rounding needed.", "A little lower and farther back than seat.", "Let it open a little.", "Keep the voice on."], "vowels",
        note="The model does not measure vowel length; shortening a sound alone does not establish this contrast."),
    "ɛ": lesson("æ", "bed", "bad", "Close the jaw a little", [
        ("Find", "Begin with the open vowel in bad.", "jaw", 0),
        ("Move", "Bring the jaw and tongue up a little, keeping the tongue toward the front.", "jaw", 50),
        ("Feel", "Rest a hand lightly under the chin to notice the smaller opening.", "jaw", 100),
        ("Use", "Try bad, bed, bad. Listen for the change as the jaw moves.", "voice", 100)],
        "Can you change the vowel with a small jaw movement?", ["Keep them unrounded.", "Stay toward the front.", "Less open than bad.", "Keep a gentle voice."], "jaw",
        note="Many British teaching materials write the bed vowel /e/. This demo uses /ɛ/; accent and notation vary."),
    "æ": lesson("ɛ", "bad", "bed", "Open the jaw a little more", [
        ("Find", "Start with the vowel in bed.", "jaw", 0),
        ("Move", "Let the jaw and tongue drop a little, keeping the tongue toward the front.", "jaw", 50),
        ("Feel", "Watch the opening in a mirror; keep it comfortable.", "lips", 100),
        ("Use", "Try bed, bad, bed. Notice which opening produces each vowel.", "voice", 100)],
        "Can you feel the jaw opening without adding tension?", ["Unrounded and comfortable.", "Low toward the front.", "More open than bed.", "Keep the voice on."], "open_vowel"),
    "uː": lesson("iː", "food", "seat", "Explore gentle lip rounding", [
        ("Find", "Begin with the vowel in seat and notice the lips.", "lips", 0),
        ("Move", "Round the lips gently; explore how the tongue shifts as the sound changes.", "lips", 50),
        ("Feel", "Use a mirror to notice rounding and a small forward lip movement.", "tongue", 100),
        ("Use", "Try food. Find a comfortable rounded vowel.", "voice", 100)],
        "What changes when you round your lips?", ["Gently rounded, without strain.", "Explore a shift from the front-vowel position.", "Keep a small comfortable opening.", "Keep a gentle voice vibration."], "lip_rounding",
        note="The back-tongue drawing is a broad reference; the food vowel is more central or front in some English accents."),
    "p": lesson("b", "pen", "ben", "Close the lips, then release a puff", [
        ("Find", "Bring both lips together gently.", "lips", 0),
        ("Move", "Release the lips with a brief puff into the vowel.", "lips", 65),
        ("Feel", "Hold a hand in front of your lips and notice the short puff.", "voice", 100),
        ("Use", "Say pen once. Let the vowel follow the release.", "lips", 100)],
        "Can you feel a brief release rather than continuous air?", ["Both lips meet, then separate.", "Keep it relaxed for the next vowel.", "A comfortable opening after release.", "Explore s/z to feel voice off/on; then return to pen."], "stops", "release",
        "This exercise uses a stressed word beginning. Breath release also matters; voicing alone is not the whole p/b contrast."),
    "t": lesson("d", "ten", "den", "Front tongue contact, then release", [
        ("Find", "Place the tongue tip at the ridge just behind the upper teeth.", "tongue", 0),
        ("Move", "Release the contact with a small puff into the vowel.", "tongue", 65),
        ("Feel", "Notice the brief contact and release; keep the jaw loose.", "jaw", 100),
        ("Use", "Try ten once, without adding an extra vowel after it.", "voice", 100)],
        "Can you feel the front contact and the brief release?", ["Let the next vowel shape them.", "Tip at the ridge, then away.", "Keep it loose.", "Explore a quiet release before the voiced vowel."], "stops", "release"),
    "k": lesson("ɡ", "key", "gear", "Back tongue contact, then release", [
        ("Find", "Lift the back of the tongue toward the soft roof of the mouth.", "tongue", 0),
        ("Move", "Release that contact with a small puff into the vowel.", "tongue", 65),
        ("Feel", "Notice the contact farther back than the contact for t.", "tongue", 100),
        ("Use", "Try key once with an easy release.", "voice", 100)],
        "Where do you feel the release: toward the front or back?", ["Let the vowel shape them.", "Back of tongue meets the soft palate.", "Keep it comfortable.", "Let the vowel begin after the release."], "stops", "release"),
    "s": lesson("ʃ", "see", "she", "A small forward tongue movement", [
        ("Find", "Start with a gentle sh sound and let the air flow.", "tongue", 0),
        ("Move", "Bring the tongue contact region a little forward toward the tooth ridge.", "tongue", 50),
        ("Feel", "Listen as the hiss changes. Keep the air steady and gentle.", "voice", 100),
        ("Use", "Try she, see, she. Notice the small place change.", "tongue", 100)],
        "Can you change the hiss with a small movement?", ["Keep them comfortable.", "Narrow air passage near the front ridge.", "Leave a small opening.", "Keep throat vibration off during the hiss."], "friction", "flow"),
    "ʃ": lesson("s", "she", "see", "A small backward tongue movement", [
        ("Find", "Begin with a gentle s hiss.", "tongue", 0),
        ("Move", "Ease the tongue contact region slightly back behind the tooth ridge.", "tongue", 50),
        ("Feel", "Notice the hiss changing while air keeps flowing.", "voice", 100),
        ("Use", "Try see, she, see. Keep the movement small.", "tongue", 100)],
        "Can you feel the place change without pushing harder?", ["Allow a comfortable shape.", "A narrow passage a little behind s.", "Keep it easy and slightly open.", "No throat buzz during the hiss."], "friction", "flow"),
}


QUICK_CUES = {
    "iː": "Gently spread the lip corners sideways for seat. Keep a small opening.",
    "ɪ": "Start with seat; relax the lips and tongue a little, then try sit.",
    "ɛ": "Start with bad; close the jaw a little, then say bed.",
    "æ": "Start with bed; open the jaw a little more, then say bad.",
    "uː": "Round the lips gently for the vowel in food.",
    "p": "Close both lips, then let out a short puff as you say pen.",
    "t": "Touch the ridge behind your top teeth, then release into ten.",
    "k": "Lift the back of the tongue, then release into key.",
    "s": "From sh, move the tongue a little forward and try see.",
    "ʃ": "From s, move the tongue a little back and try she.",
}

# Relative artwork settings, not measured dimensions or pronunciation scores.
LIP_SPREAD = {"iː":.95,"i":.95,"ɪ":.24,"ɛ":.45,"e":.5,"æ":.6,"a":.42,
              "ə":.08,"ɐ":.08,"ʌ":.08,"ɑ":.04,"ɑː":.04}


# Preserve the legacy long-vowel examples while American targets use /i u/.
LESSONS['i']={**LESSONS['iː'], 'anchor_phone':'ɪ'}
LESSONS['u']={**LESSONS['uː'], 'anchor_phone':'i'}
QUICK_CUES.update({'i':QUICK_CUES['iː'],'u':QUICK_CUES['uː']})
PAIR_ANCHORS={'b':'p','d':'t','ɡ':'k','f':'v','v':'f','θ':'ð','ð':'θ','z':'s','ʒ':'ʃ','tʃ':'dʒ','dʒ':'tʃ',
              'm':'b','n':'d','ŋ':'ɡ','l':'n','ɹ':'l','w':'u','j':'i','h':'ə'}
VOWEL_CUES={
    'ʊ':'Round the lips gently but keep a more relaxed vowel than food; try foot.',
    'ə':'Let the first vowel in about be light and relaxed; do not force a full stressed vowel.',
    'ʌ':'Keep the lips unrounded and the jaw comfortably open for cup.',
    'ɑ':'Let the jaw open with comfortable, unrounded lips for hot.',
    'ɔ':'Explore a slightly rounded, open vowel for caught; many Americans use the same vowel as cot.',
    'ɝ':'Brace the tongue sides gently for bird; explore a bunched or curled r shape without touching the roof.',
    'ɚ':'Keep the final r-colored vowel in teacher easy and light; avoid forcing a tongue-tip contact.',
}
for _phone in tuple(PRIMARY_TARGETS)+tuple(R_SEQUENCES):
    if _phone in LESSONS:continue
    _prompt=next(p for p in PROMPTS.values() if p['target_phone']==_phone)
    _word=_prompt['word']
    if _phone in MOVING_VOWELS:
        _start,_end=MOVING_VOWELS[_phone];_anchor=_start
        _cue=f'Begin near /{_start}/, then move smoothly toward /{_end}/ as one connected vowel in {_word}.'
        _mode='r_sequence' if _phone in R_SEQUENCES else 'diphthong'
        _focus='tongue';_note='The start and finish are teaching references. Neither the actual path nor duration is measured.'
    elif _phone in VOWEL_FEATURES:
        _anchor='ə' if _phone!='ə' else 'ʌ';_cue=VOWEL_CUES[_phone];_mode='glide';_focus='tongue'
        _note='American r can be bunched or curled; do not force one tongue shape.' if _phone in {'ɝ','ɚ'} else 'American vowel realizations vary. Keep the movement comfortable.'
    else:
        _place,_manner,_voiced,_tip=CONSONANT_FEATURES[_phone]
        _anchor=PAIR_ANCHORS[_phone];_cue=_tip
        _mode='release' if _manner=='stop' else 'affricate' if _manner=='affricate' else 'flow'
        _focus='lips' if _place in {'bilabial','labiodental','labial_velar'} else 'voice' if _place=='glottal' else 'tongue'
        _note='Notice airflow through the nose; the oral closure stays in place.' if _manner=='nasal' else 'This is a sound-category teaching example, not a measurement of your mouth.'
    QUICK_CUES[_phone]=_cue
    LESSONS[_phone]=lesson(_anchor,_word,f'/{_anchor}/',_cue,[
        ('Find',f'Explore the starting reference /{_anchor}/ without forcing it.',_focus,0),
        ('Move',_cue,_focus,50),
        ('Feel','Notice one change in your lips, tongue, jaw or gentle voice vibration.',_focus,100),
        ('Use',f'Say {_word} once and listen back for that one change.','voice',100)],
        'What small change can you feel and hear?',
        ['Keep the lip movement small and comfortable.',_cue,'Let the jaw stay easy.','Use gentle vibration when the reference is voiced.'],
        'american',_mode,_note)

def lip_pose(phone, *, rounded=False, place=None):
    if place=='labiodental':
        return {'lip_spread':.12,'lip_round':0.,'lip_closed':False,'lip_teeth':True,'lip_label':'Lower lip meets upper front teeth'}
    if place=='dental':
        return {'lip_spread':.12,'lip_round':0.,'lip_closed':False,'lip_tongue':True,'lip_label':'Tongue tip gently near the front teeth'}
    if rounded:
        return {"lip_spread":0.,"lip_round":.65 if phone=="ʊ" else 1.,"lip_closed":False,
                "lip_label":"Gently rounded lips"}
    if place=="bilabial":
        return {"lip_spread":.08,"lip_round":0.,"lip_closed":True,"lip_label":"Both lips together"}
    spread=LIP_SPREAD.get(phone,.12)
    label=("Spread gently sideways" if spread>.7 else "Relaxed, less spread" if phone=="ɪ" else
           "Open with the jaw" if phone in {"æ","a","ɑ","ɑː"} else "Comfortable, unrounded lips")
    return {"lip_spread":spread,"lip_round":0.,"lip_closed":False,"lip_label":label}


def teaching_config():
    poses = {}
    for phone, (front, opening, rounded, _) in VOWEL_FEATURES.items():
        poses[phone] = {"family": "vowel", "front": front, "opening": opening,
                        "rounded": rounded, "voiced": True, "r_coloring":phone in {'ɝ','ɚ'}, **lip_pose(phone,rounded=rounded)}
    for phone, (place, manner, voiced, _) in CONSONANT_FEATURES.items():
        poses[phone] = {"family": "consonant", "front": {"velar": .12, "postalveolar": .68, "alveolar": .9, "dental": 1,'palatal':.75,'labial_velar':.2}.get(place, .5),
                        "opening": .28, "rounded": False, "voiced": voiced,
                        "place": place, "manner": manner, **lip_pose(phone,rounded=phone=='w',place=place)}
    for phone,(start,end) in MOVING_VOWELS.items():
        path=list(poses[start]['path_poses']) if start in MOVING_VOWELS else [poses[start]]
        path.append(poses[end])
        poses[phone]={**poses[start], 'family':'vowel','moving':True,'start_phone':start,'end_phone':end,
                      'start_pose':path[0],'end_pose':path[-1],'path_poses':path}
    assert set(PRIMARY_TARGETS) <= set(LESSONS)
    lessons = {phone: {**data, "quick_cue": QUICK_CUES[phone]} for phone, data in LESSONS.items()}
    return {"revision": "american-inventory-1", "controls": CONTROLS, "lessons": lessons,
            "poses": poses, "sources": UNDERHILL_SOURCES,
            "credit": "Original WordSpeak activities informed by Adrian Underhill's physical approach, with General American sound references. Not reviewed or endorsed by him."}
