import assert from 'node:assert/strict';
import {pitchFrames} from '../app/demo_static/pitch.mjs';
const rate=16000;
function signal(fn){return Float32Array.from({length:rate},(_,n)=>fn(n/rate));}
for(const hz of [80,120,200,320,550]){
 const frames=pitchFrames(signal(t=>.2*Math.sin(2*Math.PI*hz*t)+.1*Math.sin(4*Math.PI*hz*t)),rate);
 for(const frame of frames)assert.ok(Math.abs(frame.hz-hz)/hz<.012);
}
const rise=pitchFrames(signal(t=>.3*Math.sin(2*Math.PI*(120*t+40*t*t))),rate);
assert.ok(rise.at(-1).hz>rise[0].hz+60);
for(const value of [0,.3])assert.ok(pitchFrames(signal(()=>value),rate).every(f=>f.hz===null));
let seed=937;
const noise=signal(()=>{seed=(1664525*seed+1013904223)>>>0;return .4*(seed/4294967296-.5);});
assert.ok(pitchFrames(noise,rate).every(f=>f.hz===null));
assert.ok(pitchFrames(signal(t=>Math.sign(Math.sin(2*Math.PI*160*t))),rate).every(f=>f.hz===null));
console.log('Pitch estimates verified on five harmonic tones, rising pitch, silence, constant input, noise and clipping');
