COLUMNS = ('sample', 'entity', 'fingerprint', 'day', 'split_code')
KINDS = ('record', 'duplicate', 'rule')
PROJECT = {'name': '训练样本切分核验', 'actor': '离线训练数据工程师', 'stages': [('intake', '样例采信'), ('prepare', '样本关联'), ('calculate', '切分裁决'), ('policy', '泄漏核对'), ('balance', '运行对账')], 'chart': '样本归集', 'mark': '训'}
