import {addPitchReview} from './pitch-review.mjs';
import {assessRecording} from './phrase-assessment.mjs';
import {addTimingReview} from './timing-review.mjs';
import {conversationVoice} from './conversation-voice.mjs';
import {conversationLesson} from './conversation.mjs';
import {startPCMRecording} from './audio.mjs?v=mic-playback-3';
import {PROSODY_LESSONS,gesturePoints} from './prosody-lessons.mjs?v=physical-practice-1';
const el=(tag,css,text)=>{const node=document.createElement(tag);if(css)node.className=css;if(text!==undefined)node.textContent=text;return node;};
const svgEl=(tag,attrs)=>{const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))node.setAttribute(k,String(v));return node;};

async function transcribeLocal(blob){
  const form=new FormData();form.append('audio',blob,'turn.wav');
  const response=await fetch('/transcribe',{method:'POST',body:form});
  if(!response.ok)throw new Error(response.status===422?'No clear transcript. Listen back or try again.':'Transcription unavailable. You can still replay your turn.');
  return response.json();
}

export function renderProsody(container,{bank,onPracticeWord,fixedPrompt,transcribe=transcribeLocal,captureOptions=()=>({}),onBusy=()=>{},soundPrompts=[],openRecordedWord,spokenTutor}={}) {
  let lesson=PROSODY_LESSONS[0],variant=lesson.variants[0],capture,timer,frame,lastLevel,working=false,disposed=false;
  const recordings=new Map();
  const initial=captureOptions();let deviceId=initial.deviceId||'',gain=initial.gain||1;
  container.replaceChildren();
  const header=el('div','result-heading');header.append(el('h2',null,'Words & meaning'));
  const intro=el('p','muted','Choose a practice goal, rehearse it, and record a take.');
  const topics=el('div','prosody-topics');topics.setAttribute('aria-label','Choose a practice focus');
  const title=el('h3','prosody-title'),variants=el('div','prosody-variants'),meaning=el('p','prosody-meaning');
  const words=el('div','prosody-words');words.setAttribute('aria-label','Reference stress pattern');
  const cue=el('p','quick-cue'),drawing=el('div','prosody-drawing');
  const gesture=el('p','gesture-caption'),details=el('p','muted');
  const action=el('div','quick-actions');
  const trace=el('button','secondary','Trace gesture'),record=el('button',null,'Record phrase'),stop=el('button','secondary','Stop');stop.disabled=true;
  action.append(trace,record,stop);
  const status=el('p','prosody-status','Try the gesture or record whenever you are ready.');status.setAttribute('role','status');
  const meter=el('meter');meter.min=0;meter.max=1;meter.value=0;meter.setAttribute('aria-label','Phrase recording level');
  const clips=el('div','prosody-clips'),check=el('p','feel-check'),reflection=el('div','prosody-reflection');
  reflection.setAttribute('aria-label','Your listening observation');
  for(const text of ['I noticed a change','Try another version']){
    const button=el('button','secondary',text);button.addEventListener('click',()=>{
      for(const other of reflection.querySelectorAll('button'))other.setAttribute('aria-pressed',String(other===button));
      status.textContent=text==='I noticed a change'?'Keep that observation. Try it in your next conversation.':'Choose one change and compare the next attempt. A retry is optional.';
    });button.setAttribute('aria-pressed','false');reflection.append(button);
  }
  const settings=el('details','prosody-settings');settings.append(el('summary',null,'Microphone settings'));
  const micLabel=el('label',null,'Microphone'),mic=el('select');mic.id='prosody-mic';micLabel.htmlFor=mic.id;
  const boostLabel=el('label'),boost=el('input');boost.type='range';boost.min='1';boost.max='8';boost.step='.5';boost.value=String(gain);boost.id='prosody-gain';boostLabel.htmlFor=boost.id;
  const boostText=()=>{boostLabel.textContent=`Microphone input boost: ${gain}×`;};boostText();
  boost.addEventListener('input',()=>{gain=Number(boost.value);boostText();});mic.addEventListener('change',()=>{deviceId=mic.value;});
  async function devices(){
    const options=[{deviceId:'',label:'System default microphone'}];
    try{options.push(...(await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==='audioinput'&&d.deviceId&&d.deviceId!=='default'));}catch{}
    if(disposed)return;mic.replaceChildren();
    options.forEach((d,i)=>{const option=el('option',null,d.label||`Microphone ${i}`);option.value=d.deviceId;mic.append(option);});
    if(options.some(d=>d.deviceId===deviceId))mic.value=deviceId;
  }
  settings.append(micLabel,mic,boostLabel,boost,el('p','muted','Boost applies to new recordings. Clips clear on reload.'));
  const source=el('a',null,'Teaching background');source.target='_blank';source.rel='noopener noreferrer';
  const note=el('p','muted'),boundary=el('p','muted','Lines and beats are teaching references, not measurements of your recording. Use your playback to compare.');
  container.append(header,intro,topics,title,variants,meaning,words,cue,drawing,gesture,details,action,status,meter,clips,check,reflection,settings,note,boundary,source);
  action.before(el('p','muted','When you stop recording, this take goes to the speech service for a practice assessment.'));
  const listening=el('div','conversation-listening');
  const listen=el('button','secondary','Listen to line');
  const slow=el('input');slow.type='checkbox';slow.id='conversation-slow';
  const slowLabel=el('label',null,'Slower playback');slowLabel.htmlFor=slow.id;
  const hiddenText=el('input');hiddenText.type='checkbox';hiddenText.id='conversation-hide-text';
  const hiddenLabel=el('label',null,'Hide line while listening');hiddenLabel.htmlFor=hiddenText.id;
  const voiceInfo=el('p','muted');voiceInfo.setAttribute('role','status');
  const focusLabel=el('label',null,'Choose a word to emphasize'),focusWord=el('select');
  focusLabel.append(focusWord);
  function updateFocusVisibility(){
    focusLabel.hidden=hiddenText.checked || !lesson.conversation || variant.id!=='phrase' || focusWord.options.length<3;
  }
  focusWord.addEventListener('change',()=>{
    meaning.replaceChildren();
    variant.meaning.split(/(\s+)/).forEach((part,index)=>{
      meaning.append(String(index)===focusWord.value ? el('strong',null,part) : document.createTextNode(part));
    });
    cue.textContent=focusWord.value ? 'Give that word the main beat. Try a different word on your next take and listen for a change in meaning.' : lesson.cue;
  });
  listening.append(listen,slow,slowLabel,hiddenText,hiddenLabel,voiceInfo);meaning.after(listening);
  listening.after(focusLabel);
  let voiceAvailable=false,speaking=false;
  const voice=conversationVoice({onState:state=>{
    voiceAvailable=state.available;speaking=state.speaking;
    listen.disabled=working || !voiceAvailable;
    listen.textContent=speaking?'Stop listening':'Listen to line';
    voiceInfo.textContent=state.failed?'Playback was interrupted. Try again.':
      voiceAvailable?'Device voice · US English':'Listening needs an installed US English voice available to this browser.';
  }});
  hiddenText.addEventListener('change',()=>{meaning.hidden=hiddenText.checked;updateFocusVisibility();});
  listen.addEventListener('click',()=>{
    if(speaking){voice.stop();return;}
    pausePlayback();voice.play(variant.meaning,slow.checked);
  });
  const savedLabel=el('label',null,'Saved conversation words'), saved=el('select');
  saved.id='conversation-words'; savedLabel.htmlFor=saved.id;
  const remove=el('button','secondary','Remove saved word');
  const revisit=el('button','secondary','Practice this sound');
  const nextWord=el('button','secondary','Next saved word');
  const addBox=el('details','prosody-settings');
  const addForm=el('form');
  function entryField(labelText,id,maxLength){
    const label=el('label',null,labelText), input=el('input');
    label.htmlFor=id;input.id=id;input.maxLength=maxLength;addForm.append(label,input);
    return input;
  }
  const newWord=entryField('Word or expression','personal-word',100);
  const newLine=entryField('Practice sentence (optional)','personal-line',500);
  const newSituation=entryField('Question or situation for your reply (optional)','personal-situation',500);
  newWord.required=true;
  const add=el('button',null,'Save and practice');add.type='submit';addForm.append(add);
  addBox.append(el('summary',null,'Add your own word or expression'),addForm);
  topics.after(savedLabel,saved,revisit,nextWord,remove,addBox);
  addForm.addEventListener('submit',event=>{
    event.preventDefault();
    if(working)return;
    try{
      const {id,persistent}=bank.add(newWord.value,newLine.value,newSituation.value);
      addForm.reset();addBox.open=false;openWord(id,persistent);saved.focus();
    }catch(error){status.textContent=error.message;newWord.focus();}
  });
  revisit.addEventListener('click',()=>onPracticeWord(saved.value));
  nextWord.addEventListener('click',()=>{
    const next=bank.next(saved.value);
    if(next)openWord(next);

  });
  function updateBank(selected=''){
    saved.replaceChildren(el('option',null,'Choose a saved word'));
    saved.options[0].value='';
    for(const prompt of bank?.list() || []){
      const option=el('option',null,prompt.word); option.value=prompt.id; saved.append(option);
    }
    saved.value=selected;
    remove.hidden=!saved.value;
    revisit.hidden=!bank?.list().some(item=>item.id===saved.value && item.catalogWord);
    nextWord.hidden=saved.options.length<2 || Boolean(saved.value && saved.options.length<3);
    nextWord.textContent=saved.value?'Next saved word':'Practice saved words';
  }
  function openWord(id,persistent=true){
    const prompt=bank.list().find(item=>item.id===id);
    if(!prompt)return;
    showLesson(conversationLesson(prompt));updateBank(id);
    status.textContent=prompt.replyCount ? 'You have recorded '+prompt.replyCount+(prompt.replyCount===1?' reply':' replies')+' for this word. Try a new situation.' : 'Try your first reply using this word.';
    if(!persistent)status.textContent+=' Browser storage is unavailable. Changes last for this tab.';
  }
  saved.addEventListener('change',()=>saved.value?openWord(saved.value):showLesson(PROSODY_LESSONS[0]));
  remove.addEventListener('click',()=>{
    const persisted=bank.remove(saved.value);showLesson(PROSODY_LESSONS[0]);
    if(!persisted)status.textContent='Removed for this tab. Browser storage is unavailable.';
  });
  const partner=el('button','secondary','Ask a listener');
  clips.after(partner);
  const dialog=el('dialog'), listenerTitle=el('h2',null,'What did you hear?');
  listenerTitle.id='listener-title'; dialog.setAttribute('aria-labelledby',listenerTitle.id);
  const listenerAudio=el('audio');listenerAudio.controls=true;
  const gistLabel=el('label',null,'Describe the message in your own words');
  const gist=el('textarea');gist.id='listener-gist';gistLabel.htmlFor=gist.id;
  const beatLabel=el('label',null,'Which word stood out to you?'),heardBeat=el('input');
  heardBeat.maxLength=100;heardBeat.autocomplete='off';beatLabel.append(heardBeat);
  const compare=el('button',null,'Show speaker my response'),close=el('button','secondary','Close');
  const clarify=el('button','secondary','Ask the speaker to clarify');
  const understood=el('button',null,'The clarification answered my question');
  const outcome=el('p','feel-check');outcome.setAttribute('role','status');
  const listenerHelp=el('p');
  dialog.append(listenerTitle,listenerHelp,listenerAudio,gistLabel,gist,beatLabel,compare,close);
  dialog.insertBefore(clarify,close);dialog.insertBefore(understood,close);
  container.append(dialog);partner.after(outcome);
  partner.addEventListener('click',()=>{
    const clip=recordings.get(lesson.id)?.at(-1);
    if(!clip)return;
    understood.hidden=!clip.repair;
    beatLabel.hidden=!clip.intendedFocus;heardBeat.value='';
    listenerHelp.textContent=clip.repair ? 'Your question was “'+clip.repair+'”. Listen to the new reply. You can confirm it answered your question or ask again.' :
      'Listen once. Write what you understood, or enter a question about a detail you missed.';
    pausePlayback();listenerAudio.src=clip.url;gist.value='';compare.disabled=true;dialog.showModal();
  });
  function responseChanged(){
    compare.disabled=!gist.value.trim() && (beatLabel.hidden || !heardBeat.value.trim());
  }
  gist.addEventListener('input',responseChanged);heardBeat.addEventListener('input',responseChanged);
  close.addEventListener('click',()=>dialog.close());
  clarify.addEventListener('click',()=>{
    const clip=recordings.get(lesson.id)?.at(-1);
    if(!clip)return;
    clip.question=gist.value.trim() || 'Could you say that another way?';
    clip.resolved=false;
    dialog.close();showVariant(lesson.variants.find(item=>item.id==='repair'));showClips();
  });
  understood.addEventListener('click',()=>{
    const clip=recordings.get(lesson.id)?.at(-1);
    if(!clip?.repair)return;
    clip.resolved=true;delete clip.question;
    dialog.close();showClips();
  });
  dialog.addEventListener('close',()=>{listenerAudio.pause();listenerAudio.removeAttribute('src');listenerAudio.load();});
  compare.addEventListener('click',()=>{
    const clip=recordings.get(lesson.id)?.at(-1);
    if(clip){
      clip.gist=gist.value.trim();
      clip.heardBeat=clip.intendedFocus ? heardBeat.value.trim() : '';
      delete clip.question;
      clip.resolved=false;
    }
    dialog.close();showClips();
  });
  const topicButtons=[];
  function controls(){
    newWord.disabled=newLine.disabled=newSituation.disabled=add.disabled=working;
    listen.disabled=working || !voiceAvailable;
    partner.disabled=working;
    focusWord.disabled=working;
    clips.inert=working;
    saved.disabled=revisit.disabled=nextWord.disabled=remove.disabled=working; record.disabled=working;stop.disabled=!capture;
    for(const button of [...topicButtons,...variants.querySelectorAll('button')])button.disabled=working;
    boost.disabled=mic.disabled=working;
    for(const button of reflection.querySelectorAll('button'))button.disabled=working||!(recordings.get(lesson.id)?.length);
  }
  function pausePlayback(){voice.stop();for(const audio of clips.querySelectorAll('audio'))audio.pause();}
  async function checkTake(item){
    const request=new AbortController();item.assessmentRequest=request;item.assessment=null;
    item.paintAssessment?.();
    const timeout=setTimeout(()=>request.abort(),120000);
    try{item.assessment=await assessRecording(item,request.signal);}
    catch{item.assessment={title:'Assessment unavailable',detail:'Your recording is ready for playback. Retry the assessment when the speech service is available.',retry:true};}
    finally{clearTimeout(timeout);item.assessmentRequest=null;if(!disposed)item.paintAssessment?.();}
  }
  function addAssessment(slot,item,audio){
    const panel=el('section','take-assessment');panel.setAttribute('aria-label','Recording assessment');
    const heading=el('h4',null,'Recording assessment'), result=el('div');
    result.setAttribute('role','status');panel.append(heading,result);slot.append(panel);
    item.paintAssessment=()=>{
      const a=item.assessment;
      result.replaceChildren(el('strong',null,a?.title||'Checking your recording…'));
      if(!a)return;
      result.append(el('p',null,a.detail));
      if(a.text)result.append(el('p','muted','Recognized speech: '+a.text));
      if(a.phrasing)result.append(el('p',null,a.phrasing.message));
      if(Number.isFinite(a.start)){
        const play=el('button','secondary','Replay the checked passage');
        play.onclick=()=>{audio.currentTime=a.start;audio.play().catch(()=>{});};result.append(play);
      }
      if(a.retry){
        const retry=el('button','secondary','Retry assessment');
        retry.onclick=()=>checkTake(item);result.append(retry);
      }
    };
    item.paintAssessment();
  }
  function showClips(){
    pausePlayback();clips.replaceChildren();
    const latest=recordings.get(lesson.id)?.at(-1);
    partner.hidden=!lesson.conversation || !latest;
    outcome.hidden=!lesson.conversation || !latest?.gist;
    outcome.textContent=latest?.gist ? 'Your listener heard “'+latest.gist+'”. Compare this with your intention. Try Clarify if a detail was missed.' : '';
    if(latest?.question || latest?.resolved || (latest?.repair && !latest.gist)){
      outcome.hidden=false;
      outcome.textContent=latest.question ? 'Your listener asks: '+latest.question :
        latest.resolved ? 'Your listener confirmed that the clarification answered their question.' :
        'Ask your listener whether this reply answered their question: '+latest.repair;
    }
    for(const item of [...(recordings.get(lesson.id)||[])].reverse()){
      const age=item===latest?'Latest':'Earlier';
      const slot=el('div','prosody-clip');slot.append(el('p',null,`${age} attempt: ${item.meaning}`));
      if(item.heardBeat)slot.append(el('p','feel-check','Your listener heard emphasis on “'+item.heardBeat+'”.'));
      const audio=el('audio');audio.controls=true;audio.src=item.url;audio.preload='metadata';audio.setAttribute('aria-label',`${age} phrase recording`);
      audio.addEventListener('play',()=>{if(working){audio.pause();return;}voice.stop();for(const other of clips.querySelectorAll('audio'))if(other!==audio)other.pause();});
      slot.append(audio);
      addAssessment(slot,item,audio);
      addPitchReview(slot,item);
      if(lesson.conversation){
        const button=el('button','secondary','Send for transcription');
        const result=el('p','muted',item.transcript || item.transcriptStatus || '');
        result.setAttribute('role','status');
        button.disabled=Boolean(item.transcript || item.pending);
        button.addEventListener('click',async()=>{
          button.disabled=true;item.pending=true;
          result.textContent=item.transcriptStatus='Transcribing this turn…';
          try{
            const {text,words}=await transcribe(item.blob);
            item.words=words;
            item.recognizedText=text;
            item.transcript='Automatic transcript: '+text;
          }catch(error){item.transcriptStatus=error.message;}
          finally{
            item.pending=false;
            if(!disposed && recordings.get(lesson.id)?.includes(item))showClips();
          }
        });
        slot.append(button,result);
        if(spokenTutor){
          const focusLabel=el('label',null,'Word or expression to check (optional)');
          const focus=el('input');focus.maxLength=120;
          focus.value=item.tutorFocus??fixedPrompt?.word?.slice(0,120)??'';
          focus.disabled=Boolean(item.tutorPending || item.tutorReply);
          focus.addEventListener('input',()=>{item.tutorFocus=focus.value;});
          focusLabel.append(focus);
          const send=el('button','secondary','Check pronunciation with tutor');
          send.disabled=Boolean(item.tutorPending || item.tutorReply);
          const observation=el('p','muted',item.tutorMessage || '');
          observation.setAttribute('role','status');
          send.addEventListener('click',async()=>{
            focus.disabled=send.disabled=item.tutorPending=true;
            observation.textContent='Checking your recording…';
            try{
              const turn=await spokenTutor(item.blob,focus.value.trim());
              item.tutorReply=turn.reply;
              item.tutorMessage=turn.observation.message+(turn.reply?'':' The conversation reply is unavailable.');
              item.tutorSpan=turn.observation;
            }catch(error){item.tutorMessage=error.message;}
            finally{item.tutorPending=false;if(!disposed)showClips();}
          });
          slot.append(focusLabel,send,observation);
          if(Number.isFinite(item.tutorSpan?.expression?.start)){
            const replay=el('button','secondary','Listen from your practice expression');
            replay.addEventListener('click',()=>{audio.currentTime=item.tutorSpan.expression.start;audio.play().catch(()=>{});});
            slot.append(replay);
          }
          if(item.tutorSpan?.phrasing){
            const phrasing=item.tutorSpan.phrasing;
            slot.append(el('p','muted',phrasing.message));
            const replay=el('button','secondary','Hear the phrasing around this break');
            replay.addEventListener('click',()=>{audio.currentTime=Math.max(0,phrasing.start-1);audio.play().catch(()=>{});});
            slot.append(replay);
          }
          if(Number.isFinite(item.tutorSpan?.start)){
            const replay=el('button','secondary','Listen from the checked word');
            replay.addEventListener('click',()=>{audio.currentTime=item.tutorSpan.start;audio.play().catch(()=>{});});
            slot.append(replay);
          }
        }
        if(bank && item.recognizedText){
          const reuse=el('button','secondary','Save an expression from this turn');
          reuse.addEventListener('click',()=>{
            const selection=window.getSelection();
            const selected=selection?.rangeCount && result.contains(selection.anchorNode) &&
              result.contains(selection.focusNode) ? selection.toString().trim() : '';
            addForm.reset();
            newWord.value=selected.length<=newWord.maxLength ? selected : '';
            newLine.value=item.recognizedText;
            addBox.open=true;newWord.focus();
          });
          slot.append(reuse);
        }
        addTimingReview(slot,audio,item.words,{prompts:soundPrompts,openWord:openRecordedWord &&
          (selection=>openRecordedWord(item.blob,selection))});
      }
      clips.append(slot);
    }
  }
  let points,dot;
  function showVariant(next){
    pausePlayback();cancelAnimationFrame(frame);variant=next;
    for(const button of variants.querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.variant===variant.id));
    meaning.textContent=variant.meaning;cue.textContent=lesson.cue;details.textContent=variant.detail||'';details.hidden=!variant.detail;
    words.replaceChildren();
    const conversation=Boolean(lesson.conversation);
    focusWord.replaceChildren(new Option('Choose a word',''));
    if(conversation && variant.id==='phrase'){
      variant.meaning.split(/(\s+)/).forEach((part,index)=>{
        if(/[\p{L}\p{N}]/u.test(part))focusWord.add(new Option(part,String(index)));
      });
    }
    updateFocusVisibility();
    listening.hidden=!conversation;meaning.hidden=conversation && hiddenText.checked;
    for(const item of [words,drawing,gesture,trace,boundary])item.hidden=conversation;
    if(conversation){
      check.textContent=lesson.selfCheck; note.hidden=true; source.href=lesson.source;
      for(const button of reflection.querySelectorAll('button'))button.setAttribute('aria-pressed','false');
      return;
    }
    variant.tokens.forEach((text,index)=>{const token=el('span','prosody-token',text);token.style.setProperty('--weight',String(variant.weights[index]));token.dataset.prominent=String(variant.weights[index]===1);words.append(token);});
    drawing.replaceChildren();
    const svg=svgEl('svg',{viewBox:'0 0 520 180',role:'img','aria-label':lesson.id==='intonation'?'Example pitch movement to trace with your hand':'Example energy gesture; not a measured pitch curve'});
    points=gesturePoints(variant.path);
    svg.append(svgEl('path',{d:points.map((p,i)=>`${i?'L':'M'}${p.x} ${p.y}`).join(' '),fill:'none',stroke:'#668461','stroke-width':4,'stroke-linejoin':'round'}));
    dot=svgEl('circle',{cx:points[0].x,cy:points[0].y,r:9,fill:'#b47b38'});svg.append(dot);drawing.append(svg);
    gesture.textContent=variant.gesture;check.textContent=lesson.selfCheck;note.textContent=lesson.note||'';note.hidden=!lesson.note;
    source.href=lesson.source;for(const button of reflection.querySelectorAll('button'))button.setAttribute('aria-pressed','false');
  }
  function showLesson(next){
    updateBank();lesson=next;
    record.textContent=lesson.conversation?'Record your turn':'Record phrase';title.textContent=lesson.title;variants.replaceChildren();
    for(const item of lesson.variants){const button=el('button','secondary',item.label);button.dataset.variant=item.id;button.addEventListener('click',()=>showVariant(item));variants.append(button);}
    variants.hidden=lesson.variants.length<2;
    for(const [index,button] of topicButtons.entries())button.setAttribute('aria-pressed',String(PROSODY_LESSONS[index]===lesson));
    showVariant(lesson.variants[0]);showClips();status.textContent='Try the gesture or record whenever you are ready.';controls();
  }
  for(const item of PROSODY_LESSONS){const button=el('button','secondary',item.label);button.dataset.prosodyTopic=item.id;button.addEventListener('click',()=>showLesson(item));topics.append(button);topicButtons.push(button);}
  trace.addEventListener('click',()=>{
    cancelAnimationFrame(frame);
    const pills=[...words.querySelectorAll('.prosody-token')];
    const place=t=>{
      const at=t*(points.length-1),i=Math.min(points.length-2,Math.floor(at)),f=at-i;
      dot.setAttribute('cx',points[i].x+(points[i+1].x-points[i].x)*f);
      dot.setAttribute('cy',points[i].y+(points[i+1].y-points[i].y)*f);
      const activeIdx=Math.min(pills.length-1,Math.floor(t*pills.length));
      pills.forEach((p,idx)=>p.classList.toggle('is-active',idx===activeIdx));
    };
    if(matchMedia('(prefers-reduced-motion: reduce)').matches){place(1);status.textContent=variant.gesture;return;}
    const start=performance.now();const animate=now=>{const t=Math.min(1,(now-start)/1700);place(t);if(t<1)frame=requestAnimationFrame(animate);};frame=requestAnimationFrame(animate);
    status.textContent='Follow with your hand. Imagine the phrase before speaking.';
  });
  function level(value){
    if(disposed || value.phase==='recording'&&!capture)return;
    lastLevel=value;meter.value=Math.min(1,value.peak);
    if(value.clippingFraction>.01)status.textContent='Too loud. Lower the boost before the next recording.';
    else if(value.phase==='recording')status.textContent=`Recording phrase · peak ${Math.round(value.peak*100)}%`;
  }
  record.addEventListener('click',async()=>{
    working=true;lastLevel=undefined;onBusy(true);controls();pausePlayback();status.textContent='Waiting for microphone access…';
    try{
      const active=await startPCMRecording({deviceId,gain,onLevel:level});
      if(disposed){await active.stop();return;}
      capture=active;devices();const seconds=lesson.conversation?20:5;status.textContent='Recording. Stop when finished, or recording ends after '+seconds+' seconds.';controls();timer=setTimeout(finish,seconds*1000);
    }catch(error){status.textContent=`Microphone unavailable: ${error.message}`;working=false;onBusy(false);controls();}
  });
  async function finish(){
    if(!capture)return;clearTimeout(timer);const active=capture;capture=undefined;controls();
    try{
      const blob=await active.stop();if(disposed)return;
      const savedClips=recordings.get(lesson.id)||[];
      if(savedClips.length===2){const old=savedClips.shift();old.assessmentRequest?.abort();URL.revokeObjectURL(old.url);}
      const repair=variant.id==='repair' ? savedClips.at(-1)?.question : undefined;
      const intendedFocus=focusWord.selectedOptions[0]?.value ? focusWord.selectedOptions[0].text : '';
      const takeLabel=intendedFocus ? variant.label+' · intended emphasis on '+intendedFocus : variant.label;
      const expected=['word-stress','intonation'].includes(lesson.id)?variant.tokens.join(''):variant.tokens?.join(' ');
      const goal={id:lesson.id,variant:variant.id,conversation:lesson.conversation,focus:lesson.practiceWord?.slice(0,120),
        expected:expected?.toLowerCase().replace(/’/g,"'").replace(/[^a-z' ]/g,'')};
      const item={blob,url:URL.createObjectURL(blob),meaning:takeLabel,intendedFocus,repair,goal,levels:lastLevel};
      savedClips.push(item);recordings.set(lesson.id,savedClips);showClips();checkTake(item);
      const tabOnly=bank && lesson.conversation && variant.id==='reply' && !bank.recordReply(saved.value);
      const levelAdvice=lastLevel?.clippingFraction>.01?' The recording clipped; lower the boost before trying again.':
        lastLevel?.peak<.05?' The input is quiet; adjust Microphone settings if needed.':'';
      status.textContent='Your recording and assessment are below.'+levelAdvice+(tabOnly?' Reply history is available in this tab only.':'');
    }catch(error){if(!disposed)status.textContent=error.message;}
    finally{working=false;onBusy(false);if(!disposed)controls();}
  }
  stop.addEventListener('click',finish);
  showLesson(fixedPrompt?conversationLesson(fixedPrompt):lesson);
  if(fixedPrompt){
    for(const control of [topics,savedLabel,saved,revisit,nextWord,remove,addBox,header,intro])control.hidden=true;
  }
  devices();
  return {
    openWord,
    followUp(text){
      const reply=lesson.variants.find(item=>item.id==='reply');
      if(!reply || !text)return;
      reply.meaning=text;reply.detail='Answer the tutor in your own words.';
      showVariant(reply);
    },
    pause(){pausePlayback();cancelAnimationFrame(frame);},
    dispose(){disposed=true;voice.dispose();clearTimeout(timer);cancelAnimationFrame(frame);pausePlayback();capture?.stop().catch(()=>{});capture=undefined;for(const saved of recordings.values())for(const item of saved){item.assessmentRequest?.abort();URL.revokeObjectURL(item.url);}recordings.clear();},
  };
}
