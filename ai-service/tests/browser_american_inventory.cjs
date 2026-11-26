// UI + real local assets; model answers below are explicitly synthetic fixtures.
const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT||'playwright');
const {spawnSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'data/results/american_expansion');fs.mkdirSync(out,{recursive:true});
const setup=spawnSync(process.env.WORDSPEAK_PYTHON||path.join(root,'data/phoneme-env/Scripts/python.exe'),['ai-service/scripts/build_american_ui_fixtures.py'],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'}});
assert.equal(setup.status,0,setup.stderr);
const fixtures=JSON.parse(fs.readFileSync(path.join(out,'ui_fixtures.json'),'utf8'));
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.WORDSPEAK_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-background-networking']});
 try{
  const page=await browser.newPage({viewport:{width:1360,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8013/demo?american=1');await page.waitForFunction(()=>document.querySelectorAll('.sound-chip').length===41);
  const config=await(await page.request.get('http://127.0.0.1:8013/demo/config')).json();
  assert.equal(config.accent.id,'general_american');assert.equal(config.inventory_counts.vowels,17);assert.equal(config.inventory_counts.consonants,24);
  assert.match(await page.locator('#build-badge').innerText(),/American/);
  await page.locator('#sound-family').selectOption('vowel');assert.equal(await page.locator('.sound-chip:visible').count(),17);
  await page.locator('#sound-search').fill('bird');assert.equal(await page.locator('.sound-chip:visible').count(),1);
  await page.locator('.sound-chip:visible').click();assert.equal(await page.locator('#prompt').inputValue(),'bird');
  await page.locator('#sound-search').fill('');await page.locator('#sound-family').selectOption('consonant');assert.equal(await page.locator('.sound-chip:visible').count(),24);
  await page.locator('#sound-family').selectOption('all');
  for(const prompt of config.prompts.filter(p=>p.primary)){
   await page.locator('#prompt').selectOption(prompt.id);
   await page.locator('#target-guide img').evaluate(image=>image.decode());
   assert.equal(await page.locator('#reference-details').evaluate(e=>e.open),true);
   assert.equal(await page.locator('#teaching-guide').isVisible(),true);
   assert.equal(await page.locator('#target-guide .lip-reference').count(),config.teaching.poses[prompt.target_phone].moving?2:1);
  }
  for(const guide of Object.values(config.guides)){const asset=await page.request.get('http://127.0.0.1:8013'+guide.svg_url);assert.equal(asset.status(),200);assert.match(await asset.text(),/<svg/);}
  await page.locator('#prompt').selectOption('day');
  assert.match(await page.locator('#target-guide').innerText(),/Start \/e\/.*Finish \/ɪ\//s);
  await page.locator('#target-guide').screenshot({path:path.join(out,'desktop_diphthong_reference.png')});
  await page.locator('#prompt').selectOption('fan');assert.equal(await page.locator('#target-guide .front-teeth').getAttribute('visibility'),'visible');
  await page.locator('#prompt').selectOption('thin');assert.equal(await page.locator('#target-guide .front-tongue-tip').getAttribute('visibility'),'visible');
  let answer;await page.route('**/demo/analyze',route=>route.fulfill({json:answer}));
  const audio=path.join(root,'data/results/microphone_level_checks/quiet_sine.wav');
  async function run(key){const fixture=fixtures[key];answer=fixture.response;await page.locator('#prompt').selectOption(fixture.prompt_id);await page.locator('#file').setInputFiles(audio);await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);await page.locator('#analyze').click();await page.waitForFunction(()=>!document.querySelector('#recording-feedback').hidden&&!document.querySelector('#analyze').disabled);}
  await run('diphthong_difference');assert.match(await page.locator('.heard-sound').innerText(),/aɪ/);assert.equal(await page.locator('#predicted-guide .lip-reference').count(),2);
  await run('steady_for_glide');assert.match(await page.locator('.heard-adjustment').innerText(),/move smoothly/);
  await run('nasal_difference');assert.match(await page.locator('.heard-adjustment').innerText(),/nose/);
  await page.getByRole('button',{name:'Watch movement',exact:true}).click();assert.match(await page.locator('#mime-preview').innerText(),/reference|demonstrat/i);
  await run('medial_difference');assert.match(await page.locator('.heard-sound').innerText(),/\/s\//);
  await run('ending_difference');assert.match(await page.locator('.heard-sound').innerText(),/\/n\//);
  await run('extra_ending');assert.match(await page.locator('.heard-adjustment').innerText(),/extra/);
  await run('accepted_merger');assert.match(await page.locator('#result-state').innerText(),/Accepted American/);assert.match(await page.locator('.heard-adjustment').innerText(),/No change is required/);assert.equal(await page.locator('#feedback-details').isVisible(),false);
  await run('r_stress_unknown');assert.match(await page.locator('.heard-adjustment').innerText(),/No stress/);
  await run('weak_affricate');assert.match(await page.locator('.heard-sound').innerText(),/Possible/);assert.match(await page.locator('.heard-adjustment').innerText(),/^If /);
  for(const id of ['near','care','car','four','tour','fire']){await page.locator('#prompt').selectOption(id);assert.equal(await page.locator('#target-guide .lip-reference').count(),2);assert.equal(await page.locator('#teaching-guide').isVisible(),true);}
  await page.setViewportSize({width:390,height:844});
  for(const id of ['seat','day','bird','man','vision','sing','fire']){await page.locator('#prompt').selectOption(id);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);}
  await page.locator('#prompt').selectOption('man');await page.locator('#target-guide').screenshot({path:path.join(out,'mobile_nasal_reference.png')});
  await page.locator('#prompt').selectOption('day');await page.locator('#target-guide').screenshot({path:path.join(out,'mobile_diphthong_reference.png')});
  assert.deepEqual(errors,[]);
  const report={status:'PASS',core_targets:41,vowel_entries:17,consonants:24,r_combinations:6,all_guides_load:true,start_finish_lip_views:true,search_and_family_filter:true,medial_and_final_feedback:true,nasal_airflow_cue:true,accepted_american_variants:true,no_inferred_r_stress:true,weak_affricates_conditional:true,mobile_overflow:false,page_errors:errors,input:'synthetic decoded-label fixtures; not recognition accuracy'};
  fs.writeFileSync(path.join(out,'browser_checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
