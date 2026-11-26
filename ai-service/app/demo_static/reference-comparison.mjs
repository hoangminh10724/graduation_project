const signature = profile => profile ? JSON.stringify(Object.entries(profile.features).sort(([a],[b]) => a.localeCompare(b))) : null;

export function referencePresentation(result) {
  if(result?.diagnosis?.kind==='unverified_word_location')return {kind:'target',showObserved:false,title:'Target reference',note:'Select the word to compare its sound.'};
  if (!result?.predicted_phone) return {kind:'target',showObserved:false,title:'Target reference',note:''};
  const feedback=result.articulation_feedback;
  const paired={showObserved:true,title:'Target sound: reference position',
    observedTitle:feedback?.evidence==='weak_model_hypothesis'?'Possible sound: reference position':'Model candidate: reference position'};
  if(result.details?.accepted_variant)return {...paired,kind:'accepted_variant',note:'Both references are accepted American realizations for this practice word. No correction is required.'};
  if(result.details?.unresolved_reason==='stress_not_assessed')return {...paired,kind:'notation',note:'These r-colored vowels share the illustrated quality; the stress difference has not been assessed.'};
  const sameShape=result.predicted_phone===result.target_phone || (feedback &&
    feedback.observed_reference.family===feedback.target_reference.family &&
    signature(feedback.observed_reference)===signature(feedback.target_reference));
  if(sameShape){
    if(result.predicted_phone===result.target_phone)return {...paired,kind:'shared',note:'Both references show the same model sound category. This is not a pronunciation grade.'};
    const labels=`Model /${result.predicted_phone}/ · target /${result.target_phone}/.`;
    const lengthUnknown=result.predicted_phone!==result.target_phone && feedback?.target_reference.family==='vowel';
    const notationHelp=result.predicted_phone==='i' && result.target_phone==='iː'?' Unmarked /i/ is not the same label as /ɪ/, the vowel in sit.':'';
    return {...paired,kind:'shared',note:labels+' '+(lengthUnknown?
      'Both labels use the same illustrated shape. Vowel length has not been assessed; no length error is established.':
      'Both labels use the same illustrated shape. This is a reference, not a measurement of your mouth.')+notationHelp};
  }
  if(result.details?.unresolved_reason==='notation_or_length')return {
    ...paired,kind:'notation',note:'These are references for the two labels. Transcription conventions may differ; these labels do not establish a mouth-shape correction.'};
  return {...paired,kind:'contrast',note:''};
}

export function quickCue(lesson, phone, result) {
  const quality=result?.details?.audio_quality;
  if(quality && (quality.rms<.003 || quality.clipping_fraction>.01) && result.reasons?.length)return result.reasons[0];
  if(result?.diagnosis?.adjustment)return result.diagnosis.adjustment;
  if(result?.status==='possible_difference' && result.articulation_feedback?.differences.length){
    const differences=result.articulation_feedback.differences;
    const next=['lip_shape','place','tongue_height','tongue_region','airflow','voicing'].map(name=>differences.find(d=>d.dimension===name)).find(Boolean);
    return (next || differences[0]).adjustment;
  }
  if(result?.status==='model_match')return `Keep that comfortable shape and say “${lesson.word}” once more.`;
  if(result?.status==='uncertain' && result.articulation_feedback?.differences.length){
    const differences=result.articulation_feedback.differences;
    const next=['lip_shape','place','tongue_height','tongue_region','airflow','voicing'].map(name=>differences.find(d=>d.dimension===name)).find(Boolean);
    return `If /${result.predicted_phone}/ matches what you hear: ${(next || differences[0]).adjustment}`;
  }
  if(result?.status==='uncertain')return `Try “${lesson.word}” once at a comfortable pace.`;
  return lesson.quick_cue || lesson.steps[1].text;
}
