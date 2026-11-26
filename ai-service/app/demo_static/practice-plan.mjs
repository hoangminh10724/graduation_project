// Choose a teaching transition without treating a sound label as measured anatomy.
export function movementPlan(teaching, target, result) {
  const lesson = teaching.lessons[target];
  const targetPose=teaching.poses[target];
  const fallback = {
    fromPhone: lesson.anchor_phone, mode: lesson.mode,
    caption: `Teaching example: /${lesson.anchor_phone}/ (${lesson.anchor_word}) to /${target}/ (${lesson.word}).`,
    note: 'Try the movement silently, imagine the sound, then say the word. This is a reference demonstration.',
    personalized: false,
  };
  const observed = result?.predicted_phone;
  if(result?.diagnosis?.kind==='unverified_word_location')return fallback;
  if(targetPose.moving)return {...fallback,fromPhone:target,mode:lesson.mode,
    caption:`Target /${target}/: start /${targetPose.start_phone}/, finish /${targetPose.end_phone}/. Compare this with the recording's suggested sound.`,
    note:'This demonstrates the target movement. It does not reconstruct the movement in your recording.'};
  if (!observed || !teaching.poses[observed]) return fallback;
  const feedback = result.articulation_feedback;
  const weak = result.status === 'uncertain' || feedback?.evidence === 'weak_model_hypothesis';
  if (!feedback?.differences?.length) {
    return {fromPhone: target, mode: 'hold', personalized: false,
      caption: `Target shape /${target}/. No mouth-shape change has been established from /${observed}/.`,
      note: 'Mime the target comfortably. Matching reference shapes do not establish correct timing or perfect pronunciation.'};
  }
  const from = teaching.poses[observed], to = teaching.poses[target];
  if(from.moving)return {fromPhone:target,mode:'hold',personalized:false,
    caption:`Suggested /${observed}/ is a moving vowel. Explore the steady target /${target}/.`,
    note:'Compare the two-moment reference below with this steady target example; the recorded tongue path is not measured.'};
  const canMove = from.family === 'vowel' && to.family === 'vowel' ||
    from.manner === 'fricative' && to.manner === 'fricative';
  if (!canMove) return {...fallback,
    note: `The model suggested /${observed}/. This closure/release exercise is a target demonstration; it does not reconstruct your movement.`};
  return {fromPhone: observed, mode: to.family === 'vowel' ? 'glide' : 'flow', personalized: true,
    caption: `${weak ? 'If you hear' : 'Likely sound'} /${observed}/: explore its reference shape, then move toward /${target}/.`,
    note: `${weak ? 'This starting sound is tentative. ' : ''}Try the movement silently, imagine the sound, then say the word. The positions are reference examples.`};
}
