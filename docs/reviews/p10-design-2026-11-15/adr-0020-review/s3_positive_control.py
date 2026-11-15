"""Positive control for s2_seed_context_search.py: same method, namespaces known to be in use."""
import sys
sys.argv = [sys.argv[0]] + sys.argv[1:]
import s2_seed_context_search as s
s.NAMESPACES[:] = [("P9 170001-171343", 170001, 171343), ("P9-I 182001-182020", 182001, 182020),
                   ("P9-I 180101-181900", 180101, 181900), ("P9-I init 1801-1802", 1801, 1802),
                   ("P9 init 1701-1702", 1701, 1702), ("P9-I tests 900001-900233", 900001, 900233)]
s.main()
