import {wordBank} from './conversation.mjs';
import {startPCMRecording} from './audio.mjs?v=20261125-8';
import {assessRecording} from './phrase-assessment.mjs?v=20261125-8';
import {renderTeaching} from './teaching.mjs';
import {renderDiagnosis} from './diagnosis.mjs';
import {PROSODY_LESSONS} from './prosody-lessons.mjs';
import {contourFromModel, renderIntonationVisual} from './intonation-visual.mjs?v=20261125-8';

const base='/demo/course', root=document.querySelector('#screen'), status=document.querySelector('#status');
const store='wordspeak.course.attempts.v1';
const el=(tag,text='',parent=root)=>{const n=document.createElement(tag);n.textContent=text;parent.append(n);return n;};
const title=s=>{const h=el('h1',s);h.tabIndex=-1;h.focus();};
const msg=s=>{status.textContent=s;};
function button(parent,text,action,primary=false){
  const b=el('button',text,parent);b.type='button';if(primary)b.className='primary';
  b.onclick=()=>run(action);return b;
}
function label(parent,text,control){const l=el('label',text,parent);l.append(control);return control;}
function input(parent,name,type='text'){const n=document.createElement('input');n.type=type;return label(parent,name,n);}
function choices(parent,name,values){
  const n=label(parent,name,document.createElement('select'));
  for(const [key,value] of values)n.add(new Option(value,key));return n;
}
function audio(parent,key,caption){if(caption)el('p',caption,parent);const a=el('audio','',parent);a.controls=true;a.preload='none';a.src=base+'/audio/'+key;return a;}
function readEvents(){return JSON.parse(localStorage.getItem(store)||'[]');}
let token=sessionStorage.getItem('wordspeak.course.token')||'', catalog,state,current,part=0,page='Today',busy=false;
let urls=[],capture=null,timer,levels,latest,attempt,session,recordButton;
let completed=new Set(), labPrompts=[], demoConfig=null, cleanupFns=[];
let micDeviceId='', micGain=2, activeStudio='IPA & Mouth';
let lang=localStorage.getItem('wordspeak.course.lang')||'en';

const VI_TEXT={
  'Today':'Hôm nay','Studios':'Phòng luyện','Library':'Thư viện','My Words':'Từ của tôi','Progress':'Tiến độ',
  'IPA & Mouth':'IPA & Khẩu hình','Intonation':'Ngữ điệu & Trọng âm','Talk with AI':'Nói chuyện với AI',
  'Find my starting point':'Kiểm tra trình độ đầu vào','Start from the beginning':'Bắt đầu từ bài đầu tiên',
  'Choose a starting point. You can open any lesson in the Library or jump straight into the 3 practice studios below.':'Chọn điểm bắt đầu. Bạn có thể mở bất kỳ bài học nào trong Thư viện hoặc vào thẳng 3 phòng luyện bên dưới.',
  '1. IPA & Mouth Movement':'1. Học IPA & Khẩu hình (Underhill)',
  'Underhill silent miming, 4 muscle buttons, and acoustic lip/tongue/jaw cues.':'Mô phỏng khẩu hình câm, 4 nhóm cơ (Môi · Lưỡi · Hàm · Giọng) và gợi ý chỉnh khẩu hình từ âm thanh.',
  '2. Intonation & Stress':'2. Ngữ điệu & Trọng âm (đường chuyển động)',
  'Moving pitch line that lights up syllables (a-BOUT) and situational sentences live.':'Đường cao độ chuyển động phát sáng từng âm tiết (a-BOUT) và từng từ theo ngữ cảnh.',
  '3. Talk with AI Coach':'3. Nói chuyện cùng AI Coach',
  'Speak in real situations and get pronunciation, intonation & meaning guidance.':'Luyện hội thoại theo tình huống thực tế và nhận góp ý phát âm, ngữ điệu, ý nghĩa.',
  'Tap the IPA phoneme tiles below (or type). Use ˈ before the main stressed syllable and ˌ for secondary stress.':'Bấm chọn các ký hiệu IPA bên dưới (hoặc gõ trực tiếp). Dùng ˈ trước âm tiết trọng âm chính và ˌ cho trọng âm phụ.',
  'Your IPA transcription':'Phiên âm IPA của bạn','Check transcription':'Kiểm tra phiên âm','Continue':'Tiếp tục',
  'Correct':'Chính xác!','Try again':'Thử lại nhé','Speaking attempt saved':'Đã lưu lượt nói','Microphone skip saved':'Đã bỏ qua micro',
  'Record a take':'Bắt đầu ghi âm','Stop recording':'Dừng ghi âm','Record another take':'Ghi âm lượt khác',
  'Save speaking attempt':'Lưu lượt nói','Continue without microphone':'Tiếp tục không cần micro','Ask a listener':'Nhờ người nghe kiểm tra',
  'Get AI pronunciation & meaning coaching':'Nhận góp ý phát âm & ý nghĩa từ AI',
  'General American Vowels':'Nguyên âm Mỹ (GA)','Diphthongs & R-vowels':'Nguyên âm đôi & âm R','Consonants':'Phụ âm',
  'Stress & editing':'Trọng âm & chỉnh sửa','British reference symbols (optional)':'Ký hiệu giọng Anh (tham khảo)',
  'IPA & Mouth Movement Lab':'Phòng luyện IPA & Khẩu hình (Underhill)',
  'Intonation & Stress Studio':'Phòng luyện Ngữ điệu & Trọng âm',
  'Talk with AI Coach':'Hội thoại cùng AI Coach',
  'Speak from IPA (spelling hidden)':'Đọc từ phiên âm IPA (ẩn chữ viết)',
  'Speak this IPA word':'Ghi âm từ IPA này','Next IPA word':'Từ IPA tiếp theo',
  '1. Word stress (real American dictionary audio + moving line)':'1. Trọng âm từ (giọng từ điển Mỹ thật + đường chuyển động)',
  '2. Sentences in situations (same words, different meaning)':'2. Ngữ điệu câu theo tình huống (cùng câu, khác nghĩa)',
  'Record your reply':'Ghi âm câu trả lời','Stop & send to AI':'Dừng & gửi cho AI','Record next turn':'Ghi âm lượt tiếp theo',
  '1. Meaning & what I heard':'1. Ý nghĩa & nội dung AI nghe được',
  '2. Pronunciation & mouth guidance':'2. Phát âm & gợi ý chỉnh khẩu hình',
  '3. Intonation, stress & rhythm':'3. Ngữ điệu, trọng âm & nhịp điệu',
  'Search lessons':'Tìm bài học','Book':'Sách nguồn','Skill':'Kỹ năng','IPA symbol':'Ký hiệu IPA',
  'Word or expression':'Từ hoặc cụm từ','Your situation (optional)':'Tình huống sử dụng (tuỳ chọn)','Save word':'Lưu từ',
  'Return to Today':'Về trang Hôm nay','Continue to next lesson':'Học bài tiếp theo',
  'Practice finished':'Hoàn thành bài luyện tập!','Review finished':'Hoàn thành bài ôn tập!',
  'Lips':'Môi','Tongue':'Lưỡi','Jaw':'Hàm','Voice':'Giọng (rung cổ)',
  'General American reference':'Giọng Mỹ chuẩn (US)','British English reference':'Giọng Anh (UK tham khảo)',
  'Play & watch line':'Nghe & xem đường ngữ điệu','Animate stress line':'Chạy đường ngữ điệu',
};
const t=s=>(lang==='vi'&&VI_TEXT[s])?VI_TEXT[s]:s;
const langBtn=document.querySelector('#lang-toggle');
function applyLangUI(){
  document.documentElement.lang=lang;
  if(langBtn)langBtn.textContent=lang==='vi'?'VI | en':'EN | vi';
  document.querySelectorAll('nav button').forEach(b=>{b.textContent=t(b.dataset.page);});
  const set=(sel,en,vi)=>{const n=document.querySelector(sel);if(n)n.textContent=lang==='vi'?vi:en;};
  set('#lbl-email','Email','Email');set('#lbl-pass','Password','Mật khẩu');
  set('#btn-signin','Sign in','Đăng nhập');set('#btn-register','Create account','Tạo tài khoản');
  set('#logout','Sign out','Đăng xuất');
  set('#lbl-mic-dev','Input device','Thiết bị micro');set('#lbl-mic-lvl','Live level','Mức âm lượng');
  set('#footer-lab','Open full standalone sound lab ↗','Mở phòng thí nghiệm âm thanh đầy đủ ↗');
  if(micGainLabel?.firstChild)micGainLabel.firstChild.textContent=lang==='vi'?`Khuếch đại micro: ${micGain}×`:`Input boost: ${micGain}×`;
  accountUI();
}
if(langBtn){
  langBtn.onclick=()=>{
    lang=lang==='en'?'vi':'en';
    localStorage.setItem('wordspeak.course.lang',lang);
    applyLangUI();
    if(current)renderItem();else run(()=>view(page));
  };
}
function localizeUnderhillButtons(container){
  if(lang!=='vi')return;
  container.querySelectorAll('.physical-control').forEach(b=>{
    if(VI_TEXT[b.textContent])b.textContent=VI_TEXT[b.textContent];
  });
}

