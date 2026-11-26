// Original everyday exchanges, indexed by the practice prompt ID.
const exchanges = {
  seat: ["Is this seat free?", "You're on the bus. How would you ask to sit beside someone?"],
  sit: ["Let's sit outside.", "Where would you like to sit for lunch?"],
  bed: ["I went to bed late.", "Why are you so tired today?"],
  bad: ["The traffic was bad.", "How was the drive here?"],
  food: ["I brought some food.", "What did you bring to the picnic?"],
  foot: ["My foot hurts.", "Why did you stop walking?"],
  about: ["What about Saturday?", "I can't meet on Friday. What would work for you?"],
  cup: ["Just a cup of tea, please.", "What can I get you to drink?"],
  hot: ["It's still hot.", "Can I try the soup now?"],
  caught: ["I caught the last train.", "How did you get home?"],
  bird: ["There's a bird by the window.", "What are you looking at?"],
  teacher: ["My teacher lent it to me.", "Where did you get that book?"],
  day: ["Let's make a day of it.", "How long should we spend at the beach?"],
  my: ["That's my bag.", "Whose bag is on this chair?"],
  boy: ["The boy in blue found it.", "Who found your phone?"],
  go: ["Shall we go now?", "The movie starts soon. What should we do?"],
  now: ["I can talk now.", "When is a good time to call?"],
  pen: ["Can I borrow a pen?", "You need to sign a form. What do you ask?"],
  ben: ["Ben has the tickets.", "Who should we look for at the entrance?"],
  ten: ["Let's meet at ten.", "What time works for breakfast?"],
  den: ["It's in the den.", "Where did you leave the remote?"],
  key: ["I've lost my key.", "Why are you waiting outside?"],
  give: ["Could you give me a hand?", "This box is heavy. What do you ask your friend?"],
  fan: ["Could we turn on the fan?", "It's warm in here. What would help?"],
  van: ["We could take the van.", "How will we move all those boxes?"],
  thin: ["A thin slice, please.", "How would you like your bread cut?"],
  this: ["I'll take this one.", "Which jacket would you like?"],
  see: ["I can see the sign.", "Can you tell where the entrance is?"],
  zoo: ["Let's try the zoo.", "Where should we take the kids?"],
  she: ["She'll be here soon.", "Is your sister coming?"],
  vision: ["My vision is blurry.", "How does the new pair of glasses feel?"],
  hat: ["Is this your hat?", "You found something on the bench. What do you ask?"],
  chin: ["You've got sauce on your chin.", "What did I miss with my napkin?"],
  jam: ["I'd love some jam.", "What would you like on your toast?"],
  man: ["The man by the door helped me.", "Who gave you directions?"],
  no: ["No, thanks. I'm full.", "Would you like another slice?"],
  sing: ["Let's sing together.", "What should we do for her birthday?"],
  lip: ["I bit my lip.", "Why did you put down your sandwich?"],
  red: ["Mine's the red one.", "Which bike should I bring over?"],
  wet: ["My shoes are wet.", "Why do you want to change shoes?"],
  yes: ["Yes, that works for me.", "Can we meet a little later?"],
  near: ["I live near the station.", "Where should I pick you up?"],
  care: ["I can take care of dinner.", "How should we split the chores?"],
  car: ["I left it in the car.", "Where is your umbrella?"],
  four: ["A table for four, please.", "How many people are joining you for lunch?"],
  tour: ["When does the tour start?", "What would you like to ask the museum guide?"],
  fire: ["Let's sit by the fire.", "Where can we warm up?"],
  shows: ["I like cooking shows.", "What do you watch after work?"],
  two: ["Two tickets, please.", "What would you ask for at the cinema?"],
  put: ["Put it by the door.", "Where do you want this package?"],
  can: ["I can help after lunch.", "When could you help me move?"],
};

