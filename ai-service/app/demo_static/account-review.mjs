import {wordBank} from './conversation.mjs';
import {transcribeAccountTurn} from './account-turn.mjs';
import {renderProsody} from './prosody.mjs';

const el=id=>document.getElementById(id);
let token='',cards=[],practice,pending,loading=false,recording=false;
let dialogueId=null;
let prompts=[],localEntries=[],catalog=new Map(),turns=new AbortController();
const config=fetch('/demo/config').then(response=>response.json()).then(data=>{
  prompts=data.prompts;
  catalog=new Map(prompts.map(prompt=>[prompt.word.toLowerCase(),prompt.id]));
}).catch(()=>{ /* Free reply and repair remain available. */ });
function controls(){
  el('login').inert=loading;
  el('logout').disabled=loading || recording;
  el('refresh').disabled=loading || recording || Boolean(pending);
  el('ratings').disabled=loading || recording || Boolean(pending);
  el('retry').hidden=!pending || loading;
  el('retry').disabled=recording;
  el('practice').inert=loading;
  el('conversation').inert=loading || recording || Boolean(pending);
  el('saved-conversations').inert=loading || recording || Boolean(pending);
  el('resumed-practice').inert=loading;
  el('vocabulary').inert=loading || recording || Boolean(pending);
}
function discardPractice(){
  dialogueId=null;el('dialogue-history').replaceChildren();el('dialogue-text').value='';
  el('dialogue-status').textContent='';el('conversation').open=false;
  turns.abort();turns=new AbortController();
  practice?.dispose();practice=null;el('practice').replaceChildren();
  el('resumed-practice').replaceChildren();el('resumed-practice').hidden=true;
  el('conversation').hidden=true;
}
function signOut(message){
  setRegistration(false);
  discardPractice();cards=[];pending=null;token='';recording=false;
  el('saved-conversations').hidden=el('session-picker').hidden=true;
  el('session-list').replaceChildren();el('session-status').textContent='';
  el('save-expression').reset();el('local-expression').replaceChildren();localEntries=[];
  el('vocabulary').open=false;el('vocabulary').hidden=true;el('local-expression').hidden=el('local-label').hidden=true;
  el('back').textContent='';el('remaining').textContent='';el('card').hidden=true;
  el('login').hidden=false;el('logout').hidden=true;el('refresh').hidden=true;
  el('account-status').textContent=message;el('password').value='';controls();
}
async function request(path,body,method=body?'POST':'GET'){
  const headers={};
  if(token)headers.Authorization='Bearer '+token;
  if(body)headers['Content-Type']='application/json';
  const response=await fetch('/api/'+path,{method,headers,
    body:body?JSON.stringify(body):undefined,cache:'no-store',redirect:'error'});
  if(response.status===401){
    const message=token?'Your session expired. Sign in again.':'Check your email and password.';
    signOut(message);throw new Error(message);
  }
  if(path==='auth/register' && response.status===409)throw new Error('This email already has an account. Choose Sign in to continue.');
  if(!response.ok)throw new Error('The account service could not complete this request. Try again.');
  return response.json();
}
function showCard(){
  discardPractice();
  const card=cards[0];el('card').hidden=!card;
  if(!card){el('account-status').textContent='Your due-card review is complete.';return;}
  el('remaining').textContent=cards.length+' due '+(cards.length===1?'card':'cards');
  el('back').textContent=card.back;el('card-note').open=false;
  const fixedPrompt={id:catalog.get(card.front.trim().toLowerCase()) || 'card-'+card.id,word:card.front,
    phrase:card.practice_key && card.back!==card.front ? card.back : '',situation:card.situation || ''};
  startPractice(el('practice'),fixedPrompt);
}
function startPractice(container,fixedPrompt){
  el('conversation').hidden=false;
  practice=renderProsody(container,{fixedPrompt,spokenTutor:async (blob,focus)=>{
    if(loading || recording)throw new Error('Finish the current turn and try again.');
    loading=true;controls();
    try{
      if(dialogueId===null)dialogueId=(await request('sessions',{topic:[fixedPrompt.word,fixedPrompt.situation].filter(Boolean).join(' — ').slice(0,120)})).id;
      const response=await fetch('/api/sessions/'+dialogueId+'/spoken-turn?focus='+encodeURIComponent(focus),{
        method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'audio/wav'},body:blob,signal:turns.signal});
      if(response.status===401){signOut('Your session expired. Sign in again.');throw new Error('Sign in again.');}
      if(!response.ok)throw new Error('The tutor could not check this recording. Listen back or try again.');
      const turn=await response.json();
      if(turn.reply){
        appendTurn(turn.text,turn.reply);practice.followUp(turn.reply);el('conversation').open=true;
      }
      return turn;
    }finally{loading=false;controls();}
  },transcribe:async blob=>{
    const draft=el('dialogue-text'),signal=turns.signal;
    const result=await transcribeAccountTurn(blob,token,signal);
    if(!signal.aborted && !draft.value.trim())draft.value=result.text;
    return result;
  },onBusy:value=>{recording=value;controls();}});
}
async function loadCards(){
  cards=await request('cards/due');await config;
  el('account-status').textContent='';showCard();
}
async function run(action){
  if(loading || recording)return;
  loading=true;controls();
  try{await action();}
  catch(error){el('account-status').textContent=error.message;}
  finally{loading=false;controls();}
}
let registering=false;
function setRegistration(value){
  registering=value;
  el('password').value='';
  el('password').autocomplete=value?'new-password':'current-password';
  el('password').minLength=value?8:1;
  el('password-help').hidden=!value;
  el('auth-submit').textContent=value?'Create account':'Sign in';
  el('auth-switch').textContent=value?'Sign in instead':'Create a new account';
}
el('auth-switch').addEventListener('click',()=>{
  setRegistration(!registering);el('account-status').textContent='';el('email').focus();
});
el('login').addEventListener('submit',event=>{
  event.preventDefault();run(async()=>{
    const password=el('password').value;
    if(registering && new TextEncoder().encode(password).length>72)throw new Error('Use a password of at most 72 UTF-8 bytes.');
    const newAccount=registering;
    const result=await request(registering?'auth/register':'auth/login',{email:el('email').value.trim(),password});
    token=result.access_token;el('password').value='';el('login').hidden=true;
    el('logout').hidden=el('refresh').hidden=el('vocabulary').hidden=el('saved-conversations').hidden=false;await loadCards();
    if(newAccount && token && !cards.length){
      el('vocabulary').open=true;
      el('account-status').textContent='Account created. Save an expression to start your first practice turn.';
    }
  });
});
el('show-local').addEventListener('click',async()=>{
  await config;
  if(!token)return;
  localEntries=wordBank(prompts).list();
  const select=el('local-expression');
  select.replaceChildren(new Option(localEntries.length?'Choose a word or expression':'No saved words on this device',''));
  localEntries.forEach((entry,index)=>select.add(new Option(entry.word,String(index))));
  select.hidden=el('local-label').hidden=false;
});
el('local-expression').addEventListener('change',()=>{
  const value=el('local-expression').value;
  if(value==='')return;
  const entry=localEntries[Number(value)];
  el('expression').value=entry.word;el('example').value=entry.phrase || '';el('situation').value=entry.situation || '';
});
el('save-expression').addEventListener('submit',event=>{
  event.preventDefault();run(async()=>{
    const payload={word:el('expression').value.trim(),phrase:el('example').value.trim(),situation:el('situation').value.trim()};
    const result=await request('practice-words',payload,'PUT');
    const updated=await request('cards/due');
    // Preserve any in-progress recording while refreshing the remaining queue.
    if(cards.length && updated.some(card=>card.id===cards[0].id)){
      const current=cards[0];cards=[current,...updated.filter(card=>card.id!==current.id)];
      el('remaining').textContent=cards.length+' due '+(cards.length===1?'card':'cards');
    }else{cards=updated;showCard();}
    el('account-status').textContent='Saved “'+result.front+'” to your account.';
    el('vocabulary').open=false;
  });
});
el('refresh').addEventListener('click',()=>run(loadCards));
el('list-sessions').addEventListener('click',()=>run(async()=>{
  const sessions=await request('sessions'),select=el('session-list');
  select.replaceChildren();
  for(const session of sessions){
    const topic=session.topic || 'Daily conversation';
    const option=new Option(topic+' (session '+session.id+')',String(session.id));
    option.dataset.topic=topic;select.add(option);
  }
  el('session-picker').hidden=!sessions.length;
  el('session-status').textContent=sessions.length?'':'No saved conversations yet.';
}));
function appendTurn(text,replyText){
  const entry=document.createElement('li');
  const learner=document.createElement('p'),reply=document.createElement('p');
  learner.textContent='You: '+text;reply.textContent='Tutor: '+replyText;
  entry.append(learner,reply);el('dialogue-history').append(entry);
}
el('resume-session').addEventListener('click',()=>run(async()=>{
  const option=el('session-list').selectedOptions[0];
  if(!option)return;
  const history=await request('sessions/'+option.value+'/turns');
  discardPractice();dialogueId=Number(option.value);
  el('card').hidden=true;el('resumed-practice').hidden=false;
  const topic=option.dataset.topic;
  const [expression]=topic.split(' — ');
  startPractice(el('resumed-practice'),{id:'session-'+dialogueId,word:expression,phrase:'',
    situation:history.at(-1)?.reply || topic});
  for(const turn of history)appendTurn(turn.text,turn.reply);
  practice.followUp(history.at(-1)?.reply);
  el('conversation').open=true;el('session-picker').hidden=true;
  el('session-status').textContent='Resumed '+topic+'.';el('account-status').textContent='';
}));
el('dialogue-form').addEventListener('submit',event=>{
  event.preventDefault();run(async()=>{
    const draft=el('dialogue-text'),line=draft.value.trim(),card=cards[0];
    if(!line || (!card && dialogueId===null))return;
    const status=el('dialogue-status');
    status.textContent='Waiting for your tutor…';
    try{
      if(dialogueId===null){
        const topic=[card.front,card.situation].filter(Boolean).join(' — ').slice(0,120);
        dialogueId=(await request('sessions',{topic})).id;
      }
      const response=await fetch('/api/chat/stream',{method:'POST',signal:turns.signal,
        headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
        body:JSON.stringify({session_id:dialogueId,text:line})});
      if(response.status===401){signOut('Your session expired. Sign in again.');return;}
      if(!response.ok)throw new Error();
      const events=(await response.text()).split(/\r?\n/).filter(row=>row.startsWith('data:')).map(row=>JSON.parse(row.slice(5)));
      const done=events.find(message=>message.type==='done');
      if(!done?.text)throw new Error();
      appendTurn(line,done.text);
      practice.followUp(done.text);
      draft.value='';status.textContent='Reply received. Record or type your next turn.';
    }catch{
      if(token)status.textContent='A tutor reply could not be confirmed. Your draft is still here.';
    }
  });
});
el('logout').addEventListener('click',()=>signOut('Signed out.'));
async function submitReview(){
  const result=await request('reviews',pending);
  if(result.card.id!==pending.card_id)throw new Error('Unexpected review response. Retry saving this review.');
  pending=null;cards.shift();showCard();
  if(cards.length)el('account-status').textContent='Review saved.';
}
for(const button of el('ratings').querySelectorAll('button')){
  button.addEventListener('click',()=>run(async()=>{
    if(!pending)pending={card_id:cards[0].id,rating:Number(button.dataset.rating),request_id:crypto.randomUUID()};
    await submitReview();
  }));
}
el('retry').addEventListener('click',()=>run(submitReview));
window.addEventListener('pagehide',()=>signOut('Signed out.'));
