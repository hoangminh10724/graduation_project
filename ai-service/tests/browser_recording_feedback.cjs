// UI regression: backend-produced mock cases, then one real-audio model request.
const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT||'playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');const out=path.join(root,'data/results/recording_diagnosis');
const fixtures=JSON.parse(fs.readFileSync(path.join(out,'ui_fixtures.json'),'utf8'));
const source=path.join(root,'data/results/word_feedback_v2/teacher_shows_word.wav');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.WORDSPEAK_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-background-networking']});
 try{
  const page=await browser.newPage({viewport:{width:1360,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let answer=fixtures.strong;
  await page.route('**/demo/analyze',route=>route.fulfill({json:answer}));
  await page.goto('http://127.0.0.1:8013/demo?feedback=1');
  await page.waitForFunction(()=>!document.querySelector('#prompt').disabled);
  async function check(key,prompt){
   answer=fixtures[key];await page.locator('#prompt').selectOption(prompt);
   assert.equal(await page.locator('#recording-feedback').isVisible(),false);
   await page.locator('#file').setInputFiles(source);
   await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);
   await page.locator('#analyze').click();
   await page.waitForFunction(()=>!document.querySelector('#analyze').disabled && !document.querySelector('#recording-feedback').hidden);
   assert.equal(await page.locator('#recording-feedback').isVisible(),true);
   assert.equal(await page.locator('#feedback-details').evaluate(e=>e.open),false);
   assert.equal(await page.locator('#practice-more').evaluate(e=>e.open),false);
   assert.equal(await page.locator('.quick-cue:visible').count(),0);
   assert.ok((await page.locator('.heard-adjustment').innerText()).length>10);
  }
  await check('strong','she');
  assert.match(await page.locator('.heard-sound').innerText(),/Likely \/s\/.*see/);
  assert.match(await page.locator('.target-sound').innerText(),/ʃ.*she/);
  assert.match(await page.locator('.heard-difference').innerText(),/ridge/);
  assert.match(await page.locator('.heard-adjustment').innerText(),/back/);
  assert.equal(await page.locator('#reference-grid .guide:visible').count(),2);
  await page.locator('#recording-feedback').screenshot({path:path.join(out,'desktop_comparison.png')});
  await check('weak','she');
  assert.match(await page.locator('#result-state').innerText(),/Possible starting sound/);
  assert.match(await page.locator('.heard-sound').innerText(),/Possible \/s\//);
  assert.match(await page.locator('.heard-adjustment').innerText(),/^If \/s\//);
  assert.equal(await page.locator('#predicted-column').isVisible(),true);
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  await page.locator('#recording-feedback').screenshot({path:path.join(out,'mobile_tentative_comparison.png')});
  await check('vowel','seat');
  assert.match(await page.locator('.heard-sound').innerText(),/sit/);
  assert.match(await page.locator('.heard-adjustment').innerText(),/Raise/);
  assert.equal(await page.locator('#reference-grid .guide:visible').count(),2);
  assert.match(await page.locator('#predicted-guide .guide-example').innerText(),/sit/);
  assert.match(await page.locator('#target-guide .guide-example').innerText(),/seat/);
  assert.match(await page.locator('#predicted-guide img').getAttribute('src'),/ih.svg/);
  assert.match(await page.locator('#target-guide img').getAttribute('src'),/iy.svg/);
  const observedWidth=Number(await page.locator('#predicted-guide .lip-aperture').getAttribute('rx'));
  const targetWidth=Number(await page.locator('#target-guide .lip-aperture').getAttribute('rx'));
  assert.ok(targetWidth>observedWidth);
  await page.locator('#reference-grid').screenshot({path:path.join(out,'mobile_sit_vs_seat.png')});
  await page.setViewportSize({width:1360,height:1100});
  await page.locator('#reference-grid').screenshot({path:path.join(out,'desktop_sit_vs_seat.png')});
  await check('unmarked','seat');
  assert.equal(await page.locator('#reference-grid .guide:visible').count(),2);
  assert.equal(await page.locator('#predicted-guide .symbol').innerText(),'/i/');
  assert.equal(await page.locator('#target-guide .symbol').innerText(),'/iː/');
  assert.equal(await page.locator('#predicted-guide .lip-aperture').getAttribute('rx'),await page.locator('#target-guide .lip-aperture').getAttribute('rx'));
  assert.match(await page.locator('#reference-summary').innerText(),/no length error is established/);
  assert.match(await page.locator('#reference-summary').innerText(),/not the same label as \/ɪ\//);
  assert.match(await page.locator('.heard-adjustment').innerText(),/No category-level adjustment/);
  await check('split','seat');
  assert.match(await page.locator('.heard-sound').innerText(),/ɛ.*ɪ/);
  await page.locator('.diagnosis-alternatives summary').click();
  assert.match(await page.locator('.diagnosis-alternatives').innerText(),/If this is what you hear/);
  await check('glide','seat');
  assert.match(await page.locator('.heard-sound').innerText(),/moving vowel in eye/);
  assert.equal(await page.locator('#predicted-column').isVisible(),false);
  await check('silence','she');
  assert.match(await page.locator('.heard-difference').innerText(),/No pronunciation conclusion/);
  assert.equal(await page.locator('#predicted-column').isVisible(),false);
  // Real service request through the page; no mocked response for this attempt.
  await page.unroute('**/demo/analyze');
  await page.locator('#prompt').selectOption('she');await page.locator('#file').setInputFiles(source);
  await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);
  await page.locator('#analyze').click();
  await page.waitForFunction(()=>!document.querySelector('#analyze').disabled && !document.querySelector('#recording-feedback').hidden,{},{timeout:180000});
  assert.match(await page.locator('.heard-sound').innerText(),/\/s\//);
  assert.match(await page.locator('.heard-adjustment').innerText(),/back/);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  assert.deepEqual(errors,[]);
  const report={status:'PASS',revision:'recording-diagnosis-1',heard_difference_adjustment_visible:true,
    weak_candidates_conditional:true,split_vowel_alternatives_visible:true,unsupported_glide_explained:true,
    sit_seat_lips_and_tongue_differ:true,unmarked_i_keeps_both_references:true,no_fabricated_length_or_mouth_error:true,
    silence_not_graded:true,one_primary_adjustment:true,advanced_details_optional:true,
    real_teacher_development_audio_in_browser:true,classification_accuracy_measured:false,mobile_overflow:false,page_errors:errors};
  fs.writeFileSync(path.join(out,'browser_checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
