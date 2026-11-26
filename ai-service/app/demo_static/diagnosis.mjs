// Keep recording-specific feedback visible; advanced feature tables stay optional.
export function diagnosisPresentation(result) {
  if (result?.diagnosis) return result.diagnosis;
  if (!result) return null;
  const feedback=result.articulation_feedback;
  const candidate=result.predicted_phone;
  return {kind:result.status==='uncertain'?'tentative_comparison':'comparison',
    heard:candidate?`${result.status==='model_match'?'Model candidate':'Possible'} /${candidate}/`:result.message,
    target:`/${result.target_phone}/`,comparison:result.message,
    adjustment:feedback?.differences[0]?.adjustment || 'Listen back, then try one complete word.',
    note:'Sound-category reference, not a measurement of your mouth.',alternatives:[]};
}

export function renderDiagnosis(container, result) {
  const data=diagnosisPresentation(result);
  container.replaceChildren();container.hidden=!data;
  if (!data) return;
  container.dataset.kind=data.kind;
  const element=(name,className,text)=>{
    const node=document.createElement(name);if(className)node.className=className;
    node.textContent=text;return node;
  };
  container.append(element('h2',null,'Your recording → target'));
  const rows=document.createElement('dl');rows.className='diagnosis-rows';
  const row=(name,text,className)=>{
    rows.append(element('dt',null,name),element('dd',className,text));
  };
  row('Model estimate',data.heard,'heard-sound');
  row('Target',data.target,'target-sound');
  if (data.comparison) row('Comparison',data.comparison,'heard-difference');
  if (data.adjustment) row('Try this',data.adjustment,'heard-adjustment');
  container.append(rows);
  if (data.alternatives?.length) {
    const more=element('details','diagnosis-alternatives','');
    more.append(element('summary',null,'Other decoded vowel candidates'));
    for (const other of data.alternatives) {
      more.append(element('p',null,`${other.heard}. ${other.adjustment}`));
    }
    container.append(more);
  }
  container.append(element('p','muted diagnosis-note',data.note));
}
