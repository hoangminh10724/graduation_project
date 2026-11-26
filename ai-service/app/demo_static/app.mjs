import {renderListeningContrast} from './listening-contrast.mjs';
import {renderSoundTable} from './sound-table.mjs';
import {wordBank} from './conversation.mjs';
import {decodeAudio, prepareAudio, startPCMRecording} from './audio.mjs?v=mic-playback-3';
import {renderTeaching} from './teaching.mjs?v=american-sounds-1';
import {renderProsody} from './prosody.mjs?v=physical-practice-1';
import {referencePresentation} from './reference-comparison.mjs?v=paired-references-1';
import {renderLipReference} from './lips.mjs?v=american-lips-1';
import {renderDiagnosis} from './diagnosis.mjs?v=recording-diagnosis-1';
const $ = id => document.getElementById(id);
let config, decoded, prepared, inputURL, resultURL, capture, timer, lastResult, busy = false, recording = false, sequence = 0;
let microphoneClip = false, microphoneName = 'Default microphone', preparationSequence = 0, pendingBoost = false, boostTimer;
let disposeTeaching = () => {};
let autoCheckRecording = false;
let prosodySession, bank;
const contrast=renderListeningContrast($('listen-contrast'));
$('save-word').addEventListener('click', () => {
  const prompt = config.prompts.find(item => item.id === $('prompt').value);
  const persistent = bank.save(prompt.id);
  practiceArea('prosody');
  prosodySession.openWord(prompt.id, persistent);
});
function practiceArea(area) {
  if (busy || recording || pendingBoost || !config) return;
  const prosody=area==='prosody';
  $('sound-workspace').hidden=prosody;$('prosody-workspace').hidden=!prosody;
  $('sound-targets').hidden=prosody;
  $('sound-picker').hidden=prosody;$('accent-note').hidden=prosody;
  $('practice-intro').textContent=prosody?'Choose an intention, explore its rhythm or pitch, then record and listen for one change.':
    'Record a word, listen back, then explore one sound you want to change.';
  $('practice-notice').textContent=prosody?'Visual gestures are practice examples. Phrase recordings are for listening and self-checking; this area does not assign AI grades.':
    'The illustrations show reference sounds, not the measured position of your tongue. Predictions are provisional; this demo does not give pronunciation scores.';
  $('mode-sounds').setAttribute('aria-pressed',String(!prosody));
  $('mode-prosody').setAttribute('aria-pressed',String(prosody));
  if (prosody) {
    contrast.pause();
    $('first-audio').pause();$('input-audio').pause();$('result-audio').pause();
    if (!prosodySession) prosodySession=renderProsody($('prosody-workspace'),{
      bank,
      soundPrompts:config.prompts,
      openRecordedWord:async(blob,{prompt,token})=>{
        practiceArea('sounds');$('prompt').value=prompt.id;$('input-scope').value='word';changePrompt();
        busy=true;controls();
        try{
          await acceptBlob(blob,{segment:token});
          setMessage('Listen to the estimated word selection. Adjust the boundaries if needed before analyzing.');
        }catch(error){prepared=undefined;setMessage(error.message);}
        finally{busy=false;controls();$('input-audio').focus();}
      },
      onPracticeWord:id=>{
        practiceArea('sounds');
        $('prompt').value=id;
        changePrompt();
        $('prompt').focus();
      },
      captureOptions:()=>({deviceId:$('mic-device').value,gain:Number($('mic-gain').value)}),
      onBusy:value=>{busy=value;controls();},
    });
  } else prosodySession?.pause();
}
$('mode-sounds').addEventListener('click',()=>practiceArea('sounds'));
$('mode-prosody').addEventListener('click',()=>practiceArea('prosody'));
function teaching(phone, result) {
  disposeTeaching(); disposeTeaching = renderTeaching($('teaching-guide'), config.teaching, phone, {result,onTry:startQuickTry});
}
function startQuickTry(phone) {
  const practicePhone=({'iː':'i','uː':'u'})[phone]||phone;
  const selected=config.prompts.find(p=>p.id===$('prompt').value);
  const prompt=selected?.target_phone===practicePhone?selected:config.prompts.find(p=>p.target_phone===practicePhone);
  if (!prompt || $('record').disabled) return;
  if ($('prompt').value!==prompt.id) { $('prompt').value=prompt.id;changePrompt(); }
  autoCheckRecording=true; $('record').click();
}
function presentReferences(result) {
  const presentation=referencePresentation(result);
  $('predicted-column').hidden=!presentation.showObserved;
  $('reference-grid').classList.toggle('single-reference',!presentation.showObserved);
  $('predicted-title').textContent=presentation.observedTitle || 'Model candidate: reference position';
  $('target-title').textContent=presentation.title;
  $('reference-summary').textContent=presentation.note;
  $('reference-summary').hidden=!presentation.note;
  $('reference-details').open=true;
}
const setMessage = text => { $('input-status').textContent = text; };
let earlierTake;
function clearEarlierTake(){
  const audio=$('first-audio');audio.pause();audio.removeAttribute('src');audio.load();
  if(earlierTake)URL.revokeObjectURL(earlierTake.url);
  earlierTake=undefined;$('first-take').hidden=true;
}
$('keep-take').addEventListener('click',()=>{
  if(!prepared)return;
  clearEarlierTake();
  earlierTake={url:URL.createObjectURL(prepared),prompt:$('prompt').value,scope:$('input-scope').value,blob:prepared};
  $('first-audio').src=earlierTake.url;$('first-take').hidden=false;
  $('first-take-label').textContent='Earlier take · '+config.prompts.find(p=>p.id===earlierTake.prompt).word+
    '. Try the word again, then listen to both takes for one change.';
  controls();
});
$('clear-take').addEventListener('click',()=>{clearEarlierTake();controls();});
for(const id of ['input-audio','result-audio','first-audio']){
  $(id).addEventListener('play',()=>{
    for(const other of ['input-audio','result-audio','first-audio'])if(other!==id)$(other).pause();
  });
}
function controls() {
  contrast.setBusy(busy || recording || pendingBoost || !config);
  for (const id of ['sound-family','sound-search']) $(id).disabled=busy || recording || pendingBoost || !config;
  for (const id of ['mode-sounds','mode-prosody']) $(id).disabled=busy || recording || pendingBoost || !config;
  for (const id of ['record', 'save-word', 'file', 'prompt', 'input-scope', 'mic-device']) $(id).disabled = busy || recording || pendingBoost || !config;
  $('mic-gain').disabled = busy || recording || !config;
  $('keep-take').disabled=busy || recording || pendingBoost || !prepared || prepared===earlierTake?.blob;
  $('keep-take').hidden=!prepared;
  $('clear-take').disabled=busy || recording;
  $('save-audio').disabled = busy || recording || pendingBoost || !prepared;
  $('stop').disabled = !recording;
  for (const id of ['input-audio','result-audio','first-audio']) $(id).inert = busy || recording;
  $('prepare').disabled = busy || recording || pendingBoost || !decoded;
  $('analyze').disabled = busy || recording || pendingBoost || !prepared;
  for (const button of $('examples').querySelectorAll('button')) button.disabled = busy || recording || pendingBoost || button.dataset.available !== 'true';
  for (const button of $('sound-targets').querySelectorAll('button')) button.disabled = busy || recording || pendingBoost;
  for (const button of document.querySelectorAll('[data-practice-record]')) button.disabled=busy || recording || pendingBoost || !config;
}
function guide(container, phone) {
  container.replaceChildren(); container.className = phone ? 'guide' : 'guide-placeholder';
  const data = config.guides[phone];
  if (!data) { container.textContent = 'No sound category has been established yet. The result above explains what prevented the comparison and what to try next.'; return; }
  const heading = document.createElement('div'); heading.className = 'guide-title';
  const symbol = document.createElement('span'); symbol.className = 'symbol'; symbol.textContent = `/${phone}/`;
  const voice = document.createElement('span'); voice.className = 'voice'; voice.textContent = data.voicing;
  heading.append(symbol, voice);
  const example=document.createElement('p');example.className='guide-example';example.textContent=data.sound_example || data.name;
  const views=document.createElement('div');views.className='reference-views';
  const pose=config.teaching?.poses[phone];
  if(pose){const front=document.createElement('div');front.className='reference-front';const label=document.createElement('p');label.className='view-label';label.textContent=pose.moving?'Front lips: start and finish':'Front view: lips';front.append(label);
    if(pose.moving){const pair=document.createElement('div');pair.className='moving-lips';for(const [position,p,pLabel] of [['Start',pose.start_pose,pose.start_phone],['Finish',pose.end_pose,pose.end_phone]]){const moment=document.createElement('div');const caption=document.createElement('p');caption.className='view-label';caption.textContent=`${position} /${pLabel}/`;moment.append(caption);renderLipReference(moment,p,pLabel);pair.append(moment);}front.append(pair);}
    else renderLipReference(front,pose,phone);views.append(front);}
  const inside=document.createElement('div');inside.className='reference-inside';
  const sideLabel=document.createElement('p');sideLabel.className='view-label';sideLabel.textContent='Side view · inside the mouth';
  const image = document.createElement('img'); image.src = data.svg_url; image.alt = `Schematic reference for ${data.name}; not a measurement of the speaker.`;
  inside.append(sideLabel,image);views.append(inside);
  const list = document.createElement('ul');
  for (const text of data.tips) { const item = document.createElement('li'); item.textContent = text; list.append(item); }
  const caption = document.createElement('p'); caption.className = 'guide-caption'; caption.textContent = data.caption || 'Reference illustration. Simplified, not to scale.';
  const positionDetails=document.createElement('details');positionDetails.className='position-details';const summary=document.createElement('summary');summary.textContent='Position details';positionDetails.append(summary,list);
  const featureSummary=document.createElement('p');featureSummary.className='guide-feature-summary';
  featureSummary.textContent=data.features?.tongue_height ? `Tongue reference: ${data.features.tongue_height}, ${data.features.tongue_region}. Lips: ${data.features.lip_shape}.` : '';
  featureSummary.hidden=!featureSummary.textContent;
  if(pose?.moving){featureSummary.textContent=`Moving reference: /${pose.start_phone}/ toward /${pose.end_phone}/. Keep the movement connected.`;featureSummary.hidden=false;}
  container.append(heading,example,views,featureSummary,positionDetails,caption);
}
function target() {
  const prompt = config.prompts.find(p => p.id === $('prompt').value);
  const wordOnly = $('input-scope').value === 'word';
  $('prompt-help').textContent = `Say “${wordOnly ? prompt.word : prompt.phrase || prompt.word}” once. Focus on /${prompt.target_phone}/ in “${prompt.word}”.`;
  $('recording-help').textContent = wordOnly ? 'Say only the word once, with a short pause before and after it. Recording stops after 3 seconds.' : 'Read the suggested phrase once. Recording stops after 3 seconds. This mode uses nearby sounds to locate the focus.';
  if ($('sound-table').dataset.prompt !== prompt.id) {
    renderSoundTable($('sound-table'),prompt);
    $('sound-table').dataset.prompt=prompt.id;
  }
  guide($('target-guide'), prompt.target_phone);
  teaching(prompt.target_phone);
  presentReferences(null);
  for (const button of $('sound-targets').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.phone === prompt.target_phone));
}
function feedback(data, status) {
  const box = $('articulation-feedback'); box.replaceChildren(); box.hidden = !data;
  $('feedback-details').hidden=!data?.differences.length;
  if (!data) return;
  const weak = data.evidence === 'weak_model_hypothesis';
  const title = document.createElement('h3'); title.textContent = weak ? 'Tentative starting sound — listen before adjusting' : 'Sound difference and adjustment';
  const summary = document.createElement('p');
  summary.textContent = `${weak ? 'Tentative candidate' : 'Model candidate'}: /${data.observed_reference.phone}/ (${data.observed_reference.name}). Target: /${data.target_reference.phone}/ (${data.target_reference.name}).`;
  box.append(title, summary);
  if (data.differences.length) {
    const table = document.createElement('table'); const head = document.createElement('thead'); const row = document.createElement('tr');
    for (const text of ['Feature', 'Model candidate reference', 'Target reference']) { const th = document.createElement('th'); th.textContent = text; row.append(th); }
    head.append(row); table.append(head); const body = document.createElement('tbody');
    const names = {tongue_height:'Tongue height',tongue_region:'Tongue region',lip_shape:'Lip shape',place:'Contact point',airflow:'Airflow',voicing:'Voice',bilabial:'both lips',alveolar:'ridge behind upper teeth',postalveolar:'just behind the tooth ridge',velar:'back of mouth / soft palate',dental:'tongue near upper teeth',labiodental:'lower lip and upper teeth'};
    for (const difference of data.differences) {
      const tr = document.createElement('tr');
      for (const text of [difference.dimension, difference.observed_reference, difference.target_reference]) { const td = document.createElement('td'); td.textContent = names[text] || text.replaceAll('_', ' '); tr.append(td); }
      body.append(tr);
    }
    table.append(body); box.append(table);
    const label = document.createElement('p'); label.className = 'adjustment-label'; label.textContent = weak ? 'If this candidate matches what you hear, try:' : 'Try this adjustment:'; box.append(label);
    const steps = document.createElement('ol');
    for (const difference of data.differences) { const li = document.createElement('li'); li.textContent = difference.adjustment; steps.append(li); }
    const retry = document.createElement('li'); retry.textContent = 'Say the word again and compare the new recording.'; steps.append(retry); box.append(steps);
  } else {
    const text = document.createElement('p'); text.textContent = status === 'model_match' ? 'No category-level feature difference was detected. This does not certify perfect pronunciation.' : 'No supported category-level correction is established. Duration and exact tongue coordinates have not been measured.'; box.append(text);
  }
  const note = document.createElement('p'); note.className = 'muted'; note.textContent = data.note; box.append(note);
}
function render(result) {
  lastResult = result; $('export').disabled = false;
  $('mode').textContent = result.mode === 'live_audio' ? 'Fresh audio inference' : 'Cached development example';
  $('result-message').textContent = result.message;
  const needsSelection=result.diagnosis?.kind==='unverified_word_location';
  $('select-target-word').hidden=!needsSelection || !decoded;
  const labels = {model_match: 'Target-like sound detected', possible_difference: 'Listen for a possible sound difference', uncertain: 'Needs another listen · no grade assigned'};
  $('result-state').hidden = false; $('result-state').className = `state ${result.status}`;
  $('result-state').textContent = labels[result.status] || 'Uncertain';
  if(needsSelection)$('result-state').textContent='Check the word location';
  if (result.diagnosis?.kind==='tentative_comparison') $('result-state').textContent='Possible starting sound — compare before adjusting';
  renderDiagnosis($('recording-feedback'), result);
  if (result.diagnosis?.kind==='accepted_variant') $('result-state').textContent=result.status==='uncertain'?'Possible accepted American variant':'Accepted American variant';
  $('practice-cue').hidden=true;
  feedback(result.articulation_feedback, result.status);
  if (result.articulation_feedback?.differences.length) $('practice-cue').hidden = true;
  $('predicted-title').textContent = result.articulation_feedback?.evidence === 'weak_model_hypothesis' ? 'Tentative sound: reference position' : 'Model candidate: reference position';
  guide($('target-guide'), result.target_phone); guide($('predicted-guide'), result.predicted_phone);
  teaching(result.target_phone,result); presentReferences(result);
  $('reasons').replaceChildren();
  for (const text of result.reasons || []) { const item = document.createElement('li'); item.textContent = text; $('reasons').append(item); }
  $('raw').textContent = result.raw_phones.join(' ') || 'No reliable sequence';
  $('technical').textContent = JSON.stringify(result.details, null, 2);
  $('teacher-section').hidden = !result.teacher_feedback; $('teacher').textContent = result.teacher_feedback || '';
  if (resultURL) { URL.revokeObjectURL(resultURL); resultURL = undefined; }
  if (result.audio_url) $('result-audio').src = result.audio_url;
  else if (prepared) { resultURL = URL.createObjectURL(prepared); $('result-audio').src = resultURL; }
  $('result-audio').hidden = !result.audio_url && !prepared;
}
async function checkedJSON(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The server could not analyze this recording.');
  return data;
}
async function prepare() {
  const token = ++preparationSequence;
  const audio = await prepareAudio(decoded, Number($('start').value), Number($('end').value), {
    gain: microphoneClip ? Number($('mic-gain').value) : 1,
    onLevel: level => { if (microphoneClip && token === preparationSequence) microphoneLevel({...level, deviceLabel: microphoneName}); }
  });
  if (token !== preparationSequence) return;
  prepared = audio;
  if (inputURL) URL.revokeObjectURL(inputURL);
  inputURL = URL.createObjectURL(prepared); $('input-audio').src = inputURL; $('input-audio').hidden = false;
  $('input-audio').volume = 1; $('input-audio').muted = false; $('input-audio').load();
  setMessage('Selection ready. Listen once, then analyze.'); controls();
}
async function acceptBlob(blob, {fromMicrophone = false,segment} = {}) {
  microphoneClip = fromMicrophone;
  prepared = undefined; decoded = undefined; decoded = await decodeAudio(blob);
  $('selection').hidden = false; $('start').value = '0'; $('end').value = Math.min(3, decoded.duration).toFixed(2);
  if(segment){
    const length=Math.min(decoded.duration,4,Math.max(.26,segment.end-segment.start+.1));
    const start=Math.max(0,Math.min(decoded.duration-length,(segment.start+segment.end-length)/2));
    $('start').value=start.toFixed(3);$('end').value=(start+length).toFixed(3);
    await prepare();return;
  }
  if (decoded.duration <= 4) { $('end').value = String(decoded.duration); await prepare(); }
  else {
    if (inputURL) URL.revokeObjectURL(inputURL);
    inputURL = URL.createObjectURL(blob); $('input-audio').src = inputURL; $('input-audio').hidden = false;
    setMessage('Longer recording loaded. Select a complete target word with a little context, then prepare it.');
  }
}
function changePrompt() {
  $('select-target-word').hidden=true;
  if(earlierTake && (earlierTake.prompt!==$('prompt').value || earlierTake.scope!==$('input-scope').value))clearEarlierTake();
  sequence++; target(); lastResult = undefined; $('export').disabled = true;
  $('result-state').hidden = true; $('result-message').textContent = 'Record or upload the selected word for a fresh comparison.';
  $('mode').textContent = 'Ready to explore'; $('raw').textContent = '—'; $('technical').textContent = 'No analysis for this selection yet.';
  $('result-audio').pause(); $('result-audio').removeAttribute('src'); $('result-audio').hidden = true;
  $('teacher-section').hidden = true; $('reasons').replaceChildren(); guide($('predicted-guide'), null);
  $('practice-cue').hidden=true;
  $('reference-details').open=true; $('feedback-details').open=false;
  feedback(null); $('predicted-title').textContent = 'Model candidate: reference position';
  renderDiagnosis($('recording-feedback'), null);
}
$('prompt').addEventListener('change', changePrompt);
$('input-scope').addEventListener('change', changePrompt);
$('select-target-word').addEventListener('click',()=>{
  if(busy || recording || !decoded)return;
  $('input-scope').value='word';changePrompt();prepared=undefined;controls();
  $('start').focus();setMessage('Set the start and end around the whole word. Prepare the selection and listen before analyzing.');
});
for (const id of ['start', 'end']) $(id).addEventListener('input', () => { prepared = undefined; controls(); setMessage('Prepare the changed selection before analyzing.'); });
$('file').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  changePrompt();
  busy = true; controls();
  try { await acceptBlob(file); } catch (error) { prepared = undefined; setMessage(error.message); }
  finally { busy = false; controls(); }
});
$('prepare').addEventListener('click', async () => {
  busy = true; controls(); try { await prepare(); } catch (error) { prepared = undefined; setMessage(error.message); }
  finally { busy = false; controls(); }
});
$('mic-gain').addEventListener('input', () => {
  $('mic-gain-value').textContent = `${Number($('mic-gain').value)}×`;
  clearTimeout(boostTimer);
  if (!microphoneClip || !decoded) {
    $('mic-level-status').textContent = 'Boost set for your next microphone recording. Uploaded files retain their original level.';
    return;
  }
  pendingBoost = true; prepared = undefined; preparationSequence++; changePrompt(); controls();
  setMessage('Updating the current recording volume…');
  boostTimer = setTimeout(async () => {
    busy = true; controls();
    try { await prepare(); setMessage('Recording volume updated. Press Play to compare, or analyze the updated audio.'); }
    catch (error) { prepared = undefined; setMessage(error.message); }
    finally { pendingBoost = false; busy = false; controls(); }
  }, 120);
});
function microphoneLevel(level) {
  if (level.deviceLabel) microphoneName = level.deviceLabel;
  const percent = Math.min(100, level.peak * 100).toFixed(level.peak < .01 ? 2 : 1);
  $('mic-level').value = Math.min(1, level.peak);
  const distorted = level.clippingFraction > .01 || level.peak >= 1;
  const advice = distorted ? 'Too loud: reduce input boost and record again.' : level.peak < .05 ? 'Low input: move closer or increase input boost.' : 'Level detected.';
  const rawPercent = ((level.rawPeak || 0) * 100).toFixed((level.rawPeak || 0) < .01 ? 2 : 1);
  $('mic-level-status').textContent = `${level.phase === 'finished' ? 'Recorded' : 'Recording'} peak ${percent}% (${level.gain}×; original ${rawPercent}%) · ${advice} Microphone: ${microphoneName}`;
  $('mic-level-status').dataset.level = distorted ? 'clipping' : level.peak < .05 ? 'low' : 'detected';
}
$('record').addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getUserMedia) { autoCheckRecording=false; setMessage('Recording is unavailable in this browser. Upload a file instead.'); return; }
  $('first-audio').pause();$('input-audio').pause(); $('result-audio').pause();
  busy = true; controls(); setMessage('Waiting for microphone access…');
  try {
    $('mic-level').value = 0;
    capture = await startPCMRecording({gain: Number($('mic-gain').value), deviceId: $('mic-device').value, onLevel: microphoneLevel}); changePrompt(); recording = true; prepared = undefined; busy = false;
    refreshMicrophones();
    setMessage($('input-scope').value === 'word' ? 'Recording… say just the word once.' : 'Recording… read the suggested phrase once.'); timer = setTimeout(stopRecording, 3000);
  } catch (error) { autoCheckRecording=false; busy = false; setMessage(`Microphone unavailable: ${error.message}`); }
  controls();
});
async function stopRecording() {
  if (!recording || !capture) return;
  clearTimeout(timer); recording = false; busy = true; controls();
  const active = capture; capture = undefined;
  const checkAfterRecording=autoCheckRecording;autoCheckRecording=false;
  try { const audio = await active.stop(); await acceptBlob(active.rawBlob || audio, {fromMicrophone: true}); }
  catch (error) { prepared = undefined; setMessage(error.message); }
  finally { busy = false; controls(); }
  if (checkAfterRecording && prepared) $('analyze').click();
}
$('stop').addEventListener('click', stopRecording);
$('save-audio').addEventListener('click', () => {
  if (!prepared || !inputURL) return;
  const link = document.createElement('a'); link.href = inputURL; link.download = 'wordspeak-recording.wav'; link.click();
});
$('mic-device').addEventListener('change', () => setMessage('Microphone changed. Record a new clip to use this device.'));
async function refreshMicrophones() {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  try {
    const selected = $('mic-device').value;
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'audioinput');
    $('mic-device').replaceChildren();
    for (const [id, label] of [['', 'System default microphone'], ...devices.filter(d => d.deviceId && d.deviceId !== 'default').map((d, i) => [d.deviceId, d.label || `Microphone ${i + 1}`])]) {
      const option = document.createElement('option'); option.value = id; option.textContent = label; $('mic-device').append(option);
    }
    if ([...$('mic-device').options].some(o => o.value === selected)) $('mic-device').value = selected;
  } catch { /* The default device remains available without device enumeration. */ }
}
$('analyze').addEventListener('click', async () => {
  if (!prepared) return;
  const token = ++sequence; const data = new FormData(); data.append('audio', prepared, 'word.wav'); data.append('prompt_id', $('prompt').value); data.append('input_scope', $('input-scope').value);
  busy = true; controls(); setMessage('Analyzing locally… the first request also loads the speech model.');
  try { const result = await checkedJSON(await fetch('/demo/analyze', {method: 'POST', body: data})); if (token === sequence) { render(result); setMessage('Recording checked. A retry is optional.'); } }
  catch (error) { setMessage(error.message); } finally { busy = false; controls(); }
});
async function init() {
  try {
    config = await checkedJSON(await fetch('/demo/config'));
    if (config.build !== 'american-sounds-v1') throw new Error('This is an older server build. Restart using START_WORDSPEAK.cmd and refresh the page.');
    $('account-review').hidden=!config.account_review_enabled;
    const counts=config.inventory_counts;
    $('build-badge').textContent=`${counts.core} core targets: General American`;
    $('accent-note').textContent=config.accent.note+' All recognition results remain experimental.';
    for (const [name, matches] of [['Steady & r-colored vowels', p=>p.primary && p.family==='vowel'&&p.category!=='Diphthongs'],['Diphthongs',p=>p.primary&&p.category==='Diphthongs'],['Consonants',p=>p.primary && p.family==='consonant'],['R-vowel combinations',p=>!p.primary&&p.category==='R-vowel combinations'],['Extra contrast practice',p=>!p.primary&&p.category!=='R-vowel combinations']]) {
      const group = document.createElement('optgroup'); group.label = name;
      for (const prompt of config.prompts.filter(matches)) { const option = document.createElement('option'); option.value = prompt.id; option.textContent = `${prompt.word}  ·  /${prompt.target_phone}/`; group.append(option); }
      $('prompt').append(group);
    }
    for (const phone of config.primary_targets) {
      const prompt = config.prompts.find(p=>p.primary && p.target_phone===phone);
      const button = document.createElement('button'); button.className='sound-chip'; button.dataset.phone=phone;
      button.dataset.family=prompt.family;button.dataset.word=prompt.word;
      button.textContent=`/${phone}/`; button.setAttribute('aria-label',`${phone} as in ${prompt.word}`);
      button.addEventListener('click',()=>{$('prompt').value=prompt.id;changePrompt();}); $('sound-targets').append(button);
    }
    for (const example of config.examples) {
      const button = document.createElement('button'); button.textContent = example.word; button.dataset.available = String(example.available);
      button.addEventListener('click', async () => {
        const token = ++sequence; busy = true; controls(); setMessage('Loading cached development example…');
        try { const result = await checkedJSON(await fetch(`/demo/examples/${encodeURIComponent(example.id)}`)); if (token === sequence) { render(result); setMessage('Cached example loaded. Use Analyze word for fresh audio inference.'); } }
        catch (error) { setMessage(error.message); } finally { busy = false; controls(); }
      });
      $('examples').append(button);
    }
    for (const source of config.sources) { const link = document.createElement('a'); link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = source.label; $('sources').append(link); }
    bank = wordBank(config.prompts);
    target(); filterSounds();refreshMicrophones(); setMessage('Ready. Choose an American sound, record one word, or upload audio.'); controls();
  } catch (error) { setMessage(`Cannot load the demo: ${error.message}`); }
}
$('export').addEventListener('click',()=>{
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify({exported_at:new Date().toISOString(),...lastResult},null,2)],{type:'application/json'});
  const url = URL.createObjectURL(blob); const link=document.createElement('a');link.href=url;link.download='wordspeak-sound-result.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
