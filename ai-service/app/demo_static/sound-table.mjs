// Broad General American practice examples. Each inner sequence is one possible reading.
const examples = {
  seat:'s i t', sit:'s ɪ t', bed:'b ɛ d', bad:'b æ d', food:'f u d', foot:'f ʊ t',
  about:'ə b aʊ t', cup:'k ʌ p', hot:'h ɑ t', caught:'k ɔ t|k ɑ t', bird:'b ɝ d',
  teacher:'t i tʃ ɚ', day:'d eɪ', my:'m aɪ', boy:'b ɔɪ', go:'ɡ oʊ', now:'n aʊ',
  pen:'p ɛ n', ben:'b ɛ n', ten:'t ɛ n', den:'d ɛ n', key:'k i', give:'ɡ ɪ v',
  fan:'f æ n', van:'v æ n', thin:'θ ɪ n', this:'ð ɪ s', see:'s i', zoo:'z u',
  she:'ʃ i', vision:'v ɪ ʒ ə n', hat:'h æ t', chin:'tʃ ɪ n', jam:'dʒ æ m',
  man:'m æ n', no:'n oʊ', sing:'s ɪ ŋ', lip:'l ɪ p', red:'ɹ ɛ d', wet:'w ɛ t',
  yes:'j ɛ s', near:'n ɪ ɹ', care:'k ɛ ɹ', car:'k ɑ ɹ', four:'f ɔ ɹ',
  tour:'t ʊ ɹ|t ɔ ɹ', fire:'f aɪ ɹ', shows:'ʃ oʊ z', two:'t u', put:'p ʊ t', can:'k æ n|k ə n',
};

const phrases = {
  'Take a seat.':'t eɪ k ə s i t',
  'I can go.':'aɪ k ə n ɡ oʊ|aɪ k æ n ɡ oʊ',
  'See you soon.':'s i j u s u n|s i j ə s u n',
};

const groups = [
  ['Steady vowels','Move from front to central to back across each row. Open the jaw as you move down.',
    [['i','','u'],['ɪ','','ʊ'],['ɛ','ə','ɔ'],['æ','ʌ','ɑ']]],
  ['R-colored vowels','Compare the stressed vowel in bird with the unstressed ending of teacher.',[['ɝ','ɚ']]],
  ['Moving vowels','Feel the tongue or lips change position within one syllable.',[['eɪ','aɪ','ɔɪ','oʊ','aʊ']]],
  ['Stops','Release a closure. Compare the voice in each vertical pair.',[['p','t','k'],['b','d','ɡ']]],
  ['Fricatives','Keep air flowing through a narrow opening. Compare the voice in each vertical pair.',
    [['f','θ','s','ʃ','h'],['v','ð','z','ʒ','']]],
  ['Affricates','Start with a closure and release into friction.',[['tʃ','dʒ']]],
  ['Nasals','Feel the air pass through the nose. Move the closure from lips toward the back.',[['m','n','ŋ']]],
  ['Approximants','Explore tongue and lip shapes while the air continues to flow.',[['l','ɹ','w','j']]],
];

function element(tag,text) {
  const node=document.createElement(tag);
  if(text)node.textContent=text;
  return node;
}

export function renderSoundTable(container,prompt){
  const sequence=examples[prompt.id];
  container.hidden=!sequence;
  if(!sequence)return;
  const title=element('summary','Tap the sounds');
  const instructions=element('p','Say the word silently. Tap its sounds in order, then blend them into one movement and say it aloud.');
  const label=element('label','Word or phrase');
  const select=element('select');label.append(select);
  const items=[[prompt.word,sequence],...Object.entries(phrases)];
  for(const [name] of items)select.append(element('option',name));
  const taps=element('output');taps.setAttribute('aria-label','Sounds you tapped');taps.setAttribute('aria-live','polite');
  const feedback=element('p');feedback.setAttribute('role','status');
  const buttons=element('div');buttons.className='chart-actions';
  const undo=element('button','Undo'), check=element('button','Compare'), reveal=element('button','Show example');
  buttons.append(undo,check,reveal);
  const grid=element('div');grid.className='articulation-table';
  let selected=[];
  function display() {
    taps.textContent=selected.length?selected.map(sound=>'/'+sound+'/').join(' → '):'Tap your first sound.';
    check.disabled=undo.disabled=!selected.length;
    feedback.textContent='';
  }
  select.addEventListener('change',()=>{selected=[];display();});
  for(const [heading,cue,rows] of groups){
    const section=element('section');section.append(element('h3',heading),element('p',cue));
    const keys=element('div');keys.className='articulation-keys';keys.style.gridTemplateColumns='repeat('+rows[0].length+',minmax(0,1fr))';
    for(const sound of rows.flat()){
      if(!sound){keys.append(element('span'));continue;}
      const key=element('button','/'+sound+'/');key.className='secondary';key.dataset.chartSound=sound;
      key.addEventListener('click',()=>{selected.push(sound);display();});
      keys.append(key);
    }
    section.append(keys);grid.append(section);
  }
  undo.addEventListener('click',()=>{selected.pop();display();});
  function readings(){return items[select.selectedIndex][1].split('|');}
  check.addEventListener('click',()=>{
    feedback.textContent=readings().includes(selected.join(' '))?'You built a reference reading. Say it smoothly, then use it in a reply.':'Your sequence differs from the examples. Compare the movements or try another reading.';
  });
  reveal.addEventListener('click',()=>{
    feedback.textContent='Example readings for '+select.value+' — '+readings().map(r=>'/'+r+'/').join(' or ')+'.';
  });
  container.replaceChildren(title,instructions,label,taps,buttons,feedback,grid);display();
}
