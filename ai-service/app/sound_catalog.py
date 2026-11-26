"""General American targets, contrast references and independent word anchors.

Reference features describe generic sounds, not the learner's measured anatomy.
An unmarked model /i/ or /u/ is never silently relabeled as a long vowel.
"""
from .english_inventory import PRIMARY_TARGETS, PROMPTS as AMERICAN_PROMPTS, R_SEQUENCES
VOWEL_FEATURES = {
    # frontness (1=front), openness (0=close), rounded, descriptive name
    "iː": (1.0, 0.05, False, "Close front vowel"),
    "ɪ": (0.8, 0.25, False, "Near-close near-front vowel"),
    "ɛ": (1.0, 0.65, False, "Open-mid front vowel"),
    "æ": (1.0, 0.88, False, "Near-open front vowel"),
    "uː": (0.05, 0.05, True, "Close back rounded vowel"),
    "i": (1.0, 0.05, False, "Close front vowel; length unmarked"),
    "u": (0.05, 0.05, True, "Close back vowel; length unmarked"),
    "ʊ": (0.25, 0.25, True, "Near-close near-back rounded vowel"),
    "e": (1.0, 0.4, False, "Close-mid front vowel"),
    "ə": (0.5, 0.5, False, "Central reduced vowel"),
    "ʌ": (0.3, 0.65, False, "Open-mid vowel reference"),
    "ɑ": (0.0, 1.0, False, "Open back vowel; length unmarked"),
    "ɑː": (0.0, 1.0, False, "Open back vowel"),
    "ɔː": (0.05, 0.65, True, "Open-mid back rounded vowel"),
    "a": (1.0, 1.0, False, "Open front vowel; length unmarked"),
    "ɐ": (0.5, 0.8, False, "Near-open central vowel"),
    "ɔ": (0.05, 0.65, True, "Open-mid back rounded vowel; length unmarked"),
    "ɝ": (.5, .45, False, "Stressed American r-colored vowel"),
    "ɚ": (.5, .45, False, "Unstressed American r-colored vowel"),
    "ɜ": (.5, .45, False, "Central vowel; r-coloring unspecified"),
    "ɜː": (.5, .45, False, "Central vowel; r-coloring unspecified"),
    "o": (.05, .4, True, "Close-mid back rounded vowel"),
    "ɒ": (.05, .95, True, "Open back rounded vowel; non-American comparison"),
}
DIPHTHONG_FEATURES = {"eɪ": ("e", "ɪ"), "aɪ": ("a", "ɪ"), "ɔɪ": ("ɔ", "ɪ"),
                      "oʊ": ("o", "ʊ"), "aʊ": ("a", "ʊ"),
                      "əʊ": ("ə", "ʊ")}
