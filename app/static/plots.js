import {element} from './client.js';

function block(target,className,content) {
  const node=element('div',content,{class:className});
  target.append(node);
  return node;
}

export function visualize(report,selected) {
  const target=document.querySelector('#visual');
  target.replaceChildren();
  const measurement=report.cases?.find(row=>row.case===selected)?.measure;
  if (!measurement) {block(target,'chart-note','选择有计算值的分组');return;}
  const e=measurement.evidence;

  for(const [title,values] of [['训练',e.train],['评估',e.evaluation],['隔离',e.quarantined]]) {
    const group=block(target,'split-group'); block(group,'split-label',`${title} · ${values.length}`);
    for(const id of values) block(group,'split-id',`#${id}`);
  }
}
