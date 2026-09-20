from private_search_engine.core.document import Document
from private_search_engine.replication import ReplicatedShard,ClusterRebalancer

def test_replication_and_consistency():
    s=ReplicatedShard(0); s.add_replica('r1'); s.add(Document('https://a','A','alpha')); assert s.consistency()[0]['consistent']

def test_failover():
    s=ReplicatedShard(0); s.add_replica('r1'); s.add(Document('https://a','A','alpha')); s.fail_replica('r1')
    try: s.replicate('r1'); assert False
    except RuntimeError: pass
    s.recover_replica('r1'); s.failover('r1'); assert s.state().document_count==1

def test_rebalancing_plan():
    docs=[Document('https://a','A','alpha'),Document('https://b','B','beta')]; p=ClusterRebalancer(3).plan(docs,0); assert all(x['from_shard']==0 for x in p)
