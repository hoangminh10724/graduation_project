// Synthetic microphone verifies the teaching flow; it does not measure learning.
const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'data/results/physical_practice');fs.mkdirSync(out,{recursive:true});
const fixture=path.join(root,'data/results/microphone_level_checks/quiet_sine.wav');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.WORDSPEAK_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-background-networking','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream',...(fs.existsSync(fixture)?[`--use-file-for-fake-audio-capture=${fixture}`]:[])]});
  try{
    const context=await browser.newContext({permissions:['microphone'],viewport:{width:1360,height:1050}});
    const page=await context.newPage(),errors=[],posts=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts.push(r.url());});
    await page.goto('http://127.0.0.1:8013/demo?learning=1');await page.waitForFunction(()=>!document.querySelector('#mode-prosody').disabled);
    // Compact silent movement does not force open the full lesson.
    await page.getByRole('button',{name:'Watch movement',exact:true}).click();
    assert.equal(await page.locator('#mime-preview').isVisible(),true);
    assert.equal(await page.locator('#practice-more').evaluate(e=>e.open),false);
    assert.equal(await page.locator('#reference-details').evaluate(e=>e.open),true);
    await page.getByRole('button',{name:'Phrases & conversation',exact:true}).click();
    assert.equal(await page.locator('#sound-workspace').isVisible(),false);
    assert.match(await page.locator('#prosody-workspace').innerText(),/goes to the speech service for a practice assessment/);
    await page.route('**/transcribe',route=>route.fulfill({json:{text:'Really?',words:[{word:'Really?',start:0,end:.55}]}}));
    assert.equal(await page.locator('.prosody-topics button').count(),6);
    await page.locator('[data-prosody-topic="sentence-focus"]').click();
    assert.equal(await page.locator('.prosody-token[data-prominent=true]').innerText(),'YOU');
    await page.getByRole('button',{name:'Ask for an opinion',exact:true}).click();
    assert.equal(await page.locator('.prosody-token[data-prominent=true]').innerText(),'THINK?');
    await page.locator('[data-prosody-topic="intonation"]').click();
    const rise=await page.locator('.prosody-drawing path').getAttribute('d');
    await page.getByRole('button',{name:'Acknowledge the news',exact:true}).click();
    assert.notEqual(await page.locator('.prosody-drawing path').getAttribute('d'),rise);
    assert.match(await page.locator('#prosody-workspace').innerText(),/Questions can fall; statements can rise/);
    await page.getByRole('button',{name:'Trace gesture',exact:true}).click();
    assert.match(await page.locator('.prosody-status').innerText(),/Imagine/);
    await page.emulateMedia({reducedMotion:'reduce'});await page.getByRole('button',{name:'Trace gesture',exact:true}).click();
    assert.equal(Number(await page.locator('.prosody-drawing circle').getAttribute('cx')),480);
    async function record(){
      await page.getByRole('button',{name:'Record phrase',exact:true}).click();
      await page.waitForFunction(()=>!document.querySelector('#prosody-workspace .quick-actions button:last-child').disabled);
      assert.equal(await page.locator('#mode-sounds').isDisabled(),true);
      await page.waitForTimeout(700);await page.locator('#prosody-workspace').getByRole('button',{name:'Stop',exact:true}).click();
      await page.waitForFunction(()=>!document.querySelector('#mode-sounds').disabled);
    }
    await record();assert.equal(await page.locator('.prosody-clip audio').count(),1);
    await page.locator('.take-assessment strong').filter({hasNotText:'Checking'}).first().waitFor();
    assert.match(await page.locator('.prosody-status').innerText(),/assessment/);
    await page.getByRole('button',{name:'Check what you heard',exact:true}).click();await record();
    assert.equal(await page.locator('.prosody-clip audio').count(),2);
    const audio=await page.locator('.prosody-clip audio').evaluateAll(async nodes=>Promise.all(nodes.map(async n=>{await new Promise(resolve=>{if(n.readyState>=1)resolve();else n.addEventListener('loadedmetadata',resolve,{once:true});});return {duration:n.duration,size:(await(await fetch(n.src)).blob()).size};})));
    assert.ok(audio.every(a=>a.duration>.25&&a.size>1000));
    await record();assert.equal(await page.locator('.prosody-clip audio').count(),2);
    await page.getByRole('button',{name:'I noticed a change',exact:true}).click();
    assert.match(await page.locator('.prosody-status').innerText(),/next conversation/);
    // Permission failure releases the shared recording lock and allows navigation.
    await page.evaluate(()=>{window.savedGetUserMedia=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Permission denied for test');};});
    await page.getByRole('button',{name:'Record phrase',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('.prosody-status').textContent.includes('Permission denied'));
    assert.equal(await page.locator('#mode-sounds').isEnabled(),true);
    await page.evaluate(()=>{navigator.mediaDevices.getUserMedia=window.savedGetUserMedia;});
    await page.locator('[data-prosody-topic="connected-speech"]').click();
    assert.match(await page.locator('#prosody-workspace').innerText(),/take‿a seat/);
    assert.equal(await page.locator('.prosody-clip').count(),0);
    await page.locator('#prosody-workspace').screenshot({path:path.join(out,'desktop_connected_speech.png')});
    await page.setViewportSize({width:390,height:844});
    for(const id of ['word-stress','sentence-focus','intonation','connected-speech']){
      await page.locator(`[data-prosody-topic="${id}"]`).click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    }
    await page.locator('#prosody-workspace').screenshot({path:path.join(out,'mobile_connected_speech.png')});
    await page.getByRole('button',{name:'Sounds',exact:true}).click();
    assert.equal(await page.locator('#sound-workspace').isVisible(),true);
    assert.ok(posts.every(url=>new URL(url).pathname==='/transcribe'));assert.deepEqual(errors,[]);
    const report={status:'PASS',revision:'physical-practice-1',topics:6,compact_mime:true,meaning_choices:true,two_recording_playback:true,rolling_two_attempts:true,microphone_failure_recovery:true,no_phrase_submitted_to_word_model:true,reduced_motion:true,mobile_overflow:false,page_errors:errors,recognition_accuracy_measured:false,learning_gain_measured:false};
    fs.writeFileSync(path.join(out,'browser_checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});

