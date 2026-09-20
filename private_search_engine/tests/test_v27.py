from private_search_engine.replication.consensus import LogEntry
from private_search_engine.replication.persistence import ConsensusPersistence
from private_search_engine.replication.faults import NetworkFaultInjector

def test_consensus_persistence_round_trip(tmp_path):
    p=ConsensusPersistence(tmp_path/'node.json'); log=[LogEntry(2,1,'PUT','alpha'),LogEntry(2,2,'PUT','beta')]; p.save(node_id='b',term=2,voted_for='b',log=log,commit_index=2); loaded=p.load(); assert loaded['term']==2 and loaded['voted_for']=='b' and loaded['commit_index']==2 and loaded['log']==log

def test_atomic_persistence_replaces_previous_state(tmp_path):
    p=ConsensusPersistence(tmp_path/'node.json'); p.save(node_id='a',term=1,voted_for='a',log=[],commit_index=0); p.save(node_id='a',term=2,voted_for='b',log=[LogEntry(2,1,'PUT','x')],commit_index=1); loaded=p.load(); assert loaded['term']==2 and loaded['log'][0].value=='x'

def test_partition_blocks_cross_group_messages():
    f=NetworkFaultInjector(); f.partition({'a'},{'b','c'}); assert f.send('a','b',lambda:'ok') is None; assert f.send('b','a',lambda:'ok') is None; assert f.send('b','c',lambda:'ok')=='ok'; assert [e.action for e in f.events]==['drop','drop','deliver']

def test_heal_restores_delivery():
    f=NetworkFaultInjector(); f.drop('a','b'); assert f.send('a','b',lambda:1) is None; f.heal(); assert f.send('a','b',lambda:2)==2
