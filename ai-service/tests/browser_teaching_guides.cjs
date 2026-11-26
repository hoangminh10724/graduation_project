const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT || 'playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');const out=path.join(root,'data/results/discovery_guides');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.WORDSPEAK_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-background-networking']});
 try{
  const page=await browser.newPage({viewport:{width:1360,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8013/demo?guides=1');await page.waitForFunction(()=>document.querySelectorAll('.sound-chip').length===41);
  const config=await(await page.request.get('http://127.0.0.1:8013/demo/config')).json();
  assert.equal(config.teaching.revision,'american-inventory-1');
  for(const prompt of config.prompts.filter(p=>p.primary)){
   await page.locator('#prompt').selectOption(prompt.id);
   const lesson=page.locator('#teaching-guide');assert.equal(await lesson.isVisible(),true);
   assert.equal(await lesson.locator('#practice-more').evaluate(e=>e.open),false);
   assert.equal(await lesson.locator('.quick-cue').count(),1);
   assert.equal(await lesson.getByRole('button',{name:'Try word',exact:true}).isVisible(),true);
   await lesson.getByText('More help (optional)',{exact:true}).click();
   assert.equal(await lesson.locator('.physical-control').count(),4);assert.equal(await lesson.locator('.practice-step').count(),4);
   const before=await lesson.locator('.teaching-stage svg').evaluate(svg=>svg.innerHTML);
   await lesson.locator('.practice-step').nth(2).click();
   assert.equal(await lesson.locator('.practice-step').nth(2).getAttribute('aria-pressed'),'true');
   assert.notEqual(await lesson.locator('.teaching-stage svg').evaluate(svg=>svg.innerHTML),before);
   await lesson.locator('.physical-control').getByText('Lips',{exact:true}).click();
   assert.equal(await lesson.getByRole('button',{name:'Lips',exact:true}).getAttribute('aria-pressed'),'true');
   assert.ok((await lesson.locator('.control-hint').innerText()).length>5);
   await lesson.locator('#practice-movement').fill('25');assert.equal(await lesson.locator('#practice-movement').inputValue(),'25');
   assert.match(await lesson.getByRole('link',{name:'Read the teaching source'}).getAttribute('href'),/^https:\/\/(adrian|opentext\.ku\.edu)/);
  }
  await page.locator('#prompt').selectOption('she');
  await page.getByRole('button',{name:'Watch movement',exact:true}).click();
  assert.equal(await page.locator('#mime-preview').isVisible(),true);
  assert.equal(await page.locator('#practice-more').evaluate(e=>e.open),false);
  await page.getByText('More help (optional)',{exact:true}).click();
  await page.getByRole('button',{name:'Show movement',exact:true}).click();
  await page.waitForFunction(()=>Number(document.querySelector('#practice-movement').value)===100);
  await page.locator('#teaching-guide').screenshot({path:path.join(out,'desktop_s_to_sh.png')});
  await page.setViewportSize({width:390,height:844});
  await page.waitForFunction(()=>document.querySelector('.teaching-stage svg').getAttribute('viewBox')==='0 0 320 480');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  await page.locator('#teaching-guide').screenshot({path:path.join(out,'mobile_s_to_sh.png')});
  await page.locator('#prompt').selectOption('pen');await page.getByText('More help (optional)',{exact:true}).click();await page.locator('.practice-step').nth(0).click();
  const closure=await page.locator('.teaching-stage .lip-aperture').getAttribute('ry');
  await page.locator('.practice-step').nth(1).click();const release=await page.locator('.teaching-stage .lip-aperture').getAttribute('ry');
  assert.ok(Number(release)>Number(closure));
  await page.locator('#prompt').selectOption('sit');await page.getByText('More help (optional)',{exact:true}).click();assert.match(await page.locator('#teaching-guide').innerText(),/does not measure vowel length/);
  await page.emulateMedia({reducedMotion:'reduce'});await page.getByRole('button',{name:'Show movement',exact:true}).click();
  assert.equal(await page.locator('#practice-movement').inputValue(),'100');
  assert.deepEqual(errors,[]);
  const report={status:'PASS',revision:'american-inventory-1',primary_lessons:config.primary_targets.length,one_cue_default:true,optional_help_closed:true,four_controls_per_lesson:true,four_steps_per_lesson:true,
   changed_visuals:true,manual_movement:true,animated_movement:true,stop_closure_release:true,
   sources_linked:true,mobile_stacked_views:true,mobile_overflow:false,reduced_motion:true,page_errors:errors,
   recognition_accuracy_measured:false,student_learning_outcomes_measured:false};
  fs.writeFileSync(path.join(out,'browser_checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