const micSelect=document.querySelector('#mic-device');
const micGainInput=document.querySelector('#mic-gain');
const micGainLabel=document.querySelector('#mic-gain-label');
const micMeter=document.querySelector('#mic-meter');
const micSummary=document.querySelector('#mic-summary');
if(micGainInput){
  micGainInput.oninput=()=>{micGain=Number(micGainInput.value)||2;micGainLabel.firstChild.textContent=`Input boost: ${micGain}×`;};
}
if(micSelect){
  micSelect.onchange=()=>{micDeviceId=micSelect.value;};
}
async function refreshMicDevices(){
  if(!micSelect||!navigator.mediaDevices?.enumerateDevices)return;
  try{
    const devs=(await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==='audioinput'&&d.deviceId&&d.deviceId!=='default');
    const prev=micSelect.value;
    micSelect.replaceChildren(new Option('System default microphone',''));
    devs.forEach((d,i)=>micSelect.add(new Option(d.label||`Microphone ${i+1}`,d.deviceId)));
    if([...micSelect.options].some(o=>o.value===prev))micSelect.value=prev;
  }catch{}
}
async function startMic(onLevel=()=>{}){
  const rec=await startPCMRecording({
    gain:micGain,deviceId:micDeviceId,autoGain:true,autoNormalize:true,
    onLevel:data=>{
      if(micMeter)micMeter.value=Math.min(1,data.peak||0);
      if(micSummary&&data.phase==='recording')micSummary.textContent=`Microphone · Recording (${Math.round((data.peak||0)*100)}%)`;
      if(micSummary&&data.phase==='finished')micSummary.textContent=`Microphone · Auto-level on (${data.gain>1?data.gain.toFixed(1)+'×':'1×'})`;
      onLevel(data);
    }
  });
  refreshMicDevices();
  return rec;
}

const VOWELS=new Set(['i','ɪ','ɛ','æ','ʌ','ɑ','ɔ','ʊ','u','ɝ','ɚ','ə']);
const DIPHTHONGS=new Set(['eɪ','aɪ','ɔɪ','aʊ','oʊ','ɪɹ','ɛɹ','ʊɹ']);
const UK_ONLY=new Set(['ɒ','e','ɜ','ɪə','eə','ʊə','əʊ','r']);
const STRESS_MARKS=new Set(['ˈ','ˌ','ː',' ']);
const DIGRAPHS=['tʃ','dʒ','eɪ','aɪ','ɔɪ','aʊ','oʊ','ɪɹ','ɛɹ','ʊɹ','ɪə','eə','ʊə','əʊ'];
const IPA_HINTS={i:'seat',ɪ:'sit',ɛ:'bed',æ:'bad',ʌ:'cup',ɑ:'palm',ɔ:'caught',ʊ:'full',u:'food',ɝ:'bird',ɚ:'teacher',ə:'about',
  eɪ:'sale',aɪ:'time',ɔɪ:'coin',aʊ:'now',oʊ:'go',ɪɹ:'near',ɛɹ:'care',ʊɹ:'tour',
  p:'pack',b:'back',t:'ten',d:'den',k:'key',ɡ:'gate',s:'sip',z:'rise',ʃ:'ship',ʒ:'vision',tʃ:'chin',dʒ:'joke',
  f:'fan',v:'van',w:'wet',j:'yes',h:'hat',θ:'thin',ð:'they',m:'map',n:'net',ŋ:'sing',l:'light',ɹ:'red',
  ɒ:'UK pot',e:'UK bed',ɜ:'UK bird',ɪə:'UK near',eə:'UK care',ʊə:'UK tour',əʊ:'UK go',r:'r variant','ˈ':'main stress','ˌ':'secondary stress','ː':'long mark'};

const AI_SCENARIOS=[
  {id:'booking',title:'Correct a restaurant booking',focus:'fifteen',
   aiLine:'Host: “Got it — a table for fifty people at seven, right?”',
   goal:'Correct the number to fifteen seats (put clear prominence on FIFTEEN, not fifty).',
   sample:'I booked fifteen seats.',
   assessment:{id:'prominence',variant:'fifteen',expected:'i booked fifteen seats'},
   contour:{tokens:['I','booked','FIFTEEN','seats.'],weights:[.4,.45,1,.5],path:[.42,.45,.86,.32]}},
  {id:'seat',title:'Offer a seat (seat vs. sit)',focus:'seat',
   aiLine:'Guest: “Excuse me, did you say sit or is there a free seat?”',
   goal:'Offer a seat clearly with tense /i/ in “seat” so the listener does not hear “sit”.',
   sample:'Take a seat.',
   assessment:{id:'connected-speech',variant:'seat',expected:'take a seat'},
   contour:{tokens:['Take','a','SEAT.'],weights:[.55,.25,1],path:[.52,.36,.82]}},
  {id:'really',title:'Check surprising news (intonation)',focus:'really',
   aiLine:'Friend: “They moved our presentation to tomorrow morning.”',
   goal:'Say “Really?” with a clear rising pitch to ask for confirmation.',
   sample:'Really?',
   assessment:{id:'intonation',variant:'rise',expected:'really'},
   contour:{tokens:['Real','ly?'],weights:[1,.6],path:[.42,.38,.86]}},
  {id:'can',title:'Reassure a friend (weak vs. strong form)',focus:'can',
   aiLine:'Friend: “I thought you couldn’t drive us to the airport?”',
   goal:'Correct their doubt by emphasizing CAN: “I CAN drive.”',
   sample:'I can drive.',
   assessment:{id:'weak-forms',variant:'correct',expected:'i can drive'},
   contour:{tokens:['I','CAN','drive.'],weights:[.45,1,.45],path:[.45,.84,.32]}},
  {id:'free',title:'Free speaking check (your own topic)',focus:'',
   aiLine:'AI Coach: “Tell me one thing you have planned today, or try any word you want to test.”',
   goal:'Speak naturally for 3–10 seconds. The AI will transcribe your message, check pronunciation, and review phrasing.',
   sample:'',
   assessment:null,contour:null},
];

let queue=Promise.resolve();
function run(action){
  queue=queue.then(async()=>{
    busy=true;root.setAttribute('aria-busy','true');
    try{await action();}catch(e){msg(e.message||'The service could not respond. Try again.');}
    finally{busy=false;root.removeAttribute('aria-busy');}
  });
  return queue;
}
async function request(url,body,method,customHeaders={}){
  const headers={...customHeaders};
  if(token && url.startsWith('/api/'))headers.Authorization='Bearer '+token;
  if(body!==undefined && !(body instanceof Blob) && !(body instanceof FormData))headers['Content-Type']='application/json';
  let response;
  try{response=await fetch(url,{method:method||(body===undefined?'GET':'POST'),headers,body:(body instanceof Blob||body instanceof FormData)?body:JSON.stringify(body)});}
  catch{throw Error('Connection unavailable. Reconnect and retry. Your previous saved work is available after reconnecting.');}
  if(!response.ok){
    if(response.status===401){token='';sessionStorage.removeItem('wordspeak.course.token');accountUI();throw Error('Please sign in again to reopen your account progress.');}
    if(response.status===409)throw Error('The course or attempt changed. Reopen the lesson to continue.');
    if(url.startsWith('/api/') && [404,405,502,503].includes(response.status))throw Error('The account service is unavailable. The local course supports practice on this device.');
    throw Error('The service could not finish this request ('+response.status+'). Try again.');
  }
  return response.json();
}
async function refresh(){state=token?await request('/api/course/state'):await request(base+'/study',readEvents());}
function resetTakes(){
  clearTimeout(timer);urls.forEach(URL.revokeObjectURL);urls=[];latest=null;recordButton=null;
  for(const fn of cleanupFns){try{fn();}catch{}}cleanupFns=[];
}
function clear(){resetTakes();root.replaceChildren();msg('');}
function nav(active){document.querySelectorAll('nav button').forEach(b=>b.setAttribute('aria-current',b.dataset.page===active?'page':'false'));}
function accountUI(){
  const lbl=document.querySelector('#account-label');
  if(lbl)lbl.textContent=lang==='vi'?(token?'Tiến độ tài khoản · Đã đăng nhập':'Học trên thiết bị này · Tài khoản'):(token?'Account progress · Signed in':'Learning on this device · Account');
  document.querySelector('#auth').hidden=!!token;document.querySelector('#logout').hidden=!token;
  document.querySelector('#auth').style.display=token?'none':'';
}
function startActions(parent,lessonId,phase='practice'){
  const info=catalog.lessons.find(l=>l.id===lessonId);
  button(parent,(phase==='review'?'Review · ':'')+info.title,()=>openLesson(lessonId,phase),true);
}

