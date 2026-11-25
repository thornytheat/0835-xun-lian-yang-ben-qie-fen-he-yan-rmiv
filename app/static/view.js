import {element} from './client.js';

const labels = {READY:'通过', MISMATCH:'数值不符', PENDING:'待复核', APPROVED:'已签发', HELD:'已暂缓',
  INVALID_EQUIVALENCE:'互认条件无效', CREDIT_SHORTFALL:'学分不足', TICKET_MISMATCH:'联单信息不符',
  CONTAMINATION_LIMIT:'杂质率超限', DATA_POSITION_CONFLICT:'数据位置冲突', DANGLING_POSITION:'悬空位置删除',
  LINEAGE_CYCLE:'字段依赖成环', LABEL_TOO_LOW:'分级低于来源', DEPENDENCY_CYCLE:'任务依赖成环',
  NO_FEASIBLE_SLOT:'无可用时隙', PICKUP_BEFORE_ENTRY:'领取早于入柜', DWELL_RATE_MISMATCH:'滞留率不符',
  HORIZON_UNOBSERVED:'超出观察范围', CELL_CONFLICT:'单元格重复', MARGINAL_INFERENCE:'可经边际反推',
  FIELD_REGISTRY_CONFLICT:'字段登记冲突', BREAKING_SCHEMA:'存在不兼容变更', SLOT_COLLISION:'号源登记冲突',
  STALE_CANCELLATION:'取消记录失效', STOP_ORDER_CONFLICT:'站序冲突', MISSING_STOPS:'到站序列缺站',
  SAMPLE_PAIR_MISSING:'平行样不完整', METHOD_MISMATCH:'检测方法不一致', QUALITY_LIMIT:'质控限值超出',
  UNKNOWN_AUTHOR:'未知作者', ENTITY_COUNT_MISMATCH:'归并组数不符', DUPLICATE_DAY:'日期重复',
  INVALID_SCENARIO:'补货参数无效', SERVICE_TARGET_MISSED:'服务目标未达', INVALID_SAMPLING_PLAN:'抽样计划无效',
  LOT_REJECTED:'样品拒收', PRODUCER_RISK_LIMIT:'生产方风险超限', CONSUMER_RISK_LIMIT:'使用方风险超限',
  CROSS_CUTOFF_LEAKAGE:'跨截止日泄漏', UNKNOWN_SAMPLE:'未知样本', INVALID_TASK_WINDOW:'任务时间窗无效',
  INVALID_PLAN:'排程参数无效', UNKNOWN_TASK:'未知任务', INVALID_RESERVATION:'停用区间无效',
  UNKNOWN_COURSE:'未知课程', COURSE_REGISTER_CONFLICT:'课程登记冲突', COURSE_LIMIT:'课程数量超限',
  DUPLICATE_WEIGHING:'重复过磅记录', WEIGHING_MISSING:'过磅记录缺失', TARE_OUT_OF_RANGE:'皮重时间超出范围',
  INVALID_LAB_READING:'化验读数无效', MOISTURE_MISSING:'缺少含水率', INVALID_FIELD:'字段定义无效',
  UNKNOWN_FIELD:'未知字段', INVALID_APPROVAL:'审批区间无效', APPROVAL_OVERLAP:'审批区间重叠',
  INVALID_TABLE:'公开表结构无效', INVALID_PING:'定位点无效', INVALID_DISPATCH:'班次要求无效',
  INVALID_SAMPLE:'样本登记无效', INVALID_REGISTER:'作者登记无效', INVALID_SIMILARITY:'相似度无效',
  AUTHORITY_EXCLUSION_CONFLICT:'权威编号与禁用关系冲突', HISTORY_LIMIT:'历史窗口过长',
  DAY_OUT_OF_RANGE:'观测日超出范围', INVALID_COHORT:'入柜队列无效', PICKUP_CONFLICT:'领取记录冲突',
  INVALID_OBSERVATION:'抽检记录无效', INVALID_SAMPLE_REGISTRY:'样本记录无效'};

const valueLabels = {RPD:'相对偏差', ABSOLUTE:'绝对差', BOTH_ND:'双方未检出', MIXED_LOD:'一侧低于检出限',
  EQUALITY:'等值删除', POSITION:'位置删除', PRIMARY:'初次遮蔽', SECONDARY:'追加遮蔽',
  WIDEN_INTEGER:'整数位加宽', WIDEN_SCALE:'小数位加宽', DEFAULT:'默认值补齐', IMPLICIT_NULL:'隐式空值',
  EXACT:'完全一致', TYPE_CHANGED:'类型变化', DECIMAL_SCALE_NARROWED:'小数位收窄', NULLABILITY_NARROWED:'可空性收窄',
  MISSING_REQUIRED:'缺少必填字段', AUTHORITY_CONFLICT:'权威编号冲突', CANNOT_LINK:'禁止合并',
  UPSTREAM_UNSCHEDULED:'上游未排程', NO_FEASIBLE_SLOT:'无可用时隙', LEGAL_HOLD:'合法保全',
  RECLAIM:'可回收', LIVE_SNAPSHOT:'活动快照', TRANSPORT:'运输中', DELIVERED:'已签收', CANCELLED:'已取消'};
const headers = ['业务分组', '输入行', '计算值', '参考值', '判定'];

export function badge(status) {
  return element('span', labels[status] || status, {class:'badge', 'data-result':status, title: status});
}

