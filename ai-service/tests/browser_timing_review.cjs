const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT || 'playwright');

// The simulated microphone and timestamp fixture exercise replay mechanics.
(async()=>{
 const {encodeWav}=await import('../app/demo_static/audio.mjs');
 const fixtureDir=fs.mkdtempSync(path.join(os.tmpdir(),'wordspeak-pitch-'));
 const fixturePath=path.join(fixtureDir,'voice.wav');
 const tone=Float32Array.from({length:16000*5},(_,i)=>.25*Math.sin(2*Math.PI*200*i/16000));
 fs.writeFileSync(fixturePath,Buffer.from(await encodeWav(tone).arrayBuffer()));
 const browser=await chromium.launch({executablePath:process.env.WORDSPEAK_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
   args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+fixturePath]});
 try{
   const page=await browser.newPage({permissions:['microphone']});
   await page.goto('http://127.0.0.1:8013/demo');await page.locator('#prompt').selectOption('seat');
   await page.locator('#save-word').click();
   await page.getByRole('button',{name:'Record your turn'}).click();
   await page.waitForFunction(()=>!document.querySelector('#prosody-workspace .quick-actions button:last-child').disabled);
   await page.waitForTimeout(2200);
   await page.locator('#prosody-workspace').getByRole('button',{name:'Stop',exact:true}).click();
   await page.getByText('Explore pitch in this recording').click();
   await page.getByRole('img',{name:/Estimated pitch over/}).waitFor();
   const range=await page.getByText(/^Estimated pitch .* Hz/).textContent();
   assert.match(range,/Estimated pitch (199|200|201)–(199|200|201) Hz/);
   await page.route('**/transcribe',r=>r.fulfill({json:{text:'Sure, sit here.',words:[
     {word:'Sure,',start:0.1,end:0.4},{word:'sit',start:1.2,end:1.4},{word:'here.',start:1.42,end:1.8}
   ]}}));
   await page.getByRole('button',{name:'Send for transcription'}).click();
   await page.getByText('Listen to your phrasing',{exact:true}).click();
   assert.ok(await page.getByText('0.8 s between recognized words').isVisible());
   await page.getByRole('button',{name:'Play from sit here.'}).click();
   const audio=page.locator('.prosody-clip audio');
   const position=await audio.evaluate(a=>a.currentTime);assert.ok(position>=1.07 && position<1.5,position);
   assert.ok(await audio.evaluate(a=>!a.paused));
   await page.getByRole('button',{name:'Record your turn'}).click();
   assert.ok(await audio.evaluate(a=>a.paused && a.closest('.prosody-clips').inert));
   await page.locator('#prosody-workspace').getByRole('button',{name:'Stop',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('.prosody-clips').inert);
   await page.getByText('Listen to your phrasing',{exact:true}).click();
   await page.getByRole('button',{name:'Open selected word in sound practice'}).click();
   await page.getByText(/Listen to the estimated word selection/).waitFor();
   assert.equal(await page.locator('#prompt').inputValue(),'sit');
   assert.equal(await page.locator('#input-scope').inputValue(),'word');
   assert.equal(Number(await page.locator('#start').inputValue()),1.15);
   assert.equal(Number(await page.locator('#end').inputValue()),1.45);
   const excerpt=await page.locator('#input-audio').evaluate(async a=>{
     const wav=await (await fetch(a.src)).arrayBuffer();
     return (wav.byteLength-44)/32000;
   });
   assert.ok(Math.abs(excerpt-.3)<.001);
   await page.locator('#keep-take').click();
   const earlier=await page.locator('#first-audio').getAttribute('src');
   await page.locator('#file').setInputFiles(fixturePath);
   await page.getByText(/Longer recording loaded/).waitFor();
   await page.locator('#prepare').click();
   await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);
   assert.equal(await page.locator('#first-audio').getAttribute('src'),earlier);
   await page.locator('#first-audio').evaluate(audio=>audio.play());
   await page.locator('#input-audio').evaluate(audio=>audio.play());
   assert.ok(await page.locator('#first-audio').evaluate(audio=>audio.paused));
   await page.locator('#prompt').selectOption('seat');
   assert.ok(await page.locator('#first-take').isHidden());
   assert.equal(await page.locator('#first-audio').getAttribute('src'),null);
   await page.locator('#mode-prosody').click();
   assert.equal(await page.locator('.prosody-clip audio').count(),2);
   await page.getByRole('button',{name:'Save an expression from this turn'}).click();
   assert.equal(await page.getByLabel('Practice sentence (optional)').inputValue(),'Sure, sit here.');
   await page.getByLabel('Word or expression',{exact:true}).fill('sit here');
   await page.getByLabel('Practice sentence (optional)').fill('Sure, you can sit here.');
   await page.getByRole('button',{name:'Save and practice'}).click();
   await page.getByText('In conversation · sit here',{exact:true}).waitFor();
   await page.getByText('Sure, you can sit here.',{exact:true}).waitFor();
   console.log('Transcript grouped by a timestamp gap; replay sought to the selected words in the recorded turn');
 }finally{await browser.close();fs.unlinkSync(fixturePath);fs.rmdirSync(fixtureDir);}
})().catch(e=>{console.error(e);process.exitCode=1;});
