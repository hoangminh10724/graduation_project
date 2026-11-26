"""General American teaching inventory, separate from model-specific labels.

41 core practice entries: 12 steady/r-colored vowel entries, 5 diphthongs,
24 consonants. This is a teaching count, not a claim of 41 distinct phonemes
in every American accent. R-vowel sequences and allophones are extra practice.
"""
ACCENT = {
    "id": "general_american", "label": "General American English",
    "note": "American reference. Cot/caught merger and common American variants are accepted; vowel duration and lexical stress are not graded.",
    "inventory_note": "41 core practice entries: 17 vowel entries and 24 consonants. R-colored stress variants are listed separately for teaching.",
}
MONOPHTHONGS = ("i", "ɪ", "ɛ", "æ", "u", "ʊ", "ə", "ʌ", "ɑ", "ɔ", "ɝ", "ɚ")
DIPHTHONGS = ("eɪ", "aɪ", "ɔɪ", "oʊ", "aʊ")
CONSONANTS = ("p", "b", "t", "d", "k", "ɡ", "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h", "tʃ", "dʒ", "m", "n", "ŋ", "l", "ɹ", "w", "j")
PRIMARY_TARGETS = MONOPHTHONGS + DIPHTHONGS + CONSONANTS
ARPABET = dict(zip(PRIMARY_TARGETS, (
    "IY", "IH", "EH", "AE", "UW", "UH", "AH0", "AH", "AA", "AO", "ER1", "ER0",
    "EY", "AY", "OY", "OW", "AW", "P", "B", "T", "D", "K", "G", "F", "V", "TH", "DH", "S", "Z", "SH", "ZH", "HH", "CH", "JH", "M", "N", "NG", "L", "R", "W", "Y")))

# Only notation/allophonic mappings with an explicit English interpretation.
# Opaque multilingual labels (i5, tone-marked strings, etc.) are never guessed.
LABEL_ALIASES = {"g": "ɡ", "iː": "i", "uː": "u", "ɑː": "ɑ", "ɔː": "ɔ",
                 "r": "ɹ", "ɻ": "ɹ", "ɫ": "l", "t͡ʃ": "tʃ", "d͡ʒ": "dʒ",
                 "pʰ":"p","tʰ":"t","kʰ":"k","p̚":"p","t̚":"t","k̚":"k","d̚":"d","b̚":"b","ɡ̚":"ɡ",
                 "ɜ˞":"ɝ","ə˞":"ɚ"}
PAIR_LABELS = {("e", "ɪ"): "eɪ", ("a", "ɪ"): "aɪ", ("ɔ", "ɪ"): "ɔɪ",
               ("o", "ʊ"): "oʊ", ("a", "ʊ"): "aʊ",
               ("t", "ʃ"): "tʃ", ("d", "ʒ"): "dʒ",
               ("ɜː", "ɹ"): "ɝ", ("ɜ", "ɹ"): "ɝ", ("ə", "ɹ"): "ɚ"}
R_SEQUENCES = {"ɪɹ": ("ɪ", "ɹ"), "ɛɹ": ("ɛ", "ɹ"), "ɑɹ": ("ɑ", "ɹ"),
               "ɔɹ": ("ɔ", "ɹ"), "ʊɹ": ("ʊ", "ɹ"), "aɪɹ": ("aɪ", "ɹ")}
R_LABEL_ALIASES = {"ɪr": "ɪɹ", "ɛr": "ɛɹ", "ɑːɹ": "ɑɹ", "ɔːɹ": "ɔɹ", "ʊr": "ʊɹ", "aɪɚ": "aɪɹ"}

def normalize_label(phone):
    return LABEL_ALIASES.get(phone, R_LABEL_ALIASES.get(phone, phone))

def prompt(word, phone, before=(), after=(), *, position="initial", nucleus=0, nuclei=1, primary=True):
    vowel = phone in MONOPHTHONGS + DIPHTHONGS or phone in R_SEQUENCES
    return {"word": word, "phrase": f"Say {word} now.", "target_phone": phone,
            "family": "vowel" if vowel else "consonant", "primary": primary,
            "before": [set(x) if not isinstance(x, str) else {x} for x in before],
            "after": [set(x) if not isinstance(x, str) else {x} for x in after],
            "focus_position": position, "nucleus_index": nucleus, "expected_nuclei": nuclei,
            "focus_unit": "r_sequence" if phone in R_SEQUENCES else "phone",
            "category": "R-vowel combinations" if phone in R_SEQUENCES else
                        "Diphthongs" if phone in DIPHTHONGS else "Steady & r-colored vowels" if vowel else "Consonants"}