const fieldLabels = {matched:'匹配关系', unmet:'未覆盖', loads:'磅单明细', over_limit:'超限联单',
  visible:'可见记录', removed:'删除记录', dangling:'悬空删除', grades:'传播级别', approved:'已批准降级',
  expired:'已过期审批', schedule:'排程', rejected:'未排入', curve:'剩余比例', horizon:'观察时点',
  suppressed:'遮蔽单元格', exposed:'可反推', compatible:'通过字段', violations:'差异字段',
  occupied:'占用号源', promoted:'候补转入', invalid_cancels:'无效取消', route:'到站路径',
  pings:'采信定位', missing:'缺站', pairs:'样本对', failed:'未通过', clusters:'归并分组',
  blocked:'阻止合并', forecast:'预测需求', reorder:'补货点', unserved:'未满足', requested:'总需求',
  orders:'到货安排', closing:'期末库存', producer_reject_bp:'生产方拒收基点数', consumer_accept_bp:'使用方接收基点数',
  acceptance_number:'接收数上限', observed_defects:'实测缺陷', observed_passed:'样品判定',
  producer_risk_passed:'生产方风险', train:'训练集', evaluation:'评估集', quarantined:'隔离集',
  groups:'归并组', primary:'初次遮蔽', secondary:'追加遮蔽', net_g:'净重克', dry_g:'干重克',
  payable_g:'结算克', reject_bp:'杂质基点', selected:'已选触点', channel:'归因渠道', elapsed_min:'距触点分钟',
  origins_g:'来源克数', overdrawn:'超投批次', unbalanced:'投料不平衡', segments:'客群金额', gaps:'缺失关联',
  stockout_min:'缺货分钟', selling_min:'可售分钟', confidence:'置信度', peak_start_min:'峰窗起点',
  windows:'窗口需量', debit:'借方', credit:'贷方', resident:'本币金额', price:'汇率', matched_cents:'匹配分',
  matched_g:'匹配克数', pending:'待匹配', remaining:'剩余余额', live:'可见顺序', tombstones:'墓碑序列',
  accounted:'已记账行', balanced:'总数平衡', input:'输入行', accepted:'采信行', isolated:'隔离行', mode:'判定方式', pass:'结论', value:'测量值', age:'龄期', picked:'领取数', censored:'删失数', risk:'在险数', remaining_bp:'剩余基点', external:'外校课程', local:'校内课程', field:'字段', ticket:'磅单', net:'净重', revenue:'收入', segment:'客群', channel:'渠道', chosen_touch:'命中触点', elapsed_min:'经过分钟', old_cents:'旧金额', new_cents:'新金额', expansion_cents:'扩张金额', contraction_cents:'收缩金额', churn_cents:'流失金额', due_cents:'应付金额', paid_cents:'已付金额', gap_cents:'差额', warnings:'提示', records:'记录数'};

function detailValue(value) {
  if (Array.isArray(value) && value.every(item => item === null || typeof item !== 'object')) {
    return document.createTextNode(value.length ? value.join('、') : '—');
  }
  if (value === null || typeof value !== 'object') {
    return document.createTextNode(value === null ? '—' : value === true ? '是' : value === false ? '否' : (valueLabels[value] || String(value)));
  }
  const list = element('dl');
  for (const [key, item] of Object.entries(value)) {
    const entry = element('dd');
    entry.append(detailValue(item));
    list.append(element('dt', Array.isArray(value) ? `记录 ${Number(key)+1}` : (fieldLabels[key] || key)), entry);
  }
  return list.children.length ? list : document.createTextNode('—');
}

export function snapshot(report, selected, stage) {
  const stats = report.intake;
  document.querySelector('[data-metric="input"]').textContent = stats.input;
  document.querySelector('[data-metric="accepted"]').textContent = stats.accepted;
  document.querySelector('[data-metric="isolated"]').textContent = stats.rejected;
  document.querySelector('[data-metric="cases"]').textContent = report.cases?.length ?? '—';
  const table = document.querySelector('#rows');
  table.replaceChildren();
  const head = element('tr');
  const body = table.createTBody();
  if (stage === 'intake') {
    head.append(...['源行', '记录键', '业务分组', '原因码'].map(title => element('th', title, {scope:'col'})));
    for (const item of stats.isolation) {
      const tr = body.insertRow();
      tr.append(...[item.line,item.record,item.case,item.reason].map(value=>element('td',value)));
    }
    if (!stats.isolation.length) body.insertRow().insertCell().textContent = '当前文件没有隔离行';
  } else {
    head.append(...headers.map(title => element('th', title, {scope:'col'})));
    for (const row of report.cases || []) {
      const tr = body.insertRow();
      const button = element('button',row.case,{type:'button','data-case':row.case,'aria-pressed':String(row.case===selected)});
      tr.insertCell().append(button);
      [row.records.length, row.measure ? `${row.measure.value} ${row.measure.unit}` : '—', row.measure ? `${row.measure.expected} ${row.measure.unit}` : '—'].forEach(value=>tr.insertCell().textContent=value);
      tr.insertCell().append(badge(row.status));
    }
  }
  table.createTHead().append(head);
  const picked = report.cases?.find(row=>row.case===selected);
  document.querySelector('#detail-title').textContent = picked ? `分组 ${picked.case}` : '采信摘要';
  const shown = picked ? picked.measure?.evidence ?? picked.prep?.details ?? {原因:picked.status} : stats.reasons;
  document.querySelector('#detail').replaceChildren(detailValue(shown));
  document.querySelector('#counts').textContent = report.balance ? `行数 ${report.balance.accounted}/${report.balance.input} · ${report.balance.ready} 组通过` : `采信 ${stats.accepted} 行 · 隔离 ${stats.rejected} 行`;
}

export function history(items, active) {
  const target = document.querySelector('#history');
  target.replaceChildren();
  for (const run of items) {
    const button = element('button', run.id.slice(0,10), {'data-run':run.id,'aria-pressed':String(run.id===active),type:'button'});
    const item = element('li');
    item.append(button, badge(run.status));
    target.append(item);
  }
  if (!items.length) target.append(element('li','尚无执行批次'));
}