CONSONANT_FEATURES = {
    "p": ("bilabial", "stop", False, "Close both lips, then release the closure."),
    "b": ("bilabial", "stop", True, "Close both lips, then release with voicing."),
    "t": ("alveolar", "stop", False, "Make a closure at the ridge behind the upper teeth, then release."),
    "d": ("alveolar", "stop", True, "Make a front tongue closure at the ridge, with voicing."),
    "k": ("velar", "stop", False, "Raise the back of the tongue to the soft palate, then release."),
    "ɡ": ("velar", "stop", True, "Make a back tongue closure at the soft palate, with voicing."),
    "s": ("alveolar", "fricative", False, "Keep a narrow front tongue channel and continuous airflow."),
    "z": ("alveolar", "fricative", True, "Use a similar front tongue channel to /s/, adding voicing."),
    "ʃ": ("postalveolar", "fricative", False, "Compared with /s/, raise the tongue blade slightly farther back."),
    "ʒ": ("postalveolar", "fricative", True, "Use a similar tongue region to /ʃ/, adding voicing."),
    "f": ("labiodental", "fricative", False, "Bring the lower lip toward the upper front teeth; keep air flowing."),
    "v": ("labiodental", "fricative", True, "Use a lower-lip/upper-teeth air passage, adding voicing."),
    "θ": ("dental", "fricative", False, "Bring the tongue tip gently toward the upper teeth and let air pass."),
    "ð": ("dental", "fricative", True, "Use a tongue-tip/upper-teeth air passage with voicing."),
    "h": ("glottal", "fricative", False, "Let a gentle breath flow into the next vowel; do not force a tongue constriction."),
    "tʃ": ("postalveolar", "affricate", False, "Make a brief closure behind the tooth ridge, then release into a sh-like flow."),
    "dʒ": ("postalveolar", "affricate", True, "Make a brief closure behind the tooth ridge, then release with a gentle voice buzz."),
    "m": ("bilabial", "nasal", True, "Close both lips gently and let voiced air pass through the nose."),
    "n": ("alveolar", "nasal", True, "Touch the ridge with the tongue tip and let voiced air pass through the nose."),
    "ŋ": ("velar", "nasal", True, "Lift the back of the tongue and hum through the nose; do not add a separate g after sing."),
    "l": ("alveolar", "lateral", True, "Touch the tongue tip near the ridge and let air pass around its sides."),
    "ɹ": ("postalveolar", "approximant", True, "Brace the tongue sides gently; explore a bunched or slightly curled tongue without touching the roof."),
    "w": ("labial_velar", "approximant", True, "Round the lips and glide into the vowel without touching the teeth."),
    "j": ("palatal", "approximant", True, "Lift the tongue body near the hard palate and glide into the vowel; this is the y in yes."),
    "ɾ": ("alveolar", "tap", True, "Use one very brief tongue-tip contact, as in many American pronunciations of water."),
    "ʔ": ("glottal", "stop", False, "Briefly interrupt airflow at the voice box; do not force the throat."),
}
FILENAMES = {
    "iː":"iy", "ɪ":"ih", "ɛ":"eh", "æ":"ae", "uː":"uw", "i":"i", "u":"u",
    "ʊ":"uh", "e":"e", "ə":"schwa", "ʌ":"ah", "ɑ":"a", "ɑː":"aa", "ɔː":"ao",
    "p":"p", "b":"b", "t":"t", "d":"d", "k":"k", "ɡ":"g", "s":"s", "z":"z",
    "ʃ":"sh", "ʒ":"zh", "f":"f", "v":"v",
    "a":"open_front", "ɐ":"central_open", "ɔ":"open_mid_back", "θ":"th", "ð":"dh"
}
FILENAMES.update({"ɝ":"er_stressed", "ɚ":"er_unstressed", "ɜ":"central_mid", "ɜː":"central_mid_long", "o":"close_mid_back", "ɒ":"lot_comparison",
                  "eɪ":"ey", "aɪ":"ay", "ɔɪ":"oy", "oʊ":"ow", "aʊ":"aw", "əʊ":"goat_comparison",
                  "h":"h", "tʃ":"ch", "dʒ":"jh", "m":"m", "n":"n", "ŋ":"ng", "l":"l", "ɹ":"r", "w":"w", "j":"y", "ɾ":"tap", "ʔ":"glottal"})
FILENAMES.update({phone:f"r_sequence_{index}" for index,phone in enumerate(R_SEQUENCES)})
MOVING_VOWELS = {**DIPHTHONG_FEATURES, **R_SEQUENCES}
AIRFLOW = {"stop":"closure then release", "fricative":"continuous friction", "affricate":"closure then friction",
           "nasal":"air through nose", "lateral":"air around tongue sides", "approximant":"open oral passage", "tap":"one brief tongue contact"}
GUIDES = {}


def vowel_reference_features(front, openness, rounded):
    height = ("close/high" if openness < .15 else "near-close" if openness < .3 else
              "close-mid" if openness < .45 else "mid" if openness < .6 else
              "open-mid" if openness < .75 else "near-open" if openness < .95 else "open/low")
    region = "front" if front > .9 else "near-front" if front > .7 else "back" if front < .15 else "near-back" if front < .3 else "central"
    return {"tongue_height": height, "tongue_region": region,
            "lip_shape": "rounded" if rounded else "unrounded"}


for phone, (front, openness, rounded, name) in VOWEL_FEATURES.items():
    features = vowel_reference_features(front, openness, rounded)
    GUIDES[phone] = {"phone": phone, "name": name, "family": "vowel", "primary": phone in PRIMARY_TARGETS,
        "svg_url": f"/demo/assets/{FILENAMES[phone]}.svg", "voicing": "Vowel reference",
        "tips": [f"Tongue height: {features['tongue_height']}.",
                 f"Tongue region: {features['tongue_region']}.",
                 f"Lips: {features['lip_shape']}."],
        "caption": "Schematic tongue region, not measured anatomy. Vowel length is not graded."}
for phone, (place, manner, voiced, tip) in CONSONANT_FEATURES.items():
    GUIDES[phone] = {"phone": phone, "name": f"{'Voiced' if voiced else 'Voiceless'} {place} {manner}",
        "family": "consonant", "primary": phone in PRIMARY_TARGETS,
        "svg_url": f"/demo/assets/{FILENAMES[phone]}.svg", "voicing": "Voice on" if voiced else "Voice off",
        "tips": [tip, "Airflow reference: " + AIRFLOW[manner] + "."],
        "caption": "Generic reference illustration, simplified and not to scale."}
