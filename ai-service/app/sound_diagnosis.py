"""Learner-facing observations and conditional corrections from decoded sounds.

These explanations compare sound categories. They never estimate a speaker's
anatomy or treat uncalibrated model peaks as pronunciation accuracy.
"""
from .sound_catalog import VOWEL_FEATURES, PROMPTS, articulation_feedback

EXAMPLES = {
    "iː": "the vowel in seat", "i": "the vowel quality in seat (length unspecified)",
    "ɪ": "the vowel in sit", "ɛ": "the vowel in bed", "e": "a close-mid front vowel",
    "æ": "the vowel in bad", "uː": "the vowel in food",
    "u": "the vowel quality in food (length unspecified)", "ʊ": "the vowel in put",
    "ə": "the unstressed vowel in about", "ʌ": "the vowel in cup",
    "p": "the start of pen", "b": "the start of ben", "t": "the start of ten",
    "d": "the start of den", "k": "the start of key", "ɡ": "the start of go",
    "s": "the start of see", "z": "the start of zoo", "ʃ": "the start of she",
    "f": "the start of fan", "v": "the start of van", "θ": "the start of thin",
    "ð": "the start of this", "ʒ": "the middle sound in vision",
}
GLIDES = {"eɪ": "day", "aɪ": "eye", "ɔɪ": "boy", "oʊ": "go", "əʊ": "go", "aʊ": "how"}
for _prompt in PROMPTS.values():
    _phone=_prompt['target_phone']
    if _prompt['primary'] or _phone not in EXAMPLES:
        _position=_prompt.get('focus_position','initial')
        EXAMPLES[_phone]=(f"the vowel in {_prompt['word']}" if _prompt['family']=='vowel' else
                          f"the {'end' if _position=='final' else 'middle' if _position=='medial' else 'start'} of {_prompt['word']}")
PRIORITY = ("vowel_movement", "r_coloring", "lip_shape", "place", "tongue_height", "tongue_region", "airflow", "voicing")
PLACES = {"bilabial": "both lips", "alveolar": "the ridge behind the upper teeth",
          "postalveolar": "just behind the tooth ridge", "velar": "the back of the mouth",
          "dental": "the tongue and upper teeth", "labiodental": "the lower lip and upper teeth",
          "glottal":"the voice box, with the mouth following the vowel", "palatal":"the tongue body near the hard palate",
          "labial_velar":"rounded lips and the back of the tongue"}


def label(phone):
    return f"/{phone}/" + (f" — {EXAMPLES[phone]}" if phone in EXAMPLES else "")


def main_difference(feedback):
    differences = feedback["differences"]
    return next((d for name in PRIORITY for d in differences if d["dimension"] == name), None)


def contrast_text(feedback, difference):
    observed, target = feedback["observed_reference"], feedback["target_reference"]
    dimension = difference["dimension"]
    if dimension=='vowel_movement':
        return f"The candidate reference uses {difference['observed_reference']}; the target uses {difference['target_reference']}."
    if dimension=='r_coloring':
        return 'The target has American r coloring; the candidate reference does not.' if difference['target_reference']=='on' else 'The candidate has r coloring; the target reference does not.'
    if dimension == "tongue_height":
        more_open = VOWEL_FEATURES[observed["phone"]][1] > VOWEL_FEATURES[target["phone"]][1]
        return "The candidate vowel is more open than the target." if more_open else "The candidate vowel is less open than the target."
    if dimension == "tongue_region":
        forward = VOWEL_FEATURES[observed["phone"]][0] > VOWEL_FEATURES[target["phone"]][0]
        return "Its tongue reference is farther forward than the target's." if forward else "Its tongue reference is farther back than the target's."
    if dimension == "lip_shape":
        return ("The candidate uses unrounded lips; the target uses rounded lips." if difference["target_reference"] == "rounded" else
                "The candidate uses rounded lips; the target uses unrounded lips.")
    if dimension == "place":
        return (f"The candidate's reference uses {PLACES[difference['observed_reference']]}; "
                f"the target uses {PLACES[difference['target_reference']]}.")
    if dimension == "airflow":
        return f"The candidate reference uses {difference['observed_reference']}; the target uses {difference['target_reference']}."
    return ("The candidate has a throat buzz; the target consonant is unvoiced." if difference["target_reference"] == "off" else
            "The candidate is unvoiced; the target adds a gentle throat buzz.")


