const assert = require('node:assert/strict');
const {chromium} = require(process.env.WORDSPEAK_PLAYWRIGHT || 'playwright');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.WORDSPEAK_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  try{
    const page=await browser.newPage();
    await page.goto('http://127.0.0.1:8013/demo');
    await page.locator('#prompt').selectOption('seat');
    await page.locator('#save-word').click();
    const listen=page.getByRole('button',{name:'Listen to line'});
    await page.getByLabel('Hide line while listening').check();
    assert.equal(await page.locator('.prosody-meaning').isVisible(),false);
    if(await page.evaluate(()=>!window.speechSynthesis?.getVoices().some(v=>v.localService && v.lang==='en-US'))){
      console.log('No installed US English voice found; testing unavailable state');
      await page.getByText('Listening needs an installed US English voice available to this browser.').waitFor();
      assert.ok(await listen.isDisabled());return;
    }
    await page.getByLabel('Slower playback').check();
    await listen.click();await page.getByRole('button',{name:'Stop listening'}).waitFor();
    await listen.waitFor({timeout:15000});
    assert.equal(await page.getByText(/Playback was interrupted/).count(),0);
    await page.getByLabel('Hide line while listening').uncheck();
    assert.equal(await page.locator('.prosody-meaning').innerText(),'Is this seat free?');
    await listen.click();await page.getByRole('button',{name:'Reply',exact:true}).click();
    await listen.waitFor();
    await listen.click();await page.locator('#mode-sounds').click();
    await page.waitForFunction(()=>!speechSynthesis.speaking);
    console.log('Installed speech voice completed a phrase, text reveal worked, and navigation stopped playback');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