for phone, (start, end) in MOVING_VOWELS.items():
    r_sequence=phone in R_SEQUENCES
    GUIDES[phone]={"phone":phone,"name":"American vowel + r combination" if r_sequence else "Moving vowel / diphthong",
        "family":"vowel","subtype":"r_sequence" if r_sequence else "diphthong","primary":phone in PRIMARY_TARGETS,
        "svg_url":f"/demo/assets/{FILENAMES[phone]}.svg","voicing":"Voice on through the movement",
        "tips":[f"Begin near /{start}/ and move smoothly toward /{end}/.",
                "Keep this connected; the drawing shows two reference moments, not measured positions."],
        "caption":"Start and end reference shapes. The path is illustrative, not a measured tongue trajectory."}


def consonant(word, phone, tail, phrase=None, primary=True):
    return {"word": word, "phrase": phrase or f"Say {word} now.", "target_phone": phone,
            "family": "consonant", "primary": primary, "before": [], "after": tail}


def vowel(word, phone, before, after):
    return {"word": word, "phrase": f"Say {word} now.", "target_phone": phone,
            "family": "vowel", "primary": True, "before": before, "after": after}


PROMPTS = {
    "seat": vowel("seat", "iː", [{"s"}], [{"t", "ʔ", "t̚"}]),
    "sit": vowel("sit", "ɪ", [{"s"}], [{"t", "ʔ", "t̚"}]),
    "bed": vowel("bed", "ɛ", [{"b"}], [{"d", "d̚"}]),
    "bad": vowel("bad", "æ", [{"b"}], [{"d", "d̚"}]),
    "food": vowel("food", "uː", [{"f"}], [{"d", "d̚"}]),
    "pen": consonant("pen", "p", [{"ɛ", "e"}, {"n"}]),
    "ten": consonant("ten", "t", [{"ɛ", "e"}, {"n"}]),
    "key": consonant("key", "k", [{"iː", "i"}]),
    "see": consonant("see", "s", [{"iː", "i"}], "I can see it."),
    "she": consonant("she", "ʃ", [{"iː", "i"}], "She is here today."),
    "zoo": consonant("zoo", "z", [{"uː", "u"}], "I like the zoo.", primary=False),
    "shows": consonant("shows", "ʃ", [{"oʊ", "əʊ"}, {"z"}], primary=False),
    "two": {**vowel("two", "uː", [{"t"}], []), "primary": False},
    "put": consonant("put", "p", [{"ʊ"}, {"t", "t̚"}], primary=False),
    "can": consonant("can", "k", [{"æ", "ə"}, {"n"}], primary=False),
}
# Retain old extra word IDs for recordings and development links. New primary
# entries use American notation, including /i u/ rather than a length contrast.
PROMPTS={**{key:{**value,"primary":False} for key,value in PROMPTS.items()}, **AMERICAN_PROMPTS}
PROMPTS.update({"seat_long":{**PROMPTS['seat'],"target_phone":"iː","primary":False},
                "food_long":{**PROMPTS['food'],"target_phone":"uː","primary":False}})
PROMPTS['two']['target_phone']='u'
PROMPTS['see']['phrase']='I can see it.'
PROMPTS['she']['phrase']='She is here today.'
SOURCES = [
    {"label":"General American sound chart", "url":"https://soundsamerican.net/"},
    {"label":"American vowels and r-coloring", "url":"https://opentext.ku.edu/amenglishpronunciation/chapter/chapter-1/"},
    {"label":"IPA sound categories", "url":"https://www.internationalphoneticassociation.org/IPAcharts/IPA_charts_EI/IPA_charts_EI.html"},
    {"label":"Sheffield articulation reference", "url":"https://sheffield.ac.uk/linguistics/home/all-about-linguistics/about-website/branches-linguistics/phonetics/what-do-phoneticians-study/articulatory"},
    {"label":"PolyU consonant practice", "url":"https://elc.polyu.edu.hk/sounds/lesson8.htm"}
]


def practice_cue(predicted, target):
    """Describe a contrast between reference categories, not learner anatomy."""
    if not predicted or predicted == target:
        return None
    if predicted in MOVING_VOWELS or target in MOVING_VOWELS:
        return movement_cue(predicted,target)
    if predicted in VOWEL_FEATURES and target in VOWEL_FEATURES:
        pfront, popen, pround, _ = VOWEL_FEATURES[predicted]
        front, openness, rounded, _ = VOWEL_FEATURES[target]
        changes = []
        if abs(openness - popen) > 0.08:
            changes.append("a higher tongue reference" if openness < popen else "a lower tongue reference")
        if abs(front - pfront) > 0.08:
            changes.append("a more front reference" if front > pfront else "a more back reference")
        if rounded != pround:
            changes.append("rounded lips" if rounded else "unrounded lips")
        return (f"Practice /{target}/ by comparing " + ", ".join(changes) +
                ". These are reference differences; vowel duration is not graded.") if changes else None
    if predicted in CONSONANT_FEATURES and target in CONSONANT_FEATURES:
        place, manner, voiced, tip = CONSONANT_FEATURES[target]
        pplace, pmanner, pvoiced, _ = CONSONANT_FEATURES[predicted]
        if place == pplace and manner == pmanner and voiced != pvoiced:
            return f"Practice /{target}/ with voicing {'on' if voiced else 'off'}, using a similar reference place of articulation."
        return f"Practice cue for /{target}/: {tip} Compare the two reference drawings."
    return None