async function serviceStatus(){
 try { const status = await checkedJSON(await fetch('/demo/status'));
  const label = status.phase==='loading_model'?'Loading the local model':status.phase==='inference'?'Analyzing audio locally':status.model_loaded?'Local model ready':'Service online; model loads on first analysis';
  $('service-status').textContent=label;
 }catch{ $('service-status').textContent='Local server unavailable. Start it using ai-service/DEMO.md.'; }
}
serviceStatus();setInterval(serviceStatus,3000);
window.addEventListener('pagehide', () => { clearEarlierTake();clearTimeout(timer); contrast.dispose(); disposeTeaching(); prosodySession?.dispose(); capture?.stop().catch(() => {}); });
init();

function filterSounds(){
  const family=$('sound-family').value,query=$('sound-search').value.toLowerCase().trim();let visible=0;
  for(const button of $('sound-targets').querySelectorAll('button')){button.hidden=(family!=='all'&&button.dataset.family!==family)||!(button.dataset.phone+' '+button.dataset.word).toLowerCase().includes(query);if(!button.hidden)visible++;}
  $('sound-count').textContent=`${visible} of ${config?.primary_targets.length||0} core practice sounds`;
}
$('sound-family').addEventListener('change',filterSounds);
$('sound-search').addEventListener('input',filterSounds);
