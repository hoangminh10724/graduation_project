// Synthetic microphone + mocked model responses: UI flow checks, not accuracy.
const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT||'playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');const out=path.join(root,'data/results/simple_practice');fs.mkdirSync(out,{recursive:true});
const profile=(phone,height,region)=>({phone,family:'vowel',name:'Vowel reference',features:{tongue_height:height,tongue_region:region,lip_shape:'unrounded'}});
const shared={mode:'live_audio',status:'uncertain',target_phone:'iː',predicted_phone:'i',raw_phones:['s','i','t'],
 message:'The model suggests /i/, but notation or length remains unresolved.',reasons:[],score:null,
 details:{unresolved_reason:'notation_or_length',vowel_duration_assessed:false},
 articulation_feedback:{evidence:'model_hypothesis',anatomy_measured:false,observed_reference:profile('i','close/high','front'),target_reference:profile('iː','close/high','front'),differences:[],note:'Reference only.'}};
(async()=>{
 const fixture=path.join(root,'data/results/microphone_level_checks/quiet_sine.wav');
 const browser=await chromium.launch({headless:true,executablePath:process.env.WORDSPEAK_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',
 args:['--disable-background-networking','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream',`--use-file-for-fake-audio-capture=${fixture}`]});
 try{
  const context=await browser.newContext({permissions:['microphone'],viewport:{width:1360,height:1000}});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let calls=0;let answer=shared;
  await page.route('**/demo/analyze',route=>{
   calls++;const body=route.request().postDataBuffer();assert.ok(body.includes(Buffer.from('RIFF')));assert.match(body.toString(),/name="input_scope"\r\n\r\nword/);
   return route.fulfill({json:answer});
  });
  await page.goto('http://127.0.0.1:8013/demo?practice=2');
  await page.waitForFunction(()=>!document.querySelector('[data-practice-record]')?.disabled);
  assert.equal(await page.locator('#practice-more').evaluate(e=>e.open),false);
  assert.equal(await page.locator('#reference-details').evaluate(e=>e.open),true);
  assert.equal(await page.locator('.quick-cue').count(),1);
  await page.getByRole('button',{name:'Try word',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#mode').textContent==='Fresh audio inference' && !document.querySelector('[data-practice-record]').disabled,{},{timeout:15000});
  assert.equal(calls,1);assert.equal(await page.getByRole('button',{name:'Try again',exact:true}).isVisible(),true);
  assert.match(await page.locator('#reference-summary').innerText(),/no length error is established/);
  assert.doesNotMatch(await page.locator('.quick-cue').innerText(),/Raise|Lower/);
  assert.equal(await page.locator('#feedback-details').isVisible(),false);
  assert.equal(await page.locator('#reference-grid .guide:visible').count(),2);
  assert.match(await page.locator('#target-title').innerText(),/Target/);
  answer=structuredClone(shared);answer.status='possible_difference';answer.predicted_phone='ɪ';answer.details={};
  answer.message='The model suggests /ɪ/; the target is /iː/.';
  answer.articulation_feedback.observed_reference=profile('ɪ','near-close','near-front');
  answer.articulation_feedback.differences=[{dimension:'tongue_height',observed_reference:'near-close',target_reference:'close/high',adjustment:'Raise your tongue a little.'},
    {dimension:'tongue_region',observed_reference:'near-front',target_reference:'front',adjustment:'Bring the tongue forward.'}];
  await page.getByRole('button',{name:'Try again',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.quick-cue')?.textContent==='Raise your tongue a little.' && !document.querySelector('[data-practice-record]').disabled,{},{timeout:15000});
  assert.equal(calls,2);assert.equal(await page.locator('#practice-more').evaluate(e=>e.open),false);
  assert.equal(await page.locator('#feedback-details').evaluate(e=>e.open),false);
  assert.doesNotMatch(await page.locator('.quick-cue').innerText(),/forward/);
  await page.locator('#teaching-guide').screenshot({path:path.join(out,'desktop_one_cue.png')});
  assert.equal(await page.locator('#reference-grid .guide:visible').count(),2);
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  await page.locator('#teaching-guide').screenshot({path:path.join(out,'mobile_one_cue.png')});
  assert.deepEqual(errors,[]);
  const report={status:'PASS',revision:'simple-practice-2',one_cue_default:true,one_click_records_and_requests_analysis:true,
   first_attempt_and_retry:true,shared_i_length_reference:true,no_unsupported_length_correction:true,
   genuine_quality_contrast_keeps_two_references:true,advanced_help_optional:true,mobile_overflow:false,
   test_input:'synthetic microphone; model responses mocked for UI cases',classification_accuracy_measured:false,page_errors:errors};
  fs.writeFileSync(path.join(out,'browser_checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
