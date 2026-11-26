import assert from 'node:assert/strict';
import {movementPlan} from '../app/demo_static/practice-plan.mjs';
const poses={i:{family:'vowel'},ih:{family:'vowel'},a:{family:'vowel'},u:{family:'vowel'},s:{family:'consonant',manner:'fricative'},z:{family:'consonant',manner:'fricative'},sh:{family:'consonant',manner:'fricative'},p:{family:'consonant',manner:'plosive'}};
const teaching={poses,lessons:{i:{anchor_phone:'ih',anchor_word:'sit',word:'seat',mode:'glide'},sh:{anchor_phone:'s',anchor_word:'see',word:'she',mode:'flow'},p:{anchor_phone:'s',anchor_word:'see',word:'pen',mode:'release'}}};
const result=(phone,differences=[{dimension:'place'}])=>({predicted_phone:phone,status:'possible_difference',articulation_feedback:{differences,evidence:'model_hypothesis'}});
// The observed category must replace the fixed lesson anchor, even for a new error.
assert.equal(movementPlan(teaching,'i',result('a')).fromPhone,'a');
assert.equal(movementPlan(teaching,'sh',result('z')).fromPhone,'z');
assert.equal(movementPlan(teaching,'sh',result('z')).personalized,true);
const weak={...result('z'),status:'uncertain'};
assert.match(movementPlan(teaching,'sh',weak).caption,/If you hear/);
assert.match(movementPlan(teaching,'sh',weak).note,/tentative/);
// No category/shape correction should be fabricated for an equivalent reference.
assert.equal(movementPlan(teaching,'i',result('i',[])).mode,'hold');
assert.equal(movementPlan(teaching,'i',result('i',[])).fromPhone,'i');
// An unknown category or incompatible articulatory mechanism uses a labeled example.
assert.equal(movementPlan(teaching,'i',result('unknown')).personalized,false);
assert.equal(movementPlan(teaching,'p',result('s')).personalized,false);
assert.match(movementPlan(teaching,'p',result('s')).note,/does not reconstruct/);
assert.equal(movementPlan(teaching,'i',null).fromPhone,'ih');
console.log('Starting-category transitions, conditional evidence and non-diagnostic references passed.');
