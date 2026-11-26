// Original short activities. These are practice references, not model predictions.
export const PROSODY_LESSONS = [
  {id:'word-stress', label:'Word stress', title:'One strong syllable, one light syllable',
    cue:'Tap BOUT; let the first syllable stay light: a-BOUT.',
    selfCheck:'Can you hear a light first syllable and a clearer second one? Stress uses timing, pitch and vowel quality as well as loudness.',
    variants:[{id:'about',label:'about',meaning:'A word with its main stress on the second syllable.',
      tokens:['a','BOUT'],weights:[.3,1],path:[.45,.65],gesture:'One light tap, then one fuller tap.',
      detail:'The first vowel can relax toward /ə/. Keep the change comfortable.'}],
    source:'https://adrianunderhill.com/2012/06/07/sentence-stress-prominence-and-word-stress/'},
  {id:'sentence-focus',label:'Sentence focus',title:'Same words. Choose your meaning.',
    cue:'Choose what you mean; give that word the main beat.',
    selfCheck:'Listen back. Would a listener notice the word you meant to bring forward?',
    variants:[
      {id:'you',label:'Invite someone',meaning:'Bring another person into the discussion.',tokens:['What','do','YOU','think?'],weights:[.45,.25,1,.5],path:[.45,.4,.72,.4],gesture:'Give YOU the fullest hand beat.'},
      {id:'think',label:'Ask for an opinion',meaning:'Ask what the person thinks.',tokens:['What','do','you','THINK?'],weights:[.45,.25,.3,1],path:[.45,.4,.4,.72],gesture:'Move the fullest hand beat to THINK.'}],
    source:'https://adrianunderhill.com/2012/06/07/sentence-stress-prominence-and-word-stress/'},
  {id:'intonation',label:'Intonation',title:'Let the pitch carry your intention',
    cue:'Trace the line with your hand; imagine the voice, then say Really.',
    selfCheck:'Did you hear the ending move upward or downward? Which version fits the meaning you chose?',
    variants:[
      {id:'rise',label:'Check what you heard',meaning:'One possible way to ask for confirmation: Really?',tokens:['Real','ly?'],weights:[1,.55],path:[.4,.35,.45,.78],gesture:'Let your hand lift at the end.'},
      {id:'fall',label:'Acknowledge the news',meaning:'One possible acknowledging response: Really.',tokens:['Real','ly.'],weights:[1,.55],path:[.65,.7,.45,.25],gesture:'Let your hand settle at the end.'}],
    note:'These are possible readings in this context. Questions can fall; statements can rise. Pitch alone does not determine meaning.',
    source:'https://adrianunderhill.com/2012/06/07/sentence-stress-prominence-and-word-stress/'},
  {id:'connected-speech',label:'Connected speech',title:'Carry a word into a short phrase',
    cue:'Keep take a in one comfortable flow, then give seat the main beat.',
    selfCheck:'Did the words join comfortably while seat stayed easy to hear?',
    variants:[{id:'seat',label:'Offer a seat',meaning:'Invite someone to sit down: Take a seat.',
      tokens:['Take','a','SEAT'],weights:[.6,.25,1],path:[.55,.45,.7,.3],gesture:'Sweep your hand across the phrase; settle on SEAT.',
      detail:'Try take‿a seat, with a light /ə/ in a. Do not add a pause after every word.'}],
    source:'https://www.teachingenglish.org.uk/professional-development/teachers/knowing-subject/core-pronunciation-activities-using-phonemic'},
  {id:'thought-groups',label:'Pausing',title:'Give the listener time to follow',
    cue:'Say the time first. Leave a small boundary before the invitation.',
    selfCheck:'Can you hear where the time ends and the invitation begins? Try a shorter pause and compare.',
    variants:[{id:'after-work',label:'Make a plan',meaning:'Suggest a plan to a colleague.',
      tokens:['After','WORK,','let’s','get','LUNCH.'],weights:[.45,1,.4,.4,1],path:[.45,.7,.4,.5,.32],
      gesture:'Sweep once for the time and once for the invitation.'}],
    source:'https://adrianunderhill.com/2015/11/30/three-levels-of-pronunciation-an-example-activity/'},
  {id:'weak-forms',label:'Weak forms',title:'Give small words room to change',
    cue:'Try a light can in the offer and a fuller can in the correction.',
    selfCheck:'Does the listener hear the offer or the correction you meant? Compare both readings at a comfortable pace.',
    variants:[
      {id:'offer',label:'Offer help',meaning:'Your friend needs a lift.',tokens:['I','can','DRIVE.'],weights:[.5,.25,1],path:[.45,.42,.3],gesture:'Move lightly through can and tap on drive.',detail:'An unstressed can may sound like /kən/.'},
      {id:'correct',label:'Correct a misunderstanding',meaning:'Your friend thinks you cannot drive.',tokens:['I','CAN','drive.'],weights:[.5,1,.45],path:[.45,.75,.32],gesture:'Tap on can and let drive settle.',detail:'Emphatic can often keeps /æ/.'}],
    source:'https://adrianunderhill.com/2012/06/07/sentence-stress-prominence-and-word-stress/'},
];

export function gesturePoints(path) {
  return path.map((height,index)=>({x:40+index*440/(path.length-1),y:155-height*120}));
}
