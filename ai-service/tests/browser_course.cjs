const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT||'playwright');
const assert=require('node:assert/strict');
const base=process.argv[2], origin=base+'/demo/course';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']});
 try{
  const ctx=await browser.newContext({viewport:{width:390,height:844},permissions:['microphone']});
  const page=await ctx.newPage();page.setDefaultTimeout(20000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const press=name=>page.getByRole('button',{name,exact:true}).click();
  const heading=name=>page.getByRole('heading',{name,exact:true}).waitFor();
  const advance=()=>press('Continue');
  await page.goto(origin);await heading('Today');await press('Library');await page.getByLabel('Search lessons').fill('classroom-74');
  assert.equal(await page.locator('.list li').count(),1);
  await press('Today');await press('Start from the beginning');await press('seat');await advance();
  await press('Invite this particular person');await advance();await press('i');await advance();await press('seat');await advance();
  await page.getByLabel('Your IPA transcription').fill('sɪt');await press('Check transcription');
  await page.getByText('ɪ → i',{exact:true}).waitFor();assert.equal(await page.locator('.feedback audio').count(),2);
  await page.reload();await page.getByLabel('Your IPA transcription').waitFor();
  for(const s of ['s','i','t'])await press('Insert '+s);
  await press('Check transcription');await advance();await press('/siːt/');await advance();
  await press('Raise the front of the tongue gently; move toward the vowel in sit and back.');await advance();await press('Please take this seat.');await advance();
  await press('Save “seat” to My Words');await press('Continue without microphone');await advance();
  await press('Record a take');await page.waitForTimeout(1100);await press('Stop recording');
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='');
  assert.equal(await page.locator('#screen audio[src^="blob:"]').count(),1);
  await press('Ask a listener');await page.getByLabel('Listener’s own words').fill('A seat');await press('Return to learner');await press('They recovered the detail');
  await press('Save speaking attempt');await advance();
  await press('Yes, they recovered the requested detail.');await advance();await heading('Practice finished');
  await press('My Words');await press('seat');await page.getByRole('button',{name:'Practise graded transcription'}).waitFor();
  await press('Today');await press('Repair a misunderstood booking');await press('Fifteen');await advance();await press('Correct the number');await advance();
  await press('Correct what was booked');await advance();await page.getByLabel('Your IPA transcription').fill('ˌfɪfˈtin');await press('Check transcription');await advance();
  await press('fifteen');await advance();await press('Fifteen, please. One five.');await advance();
  for(const label of ['Record a take','Record another take']){
    await press(label);await page.waitForTimeout(1000);await press('Stop recording');await page.waitForFunction(()=>document.querySelector('#status').textContent==='');
  }
  assert.equal(await page.locator('#screen audio[src^="blob:"]').count(),2);
  await press('Save speaking attempt');await advance();await press('Continue without microphone');await advance();
  await press('Yes, they recovered the requested detail.');await advance();await heading('Practice finished');
  await press('Progress');await page.getByText('2 lessons completed · 0 reviews due').waitFor();
  await page.getByText(/1 listener checks recovered/).waitFor();
  await page.evaluate(()=>{const k='wordspeak.course.attempts.v1',events=JSON.parse(localStorage.getItem(k)),y=new Date(Date.now()-86400000).toISOString().slice(0,10);events.forEach(e=>e.day=y);localStorage.setItem(k,JSON.stringify(events));});
  await press('Today');await press('Review · Seat · explore /i/');await page.getByRole('button',{name:'peach',exact:true}).waitFor();
  await page.locator('#account summary').click();await page.getByLabel('Email',{exact:true}).fill('course@example.com');
  await page.getByLabel('Password',{exact:true}).fill('test-pass');await press('Create account');await press('Start from the beginning');
  let lostID;
  await page.route('**/api/course/attempts',async route=>{lostID=route.request().postDataJSON().attempt_id;await route.fetch();await route.abort('failed');},{times:1});
  await press('seat');await page.getByText(/Connection unavailable/).waitFor();
  const retried=page.waitForRequest(r=>r.url().endsWith('/api/course/attempts'));await press('seat');assert.equal((await retried).postDataJSON().attempt_id,lostID);
  await advance();await press('My Words');await page.getByLabel('Word or expression').fill('rain check');await press('Save word');
  await press('Sign out');await page.getByRole('button',{name:'Review · Seat · explore /i/'}).waitFor();
  await page.getByLabel('Email',{exact:true}).fill('course@example.com');await page.getByLabel('Password',{exact:true}).fill('test-pass');await press('Sign in');
  await press('Seat · explore /i/');await page.getByRole('button',{name:'Invite this particular person'}).waitFor();
  await press('My Words');await press('rain check');await page.getByText(/transcription key is pending/).waitFor();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
  console.log('Passed mobile course, IPA retry, two reference lessons, capture/replay, dated review, account resume and isolated word banks.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
