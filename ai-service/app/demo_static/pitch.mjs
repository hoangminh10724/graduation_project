// Framewise pitch estimate using a YIN-style normalized difference. Frames
// below the energy/periodicity gates have no estimate. No interpolation across gaps.
export function pitchFrames(samples,rate,{hopSec=.04,threshold=.16}={}){
  const width=Math.round(.032*rate),hop=Math.round(hopSec*rate);
  const maxLag=Math.ceil(rate/65)+1;
  const normalized=new Float64Array(maxLag+1), frames=[];
  for(let start=0;start+width+maxLag<=samples.length;start+=hop){
    let sum=0,squares=0,clipped=0;
    for(let i=start;i<start+width;i++){
      const v=samples[i];sum+=v;squares+=v*v;
      if(Math.abs(v)>=.99)clipped++;
    }
    const frame={time:(start+width/2)/rate,hz:null};frames.push(frame);
    if(squares/width-(sum/width)**2<.003**2 || clipped>width*.01)continue;
    let cumulative=0;
    normalized[0]=1;
    for(let lag=1;lag<=maxLag;lag++){
      let difference=0;
      for(let i=start;i<start+width;i++)difference+=(samples[i]-samples[i+lag])**2;
      cumulative+=difference;
      normalized[lag]=cumulative ? difference*lag/cumulative : 1;
      if(lag<3)continue;
      const a=normalized[lag-2],b=normalized[lag-1],c=normalized[lag];
      if(b>=threshold || b>a || b>=c)continue;
      const period=lag-1+.5*(a-c)/(a-2*b+c);
      const hz=rate/period;
      if(hz>=65 && hz<=600)frame.hz=hz;
      break;
    }
  }
  return frames;
}
