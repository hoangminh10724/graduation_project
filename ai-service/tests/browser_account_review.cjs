const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict');
const {randomUUID}=require('node:crypto');
const path=require('node:path');
(async()=>{
 const url=process.argv[2], password=randomUUID();
 const wav=process.env.WORDSPEAK_REVIEW_WAV || path.resolve(__dirname,'../../data/speechocean762/WAVE/SPEAKER0056/000560016.WAV');
 const browser=await chromium.launch({executablePath:process.env.WORDSPEAK_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+wav]});
 try{
  const page=await browser.newPage({permissions:['microphone'],viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  async function account(email){
   const r=await page.request.post(url+'/api/auth/register',{data:{email,password}});assert.equal(r.status(),201);
   return {Authorization:'Bearer '+(await r.json()).access_token};
  }
  async function login(email){
   await page.getByLabel('Account email').fill(email);await page.getByLabel('Password',{exact:true}).fill(password);
   await page.getByRole('button',{name:'Sign in',exact:true}).click();
  }
  const owner=await account('owner@example.test');await account('other@example.test');
  for(const [front,back] of [['seat','a place to sit'],['rain check','an invitation for another time']]){
   const r=await page.request.post(url+'/api/cards',{headers:owner,data:{front,back}});assert.equal(r.status(),201);
  }
  await page.goto(url+'/demo/review');
  await page.getByRole('button',{name:'Create a new account'}).click();
  await page.getByLabel('Account email').fill('owner@example.test');
  await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Create account',exact:true}).click();
  await page.getByText(/This email already has an account/).waitFor();
  await page.getByLabel('Account email').fill('beginner@example.test');
  await page.getByRole('button',{name:'Create account',exact:true}).click();
  await page.getByText(/Account created/).waitFor();
  await page.getByLabel('Word or expression',{exact:true}).fill('after work');
  await page.getByRole('button',{name:'Save expression',exact:true}).click();
  await page.getByText('In conversation · after work',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Sign out'}).click();
  await login('owner@example.test');
  await page.getByText('2 due cards').waitFor();
  await page.getByRole('button',{name:'Reply',exact:true}).click();
  await page.getByRole('button',{name:'Record your turn'}).click();
  const stop=page.locator('#practice').getByRole('button',{name:'Stop',exact:true});
  await page.waitForFunction(()=>!document.querySelector('#practice .quick-actions button:last-child').disabled);
  await page.waitForTimeout(5100);assert.ok(await page.getByRole('button',{name:'Good',exact:true}).isDisabled(),await page.locator('.prosody-status').innerText());
  await stop.click();await page.getByRole('button',{name:'Send for transcription'}).click();
  await page.getByText(/^Automatic transcript:/).waitFor({timeout:45000});
  await page.getByText('Listen to your phrasing',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Check pronunciation with tutor'}).click();
  await page.getByText("Tutor: Let's listen to your recording together.",{exact:true}).waitFor({timeout:180000});
  await page.locator('.prosody-clip').getByText(/Listen to|could not locate/).first().waitFor();
  await page.locator('#conversation summary').click();
  // Begin a fresh card session for the separate typed-turn and retry checks below.
  await page.getByRole('button',{name:'Check due cards'}).click();
  await page.getByText('Continue with a conversation tutor').click();
  const draft=page.getByLabel('Your turn',{exact:true});
  const send=page.getByRole('button',{name:'Send to tutor'});
  await draft.fill('I saved you a seat.');await send.click();
  await page.getByText('Tutor: Where shall we meet?',{exact:true}).waitFor();
  await page.locator('#practice').getByText('Where shall we meet?',{exact:true}).waitFor();
  await draft.fill('At the cafe.');await send.click();
  await page.getByText('Tutor: See you there!',{exact:true}).waitFor();
  await draft.fill('Unavailable');await send.click();
  await page.getByText(/A tutor reply could not be confirmed/).waitFor();
  assert.equal(await draft.inputValue(),'Unavailable');
  const sessions=await (await page.request.get(url+'/api/sessions',{headers:owner})).json();
  assert.equal(sessions.length,2);
  const history=await (await page.request.get(url+'/api/sessions/'+sessions[0].id+'/turns',{headers:owner})).json();
  assert.deepEqual(history.map(turn=>turn.text),['I saved you a seat.','At the cafe.']);
  console.log('Verified editable speech drafts, two stored turns with conversation context, and tutor outage recovery.');
  assert.equal((await (await page.request.get(url+'/api/cards/due',{headers:owner})).json()).length,2);
  const requests=[];
  await page.route('**/api/reviews',async route=>{
    requests.push(route.request().postDataJSON());const response=await route.fetch();
    assert.equal(response.status(),200);
    if(requests.length===1)await route.abort();else await route.fulfill({response});
  });
  await page.getByRole('button',{name:'Good',exact:true}).click();
  await page.getByRole('button',{name:'Retry saving this review'}).click();
  await page.getByText('1 due card',{exact:true}).waitFor();assert.deepEqual(requests[0],requests[1]);
  await page.getByText('In conversation · rain check').waitFor();
  await page.getByText('Show card back').click();await page.getByText('an invitation for another time').waitFor();
  await page.getByRole('button',{name:'Good',exact:true}).click();
  await page.getByText('Your due-card review is complete.').waitFor();
  await page.getByRole('button',{name:'Sign out'}).click();await login('owner@example.test');
  await page.getByRole('button',{name:'Find saved conversations'}).click();
  await page.getByRole('button',{name:'Resume conversation'}).click();
  await page.getByText('You: I saved you a seat.',{exact:true}).waitFor();
  await page.locator('#resumed-practice').getByText('See you there!',{exact:true}).waitFor();
  await draft.fill('Shall I order coffee?');await send.click();
  await page.getByText('You: Shall I order coffee?',{exact:true}).waitFor();
  const restored=await (await page.request.get(url+'/api/sessions/'+sessions[0].id+'/turns',{headers:owner})).json();
  assert.equal(restored.length,3);
  await page.getByRole('button',{name:'Sign out'}).click();await login('other@example.test');
  await page.getByText('Your due-card review is complete.').waitFor();
  await page.getByRole('button',{name:'Find saved conversations'}).click();
  await page.getByText('No saved conversations yet.').waitFor();
  assert.equal(await page.getByText('You: Shall I order coffee?',{exact:true}).count(),0);
  assert.equal(await page.getByText('In conversation · rain check').count(),0);
  assert.equal(await page.evaluate(()=>localStorage.length),0);
  await page.goto(url+'/demo');await page.locator('#mode-prosody').click();
  await page.getByText('Add your own word or expression',{exact:true}).click();
  await page.getByLabel('Word or expression',{exact:true}).fill('catch up');
  await page.getByLabel('Practice sentence (optional)').fill('Can we catch up tomorrow?');
  await page.getByLabel('Question or situation for your reply (optional)').fill('An old friend calls. What do you suggest?');
  await page.getByRole('button',{name:'Save and practice'}).click();
  await page.goto(url+'/demo/review');await login('other@example.test');
  await page.getByText('Save an expression to my account').click();
  await page.getByRole('button',{name:'Choose from this device'}).click();
  await page.getByLabel('Device word bank').selectOption({label:'catch up'});
  await page.getByRole('button',{name:'Save expression',exact:true}).click();
  await page.getByText('Saved “catch up” to your account.').waitFor();
  const fresh=await browser.newPage();
  await fresh.goto(url+'/demo/review');
  await fresh.getByLabel('Account email').fill('other@example.test');
  await fresh.getByLabel('Password',{exact:true}).fill(password);
  await fresh.getByRole('button',{name:'Sign in',exact:true}).click();
  await fresh.locator('#practice').getByText('Can we catch up tomorrow?',{exact:true}).waitFor();
  await fresh.getByRole('button',{name:'Reply',exact:true}).click();
  await fresh.getByText('An old friend calls. What do you suggest?',{exact:true}).waitFor();
  assert.equal(await fresh.evaluate(()=>localStorage.length),0);
  console.log('Imported a local expression and reopened its custom sentence and reply situation in a fresh browser context.');
  assert.deepEqual(errors,[]);console.log('Verified two-account isolation, due-word recording, real authenticated transcript with timings and idempotent review after a lost response.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
