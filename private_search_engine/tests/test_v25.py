import pytest
from private_search_engine.core.document import Document
from private_search_engine.replication import QuorumReplicaCluster

def test_quorum_write_and_read():
    c=QuorumReplicaCluster(['n1','n2','n3']); result=c.write(Document('https://a','A','alpha')); assert result.committed and result.acknowledgements==3; doc,report=c.read(result.doc_id); assert doc.doc.text=='alpha'; assert report.version==1

def test_stale_replica_is_repaired():
    c=QuorumReplicaCluster(['n1','n2','n3']); first=Document('https://a','A','alpha'); c.write(first); c.fail_node('n3'); c.write(Document('https://a','A','beta')); c.recover_node('n3'); assert 'n3' in c.stale_nodes(first.doc_id); doc,report=c.read(first.doc_id,repair=True); assert doc.doc.text=='beta'; assert report.repaired>=1; assert not c.stale_nodes(first.doc_id)

def test_read_quorum_failure():
    c=QuorumReplicaCluster(['n1','n2','n3']); c.write(Document('https://a','A','alpha')); c.fail_node('n1'); c.fail_node('n2')
    with pytest.raises(RuntimeError,match='read quorum unavailable'): c.read(Document('https://a','A','alpha').doc_id)

def test_write_quorum_not_committed_when_too_many_nodes_fail():
    c=QuorumReplicaCluster(['n1','n2','n3']); c.fail_node('n1'); c.fail_node('n2'); result=c.write(Document('https://a','A','alpha')); assert not result.committed; assert result.acknowledgements==1

def test_generation_increments_per_document():
    c=QuorumReplicaCluster(['n1','n2','n3']); assert c.write(Document('https://a','A','alpha')).version==1; assert c.write(Document('https://a','A','beta')).version==2
