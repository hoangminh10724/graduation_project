const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT||'playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');const out=path.join(root,'data/results/lip_reference_checks');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.WORDSPEAK_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-background-networking']});
 try{
  const page=await browser.newPage({viewport:{width:1360,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8013/demo?lips=3');await page.waitForFunction(()=>document.querySelectorAll('.sound-chip').length===41);
  const config=await(await page.request.get('http://127.0.0.1:8013/demo/config')).json();assert.equal(config.teaching.revision,'american-inventory-1');
  const measured={};
  for(const prompt of config.prompts.filter(p=>p.primary&&!config.teaching.poses[p.target_phone].moving)){
   await page.locator('#prompt').selectOption(prompt.id);
   await page.locator('#target-guide img').waitFor({state:'visible'});
   assert.equal(await page.locator('#reference-details').evaluate(e=>e.open),true);
   assert.equal(await page.locator('#target-guide .lip-reference').isVisible(),true);
   assert.equal(await page.locator('#target-guide img').isVisible(),true);
   assert.equal(await page.locator('#practice-more').evaluate(e=>e.open),false);
   measured[prompt.id]=await page.locator('#target-guide .lip-aperture').evaluate(e=>({rx:Number(e.getAttribute('rx')),ry:Number(e.getAttribute('ry'))}));
  }
  assert.ok(measured.seat.rx>measured.sit.rx);assert.ok(measured.sit.rx>measured.food.rx);
  assert.ok(measured.bad.ry>measured.seat.ry);assert.ok(measured.pen.ry<1);
  await page.locator('#prompt').selectOption('seat');
  assert.equal(await page.locator('#target-guide [data-lip-action]').getAttribute('data-lip-action'),'spread');
  assert.ok((await page.locator('#target-guide .lip-direction').getAttribute('d')).length>20);
  assert.match(await page.locator('.quick-cue').innerText(),/spread.*sideways/);
  await page.locator('#target-guide').screenshot({path:path.join(out,'desktop_iy_reference.png')});
  await page.getByRole('button',{name:'Watch movement',exact:true}).click();
  assert.equal(await page.locator('#mime-preview').isVisible(),true);
  assert.equal(await page.locator('#practice-more').evaluate(e=>e.open),false);
  await page.getByText('More help (optional)',{exact:true}).click();
  await page.getByRole('button',{name:'Show movement',exact:true}).click();
  await page.waitForFunction(()=>Number(document.querySelector('#practice-movement').value)===100);
  const targetWidth=Number(await page.locator('.teaching-stage .lip-aperture').getAttribute('rx'));
  await page.locator('#practice-movement').fill('0');
  assert.ok(Number(await page.locator('.teaching-stage .lip-aperture').getAttribute('rx'))<targetWidth);
  await page.locator('#prompt').selectOption('food');
  assert.equal(await page.locator('#target-guide [data-lip-action]').getAttribute('data-lip-action'),'round');
  await page.locator('#target-guide').screenshot({path:path.join(out,'desktop_uw_reference.png')});
  await page.setViewportSize({width:390,height:844});await page.locator('#prompt').selectOption('seat');
  await page.locator('#target-guide').screenshot({path:path.join(out,'mobile_iy_reference.png')});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  assert.deepEqual(errors,[]);
  const report={status:'PASS',revision:'american-inventory-1',targets_checked:Object.keys(measured).length,reference_visible_by_default:true,
   front_lips_and_inside_view:true,iy_wider_than_ih:true,rounded_uw_narrower:true,opening_independent_of_spread:true,
   bilabial_closure:true,spread_direction_arrows:true,animated_width_changes:true,advanced_help_optional:true,
   mobile_overflow:false,page_errors:errors,measured_artwork:measured,teacher_validation:false};
  fs.writeFileSync(path.join(out,'browser_checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
