# 训练样本切分核验

离线训练数据工程师可在工作台上传来源 CSV，对照规则判断差异，签发合格批次或记录暂缓意见。

按实体及近重复组切分训练与评估集，隔离跨截止日的泄漏组。晚到关系可按批次补录：跨集传递连通的整组退出后续取样，其余样本继续可用，原名单与签发快照按批次保留。

## 启动

```sh
docker compose up --build -d --wait
```

打开 <http://localhost:18334>。页面预览带异常样例。选中阶段查看计算证据，选择可签发样例并执行批次，然后提交复核意见。

## 核验

```sh
docker compose exec -T app pytest -q
```

[输入字段](docs/DATA-DICTIONARY.md) · [阶段接口](docs/HTTP.md) · [操作步骤](docs/OPERATIONS.md) · [规则与测试](docs/DEPTH.md)
