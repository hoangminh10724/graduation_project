const assert = require('node:assert/strict');
const {chromium} = require(process.env.WORDSPEAK_PLAYWRIGHT || 'playwright');

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.WORDSPEAK_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
  });
  try {
    const page = await browser.newPage({permissions:['microphone'], viewport:{width:390,height:844}});
    const errors = [], posts = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
    await page.goto('http://127.0.0.1:8013/demo');
    await page.route('**/tutor/observe',route=>route.fulfill({json:{text:'I can sit here.',observation:{kind:'uncertain',message:'Try the word once more.'}}}));
    const config = await (await page.request.get('http://127.0.0.1:8013/demo/config')).json();
    for (const prompt of config.prompts) {
      await page.locator('#prompt').selectOption(prompt.id);
      await page.locator('#save-word').click();
      assert.equal(await page.locator('#conversation-words').inputValue(),prompt.id);
      const phrase=await page.locator('.prosody-meaning').innerText();
      assert.ok(phrase.toLowerCase().includes(prompt.word.toLowerCase()),phrase);
      assert.notEqual(phrase,prompt.phrase,'Expected an everyday phrase for '+prompt.id);
      await page.getByRole('button',{name:'Reply',exact:true}).click();
      assert.match(await page.locator('.prosody-meaning').innerText(),/\?$/);
      await page.locator('#mode-sounds').click();
    }
    await page.reload();
    await page.locator('#mode-prosody').click();
    const words=page.locator('#conversation-words');
    assert.equal(await words.locator('option').count(),config.prompts.length+1);
    await words.selectOption('seat');
    await page.getByRole('button',{name:'Next saved word'}).click();
    assert.notEqual(await words.inputValue(),'seat');
    await words.selectOption('sit');
    await page.getByRole('button',{name:'Practice this sound'}).click();
    assert.equal(await page.locator('#prompt').inputValue(),'sit');
    await page.locator('#save-word').click();
    assert.equal(await words.locator('option').count(),config.prompts.length+1);
    await words.selectOption('seat');
    await page.getByRole('button',{name:'Reply',exact:true}).click();
    await page.getByRole('button',{name:'Record your turn'}).click();
    const stop=page.locator('#prosody-workspace').getByRole('button',{name:'Stop',exact:true});
    assert.equal(await page.locator('#mode-sounds').isDisabled(),true);
    await stop.click();
    await page.locator('.prosody-clip audio').waitFor();
    await page.getByRole('button',{name:'Ask a listener'}).click();
    await page.getByLabel('Describe the message in your own words').fill('You want to sit here.');
    await page.getByRole('button',{name:'Show speaker my response'}).click();
    assert.ok(await page.getByText(/Your listener heard.*You want to sit here/).isVisible());
    await page.getByRole('button',{name:'Clarify',exact:true}).click();
    assert.match(await page.locator('.prosody-meaning').innerText(),/another way/);
    assert.ok(posts.every(url=>new URL(url).pathname==='/tutor/observe'));
    await page.route('**/transcribe',route=>route.fulfill({json:{text:'Is this seat free?',words:[]}}));
    await page.getByRole('button',{name:'Send for transcription'}).click();
    await page.getByText('Automatic transcript: Is this seat free?').waitFor();
    await page.getByRole('button',{name:'Ask a listener'}).click();
    await page.getByLabel('Describe the message in your own words').fill('Which seat?');
    await page.getByRole('button',{name:'Ask the speaker to clarify'}).click();
    await page.getByText('Your listener asks: Which seat?').waitFor();
    await page.getByRole('button',{name:'Record your turn'}).click();
    await stop.click();
    await page.getByText(/whether this reply answered their question: Which seat/).waitFor();
    await page.getByRole('button',{name:'Ask a listener'}).click();
    await page.getByRole('button',{name:'The clarification answered my question'}).click();
    await page.getByText('Your listener confirmed that the clarification answered their question.').waitFor();
    await page.getByRole('button',{name:'Remove saved word'}).click();
    assert.equal(await words.locator('option[value="seat"]').count(),0);
    await page.getByText('Add your own word or expression',{exact:true}).click();
    await page.getByLabel('Word or expression',{exact:true}).fill('rain check');
    await page.getByLabel('Practice sentence (optional)').fill('Could I take a rain check?');
    await page.getByLabel('Question or situation for your reply (optional)').fill('Can you come to dinner tonight?');
    await page.getByRole('button',{name:'Save and practice'}).click();
    assert.equal(await words.inputValue(),'custom:rain check');
    assert.equal(await page.locator('.prosody-meaning').innerText(),'Could I take a rain check?');
    const focus=page.getByLabel('Choose a word to emphasize');
    await focus.selectOption({label:'I'});
    assert.equal(await page.locator('.prosody-meaning strong').innerText(),'I');
    await page.getByRole('button',{name:'Record your turn'}).click();await stop.click();
    await page.getByText(/Latest attempt: Rehearse · intended emphasis on I/).waitFor();
    await page.getByRole('button',{name:'Ask a listener'}).click();
    assert.equal(await page.getByRole('dialog').getByText(/intended emphasis/).count(),0);
    await page.getByLabel('Which word stood out to you?').fill('rain');
    await page.getByRole('button',{name:'Show speaker my response'}).click();
    await page.getByText('Your listener heard emphasis on “rain”.',{exact:true}).waitFor();
    await focus.selectOption({label:'rain'});
    assert.equal(await page.locator('.prosody-meaning strong').innerText(),'rain');
    await page.getByLabel('Hide line while listening').check();assert.ok(await focus.isHidden());
    await page.getByLabel('Hide line while listening').uncheck();
    assert.equal(await page.getByRole('button',{name:'Practice this sound'}).count(),0);
    await page.getByRole('button',{name:'Reply',exact:true}).click();
    assert.equal(await page.locator('.prosody-meaning').innerText(),'Can you come to dinner tonight?');
    await page.getByRole('button',{name:'Record your turn'}).click();
    await stop.click();await page.locator('.prosody-clip audio').last().waitFor();
    await page.reload();await page.locator('#mode-prosody').click();
    await words.selectOption('custom:rain check');
    assert.match(await page.locator('.prosody-status').innerText(),/recorded 1 repl/);
    await page.getByRole('button',{name:'Next saved word'}).click();
    assert.notEqual(await words.inputValue(),'custom:rain check');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
    assert.deepEqual(posts.map(url=>new URL(url).pathname).filter(path=>path!=='/tutor/observe'),['/transcribe']);
    assert.deepEqual(errors,[]);
    console.log(config.prompts.length+' prompt round trips, persistence, recording, clarification and removal passed');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});

