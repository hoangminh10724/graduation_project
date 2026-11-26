import {decodeAudio} from './audio.mjs?v=20261125-7';
import {pitchFrames} from './pitch.mjs?v=20261125-7';

const unclear=(detail)=>({title:'Could not confirm this target',detail});
const matched=(detail)=>({title:'This cue matched your target',detail});
const retry=(detail)=>({title:'Try one adjustment',detail});
const NUM_WORDS={'0':'zero','1':'one','2':'two','3':'three','4':'four','5':'five','6':'six','7':'seven','8':'eight','9':'nine','10':'ten',
  '11':'eleven','12':'twelve','13':'thirteen','14':'fourteen','15':'fifteen','16':'sixteen','17':'seventeen','18':'eighteen','19':'nineteen',
  '20':'twenty','30':'thirty','40':'forty','50':'fifty','60':'sixty','70':'seventy','80':'eighty','90':'ninety'};
const token=s=>{const raw=s.toLowerCase().replace(/’/g,"'").replace(/[^a-z0-9']/g,'');return NUM_WORDS[raw]||raw.replace(/[0-9]/g,'');};

// Short-time levels used for relative cues within one take. ASR boundaries
// locate the exercise; agreement with the transcript alone never passes it.
function levels(samples,rate,start,end){
  const frames=[],step=Math.round(.02*rate);
  for(let i=Math.max(0,Math.round(start*rate));i+step<=Math.min(samples.length,end*rate);i+=step){
    let sum=0;
    for(let j=i;j<i+step;j++)sum+=samples[j]**2;
    frames.push(Math.sqrt(sum/step));
  }
  return frames;
}

export function assessExercise({id,variant,expected},words,samples,rate){
  const all=words.map(w=>({...w,key:token(w.word)})).filter(w=>w.key);
  const targetTokens=(expected||'').split(/\s+/).filter(Boolean);
  let span=[];
  if(targetTokens.length && all.length>=targetTokens.length){
    for(let i=0;i<=all.length-targetTokens.length;i++){
      if(targetTokens.every((tok,j)=>all[i+j].key===tok)){
        span=all.slice(i,i+targetTokens.length);
        break;
      }
    }
  }
  if(!span.length ||
     span.some((w,i)=>!(w.start>=0 && w.end>w.start && w.end<=samples.length/rate+.025) ||
                        (i>0 && w.start<span[i-1].end))){
    return unclear('The recognizer could not locate the practice line reliably. Listen back and try the line once more.');
  }
  const first=span[0],last=span.at(-1);
  if(id==='intonation'){
    const frames=pitchFrames(samples.subarray(Math.round(first.start*rate),Math.round(last.end*rate)),rate);
    const voiced=frames.filter(f=>f.hz!==null);
    const tail=voiced.slice(-6);
    if(tail.length<5 || last.end-first.start-tail.at(-1).time>.22 ||
       tail.some((f,i)=>i>0 && f.time-tail[i-1].time>.085)){
      return unclear('There was too little steady voice at the end to compare the pitch. Try “Really” again.');
    }
    const delta=12*Math.log2((tail.at(-1).hz+tail.at(-2).hz)/(tail[0].hz+tail[1].hz));
    if(Math.abs(delta)>10)return unclear('The pitch estimate jumped at the end. Replay the ending and try again.');
    if(Math.abs(delta)<1.5)return unclear('The ending sounded fairly level in this measurement. Try a clearer '+variant+'.');
    const direction=delta>0?'rise':'fall';
    return direction===variant?matched('The recorded ending showed a '+direction+', as intended for this version of “Really”.'):
      retry('The ending showed a '+direction+'. Try tracing a '+variant+' with your hand as you speak.');
  }
  if(id==='connected-speech' || id==='thought-groups'){
    const index=id==='connected-speech'?0:1;
    const left=span[index],right=span[index+1];
    // Include the adjoining word edges: ASR sometimes places contiguous timestamps across a pause.
    const frames=levels(samples,rate,Math.max(left.start,left.end-.12),Math.min(right.end,right.start+.12));
    const peak=Math.max(...frames);
    if(frames.length<3 || peak<.012)return unclear('The word boundary was too quiet to check. Try the line again.');
    let longest=0,run=0;
    for(const v of frames){run=v<Math.min(.008,peak*.1)?run+1:0;longest=Math.max(longest,run);}
    const pause=longest*.02;
    if(id==='connected-speech')return pause<.18?matched('There was no long quiet break between “take” and “a”. Replay the join.'):
      retry('There was a quiet break between “take” and “a”. Try carrying one word into the next.');
    return pause>=.18?matched('A quiet break was audible near the end of “after work”, where you planned a boundary.'):
      retry('There was little quiet space after “work”. For this version, try a brief pause before the invitation.');
  }
  if(id==='word-stress'){
    const frames=levels(samples,rate,first.start,first.end);
    const peaks=[];
    for(let i=1;i+1<frames.length;i++){
      if(frames[i]>=Math.max(...frames)*.22 && frames[i]>=frames[i-1] && frames[i]>frames[i+1]){
        const prev=peaks.at(-1);
        if(prev===undefined || (i-prev>=4 && Math.min(...frames.slice(prev,i+1)) < .55*Math.min(frames[i],frames[prev])))peaks.push(i);
        else if(frames[i]>frames[prev])peaks[peaks.length-1]=i;
      }
    }
    if(peaks.length!==2)return unclear('The two beats in “about” could not be separated clearly. Try a light “a” followed by a fuller “BOUT”.');
    const difference=20*Math.log10(frames[peaks[1]]/frames[peaks[0]]);
    if(Math.abs(difference)<3)return unclear('The two beats had similar levels. Replay them and listen for a lighter first syllable.');
    return difference>0?matched('The second of two measured beats was louder, one cue for the stress in “about”.'):
      retry('The first of two measured beats was louder. Try a lighter first syllable and give “BOUT” the main beat.');
  }
  const wanted=id==='weak-forms'?(variant==='offer'?'drive':'can'):variant;
  const peakPitch=(start,end)=>{
    const s=Math.max(0,Math.round(start*rate)), e=Math.min(samples.length,Math.round(end*rate));
    if(e-s<Math.round(.06*rate))return null;
    const hz=pitchFrames(samples.subarray(s,e),rate,{hopSec:.015,threshold:.16}).map(f=>f.hz).filter(Number.isFinite).sort((a,b)=>a-b);
    return hz.length>=2?hz[Math.min(hz.length-1,Math.floor(hz.length*.85))]:null;
  };
  const readings=span.map(w=>{
    const frames=levels(samples,rate,w.start,w.end).sort((a,b)=>a-b);
    const level=frames[Math.floor(.8*frames.length)];
    const dur=Math.max(.05,w.end-w.start);
    return {key:w.key,level,energy:level*Math.sqrt(dur),pitch:peakPitch(w.start,w.end)};
  });
  const target=readings.find(w=>w.key===wanted);
  if(!target || readings.some(w=>!(w.level>.001)))return unclear('There was too little clear audio in the timed words to compare their loudness.');
  const others=readings.filter(w=>w!==target);
  const other=Math.max(...others.map(w=>w.level));
  const difference=20*Math.log10(target.level/other);
  const otherEnergy=Math.max(...others.map(w=>w.energy));
  const energyDiff=20*Math.log10(target.energy/otherEnergy);
  const otherPitches=others.map(w=>w.pitch).filter(Number.isFinite).sort((a,b)=>a-b);
  const semitones=(Number.isFinite(target.pitch)&&otherPitches.length)?12*Math.log2(target.pitch/otherPitches[Math.floor(otherPitches.length/2)]):null;
  const fmt=v=>`${v>=0?'+':''}${v.toFixed(1)}`;
  if(difference>=1.8){
    return matched(`“${wanted}” stood out in loudness (${fmt(difference)} dB), a clear cue for the beat you chose.`);
  }
  if(semitones!==null && semitones>=1.2){
    return matched(`“${wanted}” stood out with higher pitch (${fmt(semitones)} st), a natural cue for the beat you chose.`);
  }
  if(energyDiff>=1.0 && difference>=-1.0){
    return matched(`“${wanted}” stood out in combined duration and loudness (${fmt(energyDiff)} dB), a natural cue for the beat you chose.`);
  }
  if(difference<=-2.0){
    return retry(`Another word was louder than “${wanted}” (${fmt(difference)} dB). Try bringing “${wanted}” forward and keeping the surrounding words light.`);
  }
  const diag=`loudness ${fmt(difference)} dB`+(semitones!==null?` · pitch ${fmt(semitones)} st`:'')+` · energy ${fmt(energyDiff)} dB`;
  return unclear(`The strongest words had similar loudness and pitch (${diag}). Replay the line and listen for the beat on “${wanted}”.`);
}

export async function assessRecording(item,signal){
  if(item.levels?.clippingFraction>.01)return retry('The microphone clipped. Lower the input boost and record again.');
  if(item.levels?.peak<.008)return unclear('Very little sound was recorded. Check the microphone and try again.');
  const goal=item.goal, form=new FormData();
  form.append('audio',item.blob,'turn.wav');
  if(goal.conversation)form.append('focus',goal.focus);
  const response=await fetch(goal.conversation?'/tutor/observe':'/transcribe',{method:'POST',body:form,signal});
  if(response.status===422)return unclear('The recognizer could not make out speech in this take. Replay it or try again closer to the microphone.');
  if(!response.ok)throw new Error('Assessment unavailable');
  const result=await response.json();
  if(goal.conversation){
    const evidence=result.observation;
    const title=evidence.kind==='model_match'?'The checked sound appears on target':
      evidence.kind==='possible_difference'?'Possible sound difference':'Could not confirm the sound';
    return {title,detail:evidence.message,phrasing:evidence.phrasing,text:result.text,start:evidence.start??evidence.expression?.start};
  }
  const audio=await decodeAudio(item.blob);
  return {...assessExercise(goal,result.words,audio.getChannelData(0),audio.sampleRate),text:result.text};
}
