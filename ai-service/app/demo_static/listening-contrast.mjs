import {conversationVoice} from './conversation-voice.mjs';

// Original listening items. The carrier sentence is identical for both alternatives.
const pairs=[
  {words:['seat','sit'],line:'They said WORD.',cue:'Move between the vowels in seat and sit. Notice the tongue height.'},
  {words:['bed','bad'],line:'The word was WORD.',cue:'Try bed, then bad. Let the jaw open further for the vowel in bad.'},
  {words:['full','fool'],line:'I heard WORD.',cue:'Explore how the tongue and lip shape change between full and fool.'},
  {words:['cup','cap'],line:'Can you find the WORD?',cue:'Compare the relaxed central vowel in cup with the more open front vowel in cap.'},
  {words:['fan','van'],line:'Look at the WORD.',cue:'Keep the upper teeth near the lower lip. Explore adding voice for van.'},
  {words:['thin','tin'],line:'The word was WORD.',cue:'Feel the air continue through thin and release after the closure in tin.'},
  {words:['sip','ship'],line:'They said WORD.',cue:'Compare the tongue position and lip shape at the start of sip and ship.'},
  {words:['chin','shin'],line:'I hurt my WORD.',cue:'Feel the brief closure at the start of chin, then try the continuous airflow in shin.'},
  {words:['light','right'],line:'The word was WORD.',cue:'Try the tongue-tip contact in light and the r shape in right.'},
  {words:['back','bag'],line:'They said WORD.',cue:'Listen through the whole word, including the vowel before the final consonant.'},
  {words:['rice','rise'],line:'The word was WORD.',cue:'Compare the vowel timing and the final friction. Notice whether you feel voice.'},
  {words:['sing','sin'],line:'I heard WORD.',cue:'Keep nasal airflow and compare a closure at the back of the tongue with one at the ridge behind the teeth.'},
];
function node(tag,text){
  const item=document.createElement(tag);
  if(text)item.textContent=text;
  return item;
}
export function renderListeningContrast(container){
  const label=node('label','Choose two words'),select=node('select');
  label.append(select);
  for(const pair of pairs)select.append(node('option',pair.words.join(' / ')));
  const play=node('button','Play a line'),answers=node('div'),status=node('p');
  answers.className='quick-actions';status.setAttribute('role','status');
  container.append(label,play,answers,status);
  let target=null,heard=false,answered=false,available=false,busy=false;
  const choices=[node('button'),node('button')];
  choices.forEach((button,index)=>{
    button.className='secondary';
    button.addEventListener('click',()=>{
      if(!heard || answered)return;
      answered=true;const pair=pairs[select.selectedIndex];
      status.textContent=(index===target?'You heard it. ':'Listen once more. ')+
        'The line used “'+pair.words[target]+'”. '+pair.cue;
      controls();
    });
    answers.append(button);
  });
  function controls(){
    play.disabled=busy || !available;
    play.textContent=answered?'Try another line':heard?'Replay line':'Play a line';
    for(const button of choices)button.disabled=busy || !heard || answered;
    select.disabled=busy;
  }
  const voice=conversationVoice({onState:state=>{
    available=state.available;
    if(state.finished){heard=true;status.textContent='Which word did you hear?';}
    if(state.failed){heard=false;status.textContent='Playback failed. Try again or choose an installed US English voice in your device settings.';}
    if(!available)status.textContent='This activity needs an installed US English voice available to your browser.';
    controls();
    if(state.speaking)play.disabled=true;
  }});
  function reset(){
    voice.stop();target=null;heard=false;answered=false;
    choices.forEach((button,index)=>{button.textContent=pairs[select.selectedIndex].words[index];});
    if(available)status.textContent='Listen to the device voice, then choose the word you heard.';
    controls();
  }
  select.addEventListener('change',reset);
  container.addEventListener('toggle',()=>{if(!container.open)reset();});
  play.addEventListener('click',()=>{
    if(target===null || answered)target=Math.floor(Math.random()*2);
    heard=false;answered=false;status.textContent='Listening…';controls();
    const pair=pairs[select.selectedIndex];
    voice.play(pair.line.replace('WORD',pair.words[target]),false);
  });
  reset();
  return {
    pause:reset,
    setBusy(value){if(value && !busy)reset();busy=value;controls();},
    dispose(){voice.dispose();},
  };
}
