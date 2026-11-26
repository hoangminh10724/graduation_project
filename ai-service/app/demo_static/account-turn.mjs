// The receiving backend can finish Talk with assessment_unavailable after
// already emitting a usable transcript. Keep that transcript for playback.
export function transcribeAccountTurn(blob,token,signal){
  return new Promise((resolve,reject)=>{
    if(signal.aborted || !token){reject(new Error('This review session has ended.'));return;}
    const url=new URL('/api/ws/audio',location.href);
    url.protocol=url.protocol==='https:'?'wss:':'ws:';
    const ws=new WebSocket(url);
    let transcript,finished=false;
    const timer=setTimeout(()=>finish('Transcription timed out.'),45000);
    function finish(message){
      if(finished)return;
      finished=true;clearTimeout(timer);signal.removeEventListener('abort',cancel);ws.close();
      if(transcript && !signal.aborted)resolve(transcript);
      else reject(new Error(message || 'No transcript was returned. You can still listen back.'));
    }
    function cancel(){finish('This review session has ended.');}
    signal.addEventListener('abort',cancel,{once:true});
    ws.onopen=()=>{
      ws.send(blob);
      ws.send(JSON.stringify({type:'end',token,media_type:'audio/wav'}));
    };
    ws.onmessage=event=>{
      let message;
      try{message=JSON.parse(event.data);}catch{finish('Unexpected speech response.');return;}
      if(message.type==='transcript' && typeof message.text==='string' && message.text.trim())transcript=message;
      if(message.type==='final' || message.type==='error')finish(message.code==='unauthorized'?'Sign in again to transcribe this turn.':undefined);
    };
    ws.onerror=()=>finish('Speech service unavailable. You can still listen back.');
    ws.onclose=()=>finish();
  });
}
