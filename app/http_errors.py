from flask import jsonify

LABELS = {
    'FILE_TOO_LARGE':'文件超过 256 KiB', 'FILE_EMPTY':'文件没有内容', 'FILE_BLANK':'文件只有空白',
    'HEADER_ONLY':'文件只有标题行', 'HEADER_MISMATCH':'列名与字段字典不一致', 'ENCODING_INVALID':'请使用 UTF-8 CSV',
    'CSV_MALFORMED':'CSV 引号或行格式异常', 'ROW_LIMIT':'文件超过 2000 行', 'FILE_REQUIRED':'请选择 CSV 文件',
    'RUN_NOT_FOUND':'批次不存在', 'REVIEW_FIELDS':'请填写 3 至 200 字复核意见', 'STALE_REVIEW':'批次或可用名单已更新，请刷新',
    'ROSTER_CHANGED':'可用名单已更新，请按新名单复核', 'STALE_ROSTER':'可用名单版本已过期，请刷新',
    'LIST_CHANGED':'可用名单已变化，请刷新',
    'RUN_FINALIZED':'批次已签发', 'UNRESOLVED_ISSUES':'存在待处理差异', 'SAMPLE_UNKNOWN':'样例不存在', 'STAGE_UNKNOWN':'处理阶段不存在',
    'UNKNOWN_SAMPLE':'关系中包含未知样本，请核对样本编号', 'CASE_NOT_FOUND':'业务分组不存在',
    'UNKNOWN_CASE':'业务分组不存在', 'CASE_REQUIRED':'请指定业务分组', 'CASE_MISMATCH':'业务分组与关系不一致',
    'RELATION_FIELDS':'请提供两个有效样本编号', 'INVALID_RELATION':'补录关系格式不正确',
    'ROSTER_NOT_ISSUED':'该批次尚未签发名单', 'ROSTER_NOT_FOUND':'可用名单不存在',
}

CONFLICT = {'STALE_REVIEW', 'ROSTER_CHANGED', 'STALE_ROSTER', 'LIST_CHANGED',
            'RUN_FINALIZED', 'UNRESOLVED_ISSUES'}
NOT_FOUND = {'RUN_NOT_FOUND', 'SAMPLE_UNKNOWN', 'STAGE_UNKNOWN', 'CASE_NOT_FOUND',
             'UNKNOWN_CASE', 'ROSTER_NOT_ISSUED', 'ROSTER_NOT_FOUND'}


def response(error):
    code = error.code
    status = 404 if code in NOT_FOUND else 409 if code in CONFLICT else 413 if code=='FILE_TOO_LARGE' else 422
    body = {'code':code,'message':LABELS.get(code,code)}
    aliases = getattr(error, 'aliases', ())
    if aliases:
        body['aliases'] = list(aliases)
        body['codes'] = [code, *aliases]
    return jsonify(body),status
