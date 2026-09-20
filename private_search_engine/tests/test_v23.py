import threading,time
from private_search_engine.core.document import Document
from private_search_engine.distributed.remote import RemoteShardCoordinator,RemoteShardNode,ShardNodeServer

def start_server(node_id):
    server=ShardNodeServer(node_id=node_id); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); time.sleep(0.02); return server,thread

def test_remote_shard_search_and_health():
    s1,_=start_server('s1'); s2,_=start_server('s2')
    try:
        nodes=[RemoteShardNode('s1',s1.address),RemoteShardNode('s2',s2.address)]; coordinator=RemoteShardCoordinator(nodes); coordinator.load_documents([Document('https://a.test/python','Python','python systems search engine'),Document('https://b.test/sql','SQL','database systems and indexing')]); hits=coordinator.search('python',limit=5); assert hits and hits[0]['url'].endswith('/python'); assert coordinator.report()['partial'] is False; assert all(x['healthy'] for x in coordinator.health())
    finally: s1.shutdown(); s2.shutdown()

def test_partial_results_when_one_node_is_unavailable():
    s1,_=start_server('healthy')
    try:
        healthy=RemoteShardNode('healthy',s1.address); dead=RemoteShardNode('dead','http://127.0.0.1:1',timeout=0.05,retries=0,failure_threshold=1); coordinator=RemoteShardCoordinator([healthy,dead]); healthy.load([Document('https://a.test/python','Python','python search')]); hits=coordinator.search('python',limit=5); assert hits; report=coordinator.report(); assert report['partial'] is True; assert report['nodes_failed']==1
    finally: s1.shutdown()

def test_circuit_breaker_opens_after_failures():
    node=RemoteShardNode('dead','http://127.0.0.1:1',timeout=0.03,retries=0,failure_threshold=2,reset_timeout=60); coordinator=RemoteShardCoordinator([node]); assert coordinator.search('anything',limit=1)==[]; assert coordinator.search('anything',limit=1)==[]; assert node.breaker.open is True; assert coordinator.health()[0]['circuit_open'] is True
