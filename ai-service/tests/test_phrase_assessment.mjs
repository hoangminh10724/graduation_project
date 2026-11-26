import test from 'node:test';
import assert from 'node:assert/strict';
import {assessExercise,assessRecording} from '../app/demo_static/phrase-assessment.mjs';

const rate=16000;
function exercise(id,variant,line,volumes,ends={}){
  const words=line.split(' ').map((word,i)=>({word,start:i*.4,end:(i+1)*.4}));
  const samples=Float32Array.from({length:6400*words.length},(_,i)=>{
    const part=Math.floor(i/6400);
    const t=(i%6400)/rate;
    return (t<(ends[part]??.4)?volumes[part]:0)*Math.sin(2*Math.PI*180*i/rate);
  });
  return assessExercise({id,variant,expected:line},words,samples,rate);
}
test('focus and weak forms compare a measured cue against the selected variant',()=>{
  assert.match(exercise('sentence-focus','you','what do you think',[.1,.1,.4,.1]).title,/matched/);
  assert.match(exercise('sentence-focus','think','what do you think',[.1,.1,.4,.1]).title,/adjustment/);
  assert.match(exercise('weak-forms','offer','i can drive',[.1,.1,.4]).title,/matched/);
  assert.match(exercise('weak-forms','correct','i can drive',[.1,.1,.4]).title,/adjustment/);
});
test('linking and grouping use silence near the intended word boundary',()=>{
  assert.match(exercise('connected-speech','seat','take a seat',[.3,.3,.3]).title,/matched/);
  const words=[{word:'after',start:0,end:.4},{word:'work',start:.4,end:.8},{word:"let's",start:1.1,end:1.5}];
  const samples=Float32Array.from({length:24000},(_,i)=>i>=12800 && i<17600?0:.25*Math.sin(i/10));
  assert.match(assessExercise({id:'thought-groups',expected:"after work let's"},words,samples,rate).title,/matched/);
});
test('rising and falling pitch distinguish the two readings of Really',()=>{
  for(const direction of [1,-1]){
    const samples=Float32Array.from({length:12800},(_,i)=>{
      const t=i/rate;
      const startHz=direction>0?140:240;
      return .25*Math.sin(2*Math.PI*(startHz*t+direction*95*t*t));
    });
    for(const variant of ['rise','fall']){
      const result=assessExercise({id:'intonation',variant,expected:'really'},[{word:'Really?',start:0,end:.8}],samples,rate);
      assert.match(result.title,(direction>0)===(variant==='rise')?/matched/:/adjustment/);
    }
  }
});
test('word stress needs two distinct beats and the right word',()=>{
  const samples=Float32Array.from({length:16000},(_,i)=>{
    const t=i/rate;
    return (.12*Math.exp(-((t-.25)**2)/.003)+.4*Math.exp(-((t-.7)**2)/.006))*Math.sin(2*Math.PI*170*t);
  });
  const goal={id:'word-stress',variant:'about',expected:'about'};
  assert.match(assessExercise(goal,[{word:'About.',start:0,end:1}],samples,rate).title,/matched/);
  assert.match(assessExercise(goal,[{word:'Around.',start:0,end:1}],samples,rate).title,/Could not confirm/);
});
test('silence and clipping produce recording feedback without sending audio',async()=>{
  assert.match((await assessRecording({levels:{peak:0}})).detail,/microphone/);
  assert.match((await assessRecording({levels:{clippingFraction:.3}})).detail,/clipped/);
});
test('conversational lead-in with digits and pitch prominence match naturally',()=>{
  const words=[
    {word:'Well,',start:0,end:.3},{word:'I',start:.3,end:.6},{word:'booked',start:.6,end:1.0},
    {word:'15',start:1.0,end:1.5},{word:'seats.',start:1.5,end:1.9}
  ];
  // Equal loudness across words, but clearly higher pitch (230 Hz vs 160 Hz) on "15"
  const samples=Float32Array.from({length:Math.round(1.9*rate)},(_,i)=>{
    const t=i/rate;
    const hz=(t>=1.0 && t<1.5)?230:160;
    return .25*Math.sin(2*Math.PI*hz*t);
  });
  const res=assessExercise({id:'prominence',variant:'fifteen',expected:'i booked fifteen seats'},words,samples,rate);
  assert.match(res.title,/matched/);
  assert.match(res.detail,/pitch/);
});
