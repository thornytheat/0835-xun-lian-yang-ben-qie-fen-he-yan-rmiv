EXPECTED = {'0001': (4, 2, 'READY'),
 '0002': (2, 2, 'READY'),
 '0003': (0, None, 'UNKNOWN_SAMPLE'),
 '0004': (2, 0, 'CROSS_CUTOFF_LEAKAGE')}
EVIDENCE = {'0001': {'train': [1, 2],
          'evaluation': [3, 4],
          'quarantined': [],
          'groups': [[1, 2], [3, 4]]},
 '0004': {'train': [],
          'evaluation': [],
          'quarantined': [1, 2],
          'groups': [[1, 2]]}}