PROMPTS = {
    "seat": prompt("seat", "i", ["s"], [{"t", "ʔ", "tʰ"}]),
    "sit": prompt("sit", "ɪ", ["s"], [{"t", "ʔ", "tʰ"}]),
    "bed": prompt("bed", "ɛ", ["b"], [{"d", "d̚"}]),
    "bad": prompt("bad", "æ", ["b"], [{"d", "d̚"}]),
    "food": prompt("food", "u", ["f"], [{"d", "d̚"}]),
    "foot": prompt("foot", "ʊ", ["f"], [{"t", "ʔ"}]),
    "about": prompt("about", "ə", [], ["b", "aʊ"], nuclei=2),
    "cup": prompt("cup", "ʌ", ["k"], ["p"]),
    "hot": prompt("hot", "ɑ", ["h"], [{"t", "ʔ"}]),
    "caught": prompt("caught", "ɔ", ["k"], [{"t", "ʔ"}]),
    "bird": prompt("bird", "ɝ", ["b"], ["d"]),
    "teacher": prompt("teacher", "ɚ", ["tʃ"], [], nucleus=1, nuclei=2),
    "day": prompt("day", "eɪ", ["d"]), "my": prompt("my", "aɪ", ["m"]),
    "boy": prompt("boy", "ɔɪ", ["b"]), "go": prompt("go", "oʊ", ["ɡ"]),
    "now": prompt("now", "aʊ", ["n"]),
    "pen": prompt("pen", "p", [], [{"ɛ", "e"}, "n"]),
    "ben": prompt("ben", "b", [], [{"ɛ", "e"}, "n"]),
    "ten": prompt("ten", "t", [], [{"ɛ", "e"}, "n"]),
    "den": prompt("den", "d", [], [{"ɛ", "e"}, "n"]),
    "key": prompt("key", "k", [], ["i"]),
    "give": prompt("give", "ɡ", [], ["ɪ", "v"]),
    "fan": prompt("fan", "f", [], ["æ", "n"]), "van": prompt("van", "v", [], ["æ", "n"]),
    "thin": prompt("thin", "θ", [], ["ɪ", "n"]), "this": prompt("this", "ð", [], ["ɪ", "s"]),
    "see": prompt("see", "s", [], ["i"]), "zoo": prompt("zoo", "z", [], ["u"]),
    "she": prompt("she", "ʃ", [], ["i"]),
    "vision": prompt("vision", "ʒ", ["ɪ"], ["ə", "n"], position="medial", nuclei=2),
    "hat": prompt("hat", "h", [], ["æ", "t"]),
    "chin": prompt("chin", "tʃ", [], ["ɪ", "n"]), "jam": prompt("jam", "dʒ", [], ["æ", "m"]),
    "man": prompt("man", "m", [], ["æ", "n"]), "no": prompt("no", "n", [], ["oʊ"]),
    "sing": prompt("sing", "ŋ", ["s", "ɪ"], [], position="final"),
    "lip": prompt("lip", "l", [], ["ɪ", "p"]), "red": prompt("red", "ɹ", [], ["ɛ", "d"]),
    "wet": prompt("wet", "w", [], ["ɛ", "t"]), "yes": prompt("yes", "j", [], ["ɛ", "s"]),
    "near": prompt("near", "ɪɹ", ["n"], primary=False),
    "care": prompt("care", "ɛɹ", ["k"], primary=False),
    "car": prompt("car", "ɑɹ", ["k"], primary=False),
    "four": prompt("four", "ɔɹ", ["f"], primary=False),
    "tour": prompt("tour", "ʊɹ", ["t"], primary=False),
    "fire": prompt("fire", "aɪɹ", ["f"], primary=False),
}
assert len(PRIMARY_TARGETS) == 41
assert {p["target_phone"] for p in PROMPTS.values() if p["primary"]} == set(PRIMARY_TARGETS)

# Accepted American regional variation, not a pronunciation error.
ACCEPTED_VARIANTS = {("ɑ", "ɔ"): "cot_caught_merger", ("ɔ", "ɑ"): "cot_caught_merger",
                     ("ɔɹ", "ʊɹ"): "American_tour_vowel_variant"}
UNRESOLVED_VARIANTS = {("ɚ", "ɝ"): "stress_not_assessed", ("ɝ", "ɚ"): "stress_not_assessed",
                       ("ɜː", "ɝ"): "r_coloring_unresolved", ("ɜ", "ɝ"): "r_coloring_unresolved",
                       ("əʊ", "oʊ"): "accent_or_notation", ("e", "ɛ"): "notation_or_length",
                       ("e","eɪ"):'glide_resolution_unverified',("o","oʊ"):'glide_resolution_unverified'}
