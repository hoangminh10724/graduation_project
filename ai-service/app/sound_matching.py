"""Locate a focal label using surrounding sounds, independently of its target."""
from .sound_catalog import GUIDES, VOWEL_FEATURES, MOVING_VOWELS, practice_cue, articulation_feedback
from .english_inventory import normalize_label, ACCEPTED_VARIANTS, UNRESOLVED_VARIANTS
from .observed_units import observed_units

# Recognize nucleus positions without requiring the intended vowel. Unsupported
# diphthongs still count as nuclei, but never receive fabricated monophthong guides.
NUCLEI = set(VOWEL_FEATURES) | {"eɪ", "aɪ", "ɔɪ", "oʊ", "əʊ", "aʊ", "ɚ", "ɝ", "ɜː", "ɒ", "y", "ɨ", "ø", "œ",
                               "o", "oː", "eː", "ɜ", "ʉ", "ɯ", "iə", "ʊə", "eə"}


NUCLEI |= set(MOVING_VOWELS)

def word_candidate(phones, family, spans=None, prompt=None):
    prompt=prompt or {}
    nuclei = [index for index, phone in enumerate(phones) if phone in NUCLEI]
    # A sustained consonant is also a useful attempt, even without a vowel.
    # Do not select one consonant out of an unanchored sequence of several.
    if not nuclei and len(phones) == 1 and family == "consonant" and phones[0] in GUIDES:
        return [0], None
    groups = []
    for index in nuclei:
        adjacent = bool(groups and index == groups[-1][-1] + 1)
        if adjacent and spans:
            previous = spans[groups[-1][-1]]
            adjacent = spans[index]["start_seconds"] - previous["end_seconds"] <= .12
        if adjacent:
            groups[-1].append(index)
        else:
            groups.append([index])
    expected=prompt.get('expected_nuclei',1)
    if len(groups) != expected:
        count='one vowel nucleus' if expected==1 else f'{expected} vowel nuclei'
        return [], f"Word-only mode needs {count}. Say only the selected word once, or trim the recording to it."
    group=groups[prompt.get('nucleus_index',0)]
    nucleus = group[0]
    if family == "vowel":
        return group, None
    position=prompt.get('focus_position','initial')
    if position=='final':
        if groups[-1][-1]==len(phones)-1:
            return [], 'No final consonant was decoded after the vowel. It may be missing, or the recognizer may have missed it.'
        return [groups[-1][-1]+1],None
    if position=='medial':
        between=list(range(groups[0][-1]+1,groups[1][0]))
        if len(between)!=1:return [],'No single middle consonant was isolated between the two vowel nuclei. Listen back and try the complete word.'
        return between,None
    if nucleus == 0:
        return [], "No starting consonant was decoded before the vowel. It may be missing, or the model may have missed it. Try a clear onset, then analyze again."
    # All primary consonant prompts focus on the start of a word. No expected
    # consonant or vowel is used to choose this observed initial token.
    return [0], None