function renderGroupedIpaKeyboard(parent, box){
  const kb=el('section','',parent);kb.className='ipa-keyboard';kb.setAttribute('aria-label','IPA phoneme keyboard');
  const hintBar=el('p',lang==='vi'?'Chạm vào ký hiệu IPA bất kỳ để xem từ ví dụ (vd: /ɪ/ như trong sit).':'Tap or focus any IPA tile to see an example word (e.g. /ɪ/ as in sit).',kb);
  hintBar.className='ipa-hint-bar';
  const groups=[
    ['General American Vowels', catalog.symbols.filter(s=>VOWELS.has(s)), 'tile-vowel'],
    ['Diphthongs & R-vowels', catalog.symbols.filter(s=>DIPHTHONGS.has(s)), 'tile-diphthong'],
    ['Consonants', catalog.symbols.filter(s=>!VOWELS.has(s)&&!DIPHTHONGS.has(s)&&!STRESS_MARKS.has(s)&&!UK_ONLY.has(s)), 'tile-consonant'],
    ['Stress & editing', catalog.symbols.filter(s=>STRESS_MARKS.has(s)), 'tile-stress'],
    ['British reference symbols (optional)', catalog.symbols.filter(s=>UK_ONLY.has(s)), 'tile-edit'],
  ];
  for(const [name, list, cls] of groups){
    if(!list.length)continue;
    const g=el('div','',kb);g.className='ipa-group';
    const lbl=el('p',t(name),g);lbl.className='ipa-group-label';
    const row=el('div','',g);row.className='tiles';
    for(const s of list){
      const b=el('button',s===' '?'Space':s,row);b.type='button';b.className=cls;
      b.setAttribute('aria-label',s===' '?'Insert space':'Insert '+s);
      if(IPA_HINTS[s])b.title=`/${s}/ as in ${IPA_HINTS[s]}`;
      const showHint=()=>{if(IPA_HINTS[s])hintBar.textContent=lang==='vi'?`/${s}/ — như trong “${IPA_HINTS[s]}”`:`/${s}/ — as in “${IPA_HINTS[s]}”`;};
      b.onfocus=showHint;b.onmouseenter=showHint;
      b.onclick=()=>{
        showHint();
        const start=box.selectionStart??box.value.length, end=box.selectionEnd??box.value.length;
        box.setRangeText(s,start,end,'end');box.focus();
      };
    }
    if(name==='Stress & editing'){
      const back=el('button','⌫',row);back.type='button';back.className='tile-edit';back.setAttribute('aria-label','Backspace');
      back.onclick=()=>{
        const start=box.selectionStart??box.value.length, end=box.selectionEnd??box.value.length;
        if(start!==end)box.setRangeText('',start,end,'end');
        else if(start>0){
          const prev2=box.value.slice(Math.max(0,start-2),start);
          const delLen=DIGRAPHS.includes(prev2)?2:1;
          box.setRangeText('',start-delLen,start,'end');
        }
        box.focus();
      };
      const clr=el('button','Clear',row);clr.type='button';clr.className='tile-edit';clr.setAttribute('aria-label','Clear transcription');
      clr.onclick=()=>{box.value='';box.focus();};
    }
  }
}

async function analyzeMouthMovement(blob, promptId){
  const form=new FormData();
  form.append('audio',blob,'take.wav');
  form.append('prompt_id',promptId);
  form.append('input_scope','word');
  return request('/demo/analyze',form,'POST');
}

function revealUnderhillControls(container){
  const more=container.querySelector('details.practice-more');
  if(more)more.open=true;
  localizeUnderhillButtons(container);
}

async function recordWithManualStop(labelText, maxMs=6000){
  let active=null, stopTimer=0;
  return new Promise(async(resolve,reject)=>{
    try{
      active=await startMic();
      status.replaceChildren();
      el('span',labelText+' ',status);
      const stopBtn=el('button',t('Stop recording'),status);stopBtn.type='button';stopBtn.className='primary';
      const finish=async()=>{
        if(!active)return;
        clearTimeout(stopTimer);
        const rec=active;active=null;
        stopBtn.disabled=true;
        try{resolve(await rec.stop());}catch(e){reject(e);}
      };
      stopBtn.onclick=finish;
      stopTimer=setTimeout(finish,maxMs);
    }catch(e){reject(e);}
  });
}

function renderInlineUnderhillLab(parent, phone){
  if(!demoConfig?.teaching?.lessons?.[phone])return;
  const prompt=labPrompts.find(p=>p.target_phone===phone);
  const box=el('section','',parent);box.className='underhill-box';
  const stage=el('div','',box);
  const diagBox=el('div','',box);
  let dispose=null;
  const runTry=async()=>{
    if(!prompt){msg('Record a take below to compare your sound.');return;}
    await run(async()=>{
      const blob=await recordWithManualStop(lang==='vi'?`Đọc rõ từ “${prompt.word}”, sau đó bấm Dừng:`:`Say “${prompt.word}” clearly, then click Stop:`);
      msg(lang==='vi'?'Đang phân tích âm thanh để gợi ý chỉnh khẩu hình…':'Analyzing acoustic cues for lip/tongue/jaw guidance…');
      const result=await analyzeMouthMovement(blob,prompt.id);
      mount(result);
      renderDiagnosis(diagBox,result);
      msg('');
    });
  };
  function mount(result=null){
    dispose?.();
    dispose=renderTeaching(stage,demoConfig.teaching,phone,{result,onTry:runTry});
    revealUnderhillControls(stage);
    cleanupFns.push(()=>dispose?.());
  }
  mount(null);
}

