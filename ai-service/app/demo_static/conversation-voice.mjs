// Speak only through an installed US English voice so personal practice text stays on device.
export function conversationVoice({onState}) {
  const synth=window.speechSynthesis;
  let voice, active;
  function refresh(){
    voice=synth?.getVoices().find(item=>item.localService && item.lang.replace('_','-').toLowerCase()==='en-us');
    onState({available:Boolean(voice),speaking:Boolean(active)});
  }
  function stop(){
    if(!active)return;
    active=null;synth.cancel();refresh();
  }
  function play(text,slow){
    stop();refresh();
    if(!voice)return;
    const line=new SpeechSynthesisUtterance(text);
    line.voice=voice;line.lang=voice.lang;line.rate=slow ? .8 : 1;
    active=line;
    line.onend=()=>{if(active===line){active=null;onState({available:Boolean(voice),speaking:false,finished:true});}};
    line.onerror=()=>{if(active===line){active=null;onState({available:true,speaking:false,failed:true});}};
    onState({available:true,speaking:true});
    synth.speak(line);
  }
  refresh();
  synth?.addEventListener('voiceschanged',refresh);
  return {play,stop,dispose(){stop();synth?.removeEventListener('voiceschanged',refresh);}};
}
