(function(){
  'use strict';
  if(typeof REVIEW_MODE==='undefined'||!REVIEW_MODE)return;

  const FORM_TO_REPORT={
    form005:'first_person',
    cover:'cover_letter',
    summary:'supervisor_summary',
    investigation:'investigation',
    disciplinary:'disciplinary'
  };
  const REPORT_TYPES=new Set(Object.values(FORM_TO_REPORT));
  const state={
    classification:{},extraction:{},initialGaps:{},gapAnswers:{},
    generationResponse:{},reports:new Map(),reviewedFields:{},timings:{},
    classifyStarted:0,extractStarted:0,generateStarted:0,generationPending:false
  };

  function clone(value){
    try{return JSON.parse(JSON.stringify(value));}catch(_e){return {};}
  }
  function now(){return performance.now();}
  function elapsed(start){return start?Math.max(0,Math.round(now()-start)):0;}
  function reporterId(payload){
    const metadata=payload.form005||payload.metadata||{};
    return metadata.employee_number||metadata.officer_last||'primary';
  }
  function activeReport(){return FORM_TO_REPORT[typeof _activeForm==='string'?_activeForm:'form005'];}
  function editableNarrative(){
    if(_activeForm==='form005')return document.querySelector('#preview .ed[data-key="narrative"]');
    return document.querySelector('#preview .narrative');
  }
  function setStatus(message,kind){
    const el=document.getElementById('reviewStatus');
    if(!el)return;
    el.textContent=message;
    el.className='review-status'+(kind?' '+kind:'');
  }
  function setSubmitReady(){
    const button=document.getElementById('reviewSubmit');
    if(button)button.disabled=!ACTIVE_DEMO_SCENARIO||state.reports.size===0||state.generationPending;
  }

  function captureReviewedFields(){
    if(_activeForm!=='form005')return;
    document.querySelectorAll('#preview .ed[data-key]').forEach(function(el){
      let value=(el.innerText||'').trim();
      if(value==='—'||value==='N/A')value='';
      state.reviewedFields[el.dataset.key]=value;
    });
    const box005=document.getElementById('box005');
    const box409=document.getElementById('box409');
    if(box005)state.reviewedFields.box_005=box005.checked?'X':'';
    if(box409)state.reviewedFields.box_409=box409.checked?'X':'';
  }
  function captureActiveReport(){
    const type=activeReport();
    const el=editableNarrative();
    if(type&&el&&state.reports.has(type)){
      state.reports.get(type).edited_text=(el.innerText||'').trim();
    }
    captureReviewedFields();
  }
  function makeActiveReportEditable(){
    const type=activeReport();
    const record=state.reports.get(type);
    const el=editableNarrative();
    if(!record||!el)return;
    el.textContent=record.edited_text;
    el.contentEditable='true';
    el.classList.add('review-editable');
    el.dataset.reviewReportType=type;
    el.setAttribute('role','textbox');
    el.setAttribute('aria-multiline','true');
    el.setAttribute('aria-label','Editable '+type.replace(/_/g,' ')+' report');
    el.addEventListener('input',function(){
      record.edited_text=(el.innerText||'').trim();
      window.__reviewDirty=true;
    });
    captureReviewedFields();
  }

  function applyDemoGapAnswers(){
    const answers=(ACTIVE_DEMO_SCENARIO&&ACTIVE_DEMO_SCENARIO.review_answers)||{};
    Object.entries(answers).forEach(function(entry){
      const slot=entry[0],value=entry[1];
      let field=document.querySelector('#missingPanel [data-slot="'+CSS.escape(slot)+'"]');
      if(!field){
        field=document.createElement('input');
        field.type='hidden';
        field.dataset.slot=slot;
        document.getElementById('missingPanel').appendChild(field);
      }
      field.value=String(value);
      field.dispatchEvent(new Event('input',{bubbles:true}));
      field.dispatchEvent(new Event('change',{bubbles:true}));
      state.gapAnswers[slot]=value;
    });
    window.__reviewDirty=true;
    setStatus('Demo-only canister details applied. Continue when ready.','ok');
  }
  function addDemoGapButton(){
    const answers=(ACTIVE_DEMO_SCENARIO&&ACTIVE_DEMO_SCENARIO.review_answers)||{};
    const panel=document.getElementById('missingPanel');
    if(!panel||!Object.keys(answers).length||panel.querySelector('.demo-gap-btn'))return;
    const button=document.createElement('button');
    button.type='button';
    button.className='secondary demo-gap-btn';
    button.textContent='Apply demo-only canister details';
    button.addEventListener('click',applyDemoGapAnswers);
    panel.appendChild(button);
  }

  function collectGapAnswers(){
    const result=Object.assign({},state.gapAnswers);
    document.querySelectorAll('#missingPanel [data-slot]').forEach(function(el){
      const value=(el.value||'').trim();
      if(value)result[el.dataset.slot]=value;
    });
    return result;
  }
  function reportsPayload(){
    captureActiveReport();
    return Array.from(state.reports.values()).map(function(item){return clone(item);});
  }
  function submissionPayload(){
    return {
      scenario_id:ACTIVE_DEMO_SCENARIO&&ACTIVE_DEMO_SCENARIO.id,
      pipeline:{
        classification:clone(state.classification),
        extraction:clone(state.extraction),
        initial_gaps:clone(state.initialGaps),
        gap_answers:collectGapAnswers(),
        generation_response:clone(state.generationResponse)
      },
      reports:reportsPayload(),
      reviewed_fields:clone(state.reviewedFields),
      review:{
        score:Number(document.getElementById('reviewScore').value),
        comments:document.getElementById('reviewComments').value.trim()
      },
      step_timings_ms:clone(state.timings)
    };
  }

  async function submitReview(){
    const score=document.getElementById('reviewScore').value;
    if(!ACTIVE_DEMO_SCENARIO){setStatus('Choose a demo scenario first.','error');return;}
    if(!state.reports.size){setStatus('Generate the reports before submitting.','error');return;}
    if(!score){setStatus('Choose an overall quality score.','error');return;}
    const button=document.getElementById('reviewSubmit');
    button.disabled=true;
    setStatus('Saving the original and edited reports…','');
    try{
      const response=await fetch('/api/review-lab/submissions',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(submissionPayload())
      });
      const data=await response.json();
      if(!response.ok||data.error)throw new Error(data.error||'Review could not be saved.');
      window.__reviewDirty=false;
      setStatus('Saved privately as '+data.submission_id+'.','ok');
      await loadHistory();
    }catch(error){
      setStatus(error.message+' Your edits are still on this page.','error');
    }finally{setSubmitReady();}
  }

  function historyItem(record){
    const row=document.createElement('div');
    row.className='review-history-item';
    const link=document.createElement('a');
    link.href='/api/review-lab/submissions/'+encodeURIComponent(record.submission_id);
    link.textContent=record.scenario_label||record.scenario_id||'Review';
    const detail=document.createElement('span');
    const date=record.submitted_at?new Date(record.submitted_at).toLocaleString():'';
    detail.textContent='Score '+record.score+' · '+record.changed_count+'/'+record.report_count+' edited · '+date;
    row.append(link,detail);
    return row;
  }
  async function loadHistory(){
    const list=document.getElementById('reviewHistoryList');
    if(!list)return;
    try{
      const response=await fetch('/api/review-lab/submissions?limit=12');
      const data=await response.json();
      if(!response.ok||data.error)throw new Error(data.error||'History unavailable.');
      list.replaceChildren();
      if(!data.submissions.length){
        const empty=document.createElement('span');empty.className='review-status';empty.textContent='No reviews saved yet.';list.appendChild(empty);
      }else data.submissions.forEach(function(record){list.appendChild(historyItem(record));});
    }catch(error){
      list.replaceChildren();
      const message=document.createElement('span');message.className='review-status error';message.textContent=error.message;list.appendChild(message);
    }
  }

  document.getElementById('genBtn').addEventListener('click',function(){state.classifyStarted=now();});
  document.getElementById('confirmBtn').addEventListener('click',function(){state.extractStarted=now();});
  document.addEventListener('click',function(event){
    if(event.target&&event.target.id==='continueBtn')state.generateStarted=now();
  },true);
  document.getElementById('reviewSubmit').addEventListener('click',submitReview);

  window.addEventListener('report:classified',function(event){
    state.classification=clone(event.detail);
    state.timings.classification=elapsed(state.classifyStarted);
  });
  window.addEventListener('report:extracted',function(event){
    state.extraction=clone(event.detail);
    state.initialGaps={
      gaps:clone(event.detail.gaps||[]),
      blocking_remaining:clone(event.detail.blocking_remaining||[]),
      checklist:clone(event.detail.checklist||[])
    };
    state.timings.extraction=elapsed(state.extractStarted);
    addDemoGapButton();
  });
  window.addEventListener('report:generated',function(event){
    const payload=clone(event.detail);
    state.generationResponse=payload;
    state.generationPending=!!payload.disciplinary_deferred;
    state.timings.generation=elapsed(state.generateStarted);
    const id=reporterId(payload);
    Object.entries(payload.reports||{}).forEach(function(entry){
      const type=entry[0],text=entry[1];
      if(!REPORT_TYPES.has(type))return;
      if(!state.reports.has(type)){
        state.reports.set(type,{report_type:type,reporter_id:id,generated_text:text||'',edited_text:text||''});
      }
    });
    setSubmitReady();
  });
  window.addEventListener('report:before-form-switch',captureActiveReport);
  window.addEventListener('report:after-form-render',makeActiveReportEditable);
  window.addEventListener('report:cleared',function(){
    state.classification={};state.extraction={};state.initialGaps={};state.gapAnswers={};
    state.generationResponse={};state.reports.clear();state.reviewedFields={};state.timings={};state.generationPending=false;
    window.__reviewDirty=false;setSubmitReady();setStatus('','');
  });

  loadHistory();
  setSubmitReady();
})();
