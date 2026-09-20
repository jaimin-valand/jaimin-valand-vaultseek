from private_search_engine.replication.consensus import LogEntry
from private_search_engine.replication.snapshot import ConsensusSnapshotStore,compact_log
from private_search_engine.replication.compaction import SnapshotCompactor

def test_snapshot_round_trip_and_checksum(tmp_path):
    store=ConsensusSnapshotStore(tmp_path/'snapshot.json'); checksum=store.save(node_id='a',term=4,last_included_index=3,last_included_term=3,commit_index=3,state={'doc1':'v3','doc2':'v2'}); loaded=store.load(); assert loaded['checksum']==checksum and loaded['state']['doc1']=='v3' and loaded['last_included_index']==3

def test_snapshot_detects_corruption(tmp_path):
    store=ConsensusSnapshotStore(tmp_path/'snapshot.json'); store.save(node_id='a',term=1,last_included_index=1,last_included_term=1,commit_index=1,state={'x':'y'}); text=(tmp_path/'snapshot.json').read_text(); (tmp_path/'snapshot.json').write_text(text.replace('"y"','"tampered"'))
    try: store.load(); assert False
    except ValueError as exc: assert 'checksum' in str(exc)

def test_compaction_removes_only_snapshotted_entries(tmp_path):
    log=[LogEntry(1,i,'PUT',f'v{i}') for i in range(1,6)]; store=ConsensusSnapshotStore(tmp_path/'snapshot.json'); remaining,result=SnapshotCompactor(store).compact(node_id='a',term=2,commit_index=3,log=log,state={'k1':'v1','k2':'v2','k3':'v3'}); assert [e.index for e in remaining]==[4,5]; assert result.removed_entries==3; assert store.load()['last_included_index']==3

def test_compacted_log_helper_preserves_tail():
    log=[LogEntry(1,i,'PUT',str(i)) for i in range(1,5)]; assert [e.index for e in compact_log(log,2)]==[3,4]
