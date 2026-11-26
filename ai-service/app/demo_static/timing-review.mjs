// A transcript gap is the time between model word spans, which can include
// speech the recognizer missed. Use it as a playback bookmark.
export function timedGroups(words, duration){
  if(!Array.isArray(words) || !Number.isFinite(duration) || duration<=0)return [];
  const groups=[];
  let previousEnd=0;
  for(const token of words){
    if(!token || typeof token.word!=='string' || !token.word.trim() ||
       !Number.isFinite(token.start) || !Number.isFinite(token.end) ||
       token.start<previousEnd || token.end<token.start || token.end>duration+.02)return [];
    const gap=token.start-previousEnd;
    if(!groups.length || gap>=.5){
      groups.push({start:token.start,gap:groups.length?gap:0,words:[]});
    }
    groups.at(-1).words.push(token.word.trim());
    previousEnd=token.end;
  }
  return groups;
}

export function addTimingReview(slot,audio,words,{prompts=[],openWord}={}){
  if(!Array.isArray(words) || !words.length)return;
  function build(){
    const groups=timedGroups(words,audio.duration);
    if(!groups.length)return;
    const details=document.createElement('details'),title=document.createElement('summary');
    title.textContent='Listen to your phrasing';details.append(title);
    const help=document.createElement('p');help.textContent='Play from a group of words. Groups split where estimated word times leave at least half a second. Listen for where one idea ends and the next begins.';
    details.append(help);
    for(const group of groups){
      const row=document.createElement('p');
      if(group.gap){
        const gap=document.createElement('span');gap.className='muted';
        gap.textContent=group.gap.toFixed(1)+' s between recognized words ';
        row.append(gap);
      }
      const play=document.createElement('button');
      play.className='secondary';play.textContent=group.words.join(' ');
      play.setAttribute('aria-label','Play from '+play.textContent);
      play.addEventListener('click',async()=>{
        // Leave a short lead-in so approximate boundaries do not clip the onset.
        audio.currentTime=Math.max(0,group.start-.12);
        try{await audio.play();}
        catch{help.textContent='Use the recording controls above to listen back.';}
      });
      row.append(play);details.append(row);
    }
    if(openWord){
      const choices=[];
      for(const token of words){
        const recognized=token.word.trim().toLowerCase().replace(/^[\p{P}]+|[\p{P}]+$/gu,'');
        if(token.end<=token.start || token.end-token.start>4)continue;
        for(const prompt of prompts.filter(p=>p.word.toLowerCase()===recognized)){
          choices.push({token,prompt});
        }
      }
      if(choices.length){
        const label=document.createElement('label'),select=document.createElement('select');
        label.textContent='Practise a sound from this recording';
        for(const {token,prompt} of choices){
          select.add(new Option(prompt.word+' /'+prompt.target_phone+'/ · '+token.start.toFixed(2)+' s',String(select.length)));
        }
        label.append(select);
        const open=document.createElement('button');open.textContent='Open selected word in sound practice';
        open.addEventListener('click',()=>openWord(choices[Number(select.value)]));
        details.append(label,open);
      }
    }
    slot.append(details);
  }
  if(audio.readyState>=1)build();
  else audio.addEventListener('loadedmetadata',build,{once:true});
}
