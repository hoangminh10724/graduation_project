// Original teaching illustrations. Their coordinates are artwork, not anatomy.
import {quickCue} from './reference-comparison.mjs?v=recording-diagnosis-1';
import {addLipDrawing, lipAction} from './lips.mjs?v=american-lips-1';
import {movementPlan} from './practice-plan.mjs?v=american-sounds-1';
const ns = 'http://www.w3.org/2000/svg';
const element = (name, className, text) => {
  const node = document.createElement(name); if (className) node.className = className;
  if (text !== undefined) node.textContent = text; return node;
};
function shape(name, attributes = {}, text) {
  const node = document.createElementNS(ns, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  if (text !== undefined) node.textContent = text; return node;
}
const mix = (a, b, t) => a + (b - a) * t;

function illustration(parent, from, to, mode, target) {
  const pathPoses=to.path_poses && mode!=='hold'?to.path_poses:[from,to];
  const svg = shape('svg', {viewBox: '0 0 640 245', role: 'img', 'aria-label': `Illustrated practice movement toward ${target}; schematic reference only`});
  svg.append(shape('title', {}, 'Watch lips, tongue, jaw and voice change in a teaching example'));
  const front = shape('g', {transform: 'translate(20 5)'});
  front.append(shape('text', {x:100,y:18,'text-anchor':'middle'}, 'Front view'));
  const face = shape('path', {fill:'none',stroke:'#adbaab','stroke-width':3});
  front.append(face,shape('circle',{cx:77,cy:52,r:3,fill:'#69816d'}),shape('circle',{cx:123,cy:52,r:3,fill:'#69816d'}));
  front.append(shape('path',{d:'M100 58L94 78H104',fill:'none',stroke:'#adbaab','stroke-width':2}));
  const lipGroup=shape('g');front.append(lipGroup);const paintLips=addLipDrawing(lipGroup);
  const chin = shape('path',{fill:'none',stroke:'#69816d','stroke-width':3}); front.append(chin);
  const lipText = shape('text',{x:100,y:185,'text-anchor':'middle'});front.append(lipText);
  const side = shape('g',{transform:'translate(280 8)'});
  side.append(shape('text',{x:145,y:15,'text-anchor':'middle'},'Inside: side view'));
  side.append(shape('path',{d:'M20 150C10 90 45 45 100 40Q190 20 240 65L255 80',fill:'#fffdf7',stroke:'#adbaab','stroke-width':3}));
  const jaw = shape('path',{fill:'none',stroke:'#adbaab','stroke-width':3});side.append(jaw);
  side.append(shape('path',{d:'M205 54Q220 51 228 62',fill:'none',stroke:'#647e64','stroke-width':4}),shape('rect',{x:239,y:69,width:10,height:23,rx:2,fill:'#fff',stroke:'#81947a'}));
  const tongue = shape('path',{fill:'#d99f98',stroke:'#ad6d68','stroke-width':2});side.append(tongue);
  const air = shape('path',{d:'M248 108H298M287 102L298 108L287 114',fill:'none',stroke:'#3e8fa8','stroke-width':3});side.append(air);
  const noseAir=shape('path',{d:'M30 127Q10 30 145 34H280m-10 -6l10 6l-10 6',fill:'none',stroke:'#3e8fa8','stroke-width':3});side.append(noseAir);
  side.append(shape('text',{x:270,y:132,'text-anchor':'middle',fill:'#3e8fa8'},'air'));
  const place = shape('text',{x:145,y:201,'text-anchor':'middle'});side.append(place);
  const voice = shape('text',{x:320,y:235,'text-anchor':'middle',class:'voice-indicator'});
  svg.append(front,side,voice);parent.append(svg);
  const resize = new ResizeObserver(entries => {
    const narrow = entries[0].contentRect.width < 520;
    svg.setAttribute('viewBox', narrow ? '0 0 320 480' : '0 0 640 245');
    front.setAttribute('transform', narrow ? 'translate(50 5)' : 'translate(20 5)');
    side.setAttribute('transform', narrow ? 'translate(8 225)' : 'translate(280 8)');
    voice.setAttribute('x', narrow ? '160' : '320');voice.setAttribute('y', narrow ? '466' : '235');
  });
  resize.observe(parent);
  const update = (value, focus) => {
    const progress=value/100;
    const at=progress*(pathPoses.length-1),segment=Math.min(pathPoses.length-2,Math.floor(at));
    const from=pathPoses[segment],to=pathPoses[segment+1],t=at-segment;
    const release = mode === 'release' || mode==='affricate';
    const open = release ? Math.max(0, (t - .35) / .65) : mix(from.opening,to.opening,t);
    const round = mix(from.lip_round??Number(from.rounded),to.lip_round??Number(to.rounded),t);
    const spread = mix(from.lip_spread??.12,to.lip_spread??.12,t);
    face.setAttribute('d',`M50 42Q37 92 50 135Q100 ${174+open*12} 150 135Q163 92 150 42`);
    const heldClosure=mode==='hold' && to.manner==='stop';
    const lipClosed = release && to.place === 'bilabial' && t < .4 || heldClosure && to.place==='bilabial' || to.manner==='nasal'&&to.place==='bilabial';
    const intent=(to.lip_round??0)>(from.lip_round??0)+.2?'round':
      (to.lip_spread??0)<(from.lip_spread??0)-.2?'relax':lipAction(to);
    const contactPose=t<.5?from:to;
    paintLips({lip_spread:spread,lip_round:round,opening:open,lip_teeth:contactPose.lip_teeth,lip_tongue:contactPose.lip_tongue},{closed:lipClosed,opening:open,intent,focused:focus==='lips'});
    chin.setAttribute('d',`M72 ${144+open*15}Q100 ${157+open*15} 128 ${144+open*15}`);
    chin.setAttribute('stroke',focus==='jaw'?'#a85618':'#69816d');
    lipText.textContent = lipClosed ? 'Lips together' : intent==='spread'?'Corners gently outward':intent==='relax'?'Let the corners relax':round>.5?'Round gently':'Comfortable lip shape';
    jaw.setAttribute('d',`M20 150Q115 ${190+open*18} 220 ${156+open*10}L255 ${125+open*9}`);
    jaw.setAttribute('stroke',focus==='jaw'?'#a85618':'#adbaab');
    const frontness = mix(from.front,to.front,t);
    let x=65+160*frontness,y=66+58*open;
    if(to.manner==='fricative')y=55;
    if(release && to.place!=='bilabial')y=t<.4?48:mode==='affricate'?55:90;
    if(['nasal','lateral'].includes(to.manner)&&to.place!=='bilabial')y=48;
    if(heldClosure && to.place!=='bilabial')y=48;
    if(to.place==='bilabial'){x=140;y=136;}
    tongue.setAttribute('d',`M40 155Q${x-50} ${y+20} ${x} ${y}Q${Math.min(240,x+20)} ${y+10} 230 145Q140 188 40 155Z`);
    tongue.setAttribute('stroke',focus==='tongue'?'#a85618':'#ad6d68');tongue.setAttribute('stroke-width',focus==='tongue'?'4':'2');
    air.setAttribute('opacity',heldClosure||to.manner==='nasal'?'0':release?(t>.4?'1':'0'):'1');
    noseAir.setAttribute('opacity',to.manner==='nasal'?'1':'0');
    place.textContent=to.manner==='nasal'?'Oral closure; air through nose':to.manner==='lateral'?'Tongue-tip contact; air at sides':to.manner==='approximant'?'No complete closure or friction':heldClosure?'Closure reference; release into the vowel':release?(t<.4?'Contact / closure':mode==='affricate'?'Release into short friction':'Release into the vowel'):'Small changes reshape the sound';
    const voiced = release ? to.voiced : (t<.5?from.voiced:to.voiced);
    const activeManner=release?to.manner:t<.5?from.manner:to.manner;
    if(!release){noseAir.setAttribute('opacity',activeManner==='nasal'?'1':'0');if(activeManner==='nasal')air.setAttribute('opacity','0');else if(!heldClosure)air.setAttribute('opacity','1');}
    voice.textContent = voiced ? '≈ Voice on · gentle throat buzz' : '— Voice off · consonant only';
    voice.setAttribute('fill',focus==='voice'?'#a85618':'#45694d');
  };
  update.dispose = () => resize.disconnect();
  return update;
}

export function renderTeaching(container, teaching, phone, {result, onTry} = {}) {
  container.replaceChildren();
  const lesson=teaching?.lessons[phone];container.hidden=!lesson;
  if(!lesson)return()=>{};
  const plan=movementPlan(teaching,phone,result);
  let frame, focused=lesson.steps[0].focus;
  const title=element('h2',null,`Feel your way to /${phone}/ · ${lesson.word}`);
  const quickTitle=element('h2',null,`Try /${phone}/ in “${lesson.word}”`);
  const cue=element('p','quick-cue',quickCue(lesson,phone,result));
  // The recording-specific panel already contains the one adjustment.
  cue.hidden=!!result?.diagnosis?.adjustment;
  const actions=element('div','quick-actions');
  const tryButton=element('button',null,result?.mode==='live_audio'?'Try again':'Try word');tryButton.dataset.practiceRecord='true';
  tryButton.addEventListener('click',()=>onTry?.(phone));
  const watch=element('button','secondary','Watch movement');actions.append(tryButton,watch);
  watch.setAttribute('aria-expanded','false');watch.setAttribute('aria-controls','mime-preview');
  const mime=element('section','mime-preview');mime.id='mime-preview';mime.hidden=true;
  const mimeCaption=element('p','teaching-example',plan.caption);
  const mimeStage=element('div','mime-stage');
  const mimePaint=illustration(mimeStage,teaching.poses[plan.fromPhone],teaching.poses[phone],plan.mode,phone);
  const mimeNote=element('p','muted',plan.note);
  const hideMime=element('button','secondary','Hide movement');
  hideMime.addEventListener('click',()=>{cancelAnimationFrame(frame);mime.hidden=true;watch.setAttribute('aria-expanded','false');});
  mime.append(mimeCaption,mimeStage,mimeNote,hideMime);
  mimePaint(0,focused);
  const shortHelp=element('p','muted','Say the word once. Recording stops after 3 seconds, then checks the selected sound.');
  const advanced=element('details','practice-more');advanced.id='practice-more';
  const moreSummary=element('summary',null,'More help (optional)');advanced.append(moreSummary);
  const intro=element('p','muted',lesson.mode==='release'?'Explore a closure and a brief release, then use it in a word.':'Explore a small movement between sounds, then use the target in a word. Try the sounds yourself as you move.');
  const example=element('p','teaching-example',plan.caption);
  const controls=element('div','physical-controls');controls.setAttribute('aria-label','Explore four physical controls');
  const controlHint=element('p','control-hint');controlHint.setAttribute('aria-live','polite');
  const stage=element('div','teaching-stage');
  const paint=illustration(stage,teaching.poses[plan.fromPhone],teaching.poses[phone],plan.mode,phone);
  const controlButtons=[];
  for(const control of teaching.controls){
    const button=element('button','physical-control',control.label);button.title=control.hint;
    button.addEventListener('click',()=>{focused=control.id;updateFocus();paint(Number(slider.value),focused);});
    controls.append(button);controlButtons.push([button,control.id]);
  }
  function updateFocus(){
    for(const [button,id] of controlButtons)button.setAttribute('aria-pressed',String(id===focused));
    controlHint.textContent=lesson.controls[focused];
  }
  const stepNav=element('div','practice-steps');stepNav.setAttribute('aria-label','Practice steps');
  const instruction=element('p','practice-instruction');instruction.setAttribute('aria-live','polite');
  const sliderLabel=element('label','movement-label','Explore the movement');sliderLabel.htmlFor='practice-movement';
  const slider=element('input');slider.id='practice-movement';slider.type='range';slider.min='0';slider.max='100';slider.value='0';
  const ends=element('div','movement-ends');ends.append(element('span',null,plan.mode==='release'?'Closure':plan.mode==='hold'?'Target reference':`Start /${plan.fromPhone}/`),element('span',null,plan.mode==='release'?'Release':`Target /${phone}/`));
  const replay=element('button','secondary','Show movement');
  const stepButtons=[];
  function setProgress(value){slider.value=String(value);paint(value,focused);slider.setAttribute('aria-valuetext',`${Math.round(value)} percent through the teaching movement`);}
  function setStep(index){
    cancelAnimationFrame(frame);const step=lesson.steps[index];focused=step.focus;
    const stepText=plan.mode==='hold'?'Explore the target comfortably. No mouth-shape correction has been established.':
      plan.personalized&&index===0?`Explore the reference for the suggested /${plan.fromPhone}/. Check whether that sound matches what you hear.`:
      plan.personalized&&index===1?quickCue(lesson,phone,result):step.text;
    instruction.textContent=`${index+1}. ${stepText}`;
    stepButtons.forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
    updateFocus();setProgress(step.progress);
  }
  lesson.steps.forEach((step,index)=>{
    const button=element('button','practice-step',`${index+1} ${step.title}`);
    button.addEventListener('click',()=>setStep(index));stepNav.append(button);stepButtons.push(button);
  });
  slider.addEventListener('input',()=>{cancelAnimationFrame(frame);setProgress(Number(slider.value));});
  replay.addEventListener('click',()=>{
    setStep(1);
    if(matchMedia('(prefers-reduced-motion: reduce)').matches){setProgress(100);return;}
    const started=performance.now();
    const animate=now=>{const progress=Math.min(100,(now-started)/18);setProgress(progress);if(progress<100)frame=requestAnimationFrame(animate);};
    setProgress(0);frame=requestAnimationFrame(animate);
  });
  watch.addEventListener('click',()=>{
    cancelAnimationFrame(frame);mime.hidden=false;watch.setAttribute('aria-expanded','true');
    if(matchMedia('(prefers-reduced-motion: reduce)').matches){mimePaint(100,focused);return;}
    const started=performance.now();
    const animate=now=>{const progress=Math.min(100,(now-started)/18);mimePaint(progress,focused);if(progress<100)frame=requestAnimationFrame(animate);};
    mimePaint(0,focused);frame=requestAnimationFrame(animate);
  });
  const feel=element('p','feel-check',`Notice for yourself: ${lesson.feel}`);
  const note=element('p','muted',lesson.note);note.hidden=!lesson.note;
  const credits=element('p','teaching-credit','Original WordSpeak practice, informed by Adrian Underhill. ');
  for(const source of [lesson.source,teaching.sources.videos]){
    const link=element('a',null,source===lesson.source?'Read the teaching source':'Watch American demonstrations');
    link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';credits.append(link,document.createTextNode(' '));
  }
  const boundary=element('p','muted','This is a teaching example, not an animation reconstructed from your recording.');
  advanced.append(title,intro,example,stepNav,instruction,controls,controlHint,stage,sliderLabel,slider,ends,replay,feel,note,boundary,credits);
  container.append(quickTitle,cue,actions,shortHelp,mime,advanced);
  setStep(0);
  return()=>{cancelAnimationFrame(frame);paint.dispose();mimePaint.dispose();};
}
