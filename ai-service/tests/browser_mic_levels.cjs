// File-backed fake microphone only; no physical microphone is accessed.
const {chromium}=require(process.env.WORDSPEAK_PLAYWRIGHT || 'playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');const out=path.join(root,'data/results/microphone_level_checks');
fs.mkdirSync(out,{recursive:true});
function fixture(name, amplitude){
 const count=64000, bytes=Buffer.alloc(44+count*2);
 bytes.write('RIFF');bytes.writeUInt32LE(36+count*2,4);bytes.write('WAVEfmt ',8);
 bytes.writeUInt32LE(16,16);bytes.writeUInt16LE(1,20);bytes.writeUInt16LE(1,22);
 bytes.writeUInt32LE(16000,24);bytes.writeUInt32LE(32000,28);bytes.writeUInt16LE(2,32);bytes.writeUInt16LE(16,34);
 bytes.write('data',36);bytes.writeUInt32LE(count*2,40);
 for(let i=0;i<count;i++)bytes.writeInt16LE(Math.round(amplitude*32767*Math.sin(2*Math.PI*440*i/16000)),44+i*2);
 const filename=path.join(out,name+'.wav');fs.writeFileSync(filename,bytes);return filename;
}
async function testFile(filename, gains){
 const browser=await chromium.launch({headless:true,
  executablePath:process.env.WORDSPEAK_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args:['--disable-background-networking','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream',`--use-file-for-fake-audio-capture=${filename}`]});
 try{
  const context=await browser.newContext({permissions:['microphone'],viewport:{width:390,height:844}});
  const rows=[];
  for(const gain of gains){
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{
    const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    window.__microphoneRequests=[];
    navigator.mediaDevices.getUserMedia=async options=>{window.__microphoneRequests.push(options);const stream=await original(options);window.__tracks=stream.getTracks();return stream};
   });
   await page.goto(process.env.WORDSPEAK_DEMO_URL || 'http://127.0.0.1:8013/demo');
   await page.waitForFunction(()=>!document.querySelector('#record').disabled);
   await page.waitForFunction(()=>document.querySelector('#mic-device').options.length>1);
   const deviceIds=await page.locator('#mic-device option').evaluateAll(options=>options.map(o=>o.value).filter(Boolean));
   assert.ok(deviceIds.length,'Fake microphone should be enumerated');
   if(deviceIds.length)await page.locator('#mic-device').selectOption(deviceIds[0]);
   await page.locator('#mic-gain').fill(String(gain));
   assert.equal(await page.locator('#mic-gain-value').textContent(),`${gain}×`);
   await page.getByRole('button',{name:'Record word',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('#stop').disabled);
   assert.equal(await page.locator('#mic-gain').isDisabled(),true);
   await page.waitForFunction(()=>document.querySelector('#mic-level').value>0);
   await page.waitForFunction(()=>!document.querySelector('#analyze').disabled,{},{timeout:15000});
   assert.equal(await page.evaluate(()=>window.__tracks.every(t=>t.readyState==='ended')),true);
   const readAudio=async()=>await page.evaluate(async()=>{
    const bytes=await(await fetch(document.querySelector('#input-audio').src)).arrayBuffer();
    const view=new DataView(bytes);let peak=0,sum=0,clipped=0;const count=(bytes.byteLength-44)/2;
    for(let i=44;i<bytes.byteLength;i+=2){const x=view.getInt16(i,true)/32768;peak=Math.max(peak,Math.abs(x));sum+=x*x;if(Math.abs(x)>=.99)clipped++;}
    return {peak,rms:Math.sqrt(sum/count),clippingFraction:clipped/count,rate:view.getUint32(24,true)};
   });
   const values=await readAudio();
   assert.equal(values.rate,16000);assert.deepEqual(errors,[]);
   const status=await page.locator('#mic-level-status').innerText();assert.match(status,/Recorded peak/);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
   rows.push({gain,...values,status});
   if(deviceIds.length)assert.equal(await page.evaluate(()=>window.__microphoneRequests[0].audio.deviceId.exact),deviceIds[0]);
   if(gain===1){
    // Reprocess this exact existing recording; do not ask for another capture.
    const originalBytes=await page.locator('#input-audio').evaluate(async e=>Array.from(new Uint8Array(await(await fetch(e.src)).arrayBuffer())));
    await page.locator('#mic-gain').fill('4');
    await page.waitForFunction(()=>document.querySelector('#mic-level-status').textContent.includes('(4×;')&&!document.querySelector('#analyze').disabled);
    const sameClip4x=await readAudio();
    assert.ok(Math.abs(sameClip4x.peak/values.peak-4)<.02);
    assert.ok(Math.abs(sameClip4x.rms/values.rms-4)<.02);
    await page.locator('#mic-gain').fill('8');
    await page.waitForFunction(()=>document.querySelector('#input-status').textContent.startsWith('Recording volume updated')&&!document.querySelector('#analyze').disabled);
    const boosted=await readAudio();assert.ok(Math.abs(boosted.peak/values.peak-8)<.1);
    assert.equal(await page.evaluate(()=>window.__microphoneRequests.length),1);
    assert.match(await page.locator('#mic-level-status').innerText(),/8×; original/);
    assert.equal(await page.locator('#input-audio').evaluate(e=>e.volume),1);
    assert.equal(await page.locator('#input-audio').evaluate(e=>e.muted),false);
    const download=page.waitForEvent('download');await page.getByRole('button',{name:'Save audio',exact:true}).click();
    const saved=path.join(out,'existing_recording_8x.wav');await(await download).saveAs(saved);
    const blobBytes=await page.locator('#input-audio').evaluate(async e=>Array.from(new Uint8Array(await(await fetch(e.src)).arrayBuffer())));
    assert.deepEqual([...fs.readFileSync(saved)],blobBytes);
    const before=Buffer.from(originalBytes),after=Buffer.from(blobBytes);
    assert.equal(before.length,after.length);
    for(let i=44;i<before.length;i+=2)assert.equal(after.readInt16LE(i),before.readInt16LE(i)*8);
    await page.locator('#mic-gain').fill('1');
    await page.waitForFunction(()=>document.querySelector('#mic-level-status').textContent.includes('(1×;')&&!document.querySelector('#analyze').disabled);
    assert.deepEqual(await page.locator('#input-audio').evaluate(async e=>Array.from(new Uint8Array(await(await fetch(e.src)).arrayBuffer()))),originalBytes);
    rows[rows.length-1].same_recording_8x_peak_ratio=boosted.peak/values.peak;
    rows[rows.length-1].same_recording_4x_peak_ratio=sameClip4x.peak/values.peak;
    rows[rows.length-1].same_recording_4x_rms_ratio=sameClip4x.rms/values.rms;
    rows[rows.length-1].returned_to_original_bytes=true;
    rows[rows.length-1].capture_requests_during_adjustment=1;
    // Gain changes on a microphone clip must not silently amplify uploads.
    await page.locator('#file').setInputFiles(filename);
    await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);
    const uploaded=await readAudio();
    await page.locator('#mic-gain').fill('8');
    assert.equal((await readAudio()).peak,uploaded.peak);
    assert.match(await page.locator('#mic-level-status').innerText(),/Uploaded files retain/);
   }
   if(gain===4)await page.screenshot({path:path.join(out,'mobile_input_boost.png'),fullPage:true});
   await page.close();
  }return rows;
 }finally{await browser.close()}
}
(async()=>{
 const quiet=await testFile(fixture('quiet_sine',.01),[1,4]);
 // Compare identical PCM when asserting an exact multiplier. Separate captures
 // can contain different device-start transients and are retained independently.
 const peakRatio=quiet[0].same_recording_4x_peak_ratio, rmsRatio=quiet[0].same_recording_4x_rms_ratio;
 assert.match(quiet[0].status,/Low input/);
 const loud=await testFile(fixture('loud_sine',.3),[8]);
 assert.match(loud[0].status,/Too loud/);assert.ok(loud[0].clippingFraction>.01);
 const report={status:'PASS',audio_revision:'mic-playback-3',input:'synthetic file-backed microphone; no physical microphone accessed',
  gain_changes_recorded_wav:true,peak_ratio_4x:peakRatio,rms_ratio_4x:rmsRatio,
  same_recording_gain_edit:true,no_compounding:true,download_matches_playback:true,
  uploaded_levels_unchanged:true,microphone_selection:true,playback_volume_reset:true,
  low_input_warning:true,clipping_warning:true,tracks_released:true,mobile_overflow:false,quiet,loud};
 fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exit(1)});