function renderIpaMouthStudio(){
  title(t('IPA & Mouth Movement Lab'));
  el('p',lang==='vi'?'Học từng âm IPA Mỹ (GA) theo phương pháp vật lý Adrian Underhill: xem mô phỏng khẩu hình câm, cảm nhận Môi · Lưỡi · Hàm · Giọng, sau đó ghi âm để nhận gợi ý điều chỉnh từ tín hiệu âm thanh.':'Learn each individual General American IPA phoneme using Adrian Underhill’s physical method: watch the silent mouth movement, explore Lips · Tongue · Jaw · Voice, then record for acoustic lip/tongue/jaw adjustment cues.');
  if(!demoConfig?.teaching){el('p','Sound lab configuration is unavailable on this server.');return;}
  const allPhones=Object.keys(demoConfig.teaching.lessons).filter(p=>!(p==='iː'&&demoConfig.teaching.lessons.i)&&!(p==='uː'&&demoConfig.teaching.lessons.u));
  let activePhone=allPhones.includes('i')?'i':allPhones[0];
  const pickerWrap=el('div','',root);
  const stageWrap=el('div','',root);stageWrap.className='underhill-box';
  const diagWrap=el('div','',root);
  const buttons=[];
  let disposeTeaching=null;

  function showPhone(phone, result=null){
    activePhone=phone;
    for(const [p,b] of buttons)b.setAttribute('aria-pressed',String(p===phone));
    disposeTeaching?.();stageWrap.replaceChildren();diagWrap.replaceChildren();
    const prompt=labPrompts.find(item=>item.target_phone===phone);
    disposeTeaching=renderTeaching(stageWrap,demoConfig.teaching,phone,{
      result,
      onTry:async()=>{
        if(!prompt)return;
        await run(async()=>{
          const blob=await recordWithManualStop(lang==='vi'?`Đọc từ “${prompt.word}”, sau đó bấm Dừng:`:`Say “${prompt.word}”, then click Stop:`);
          msg(lang==='vi'?'Đang phân tích âm thanh…':'Analyzing acoustic cues…');
          const analysis=await analyzeMouthMovement(blob,prompt.id);
          showPhone(phone,analysis);
          renderDiagnosis(diagWrap,analysis);
          msg('');
        });
      }
    });
    revealUnderhillControls(stageWrap);
    cleanupFns.push(()=>disposeTeaching?.());
    if(prompt){
      const humanAudio=el('audio','',stageWrap);humanAudio.controls=true;humanAudio.preload='none';
      humanAudio.src=base+'/human-word?word='+encodeURIComponent(prompt.word)+'&accent=en-US';
      el('p',lang==='vi'?`Giọng người thật (Wiktionary US) cho từ “${prompt.word}”`:`Real American dictionary recording (Wiktionary US) for “${prompt.word}”`,stageWrap).className='muted';
      const jump=catalog.lessons.find(l=>l.symbols.includes(phone)&&l.book==='ship');
      if(jump)button(stageWrap,(lang==='vi'?'Mở bài học đầy đủ cho /':'Open full lesson for /')+phone+'/ ('+jump.title+')',()=>openLesson(jump.id));
    }
  }

  const studioGroups=[
    ['General American Vowels', allPhones.filter(p=>VOWELS.has(p)||p==='ɒ')],
    ['Diphthongs & R-vowels', allPhones.filter(p=>DIPHTHONGS.has(p))],
    ['Consonants', allPhones.filter(p=>!VOWELS.has(p)&&p!=='ɒ'&&!DIPHTHONGS.has(p))],
  ];
  for(const [labelText, groupPhones] of studioGroups){
    if(!groupPhones.length)continue;
    const lbl=el('p',t(labelText),pickerWrap);lbl.className='ipa-group-label';
    const grid=el('div','',pickerWrap);grid.className='sound-grid';
    for(const p of groupPhones){
      const lesson=demoConfig.teaching.lessons[p];
      const b=el('button','/'+p+'/ · '+lesson.word,grid);b.type='button';b.className='sound-chip';
      b.onclick=()=>showPhone(p);
      buttons.push([p,b]);
    }
  }
  showPhone(activePhone);

  // Dedicated IPA-Only -> Speak drill (English spelling hidden until spoken)
  const drillItems=[
    {ipa:'/sit/',word:'seat',phone:'i'},{ipa:'/sɪt/',word:'sit',phone:'ɪ'},
    {ipa:'/bɛd/',word:'bed',phone:'ɛ'},{ipa:'/bæd/',word:'bad',phone:'æ'},
    {ipa:'/fud/',word:'food',phone:'u'},{ipa:'/ʃɪp/',word:'ship',phone:'ʃ'},
    {ipa:'/θɪn/',word:'thin',phone:'θ'},{ipa:'/ɹɛd/',word:'red',phone:'ɹ'},
  ];
  let drillIdx=0;
  const drill=el('section','',root);drill.className='ipa-drill';
  el('h2',t('Speak from IPA (spelling hidden)'),drill);
  el('p',lang==='vi'?'Đọc to từ tiếng Anh từ ký hiệu IPA bên dưới. Hệ thống sẽ kiểm tra âm thanh và mở đáp án từ gốc.':'Read the IPA symbols below and say the English word aloud. WordSpeak checks your sound and then reveals the word.',drill);
  const ipaDisplay=el('p',drillItems[0].ipa,drill);ipaDisplay.className='ipa-big';
  const drillOut=el('div','',drill);
  const drillActions=el('div','',drill);drillActions.className='actions';
  button(drillActions,t('Speak this IPA word'),async()=>{
    const d=drillItems[drillIdx];
    const prompt=labPrompts.find(p=>p.word.toLowerCase()===d.word)||labPrompts.find(p=>p.target_phone===d.phone);
    if(!prompt)throw Error('Acoustic model unavailable for this item.');
    const blob=await recordWithManualStop(lang==='vi'?`Đọc từ cho ${d.ipa}, rồi bấm Dừng:`:`Say the word for ${d.ipa}, then click Stop:`);
    msg(lang==='vi'?'Đang kiểm tra phát âm của bạn…':'Checking your spoken word…');
    const res=await analyzeMouthMovement(blob,prompt.id);
    msg('');
    drillOut.replaceChildren();
    el('p',(lang==='vi'?'Từ đúng: “':'Revealed word: “')+d.word+'” ('+d.ipa+')',drillOut);
    renderDiagnosis(drillOut,res);
  },true);
  button(drillActions,t('Next IPA word'),()=>{
    drillIdx=(drillIdx+1)%drillItems.length;
    ipaDisplay.textContent=drillItems[drillIdx].ipa;
    drillOut.replaceChildren();
  });
}