def sound_diagnosis(result, prompt):
    """Always explain the recording, even when a sound category is unresolved."""
    target = prompt["target_phone"]
    details = result.get("details", {})
    feedback = result.get("articulation_feedback")
    raw = result.get("raw_phones", [])
    diagnosis = {"kind": "unresolved", "heard": "No single sound was established.",
                 "target": label(target), "comparison": "", "adjustment": "",
                 "alternatives": [], "anatomy_measured": False,
                 "note": "Sound-based estimate; the diagrams show typical references, not your measured mouth position."}
    if details.get("word_location_unverified"):
        candidate = result["predicted_phone"]
        diagnosis.update(kind="unverified_word_location",
                         heard=f"The model found a possible /{candidate}/ somewhere in the phrase." if candidate else
                              "The model could not identify a supported sound at this point in the phrase.",
                         comparison=f"Listen for the target word “{prompt['word']}”. Its position is uncertain.",
                         adjustment="Select the complete word in the recording, listen to the excerpt, then compare it again.")
        return diagnosis
    if details.get('accepted_variant'):
        phone=result['predicted_phone']
        diagnosis.update(kind='accepted_variant',heard=('Possible ' if result['status']=='uncertain' else 'Likely ')+label(phone),
                         comparison='This realization is accepted in American English for this practice word.',
                         adjustment='No change is required for this accepted variant. Listen back and continue if comfortable.')
        return diagnosis
    if details.get('unresolved_reason')=='extra_coda_evidence':
        phone=result['predicted_phone'];tail=' '.join(details['trailing_model_labels'])
        diagnosis.update(kind='tentative_comparison',heard=f'Possible ending /{phone}/ followed by /{tail}/.',
                         comparison='The recognizer emitted more than one consonant at the word ending. This may be an extra sound or a decoding error.',
                         adjustment=f'If you hear /{tail}/ after the ending, try finishing {prompt["word"]} without that extra release or sound.')
        return diagnosis
    if details.get('unresolved_reason') in {'stress_not_assessed','r_coloring_unresolved','accent_or_notation'}:
        phone=result['predicted_phone']
        diagnosis.update(kind='accent_or_stress',heard='Possible '+label(phone),
                         comparison='The labels do not establish a stress, r-coloring or accent error.',
                         adjustment='Listen for the American r coloring. If you hear an r-less vowel, explore gentle tongue-side bracing; stress has not been measured.' if details['unresolved_reason']=='r_coloring_unresolved' else
                                    'Compare both references by listening. No stress or accent correction is established from these labels alone.')
        return diagnosis
    if feedback:
        phone = feedback["observed_reference"]["phone"]
        tentative = result["status"] == "uncertain" or feedback["evidence"] == "weak_model_hypothesis"
        diagnosis["kind"] = "tentative_comparison" if tentative else "comparison"
        diagnosis["heard"] = ("Possible " if tentative or result["status"] == "possible_difference" else "Likely ") + label(phone)
        # British /e/ versus /ɛ/ transcription and unmarked /i u/ length do not
        # establish articulatory errors, even if the model peak is weak.
        if (phone, target) in {("i", "iː"), ("u", "uː"), ("e", "ɛ")}:
            diagnosis["comparison"] = ("The candidate and target share the same illustrated sound features. "
                "A difference in vowel length has not been established." if phone in {"i", "u"} else
                "The /e/ and /ɛ/ labels can reflect different transcription conventions; these labels alone do not establish an error.")
            diagnosis["adjustment"] = "No category-level adjustment is established. Listen back and compare the vowel quality."
            if tentative:
                diagnosis["note"] = "The sound category remains tentative. " + diagnosis["note"]
            return diagnosis
        difference = main_difference(feedback)
        if difference:
            diagnosis["comparison"] = contrast_text(feedback, difference)
            diagnosis["adjustment"] = (f"If /{phone}/ matches what you hear: " if tentative or result["status"] == "possible_difference" else "") + difference["adjustment"]
        else:
            diagnosis["comparison"] = "The candidate and target share the same illustrated sound features."
            diagnosis["adjustment"] = "No category-level adjustment is established. Listen back and try the word once more."
        if tentative:
            diagnosis["note"] = "Tentative sound candidate, not a confirmed error. " + diagnosis["note"]
        if details.get("unresolved_reason") == "fragmented_vowel_evidence":
            sequence = " → ".join(f"/{p}/" for p in details["focal_model_labels"])
            diagnosis["heard"] = f"Vowel labels {sequence}. One possible starting sound: {label(phone)}"
            diagnosis["note"] = "The vowel was split into several labels; this may be a sound change or recognizer instability. " + diagnosis["note"]
            for other in details.get("candidate_sound_hypotheses", []):
                if other == phone:
                    continue
                alternative = articulation_feedback(other, target, evidence="weak_model_hypothesis")
                change = main_difference(alternative) if alternative else None
                diagnosis["alternatives"].append({"phone": other, "heard": label(other),
                    "adjustment": f"If this is what you hear: {change['adjustment']}" if change else
                                  "No supported category-level adjustment is established for this candidate."})
                if len(diagnosis["alternatives"]) == 2:
                    break
        return diagnosis
    quality = details.get("audio_quality", {})
    if quality and (quality.get("rms", 1) < .003 or quality.get("clipping_fraction", 0) > .01):
        diagnosis.update(kind="audio_quality", heard="The recording is too quiet or distorted to compare.",
                         comparison="No pronunciation conclusion was made.", adjustment=result["reasons"][0])
        return diagnosis
    if not raw:
        diagnosis.update(heard="The recognizer did not decode a speech sound.",
                         comparison="This does not establish that you made the target sound incorrectly.",
                         adjustment=f"Say {prompt['word']} once at a comfortable volume, with a little silence before and after.")
        return diagnosis
    sequence = " / ".join(raw)
    diagnosis["heard"] = f"Decoded sequence: /{sequence}/."
    candidate = details.get("candidate_model_label")
    if candidate:
        diagnosis["heard"] = f"The model decoded /{candidate}/ at the focus."
        if candidate in GLIDES and prompt["family"] == "vowel":
            diagnosis.update(kind="glide_candidate",
                heard=f"Possible /{candidate}/ — the moving vowel in {GLIDES[candidate]}.",
                comparison=f"That is a glide between vowel qualities; the /{target}/ target is a steady vowel reference.",
                adjustment="If you hear that glide, keep one comfortable vowel shape through the word instead of moving to a second vowel.")
            diagnosis["note"] = "A decoded glide is provisional; no single starting-mouth diagram is assigned to it. " + diagnosis["note"]
            return diagnosis
        diagnosis["comparison"] = "This decoded label has no supported sound-position comparison in this demo."
        diagnosis["adjustment"] = "Listen back to check the decoded sound, then record just the selected word once more."
    elif result.get("message", "").startswith("No starting consonant"):
        diagnosis["comparison"] = "No initial consonant was decoded. It may be missing, or the recognizer may have missed it."
        diagnosis["adjustment"] = f"Keep the start of {prompt['word']} in the recording; leave a short pause before speaking."
    else:
        diagnosis["comparison"] = "The model could not reliably locate the selected sound in this sequence."
        diagnosis["adjustment"] = (f"Say only {prompt['word']} once, or trim to one complete word." if details.get("input_scope") == "word" else
                                   "Switch to ‘Just the word’ and record it once; the surrounding phrase was not located reliably.")
    return diagnosis