export function wordBank(prompts) {
  const key = 'wordspeak.conversation.words.v2';
  const catalog = new Map(prompts.map(prompt => [prompt.id, prompt]));
  const entries = new Map();
  const clean = value => typeof value === 'string' ? value.trim().replace(/\s+/g,' ').normalize('NFC') : '';
  const wordKey = word => clean(word).replaceAll('’', "'").toLowerCase();
  const idsByWord = new Map(prompts.map(prompt => [wordKey(prompt.word),prompt.id]));

  function put(word, phrase, situation) {
    word=clean(word);
    if (!word || word.length>100) throw new Error('Enter a word or expression of up to 100 characters.');
    phrase=clean(phrase);
    situation=clean(situation);
    if (phrase.length>500 || situation.length>500) throw new Error('Keep each practice line under 501 characters.');
    const id=idsByWord.get(wordKey(word)) || 'custom:'+wordKey(word);
    const previous=entries.get(id);
    entries.set(id,{id,word:catalog.get(id)?.word || word,phrase:phrase || previous?.phrase || '',
      situation:situation || previous?.situation || '',replyCount:previous?.replyCount || 0,
      lastReply:previous?.lastReply || 0});
    return id;
  }

  try {
    const current=localStorage.getItem(key);
    const saved=JSON.parse(current ?? localStorage.getItem('wordspeak.conversation.words.v1'));
    if (Array.isArray(saved)) {
      for (const item of saved) {
        if (typeof item==='string' && catalog.has(item)) put(catalog.get(item).word);
        else if (item && typeof item.word==='string' && clean(item.word) && clean(item.word).length<=100
          && clean(item.phrase).length<=500 && clean(item.situation).length<=500) {
          const entry=entries.get(put(item.word,item.phrase,item.situation));
          if(Number.isSafeInteger(item.replyCount) && item.replyCount>0 &&
             Number.isSafeInteger(item.lastReply) && item.lastReply>0){
            entry.replyCount=item.replyCount;entry.lastReply=item.lastReply;
          }
        }
      }
    }
  } catch { /* Practice also works with tab-only storage. */ }
  function persist() {
    try { localStorage.setItem(key, JSON.stringify([...entries.values()])); return true; }
    catch { return false; }
  }
  return {
    save(id) { if (!catalog.has(id)) return false; put(catalog.get(id).word); return persist(); },
    add(word, phrase, situation) {
      const id=put(word,phrase,situation);
      return {id,persistent:persist()};
    },
    recordReply(id) {
      const entry=entries.get(id);
      if(!entry)return false;
      entry.replyCount++;entry.lastReply=Date.now();return persist();
    },
    next(currentId='') {
      const others=[...entries.values()].filter(entry=>entry.id!==currentId);
      others.sort((a,b)=>a.lastReply-b.lastReply);
      return others[0]?.id;
    },
    remove(id) { entries.delete(id); return persist(); },
    list() { return [...entries.values()].map(entry=>({
      ...catalog.get(entry.id), ...entry, catalogWord:catalog.has(entry.id),
    })); },
  };
}

export function conversationLesson(prompt) {
  const defaults = exchanges[prompt.id];
  const example = prompt.phrase || defaults?.[0] || prompt.word;
  const question = prompt.situation || defaults?.[1] || 'Imagine a friend asks how your day went. What could you tell them using “' + prompt.word + '”?';
  return {
    id: 'conversation-' + prompt.id, title: 'In conversation · ' + prompt.word, conversation: true, practiceWord:prompt.word,
    cue: 'Choose one word to bring forward. Say the rest in comfortable groups.',
    selfCheck: 'Listen once for meaning. Could a listener tell what you meant on the first try? Where would a pause or a clearer beat help?',
    source: 'https://adrianunderhill.com/2015/11/30/three-levels-of-pronunciation-an-example-activity/',
    variants: [
      {id:'phrase', label:'Rehearse', meaning:example, detail:!defaults && !prompt.phrase ? 'Say the expression once, then make a sentence you could use with a friend.' : 'Say the line once. Then look away and try it in your own words.'},
      {id:'reply', label:'Reply', meaning:question, detail:'Answer in your own words using “' + prompt.word + '”.'},
      {id:'repair', label:'Clarify', meaning:'“Sorry, could you say that another way?”', detail:'Explain your answer again. Add one detail or change which word carries the main beat.'},
    ],
  };
}