def reference_profile(phone):
    """Readable category features, never coordinates estimated from audio."""
    if phone in MOVING_VOWELS:
        start,end=MOVING_VOWELS[phone]
        return {"phone":phone,"family":"vowel","name":GUIDES[phone]['name'],
                "features":{"vowel_movement":f"/{start}/ to /{end}/","lip_shape":"changes through the vowel",
                            "r_coloring":"on" if phone in R_SEQUENCES else "off"}}
    if phone in VOWEL_FEATURES:
        front, openness, rounded, name = VOWEL_FEATURES[phone]
        return {"phone": phone, "family": "vowel", "name": name,
                "features": {**vowel_reference_features(front, openness, rounded),
                             "r_coloring":"on" if phone in {'ɝ','ɚ'} else "off"}}
    if phone in CONSONANT_FEATURES:
        place, manner, voiced, _ = CONSONANT_FEATURES[phone]
        return {"phone": phone, "family": "consonant", "name": GUIDES[phone]["name"],
                "features": {"place": place, "airflow": AIRFLOW[manner],
                             "voicing": "on" if voiced else "off"}}
    return None


def articulation_feedback(predicted, target, *, evidence="model_hypothesis"):
    """Explain categorical differences; never claim measured original position."""
    observed, desired = reference_profile(predicted), reference_profile(target)
    if not observed or not desired or observed["family"] != desired["family"]:
        return None
    differences = []
    if observed["family"] == "vowel" and (predicted in MOVING_VOWELS or target in MOVING_VOWELS):
        differences=[{"dimension":"vowel_movement","observed_reference":observed['features'].get('vowel_movement','steady vowel quality'),
                      "target_reference":desired['features'].get('vowel_movement','steady vowel quality'),
                      "adjustment":movement_cue(predicted,target)}] if predicted!=target else []
        return feedback_result(observed,desired,differences,evidence)
    if observed["family"] == "vowel":
        pf, po, pr, _ = VOWEL_FEATURES[predicted]
        tf, to, tr, _ = VOWEL_FEATURES[target]
        adjustments = {
            "tongue_height": "Raise your tongue slightly; close your jaw a little." if to < po else "Lower your tongue slightly; open your jaw a little.",
            "tongue_region": "Bring the tongue body slightly forward." if tf > pf else "Move the tongue body slightly back.",
            "lip_shape": "Round your lips." if tr else "Relax the lip rounding; use unrounded lips.",
            "r_coloring":"Brace the tongue sides gently and explore a bunched or curled American r shape without roof contact." if target in {'ɝ','ɚ'} else "Ease the r coloring and try the target vowel without a tongue curl or bunching gesture."}
    else:
        adjustments = {"place": CONSONANT_FEATURES[target][3],
                       "airflow": CONSONANT_FEATURES[target][3],
                       "voicing": "Add a gentle voice vibration." if CONSONANT_FEATURES[target][2] else "Keep the voice vibration off for this consonant."}
    for dimension, value in observed["features"].items():
        desired_value = desired["features"][dimension]
        if value != desired_value:
            differences.append({"dimension": dimension, "observed_reference": value,
                                "target_reference": desired_value, "adjustment": adjustments[dimension]})
    return feedback_result(observed,desired,differences,evidence)

def movement_cue(predicted,target):
    if target in MOVING_VOWELS:
        start,end=MOVING_VOWELS[target]
        return f"Begin with a comfortable /{start}/ reference, then move smoothly toward /{end}/ in one connected syllable."
    return "If you hear a glide, keep one comfortable vowel shape through the word instead of moving to a second vowel."

def feedback_result(observed,desired,differences,evidence):
    return {"basis": "sound_category_reference_hypothesis", "evidence": evidence,
            "anatomy_measured": False, "observed_reference": observed,
            "target_reference": desired, "differences": differences,
            "note": "The starting diagram is a typical reference for the model's likely sound, not your measured tongue position. Vowel duration is not assessed."}
