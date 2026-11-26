import {decodeAudio} from './audio.mjs?v=mic-playback-3';

async function estimate(blob){
  const audio=await decodeAudio(blob);
  const samples=audio.getChannelData(0).slice();
  const frames=await new Promise((resolve,reject)=>{
    const worker=new Worker(new URL('./pitch-worker.mjs',import.meta.url),{type:'module'});
    worker.onmessage=event=>{worker.terminate();resolve(event.data);};
    worker.onerror=()=>{worker.terminate();reject(new Error('Pitch estimation unavailable.'));};
    worker.postMessage({samples,rate:audio.sampleRate},[samples.buffer]);
  });
  return {frames,duration:audio.duration};
}

export function addPitchReview(slot,item){
  const box=document.createElement('details'),title=document.createElement('summary');
  title.textContent='Explore pitch in this recording';
  const note=document.createElement('p');note.setAttribute('role','status');
  box.append(title,note);slot.append(box);
  box.addEventListener('toggle',async()=>{
    if(!box.open || box.dataset.started)return;
    box.dataset.started='true';note.textContent='Estimating pitch on this device…';
    try{
      item.pitch ??= estimate(item.blob);
      const {frames,duration}=await item.pitch;
      if(!box.isConnected)return;
      const voiced=frames.filter(f=>f.hz!==null);
      if(voiced.length<3){note.textContent='Too few stable pitch estimates. Use playback to listen for the voice movement.';return;}
      const graph=document.createElementNS('http://www.w3.org/2000/svg','svg');
      graph.setAttribute('viewBox','0 0 420 110');graph.setAttribute('role','img');
      graph.setAttribute('aria-label','Estimated pitch over '+duration.toFixed(1)+' seconds. Time moves left to right and higher dots indicate higher pitch.');
      graph.style.width='100%';
      for(const frame of voiced){
        const dot=document.createElementNS(graph.namespaceURI,'circle');
        dot.setAttribute('cx',3+414*frame.time/duration);
        dot.setAttribute('cy',105-100*Math.log(frame.hz/65)/Math.log(600/65));
        dot.setAttribute('r','2');dot.setAttribute('fill','currentColor');graph.append(dot);
      }
      const measured=voiced.map(f=>f.hz);
      note.textContent='Estimated pitch '+Math.round(Math.min(...measured))+'–'+Math.round(Math.max(...measured))+' Hz. Follow time from left to right. Higher dots show higher pitch; gaps have no estimate. Listen back for the movement you intended.';
      box.append(graph);
    }catch{item.pitch=null;delete box.dataset.started;note.textContent='Pitch view unavailable. The recording is ready for playback.';}
  });
}
