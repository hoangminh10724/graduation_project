import assert from 'node:assert/strict';
import {diagnosisPresentation} from '../app/demo_static/diagnosis.mjs';
import {quickCue} from '../app/demo_static/reference-comparison.mjs';

const diagnosis={kind:'tentative_comparison',heard:'Possible /s/ — the start of see',
  target:'/ʃ/ — the start of she',comparison:'The reference contact is farther forward.',
  adjustment:'If /s/ matches what you hear: move the tongue region slightly back.',alternatives:[]};
const result={status:'uncertain',predicted_phone:'s',target_phone:'ʃ',diagnosis};
assert.equal(diagnosisPresentation(result),diagnosis);
assert.equal(quickCue({word:'she'},'ʃ',result),diagnosis.adjustment);
assert.equal(diagnosisPresentation(null),null);
const quality={...result,diagnosis:{...diagnosis,kind:'audio_quality',adjustment:'Move closer.'},
  details:{audio_quality:{rms:0,clipping_fraction:0}},reasons:['Audio is too quiet.']};
assert.equal(quickCue({word:'she'},'ʃ',quality),'Audio is too quiet.');
console.log('Recording diagnosis and conditional weak-evidence cue checks passed.');
