import pytest
from private_search_engine.replication.consensus import RaftCluster

def test_election_and_majority_commit():
    c=RaftCluster(['a','b','c']); c.elect_leader('a'); r=c.append('PUT','doc-1'); assert r['committed'] and r['acknowledgements']==3 and c.status().commit_index==1

def test_failed_leader_requires_new_election():
    c=RaftCluster(['a','b','c']); c.elect_leader('a'); c.append('PUT','x'); c.fail_node('a'); c.elect_leader('b'); r=c.append('PUT','y'); assert r['committed'] and c.status().term==2

def test_no_majority_blocks_commit():
    c=RaftCluster(['a','b','c']); c.elect_leader('a'); c.fail_node('b'); c.fail_node('c')
    with pytest.raises(RuntimeError): c.append('PUT','x')

def test_follower_catch_up():
    c=RaftCluster(['a','b','c']); c.elect_leader('a'); c.append('PUT','x'); c.fail_node('c'); c.logs['c']=[]; c.recover_node('c'); assert c.catch_up('c')==1; assert c.state_digest('c')==c.state_digest('a')

def test_term_increments_on_re_election():
    c=RaftCluster(['a','b','c']); c.elect_leader('a'); c.elect_leader('b'); assert c.status().term==2 and c.status().leader_id=='b'
