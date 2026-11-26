// Schematic lip artwork: spreading, rounding and opening are separate controls.
const ns='http://www.w3.org/2000/svg';
const svgNode=(name,attrs={})=>{const n=document.createElementNS(ns,name);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n;};
export function lipGeometry(pose,{closed=false,opening=pose.opening}={}){
  const spread=pose.lip_spread??.12,round=pose.lip_round??Number(pose.rounded);
  return {rx:(28+spread*16)*(1-round*.48),ry:closed?.7:pose.lip_teeth?2.5:5+opening*19+round*11};
}
export function lipAction(pose){
  if(pose.lip_closed)return 'closed';
  if((pose.lip_round??Number(pose.rounded))>.55)return 'round';
  if((pose.lip_spread??0)>.7)return 'spread';
  return 'relaxed';
}
export function addLipDrawing(parent,{cx=100,cy=104}={}){
  const outer=svgNode('path',{fill:'#dfaaa5',stroke:'#9d6260','stroke-width':2});
  const aperture=svgNode('ellipse',{class:'lip-aperture',cx,cy,fill:'#683e40',stroke:'#9d6260','stroke-width':1.5});
  const arrows=svgNode('path',{class:'lip-direction',fill:'none',stroke:'#a35c13','stroke-width':2.5,'stroke-linecap':'round','stroke-linejoin':'round'});
  const teeth=svgNode('rect',{class:'front-teeth',fill:'#fffdf8',stroke:'#a1a99d','stroke-width':1,rx:1});
  const tip=svgNode('ellipse',{class:'front-tongue-tip',fill:'#d99f98',stroke:'#ad6d68','stroke-width':1});
  parent.append(outer,aperture,teeth,tip,arrows);
  return (pose,{closed=pose.lip_closed||false,opening=pose.opening,intent=lipAction(pose),focused=false}={})=>{
    const {rx,ry}=lipGeometry(pose,{closed,opening});
    outer.setAttribute('d',`M${cx-rx-3} ${cy}Q${cx-rx*.5} ${cy-ry-8} ${cx-5} ${cy-ry-3}Q${cx} ${cy-ry-7} ${cx+5} ${cy-ry-3}Q${cx+rx*.5} ${cy-ry-8} ${cx+rx+3} ${cy}Q${cx+rx*.5} ${cy+ry+10} ${cx} ${cy+ry+9}Q${cx-rx*.5} ${cy+ry+10} ${cx-rx-3} ${cy}Z`);
    aperture.setAttribute('rx',String(rx));aperture.setAttribute('ry',String(ry));
    teeth.setAttribute('x',String(cx-rx*.58));teeth.setAttribute('y',String(cy-9));teeth.setAttribute('width',String(rx*1.16));teeth.setAttribute('height',pose.lip_teeth?'11':'7');
    teeth.setAttribute('visibility',pose.lip_teeth||pose.lip_tongue?'visible':'hidden');
    tip.setAttribute('cx',String(cx));tip.setAttribute('cy',String(cy+3));tip.setAttribute('rx','11');tip.setAttribute('ry','3.5');tip.setAttribute('visibility',pose.lip_tongue?'visible':'hidden');
    outer.setAttribute('stroke',focused?'#a35c13':'#9d6260');outer.setAttribute('stroke-width',focused?'3':'2');
    let d='';
    if(!closed && intent==='spread'){
      const left=cx-rx-9,right=cx+rx+9;
      d=`M${left} ${cy}h-22m6 -5l-6 5l6 5M${right} ${cy}h22m-6 -5l6 5l-6 5`;
    }else if(!closed && (intent==='round'||intent==='relax')){
      const left=cx-rx-12,right=cx+rx+12;
      d=`M${left-21} ${cy}h21m-6 -5l6 5l-6 5M${right+21} ${cy}h-21m6 -5l-6 5l6 5`;
    }
    arrows.setAttribute('d',d);parent.dataset.lipAction=closed?'closed':intent;
  };
}

export function renderLipReference(parent,pose,phone){
  const svg=svgNode('svg',{viewBox:'0 0 240 190',role:'img','aria-label':`Front lip reference for ${phone}: ${pose.lip_label}`});
  svg.classList.add('lip-reference');
  const face=svgNode('g');
  face.append(svgNode('path',{d:'M60 38Q46 83 60 132Q120 181 180 132Q194 83 180 38',fill:'#fffdf8',stroke:'#b1beac','stroke-width':2.5}),
    svgNode('circle',{cx:92,cy:48,r:2.5,fill:'#82927d'}),svgNode('circle',{cx:148,cy:48,r:2.5,fill:'#82927d'}),
    svgNode('path',{d:'M120 55L114 75H125',fill:'none',stroke:'#b1beac','stroke-width':2}));
  const mouth=svgNode('g');face.append(mouth);svg.append(face);
  addLipDrawing(mouth,{cx:120,cy:105})(pose);
  const label=svgNode('text',{x:120,y:182,'text-anchor':'middle',fill:'#5e704f','font-size':11,'font-family':'Segoe UI, sans-serif'});
  label.textContent=pose.lip_label;svg.append(label);parent.append(svg);
}
