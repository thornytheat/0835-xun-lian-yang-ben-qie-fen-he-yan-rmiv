import {request} from './client.js';
import {snapshot, history, rosterView} from './view.js';
import {visualize} from './plots.js';

const form = document.querySelector('#source');
const file = document.querySelector('#file');
const profile = document.querySelector('#profile');
const status = document.querySelector('#notice');
const detail = document.querySelector('#review');
const evidence = document.querySelector('#evidence');
const supplementForm = document.querySelector('#supplement-form');
const rosterPanel = document.querySelector('#roster');
const viewRosterButton = document.querySelector('#view-roster');
const caseInput = document.querySelector('#supplement-case');
const caseOptions = document.querySelector('#case-codes');
const stages = [...document.querySelectorAll('[data-stage]')];
let stage = 'balance';
let report, selected, batch, running = false;

function source() {
  const data = new FormData();
  if (file.files.length) data.append('file',file.files[0]);
  else data.append('sample',profile.value);
  return data;
}

function announce(text, failure = false) {
  status.textContent = text;
  status.dataset.failure = String(failure);
}

function draw() {
  if (!report) return;
  snapshot(report, selected, stage);
  visualize(report, selected);
  for (const button of stages) button.setAttribute('aria-pressed',String(button.dataset.stage===stage));
  document.querySelector('#panel-title').textContent = stages.find(button => button.dataset.stage===stage)?.textContent || '运行对账';
  detail.hidden = !batch;
  if (supplementForm) supplementForm.hidden = !batch;
  if (viewRosterButton) viewRosterButton.disabled = !batch;
  rosterView(rosterPanel, batch);
  if (batch) {
    document.querySelector('#run-status').textContent = `${batch.id.slice(0,10)} · ${batch.status} · r${batch.revision}`;
    detail.querySelector('[value="APPROVED"]').disabled = !report.balance.releasable || batch.status==='APPROVED';
    detail.querySelector('[value="HELD"]').disabled = batch.status==='APPROVED';
    evidence.href = `/api/runs/${batch.id}/evidence`;
  }
}

function show(payload, committed = false) {
  batch = committed ? payload : null;
  report = committed ? payload.report : payload;
  detail.elements.note.value = batch?.note || '';
  selected = report.cases?.[0]?.case;
  if (caseOptions) {
    caseOptions.replaceChildren(...(report.cases || []).map(item => {
      const option = document.createElement('option');
      option.value = item.case;
      return option;
    }));
  }
  if (caseInput && batch) caseInput.value = selected || '';
  draw();
}

async function refresh() {
  const data = await request('/api/runs');
  history(data.items, batch?.id);
}

async function perform(action) {
  if (running) return;
  running = true;
  document.body.setAttribute('aria-busy','true');
  announce('处理中…');
  try { await action(); }
  catch (error) { announce(error.message,true); }
  finally { running = false; document.body.removeAttribute('aria-busy'); }
}

function preview(next) {
  return perform(async () => {
    const payload = await request(`/api/stages/${next}`,{method:'POST',body:source()});
    stage = next;
    show(payload);
    announce('阶段预览已更新');
    await refresh();
  });
}

stages.forEach(button => button.addEventListener('click',()=>preview(button.dataset.stage)));
form.addEventListener('submit', event => {
  event.preventDefault();
  perform(async () => {
    const result = await request('/api/runs',{method:'POST',body:source()});
    stage = 'balance'; show(result,true);
    announce('批次已保存'); await refresh();
  });
});
const filename = document.querySelector('#file-name');
profile.addEventListener('change',()=>{file.value=''; filename.textContent=''; preview(stage);});
file.addEventListener('change',()=>{filename.textContent=file.files[0]?.name || ''; preview(stage);});
document.querySelector('#rows').addEventListener('click',event=>{
  const button = event.target.closest('[data-case]');
  if (button) { selected = button.dataset.case; draw(); if (caseInput && batch) caseInput.value=selected; document.querySelector(`[data-case="${CSS.escape(selected)}"]`).focus(); }
});
document.querySelector('#history').addEventListener('click',event=>{
  const button = event.target.closest('[data-run]');
  if (button) perform(async()=>{
    const result = await request(`/api/runs/${button.dataset.run}`);
    stage='balance'; show(result,true); announce('已载入历史批次'); await refresh();
  });
});
detail.addEventListener('submit',event=>{
  event.preventDefault();
  perform(async()=>{
    const payload={
      status:event.submitter.value,
      revision:batch.revision,
      note:detail.elements.note.value,
      roster_revision:batch.roster?.roster_revision,
      roster_hash:batch.roster?.hash,
    };
    let result;
    try {
      result=await request(`/api/runs/${batch.id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    } catch (error) {
      if (error.code === 'STALE_REVIEW' || error.codes?.includes('ROSTER_CHANGED')) {
        const latest = await request(`/api/runs/${batch.id}`);
        show(latest,true);
        await refresh();
        announce('可用名单已被补录更新，请按新名单复核',true);
        return;
      }
      throw error;
    }
    show(result,true); announce(result.status==='APPROVED'?'批次已签发':'批次已暂缓'); await refresh();
  });
});
if (supplementForm) supplementForm.addEventListener('submit',event=>{
  event.preventDefault();
  if (!batch) return;
  perform(async()=>{
    const payload={
      case:supplementForm.elements['case'].value.trim(),
      a:supplementForm.elements.a.value.trim(),
      b:supplementForm.elements.b.value.trim(),
      note:supplementForm.elements.note.value.trim(),
    };
    const result=await request(`/api/runs/${batch.id}/supplements`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),
    });
    stage='balance';
    show(result,true);
    selected=result.case || payload.case || selected;
    if (caseInput) caseInput.value=payload.case;
    draw();
    supplementForm.elements.a.value='';
    supplementForm.elements.b.value='';
    supplementForm.elements.note.value='';
    announce(result.changed ? '关系已入账，相连组已退出可用名单' : '关系已入账，可用名单未变');
    await refresh();
  });
});
if (viewRosterButton) viewRosterButton.addEventListener('click', () => {
  if (!batch) return;
  perform(async () => {
    const latest = await request(`/api/runs/${batch.id}`);
    show(latest, true);
    announce('可用名单已刷新');
  });
});
preview(stage);
