# 阶段接口

`POST /api/stages/<stage>` 接收 `multipart/form-data`。字段 `sample=dirty`、`sample=clean` 或 `file=<CSV>` 三选一。阶段为 `intake`、`prepare`、`calculate`、`policy`、`balance`。预览不入库。

`POST /api/runs` 接收同样的输入，执行全批并返回运行报告。`GET /api/runs` 返回最近 50 批。`GET /api/runs/<id>` 查询一批和当前复核状态。

`PATCH /api/runs/<id>` 接收 `revision`、`status` 和 `note`。状态使用 `APPROVED` 或 `HELD`。冲突返回 409，客户端读取新版本后重试。

`GET /api/runs/<id>/evidence` 下载内含运行清单、行号隔离、业务证据和复核信息的 JSON。

## 晚到关系补录与可用名单

`POST /api/runs/<id>/supplements`（同义路径 `/relations`、`/links`、`/supplement`）补录同一批次的近重复关系。JSON 支持单条：

```json
{"case":"0001","a":2,"b":3}
```

也支持 `{"relations":[{"case":"0001","a":2,"b":3}]}`。`a/b` 可传样本编号或来源记录键；只有一个业务分组时可省略 `case`。接口同时接受表单、简单 CSV（`case,a,b`）和标准 `kind=duplicate` CSV。

`GET /api/runs/<id>/roster`（同义路径 `/available`、`/available_roster`）返回当前可用名单。原始切分名单始终保留在 `original_roster` / 运行报告中；签发时的名单快照保存在 `issued_roster`，也可通过 `/api/runs/<id>/issued_roster` 查询。

补录关系会沿原有实体、指纹、近重复组和新关系做传递归并。只要连通组同时触及训练集与评估集（或触及原隔离组），整组进入 `quarantined` 并退出后续取样；其他组仍保留在 `train`、`evaluation` 与 `available`。

仅在可用名单发生变化时，批次 `revision` 才前进并使旧签发令牌返回 `409 STALE_REVIEW`。同侧补录若没有改变名单样本，原 `revision` 仍可签发。补录与复核并发时由 SQLite 写事务串行化：补录先提交且改变名单后，旧令牌的条件更新失败，复核读取新版本后重试。
