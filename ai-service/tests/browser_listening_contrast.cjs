const assert=require('node:assert/strict');
const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT || 'playwright');

// A deterministic voice double verifies routing, retries and the answer key.
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.WORDSPEAK_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  await page.addInitScript(()=>{
    const synth=new EventTarget();
    synth.getVoices=()=>[{lang:'en-US',localService:false},{lang:'en-US',localService:true}];
    synth.speak=u=>{window.spoken={text:u.text,local:u.voice.localService};setTimeout(()=>{if(window.failVoice)u.onerror();else u.onend();},20);};
    synth.cancel=()=>{};
    Object.defineProperty(window,'speechSynthesis',{value:synth});
    Object.defineProperty(window,'SpeechSynthesisUtterance',{value:class{constructor(text){this.text=text;}}});
  });
  await page.goto('http://127.0.0.1:8013/demo');
  await page.locator('#prompt').selectOption('seat');
  const area=page.locator('#listen-contrast');
  await area.locator('summary').click();
  const select=area.getByRole('combobox'),answers=area.locator('.quick-actions button');
  const count=await select.locator('option').count();
  assert.equal(count,12);
  for(let i=0;i<count;i++){
    await select.selectOption({index:i});assert.ok(await answers.first().isDisabled());
    await area.getByRole('button',{name:'Play a line'}).click();
    await area.getByText('Which word did you hear?').waitFor();
    const said=await page.evaluate(()=>window.spoken);assert.ok(said.local);
    const options=await answers.allTextContents();
    const answer=options.findIndex(word=>said.text.split(/\W+/).includes(word));
    assert.ok(answer>=0);
    await area.getByRole('button',{name:'Replay line'}).click();
    await area.getByText('Which word did you hear?').waitFor();
    assert.equal(await page.evaluate(()=>window.spoken.text),said.text);
    await answers.nth(i%2 ? answer : 1-answer).click();
    const message=await area.getByRole('status').innerText();
    assert.ok(message.includes('“'+options[answer]+'”') && message.startsWith(i%2?'You heard it.':'Listen once more.'));
  }
  await page.evaluate(()=>{window.failVoice=true;});
  await area.getByRole('button',{name:'Try another line'}).click();
  await area.getByText(/Playback failed/).waitFor();assert.ok(await answers.first().isDisabled());
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  console.log('12 contrasts, same-line replay, both answer outcomes, local-only voice, failed playback and mobile width passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