function renderIntonationStudio(){
  title(t('Intonation & Stress Studio'));
  el('p',lang==='vi'?'Xem đường cao độ & trọng âm chuyển động phát sáng từng âm tiết và từng từ theo thời gian thực — đồng bộ với giọng từ điển Mỹ thật cho từng từ (a-BOUT, RE-cord / re-CORD) và âm thanh mẫu cho câu theo tình huống.':'Watch the moving pitch and stress line light up each syllable and word in real time — synced to real American dictionary recordings for individual words (a-BOUT, RE-cord vs. re-CORD) and audio models for situational sentences.');

  const wordSection=el('section','',root);
  el('h2',t('1. Word stress (real American dictionary audio + moving line)'),wordSection);
  const wordExamples=[
    {label:'about · stress on 2nd syllable (a-BOUT)',marked:'about',word:'about',cue:'Keep “a” light (/ə/), then lift pitch and clarity on BOUT.'},
    {label:'fifteen · stress on 2nd syllable (fif-TEEN)',marked:'fifteen',word:'fifteen',cue:'Lift on TEEN so listeners do not hear fifty.'},
    {label:'fifty · stress on 1st syllable (FIF-ty)',marked:'fifty',word:'fifty',cue:'Start high on FIF and drop cleanly on ty.'},
    {label:'record (noun) · stress on 1st syllable (RE-cord)',wordKey:'record_noun',word:'record',sense:'noun',cue:'Noun: “Keep a RE-cord of the meeting.” Stress the first syllable.'},
    {label:'record (verb) · stress on 2nd syllable (re-CORD)',wordKey:'record_verb',word:'record',sense:'verb',cue:'Verb: “Please re-CORD this.” Stress the second syllable.'},
    {label:'photography · stress on 2nd syllable (pho-TOG-ra-phy)',marked:'photography',word:'photography',cue:'Peak on TOG; relax the surrounding syllables.'},
  ];
  const wordPicker=choices(wordSection,'Choose a word',wordExamples.map((w,i)=>[String(i),w.label]));
  const wordSlot=el('div','',wordSection);
  function showWord(idx){
    wordSlot.replaceChildren();
    const ex=wordExamples[idx];
    const aEl=el('audio','',wordSlot);aEl.controls=true;aEl.preload='metadata';
    aEl.src=base+'/human-word?word='+encodeURIComponent(ex.word)+'&accent=en-US'+(ex.sense?'&sense='+ex.sense:'');
    const vis=renderIntonationVisual(wordSlot,{...contourFromModel(ex),label:ex.cue,audioEl:aEl,durationMs:900,buttonLabel:'Play & watch line'});
    cleanupFns.push(()=>vis.stop());
  }
  wordPicker.onchange=()=>showWord(Number(wordPicker.value));
  showWord(0);

  const sentSection=el('section','',root);
  el('h2',t('2. Sentences in situations (same words, different meaning)'),sentSection);
  const cleanExpected=tokens=>tokens.join(' ').toLowerCase().replace(/’/g,"'").replace(/[^a-z' ]/g,'').replace(/\s+/g,' ').trim();
  const situations=[
    {id:'booking-studio',lessonId:'use-53',title:'Correcting a booking · fifteen seats',cue:'Shift the peak to change whether you are correcting the number or the item.',
     variants:[
       {label:'Correct the number — “I booked FIFTEEN seats.”',speak:'I booked fifteen seats.',tokens:['I','booked','FIFTEEN','seats.'],weights:[.4,.45,1,.5],path:[.42,.45,.86,.32],gesture:'Lift on FIFTEEN, then drop on seats.',goal:{id:'prominence',variant:'fifteen',expected:'i booked fifteen seats'}},
       {label:'Correct what was booked — “I booked fifteen SEATS.”',speak:'I booked fifteen seats.',tokens:['I','booked','fifteen','SEATS.'],weights:[.4,.45,.5,1],path:[.42,.45,.48,.86],gesture:'Keep fifteen steady and lift on SEATS.',goal:{id:'prominence',variant:'seats',expected:'i booked fifteen seats'}},
     ]},
    ...PROSODY_LESSONS.filter(l=>l.id!=='word-stress').map(l=>({id:l.id,lessonId:({intonation:'use-55','weak-forms':'use-33','thought-groups':'use-43','connected-speech':'use-38'})[l.id]||'',title:l.label+' · '+l.title,cue:l.cue,
      variants:l.variants.map(v=>({label:v.label+' — '+v.meaning,speak:v.tokens.join(l.id==='intonation'?'':' '),tokens:v.tokens,weights:v.weights,path:v.path,gesture:v.gesture,
        goal:{id:l.id,variant:v.id,expected:l.id==='intonation'?v.tokens.join('').toLowerCase().replace(/[^a-z']/g,''):cleanExpected(v.tokens)}}))})),
  ];
  const sitPicker=choices(sentSection,'Choose a situation',situations.map((s,i)=>[String(i),s.title]));
  const sitSlot=el('div','',sentSection);
  async function showSituation(idx){
    sitSlot.replaceChildren();
    const sit=situations[idx];
    el('p',sit.cue,sitSlot);
    let lessonModels=[];
    if(sit.lessonId){
      try{
        const lData=await request(base+'/lesson/'+sit.lessonId+'?phase=practice');
        lessonModels=lData.exercises.find(e=>e.models?.length)?.models||[];
      }catch{}
    }
    sit.variants.forEach((v,vi)=>{
      let aEl=null;
      if(lessonModels[vi]?.audio){
        aEl=audio(sitSlot,lessonModels[vi].audio,v.label);
      }
      const vis=renderIntonationVisual(sitSlot,{tokens:v.tokens,weights:v.weights,path:v.path,label:aEl?'':v.label,audioEl:aEl,durationMs:1500,showButton:Boolean(aEl),buttonLabel:'Play & watch line'});
      cleanupFns.push(()=>vis.stop());
      if(!aEl){
        const hearBtn=el('button','Play & watch line',vis.card);hearBtn.type='button';hearBtn.className='secondary';
        hearBtn.onclick=()=>{
          vis.animate();
          if(window.speechSynthesis){const u=new SpeechSynthesisUtterance(v.speak);u.lang='en-US';u.rate=0.9;speechSynthesis.cancel();speechSynthesis.speak(u);}
        };
      }
      el('p',v.gesture,vis.card).className='muted';
    });
    recorder({kind:'record',focus:sit.variants[0].speak,hideModelVisuals:true,models:sit.variants.map(v=>({line:v.speak,intention:v.label,assessment:v.goal}))},()=>{msg('Recording checked! Try the other reading to compare.');},true,'Check & continue',sitSlot);
    if(sit.lessonId)button(sitSlot,(lang==='vi'?'Mở bài học đầy đủ (':'Open related lesson (')+sit.lessonId+')',()=>openLesson(sit.lessonId));
  }
  sitPicker.onchange=()=>showSituation(Number(sitPicker.value));
  showSituation(0);
}

function renderTalkWithAiStudio(){
  title(t('Talk with AI Coach'));
  el('p',lang==='vi'?'Luyện hội thoại nhiều lượt theo tình huống thực tế. WordSpeak phân tích ý nghĩa, phát âm & khẩu hình, và ngữ điệu/trọng âm — rồi phản hồi để bạn chỉnh ngay ở lượt tiếp theo.':'Have a multi-turn spoken exchange in a real situation. WordSpeak checks your meaning, pronunciation & mouth movement, and intonation/stress — and replies so you can clarify on your next turn.');
  const picker=choices(root,lang==='vi'?'Chọn tình huống hội thoại':'Choose a conversation situation',AI_SCENARIOS.map((s,i)=>[String(i),s.title]));
  const stage=el('section','',root);

  function showScenario(idx){
    resetTakes();stage.replaceChildren();
    const sc=AI_SCENARIOS[idx];
    const thread=el('div','',stage);thread.className='chat-thread';
    const bubble=el('div','',thread);bubble.className='ai-bubble';
    el('strong',sc.aiLine,bubble);
    el('p',sc.goal,bubble).className='muted';
    if(sc.sample)el('p','Suggested reply (or use your own words): “'+sc.sample+'”',bubble);
    if(sc.contour){
      const vis=renderIntonationVisual(stage,{...sc.contour,label:'Target stress/intonation contour to try',durationMs:1400});
      cleanupFns.push(()=>vis.stop());
    }
    const controls=el('div','',stage);controls.className='actions';
    const related=({booking:'use-53',seat:'ship-01',really:'use-55',can:'use-33'})[sc.id];
    if(related)button(controls,(lang==='vi'?'Mở bài học liên quan (':'Open related lesson (')+related+')',()=>openLesson(related));
    const out=el('div','',stage);
    let recBtn, turnCount=0;
    recBtn=button(controls,'Record your reply',async()=>{
      if(!capture){
        levels=null;
        try{capture=await startMic(d=>{levels=d;});}
        catch{throw Error('Microphone unavailable. Check browser permission.');}
        recBtn.textContent='Stop & send to AI';msg('Listening… speak your reply now.');
        timer=setTimeout(()=>{if(capture)run(()=>finishTurn());},20000);
      }else await finishTurn();
    },true);

    async function finishTurn(){
      clearTimeout(timer);const active=capture;capture=null;const blob=await active.stop();latest=blob;
      recBtn.textContent='Record next turn';
      out.replaceChildren();
      const player=el('audio','',out);player.controls=true;player.src=URL.createObjectURL(blob);urls.push(player.src);
      if(levels && levels.rawPeak < 0.002){
        msg('');
        el('p','Your recording sounded completely silent. Open Microphone settings above to select your active input device or increase Input boost.',out).className='feedback';
        return;
      }
      msg('AI is analyzing your meaning, pronunciation, and intonation…');
      const form=new FormData();form.append('audio',blob,'turn.wav');form.append('focus',sc.focus);
      const [obsRes, prosodyRes, tutorTurn] = await Promise.all([
        token ? Promise.resolve(null) : request('/tutor/observe',form,'POST').catch(()=>null),
        sc.assessment ? assessRecording({blob,levels,goal:sc.assessment},AbortSignal.timeout(45000)).catch(()=>null) : Promise.resolve(null),
        token ? (async()=>{
          if(!session)session=(await request('/api/sessions',{topic:sc.title})).id;
          return request('/api/sessions/'+session+'/spoken-turn?focus='+encodeURIComponent(sc.focus),blob,'POST',{'Content-Type':'audio/wav'});
        })().catch(()=>null) : Promise.resolve(null),
      ]);
      msg('');
      turnCount++;
      const heardText=tutorTurn?.text||obsRes?.text||prosodyRes?.text||'';
      const lower=heardText.toLowerCase().replace(/\b15\b/g,'fifteen').replace(/\b50\b/g,'fifty').replace(/\b13\b/g,'thirteen').replace(/\b30\b/g,'thirty');
      let aiFollowUp=tutorTurn?.reply||'';
      if(!aiFollowUp){
        if(sc.id==='booking' && lower.includes('fifty') && !lower.includes('fifteen'))aiFollowUp='Wait — I still heard “fifty” (5-0)! Did you mean one-five (fif-TEEN)? Stress the second syllable and try again.';
        else if(sc.id==='seat' && lower.includes('sit') && !lower.includes('seat'))aiFollowUp='I heard “sit” (/sɪt/). Spread your lips slightly and hold tense /i/ for “seat” — try telling me again!';
        else if(sc.focus && lower.includes(sc.focus.toLowerCase()))aiFollowUp=`Got it — I clearly understood “${sc.focus}”! Would you like to try a second take with even clearer emphasis, or switch situations?`;
        else if(heardText)aiFollowUp=`I heard “${heardText}”. Try emphasizing “${sc.focus||'your main detail'}” clearly on your next turn so a listener catches it right away.`;
        else aiFollowUp='I could not make out the words clearly — check the Microphone boost bar above and try one more turn.';
      }
      const uBub=el('div','',thread);uBub.className='user-bubble';
      el('strong',`You (Turn ${turnCount}): `,uBub);el('span',heardText||'(unclear audio)',uBub);
      const aBub=el('div','',thread);aBub.className='ai-bubble';
      el('strong','AI Coach: ',aBub);el('span',aiFollowUp,aBub);

      const grid=el('div','',out);grid.className='coach-grid';
      const c1=el('div','',grid);c1.className='coach-card';
      el('h4',t('1. Meaning & what I heard'),c1);
      el('p',heardText?`Transcript: “${heardText}”`:'Could not transcribe clearly — replay and check your microphone boost.',c1);
      el('p',aiFollowUp,c1);

      const c2=el('div','',grid);c2.className='coach-card';
      el('h4',t('2. Pronunciation & mouth guidance'),c2);
      const obs=tutorTurn?.observation||obsRes?.observation;
      el('p',obs?.message||'Speech check unavailable on this turn. Replay your audio and compare with the target sound.',c2);
      if(Number.isFinite(obs?.start)){
        const rep=el('button','Replay checked word',c2);rep.type='button';rep.className='secondary';
        rep.onclick=()=>{player.currentTime=obs.start;player.play().catch(()=>{});};
      }

      const c3=el('div','',grid);c3.className='coach-card';
      el('h4',t('3. Intonation, stress & rhythm'),c3);
      if(prosodyRes)el('p',prosodyRes.title+' · '+prosodyRes.detail,c3);
      else if(obs?.phrasing?.message)el('p',obs.phrasing.message,c3);
      else el('p','Replay your recording and check whether your main beat and pauses make the thought easy to follow.',c3);
      if(prosodyRes && obs?.phrasing?.message)el('p',obs.phrasing.message,c3);
      if(Number.isFinite(prosodyRes?.start)){
        const rep=el('button','Replay checked phrase',c3);rep.type='button';rep.className='secondary';
        rep.onclick=()=>{player.currentTime=prosodyRes.start;player.play().catch(()=>{});};
      }
    }
  }
  picker.onchange=()=>showScenario(Number(picker.value));
  showScenario(0);
}

function renderStudios(sub=activeStudio){
  activeStudio=sub;
  const tabs=['IPA & Mouth','Intonation','Talk with AI'];
  const bar=el('div','',root);bar.className='studio-tabs';bar.setAttribute('role','tablist');
  const tabBtns=[];
  for(const tab of tabs){
    const b=el('button',t(tab),bar);b.type='button';b.setAttribute('role','tab');
    b.id='tab-'+tab.toLowerCase().replace(/[^a-z]+/g,'-');
    b.setAttribute('aria-controls','studio-panel');
    b.setAttribute('aria-selected',String(tab===activeStudio));
    b.tabIndex=tab===activeStudio?0:-1;
    b.onclick=()=>run(()=>view('Studios',tab));
    b.onkeydown=e=>{
      if(e.key==='ArrowRight'||e.key==='ArrowLeft'){
        e.preventDefault();
        const nextIdx=(tabs.indexOf(tab)+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
        run(()=>view('Studios',tabs[nextIdx]));
      }
    };
    tabBtns.push(b);
  }
  const panel=el('div','',root);panel.id='studio-panel';panel.setAttribute('role','tabpanel');
  if(activeStudio==='IPA & Mouth')renderIpaMouthStudio();
  else if(activeStudio==='Intonation')renderIntonationStudio();
  else renderTalkWithAiStudio();
}

async function view(name, subTab){
  if(capture)throw Error('Stop your recording before leaving this exercise.');
  if(['IPA & Mouth','Intonation','Talk with AI'].includes(name)){subTab=name;name='Studios';}
  if(name==='Today'||name==='Progress')await refresh();clear();current=null;session=null;page=name;nav(name);
  history.replaceState(null,'',base);
  if(name==='Today'){
    title(t('Today'));
    const doneCount=state.completed.filter(k=>k!=='guide-start').length;
    const summaryRow=el('div','',root);summaryRow.className='today-summary';
    if(state.streak>0)el('span',lang==='vi'?`🔥 Chuỗi ${state.streak} ngày`:`🔥 ${state.streak}-day streak`,summaryRow).className='streak-pill';
    if(doneCount>0||state.due.length>0)el('span',lang==='vi'?`${doneCount} bài đã học · ${state.due.length} bài cần ôn`:`${doneCount} completed · ${state.due.length} reviews due`,summaryRow).className='meta';
    const newLearner=!Object.keys(state.doneItems).length;
    if(newLearner){
      el('p',t('Choose a starting point. You can open any lesson in the Library or jump straight into the 3 practice studios below.'));
      const a=el('div');a.className='actions';
      button(a,t('Find my starting point'),()=>openLesson('guide-start'),true);
      button(a,t('Start from the beginning'),()=>openLesson('ship-01'));
    }else{
      const next=catalog.lessons.find(l=>l.id===state.next);
      el('p',next.goal);startActions(root,state.next,state.phase);
      if(state.phase==='review')el('p',lang==='vi'?'Bài ôn tập hôm nay dùng ví dụ mới để kiểm tra khả năng ghi nhớ.':'Your next review uses a different example.');
    }
    for(const [key,skill] of [['p1','Listening'],['p2','IPA reading'],['p3','IPA writing'],['p4','Meaning']]){
      if(state.placement[key])el('p',skill+' · '+(state.recommendations[skill]?'Revisit '+catalog.lessons.find(l=>l.id===state.recommendations[skill]).title:'Continue on the guided path.'));
    }
    const pillars=el('div');pillars.className='pillar-grid';
    for(const [heading,desc,target] of [
      ['1. IPA & Mouth Movement','Underhill silent miming, 4 muscle buttons, and acoustic lip/tongue/jaw cues.','IPA & Mouth'],
      ['2. Intonation & Stress','Moving pitch line that lights up syllables (a-BOUT) and situational sentences live.','Intonation'],
      ['3. Talk with AI Coach','Speak in real situations and get pronunciation, intonation & meaning guidance.','Talk with AI'],
    ]){
      const card=el('section','',pillars);card.className='pillar-card';
      el('h3',t(heading),card);el('p',t(desc),card);button(card,(lang==='vi'?'Mở ':'Open ')+t(target),()=>view('Studios',target));
    }
  }else if(name==='Studios'){
    renderStudios(subTab||activeStudio);
  }else if(name==='Library'){
    title(t('Library'));const filters=el('div');filters.className='filters';const q=input(filters,t('Search lessons'),'search');
    const book=choices(filters,t('Book'),[['',lang==='vi'?'Tất cả sách':'All books'],...Object.entries(catalog.books)]);
    const skill=choices(filters,t('Skill'),[['',lang==='vi'?'Tất cả kỹ năng':'All skills'],...['IPA literacy','Listening and articulation','Intonation and fluency','Conversational intelligibility'].map(k=>[k,k])]);
    const symbol=choices(filters,t('IPA symbol'),[['',lang==='vi'?'Tất cả ký hiệu':'All symbols'],...catalog.symbols.filter(k=>k!==' ').map(k=>[k,k])]);
    const count=el('p');const list=el('ul');list.className='list';
    const doneSet=new Set(state?.completed||[]), dueSet=new Set(state?.due||[]);
    function filter(){list.replaceChildren();const found=catalog.lessons.filter(l=>(!book.value||l.book===book.value)&&(!skill.value||l.topics.includes(skill.value))&&(!symbol.value||l.symbols.includes(symbol.value))&&(l.id+' '+l.title+' '+l.goal).toLowerCase().includes(q.value.trim().toLowerCase()));
      count.textContent=found.length+(lang==='vi'?' bài học':' lessons');
      for(const l of found){const row=el('li','',list);button(row,l.title,()=>openLesson(l.id));
        if(dueSet.has(l.id))el('span',lang==='vi'?'Cần ôn':'Due',row).className='badge-due';
        else if(doneSet.has(l.id))el('span','✓',row).className='badge-done';
        el('small','  '+catalog.books[l.book]+' · '+l.source,row);}}
    [q,book,skill,symbol].forEach(n=>n.oninput=filter);filter();
  }else if(name==='My Words'){
    title(t('My Words'));const f=el('div');f.className='filters';const w=input(f,t('Word or expression')),s=input(f,t('Your situation (optional)'));
    button(f,t('Save word'),async()=>{await saveWord(w.value,s.value);await view('My Words');},true);
    const words=token?await request('/api/course/words'):wordBank(labPrompts).list();if(!words.length)el('p',lang==='vi'?'Lưu từ mới tại đây hoặc trong bài học để luyện nói theo tình huống của bạn.':'Save a word here or from a lesson to use it in your own reply.');
    const list=el('ul');list.className='list';for(const w of words){const row=el('li','',list);button(row,w.word,()=>personal(w));}
  }else{
    title(t('Progress'));
    if(state.streak>0)el('span',lang==='vi'?`🔥 Chuỗi ${state.streak} ngày luyện tập`:`🔥 ${state.streak}-day practice streak`,root).className='streak-pill';
    el('p',state.completed.filter(k=>k!=='guide-start').length+' lessons completed · '+state.due.length+' reviews due');
    for(const [skill,c] of Object.entries(state.skills)){
      const section=el('section');
      const labelMap={Listening:lang==='vi'?'Nghe phân biệt âm':'Listening',IPA:lang==='vi'?'Đọc & viết IPA':'IPA literacy',Speaking:lang==='vi'?'Luyện nói & ghi âm':'Speaking practice',Meaning:lang==='vi'?'Hiểu ngữ điệu & phản hồi tình huống':'Understanding tone & replies'};
      el('h2',labelMap[skill]||skill,section);
      el('p',skill==='Speaking'?((c.recorded||0)+' recorded attempts · '+(c.unavailable||0)+' microphone skips'):
        ((c.correct||0)+' correct responses · '+(c.retry||0)+' answers to revisit'),section);
    }
    el('h2',lang==='vi'?'Ôn tập cách quãng (1–7 ngày)':'Spaced review (1–7 days)');el('p',state.reviewed.length+' lessons revisited with fresh material.');
    el('p',(state.delayedFirstResponses.correct||0)+' correct first responses · '+(state.delayedFirstResponses.retry||0)+' first responses needing another try.');
    el('h2',lang==='vi'?'Kết quả giao tiếp thực tế':'Communication outcomes');el('p',(state.communication.correct||0)+' authored exchanges resolved · '+(state.communication.retry||0)+' replies needing repair. A listener can check spoken intelligibility separately.');
    el('p',(state.listeners?.listener_recovered||0)+' listener checks recovered the intended detail · '+(state.listeners?.listener_repair||0)+' needed clarification.');
    for(const [key,day] of Object.entries(state.reviewDates)){
      const row=el('p'), lessonTitle=catalog.lessons.find(l=>l.id===key).title;
      el('span',day+' · ',row);
      if(state.due.includes(key))button(row,'Review · '+lessonTitle,()=>openLesson(key,'review'));
      else el('span',lessonTitle+(lang==='vi'?' (chưa đến lịch ôn)':' (scheduled, not due yet)'),row);
    }
  }
}
async function saveWord(word,situation=''){
  word=word.trim();if(!word || word.length>100)throw Error('Enter a word or expression of up to 100 characters.');
  if(token)await request('/api/practice-words',{word,situation},'PUT');
  else if(!wordBank(labPrompts).add(word,'',situation).persistent)throw Error('This browser could not save the word.');
  msg('Saved to My Words.');
}
async function personal(w){
  const match=await request(base+'/word?word='+encodeURIComponent(w.word));
  clear();title(w.word);el('p',w.situation||'Use this expression in a reply to a friend.');
  if(match.available)button(root,'Practise graded transcription',()=>openLesson(match.lesson,match.phase,match.exercise));
  else el('p','A transcription key is pending for this expression. You can rehearse your own message.');
  button(root,'Hear the expression',async()=>{
    const a=new Audio(base+'/human-word?word='+encodeURIComponent(w.word)+'&accent=en-US');
    try{await a.play();}
    catch{
      if(!window.speechSynthesis)throw Error('Audio unavailable for this expression.');
      const u=new SpeechSynthesisUtterance(w.word);u.lang='en-US';speechSynthesis.speak(u);
    }
  });
  recorder({kind:'reply',focus:w.word,question:w.situation||'Use the word in your own message.'},()=>{if(!token)wordBank(labPrompts).recordReply(w.id);return view('My Words');},true);
}
async function openLesson(id,phase='practice',target){
  if(capture)throw Error('Stop the recording first.');
  const found=await request(base+'/lesson/'+encodeURIComponent(id)+'?phase='+phase);
  await refresh();current=found;session=null;
  completed=new Set(state.doneItems[id+'/'+phase[0]]||[]);
  let start=target?current.exercises.findIndex(e=>e.id===target):current.exercises.findIndex(e=>!completed.has(e.id));
  part=Math.max(0,start);nav('');history.replaceState(null,'',base+'?lesson='+encodeURIComponent(id)+(phase==='review'?'&phase=review':''));
  renderItem();
}
function next(){
  part++;
  if(part>=current.exercises.length)return finish();
  renderItem();
}
async function finish(){
  await refresh();clear();title(t(current.phase==='review'?'Review finished':'Practice finished'));
  if(state.streak>0)el('span',lang==='vi'?`🔥 Chuỗi ${state.streak} ngày luyện tập`:`🔥 ${state.streak}-day practice streak`,root).className='streak-pill';
  const due=state.reviewDates[current.id];if(due)el('p',(lang==='vi'?'Lịch ôn tập tiếp theo · ':'Next scheduled review · ')+due);
  for(const [skill,lid] of Object.entries(state.recommendations))el('p',skill+' · '+catalog.lessons.find(l=>l.id===lid).title);
  const actions=el('div','',root);actions.className='actions';
  if(state.next && state.next!==current.id)button(actions,t('Continue to next lesson'),()=>openLesson(state.next,state.phase),true);
  button(actions,t('Return to Today'),()=>view('Today'),!(state.next && state.next!==current.id));
}
function renderItem(){
  clear();attempt=null;const item=current.exercises[part];
  const meta=el('p',catalog.books[current.book]+' · '+current.source+' · '+current.phase+' · '+(part+1)+' of '+current.exercises.length);meta.className='meta';
  const bar=el('div','',root);bar.className='lesson-progress';
  const fill=el('div','',bar);fill.className='lesson-progress-fill';
  fill.style.width=Math.round(((part+1)/current.exercises.length)*100)+'%';
  const blind=item.kind==='choice' && (item.skill==='Listening'||item.question.startsWith('Which word fits'));
  title(blind?'Listening and reading check':current.title);if(!blind)el('p',current.goal);el('h2',item.question);
  if(item.context)el('p',item.context);
  if(item.audio)audio(root,item.audio,t(item.accent==='en-GB'||item.question.startsWith('British')?'British English reference':'General American reference'));
  if(item.kind==='choice'){const a=el('div');a.className='actions';for(const opt of item.options)button(a,opt,()=>submit(item,opt));}
  else if(item.kind==='ipa'){
    el('p',t('Tap the IPA phoneme tiles below (or type). Use ˈ before the main stressed syllable and ˌ for secondary stress.'));
    const box=input(root,t('Your IPA transcription'));box.className='ipa';box.spellcheck=false;box.autocomplete='off';
    renderGroupedIpaKeyboard(root, box);
    button(root,t('Check transcription'),()=>{if(!box.value.trim())throw Error('Enter a transcription first.');return submit(item,box.value);},true);
    box.onkeydown=e=>{if(e.key==='Enter'&&box.value.trim())run(()=>submit(item,box.value));};
  }else{
    if(item.kind==='record' && current.symbols?.length){
      renderInlineUnderhillLab(root, current.symbols[0]);
    }
    recorder(item,(outcome)=>submit(item,outcome));
  }
  if(item.kind!=='choice'){const word=item.word||item.focus||current.focus;const save=button(root,'Save “'+word+'” to My Words',()=>saveWord(word));save.classList.add('save');}
}
async function submit(item,answer){
  let owner='device';
  if(token){try{const raw=token.split('.')[1].replaceAll('-','+').replaceAll('_','/');owner=JSON.parse(atob(raw+'='.repeat((4-raw.length%4)%4))).sub||'device';}catch{owner='device';}}
  const pendingKey='wordspeak.course.pending.'+owner;
  const previous=JSON.parse(sessionStorage.getItem(pendingKey)||'null');
  if(previous && previous.version===current.version && previous.lesson===current.id && previous.exercise===item.id && previous.answer===answer)attempt=previous;
  else attempt={attempt_id:crypto.randomUUID(),version:current.version,lesson:current.id,exercise:item.id,answer};
  sessionStorage.setItem(pendingKey,JSON.stringify(attempt));
  const verdict=await request(token?'/api/course/attempts':base+'/grade',attempt);
  if(!token){const events=readEvents();if(!events.some(e=>e.attempt_id===verdict.attempt_id)){
    events.push({attempt_id:verdict.attempt_id,day:verdict.day,version:verdict.version,lesson_version:verdict.lesson_version,lesson:verdict.lesson,exercise:verdict.exercise,skill:verdict.skill,outcome:verdict.outcome,listener:verdict.listener});
    localStorage.setItem(store,JSON.stringify(events));}}
  attempt=null;sessionStorage.removeItem(pendingKey);root.querySelector('.feedback')?.remove();const out=el('section');out.className='feedback';out.setAttribute('role','status');
  const retry=verdict.outcome==='retry';
  el('h2',t(({correct:'Correct',retry:'Try again',recorded:'Speaking attempt saved',unavailable:'Microphone skip saved'})[verdict.outcome]),out);
  el('p',verdict.feedback,out);
  if(verdict.word && !root.querySelector('.save'))button(out,'Save “'+verdict.word+'” to My Words',()=>saveWord(verdict.word)).classList.add('save');
  if(verdict.diff){const line=el('p','',out);line.className='ipa';for(const d of verdict.diff){const p=el('span',d.kind==='equal'?d.target:(d.entered||'∅')+' → '+(d.target||'∅'),line);if(d.kind!=='equal')p.className='change';}
    el('p','Accepted IPA · '+verdict.reference.map(s=>'/'+s+'/').join(' or '),out);}
  if(retry&&verdict.kind==='choice')el('p','Check against the model answer · '+verdict.reference,out);
  if(retry&&verdict.contrast)for(const c of verdict.contrast)audio(out,c.audio,c.word);
  if(!retry){root.querySelectorAll('button,input').forEach(b=>{if(!b.classList.contains('save'))b.disabled=true;});button(out,t('Continue'),next,true);}
  out.scrollIntoView({block:'nearest'});
}
function recorder(item,save,personalWord=false,saveLabel='',container=root){
  const wrapper=el('section','',container),models=item.models||[];let selected=null,listener='';const recordedModels=new Set();
  if(models.length){
    if(!item.hideModelVisuals){
      el('h3','Reference readings & moving stress contour',wrapper);
      for(const model of models){
        const aEl=model.audio?audio(wrapper,model.audio,model.line+' · '+model.intention):null;
        const vis=renderIntonationVisual(wrapper,{...contourFromModel(model),label:model.intention,audioEl:aEl});
        cleanupFns.push(()=>vis.stop());
      }
    }
    if(models.length===2)el('p','Record both readings. Change one feature and compare the two takes.',wrapper);
    else if(models.length>2)el('p','Record and compare at least two readings. Change one feature between takes.',wrapper);
    selected=choices(wrapper,'Target for this take',models.map((m,i)=>[String(i),m.intention]));
  }
  const controls=el('div','',wrapper);controls.className='actions';const playback=el('div','',wrapper);
  recordButton=button(controls,t('Record a take'),async()=>{
    if(!capture){
      levels=null;
      try{capture=await startMic(data=>{levels=data;});}
      catch{throw Error('Microphone unavailable. Check browser permission or continue with the microphone skip.');}
      recordButton.textContent=t('Stop recording');msg('Recording…');timer=setTimeout(()=>{if(capture)run(()=>recordButtonAction());},45000);
    }else await recordButtonAction();
  },true);
  async function recordButtonAction(){
    clearTimeout(timer);const active=capture;capture=null;const blob=await active.stop();latest=blob;listener='';
    recordButton.textContent='Record another take';if(urls.length===2){URL.revokeObjectURL(urls.shift());playback.firstElementChild?.remove();}
    const wrap=el('section','',playback);const m=selected?models[Number(selected.value)]:null;
    if(selected)recordedModels.add(selected.value);
    el('strong',m?m.intention:'Your reply',wrap);const a=el('audio','',wrap);a.controls=true;a.src=URL.createObjectURL(blob);urls.push(a.src);
    msg('Checking the recording…');let goal={conversation:true,focus:item.focus};
    if(m?.assessment)goal=m.assessment;
    try{const result=await assessRecording({blob,levels,goal},AbortSignal.timeout(45000));
      el('p',result.title+' · '+result.detail,wrap);if(result.phrasing?.message)el('p',result.phrasing.message,wrap);
      if(Number.isFinite(result.start))button(wrap,'Replay checked passage',()=>{a.currentTime=result.start;return a.play();});
    }catch{el('p','Acoustic check unavailable. Replay and compare one feature with the model.',wrap);}
    msg('');if(selected && models.length>1)selected.value=String((Number(selected.value)+1)%models.length);
  }
  button(controls,saveLabel||(personalWord?'Finish personal practice':t('Save speaking attempt')),()=>{if(capture||!latest)throw Error('Record and stop a take first.');
    if(models.length===2 && recordedModels.size<2)throw Error('Choose the other target and record its reading before saving.');
    return save(listener?'recorded:'+listener:'recorded');});
  if(!personalWord)button(controls,t('Continue without microphone'),()=>{if(capture)throw Error('Stop recording first.');return save('unavailable');});
  if(item.kind==='reply'){
    el('p','On replay, can you recover the intended detail? Ask the AI coach below or ask a human listener.',wrapper);
    const aiOut=el('div','',wrapper);
    button(wrapper,t('Get AI pronunciation & meaning coaching'),async()=>{
      if(!latest||capture)throw Error('Finish recording a reply first.');
      aiOut.replaceChildren();msg('Analyzing your reply with the AI speech coach…');
      if(token){
        if(!session)session=(await request('/api/sessions',{topic:item.question.slice(0,120)})).id;
        const turn=await request('/api/sessions/'+session+'/spoken-turn?focus='+encodeURIComponent(item.focus),latest,'POST',{'Content-Type':'audio/wav'});
        el('p',turn.reply?'AI Coach · '+turn.reply:'AI reply unavailable; review the speech observation below.',aiOut);
        el('p',turn.observation.message,aiOut);
      }else{
        const form=new FormData();form.append('audio',latest,'reply.wav');form.append('focus',item.focus||'');
        const obs=await request('/tutor/observe',form,'POST');
        if(obs.text)el('p','Heard transcript: “'+obs.text+'”',aiOut);
        el('p','AI observation: '+obs.observation.message,aiOut);
        if(obs.observation?.phrasing?.message)el('p',obs.observation.phrasing.message,aiOut);
      }
      msg('');
    });
    if(!personalWord)button(wrapper,'Ask a listener',()=>{
      if(!latest||capture)throw Error('Finish recording your message first.');
      const dialog=el('dialog','',document.body);dialog.setAttribute('aria-label','Listener check');dialog.onclose=()=>dialog.remove();
      const modalBtn=(text,fn)=>{const b=el('button',text,dialog);b.type='button';b.onclick=fn;return b;};
      const render=()=>{dialog.replaceChildren();el('h2','What detail did you hear?',dialog);const a=el('audio','',dialog);a.controls=true;a.src=urls.at(-1);
        const heard=input(dialog,'Listener’s own words');const note=el('p','',dialog);note.setAttribute('role','status');
        modalBtn('Return to learner',()=>{
          if(!heard.value.trim()){note.textContent='Enter what you heard, or close the listener check.';heard.focus();return;}
          const response=heard.value;dialog.replaceChildren();el('h2','Compare with your intention',dialog);el('p',response,dialog);
          for(const [label,value] of [['They recovered the detail','listener_recovered'],['I need to clarify','listener_repair']])modalBtn(label,()=>{listener=value;dialog.close();msg('Listener check ready. Save this speaking attempt.');});
        });modalBtn('Close',()=>dialog.close());};render();dialog.showModal();
    });
  }
}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>run(()=>view(b.dataset.page)));
document.querySelector('#auth').onsubmit=e=>{e.preventDefault();const action=e.submitter?.value==='yes'?'register':'login';
  run(async()=>{if(capture)throw Error('Stop your recording first.');
    const f=e.target;const result=await request('/api/auth/'+action,{email:f.elements.email.value.trim(),password:f.elements.password.value});
    token=result.access_token;sessionStorage.setItem('wordspeak.course.token',token);f.reset();accountUI();await view('Today');});};
document.querySelector('#logout').onclick=()=>run(async()=>{if(capture)throw Error('Stop your recording first.');token='';sessionStorage.removeItem('wordspeak.course.token');accountUI();await view('Today');});
window.addEventListener('offline',()=>msg('Offline. You can replay loaded recordings. Reconnect to check or save an answer.'));
window.addEventListener('pagehide',()=>{if(capture)capture.stop().catch(()=>{});resetTakes();});
async function boot(){
  const [cat, cfg]=await Promise.all([request(base+'/catalog'),request('/demo/config').catch(()=>null)]);
  catalog=cat;demoConfig=cfg;labPrompts=cfg?.prompts||[];
  applyLangUI();accountUI();const query=new URLSearchParams(location.search);
  if(query.has('lesson'))await openLesson(query.get('lesson'),query.get('phase')==='review'?'review':'practice');else await view('Today');
}
run(async()=>{try{await boot();}catch(e){clear();title('Course unavailable');button(root,'Try again',boot);throw e;}});
