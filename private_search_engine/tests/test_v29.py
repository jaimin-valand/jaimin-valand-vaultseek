import threading,time
from private_search_engine.core.document import Document
from private_search_engine.distributed.remote import RemoteShardCoordinator,RemoteShardNode,ShardNodeServer
from private_search_engine.observability import SearchTrace,TraceStore

def start_server(node_id):
    server=ShardNodeServer(node_id=node_id); threading.Thread(target=server.serve_forever,daemon=True).start(); time.sleep(.02); return server

def test_trace_captures_query_stages():
    s1=start_server('s1'); s2=start_server('s2')
    try:
        c=RemoteShardCoordinator([RemoteShardNode('s1',s1.address),RemoteShardNode('s2',s2.address)]); c.load_documents([Document('https://a/python','Python','python search')]); hits=c.search('python'); assert hits and c.report()['trace_id']; trace=c.trace(c.report()['trace_id']); names={e['name'] for e in trace['events']}; assert {'query.fanout','shard.search','result.merge','query'}<=names
    finally: s1.shutdown(); s2.shutdown()

def test_trace_store_metrics_and_limit():
    store=TraceStore(max_traces=2)
    for _ in range(3):
        t=SearchTrace()
        with t.span('search'): pass
        store.add(t)
    assert store.metrics()['traces']==2

def test_error_trace_records_failure():
    t=SearchTrace()
    try:
        with t.span('failing',node_id='x'): raise RuntimeError('boom')
    except RuntimeError: pass
    event=t.finish()[0]; assert event['status']=='error' and 'boom' in event['attributes']['error']