def match_sound(prediction, prompt, input_scope="context"):
    units=observed_units(prediction)
    phones = [unit['phone'] for unit in units]
    spans=units
    before, after = prompt["before"], prompt["after"]
    target = prompt["target_phone"]
    details = {"timing_status": prediction["timing_status"],
               "probability_status": "uncalibrated; experimental gates are not accuracy",
               "reference_transcript_used_by_model": False,
               "guide_status": "generic_reference_not_measured_mouth_position",
               "vowel_duration_assessed": False, "input_scope": input_scope}
    details['reference_accent']='general_american'
    details['observed_units']=[{'phone':u['phone'],'raw_labels':u['raw_labels'],'combined':u['combined']} for u in units]
    result = {"status": "uncertain", "predicted": None, "raw": prediction['predicted_phones'], "details": details, "practice_cue": None,
              "message": "I could not isolate the requested sound reliably.",
              "reasons": ["Read the suggested phrase once, keeping the complete word and a little surrounding context."],
              "articulation_feedback": None}
    candidates = []
    if input_scope == "word":
        candidates, problem = word_candidate(phones, prompt["family"], spans, prompt)
        if problem:
            result["message"] = problem
            result["reasons"] = ["The model has not established a sound substitution; no mouth position is inferred."]
            details["unresolved_reason"] = "isolated_word_structure"
    else:
        for index in range(len(phones)):
            if index < len(before) or index + len(after) >= len(phones):
                continue
            prefix = phones[index - len(before):index]
            suffix = phones[index + 1:index + 1 + len(after)]
            if (all(phone in {normalize_label(x) for x in choices} for phone, choices in zip(prefix, before)) and
                    all(phone in {normalize_label(x) for x in choices} for phone, choices in zip(suffix, after))):
                candidates.append(index)
    details["candidate_anchor_count"] = len(candidates)
    fragmented = input_scope == "word" and len(candidates) > 1
    if not candidates or (len(candidates) != 1 and not fragmented):
        return result
    if fragmented:
        # Rank only observed emissions, never by proximity to the chosen target.
        # Several adjacent vowel labels are not a verified error or a measured glide.
        details["focal_model_labels"] = [phones[index] for index in candidates]
        details["candidate_selection"] = "highest_emission_peak_in_one_adjacent_vowel_group_not_target_conditioned"
        ranked = sorted(candidates, key=lambda i: spans[i]["mean_frame_peak_probability"], reverse=True)
        details["candidate_sound_hypotheses"] = list(dict.fromkeys(phones[i] for i in ranked))
        index = ranked[0]
    else:
        index = candidates[0]
    raw_phone = phones[index]
    # Latin g and IPA script-g are notation variants, not sound corrections.
    phone = "ɡ" if raw_phone == "g" else raw_phone
    details["candidate_model_label"] = ' + '.join(spans[index]['raw_labels'])
    guide = GUIDES.get(phone)
    if not guide or guide["family"] != prompt["family"]:
        result["message"] = f"The model decoded /{raw_phone}/ here; this sound does not have a supported comparison guide."
        result["reasons"] = ["The raw prediction is retained below. A mouth-position estimate for an unsupported label would be a guess."]
        details["unresolved_reason"] = "unsupported_sound_category"
        return result
    span = spans[index]
    extra_coda=input_scope=='word' and prompt.get('focus_position')=='final' and index<len(phones)-1
    if extra_coda:details['trailing_model_labels']=phones[index+1:]
    details["approximate_target_sound_span"] = [span["start_seconds"], span["end_seconds"]]
    details["word_anchor_status"] = ("one_observed_nucleus; selected_by_word_position_not_target_label" if input_scope == "word"
                                     else "one_unique_surrounding_sound_pattern; word alignment is unverified")
    details["target_model_peak_probability_uncalibrated"] = span["mean_frame_peak_probability"]
    composed=span.get('combined',False)
    if (phone,target) in ACCEPTED_VARIANTS and not fragmented:
        details['accepted_variant']=ACCEPTED_VARIANTS[(phone,target)]
        result['predicted']=phone
        result['status']='uncertain' if composed or span['mean_frame_peak_probability']<.6 else 'model_match'
        result['articulation_feedback']=articulation_feedback(phone,target,evidence='weak_model_hypothesis' if result['status']=='uncertain' else 'model_hypothesis')
        if result['articulation_feedback']:result['articulation_feedback']['differences']=[]
        result['message']=f'/{phone}/ is an accepted American variant for this practice word; the sound candidate remains provisional.'
        result['reasons']=['American accents vary. No accent correction is assigned.']
        return result
    if (phone,target) in UNRESOLVED_VARIANTS and not fragmented:
        details['unresolved_reason']=UNRESOLVED_VARIANTS[(phone,target)]
        result['predicted']=phone
        result['articulation_feedback']=articulation_feedback(phone,target,evidence='weak_model_hypothesis')
        result['message']=f'The model suggests /{phone}/; this label alone does not establish an error for the selected American reference.'
        result['reasons']=['No accent or stress error is established by these labels alone.']
        return result
    if fragmented or composed or extra_coda or span["mean_frame_peak_probability"] < 0.6:
        result["predicted"] = phone
        result["articulation_feedback"] = articulation_feedback(phone, target, evidence="weak_model_hypothesis")
        result["message"] = ("The model split this vowel into " + " → ".join(f"/{p}/" for p in details["focal_model_labels"]) +
                             f". /{phone}/ is one candidate, not a settled diagnosis." if fragmented else
                             f"The decoded labels were provisionally combined as /{phone}/; listen before using the reference." if composed else
                             f"A tentative candidate is /{phone}/; the evidence is weak, so a pronunciation error is not confirmed.")
        result["reasons"] = ["Listen to your recording before using this candidate's reference. Try recording the word once more."]
        details["unresolved_reason"] = "fragmented_vowel_evidence" if fragmented else "extra_coda_evidence" if extra_coda else "combined_model_labels" if composed else "weak_acoustic_evidence"
        return result
    # A CTC emission run is not phoneme duration. Do not infer vowel length or
    # reject a valid label just because its emission is a single frame.
    result["predicted"] = phone
    result["articulation_feedback"] = articulation_feedback(phone, target, evidence=(
        "weak_model_hypothesis" if input_scope == "context" and phone != target else "model_hypothesis"))
    if (phone, target) in {("i", "iː"), ("u", "uː"), ("e", "ɛ")}:
        result["message"] = f"The model suggests /{phone}/, but notation or length remains unresolved."
        result["reasons"] = ["Compare the quality references; this output does not establish vowel duration or an accent error."]
        details["unresolved_reason"] = "notation_or_length"
        return result
    matched = phone == target
    result["status"] = "model_match" if matched else "possible_difference"
    result["practice_cue"] = practice_cue(phone, target) if not matched else None
    result["message"] = (f"The model's selected sound matches /{target}/." if matched else
                         f"The model suggests /{phone}/ for the selected sound; the target is /{target}/.")
    result["reasons"] = ["This is an experimental label comparison, not an expert pronunciation grade.",
                         "Only the selected sound is compared; the other sounds in the word are not graded."]
    if prompt["family"] == "vowel":
        result["reasons"].append("Vowel quality is compared; how long you held the vowel is not graded.")
    return result
