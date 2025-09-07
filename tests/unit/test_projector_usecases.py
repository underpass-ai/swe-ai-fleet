# tests/context/usecases/test_projector_usecases.py
from swe_ai_fleet.context.usecases.projector_coordinator import ProjectorCoordinator

class _FakeWriter:
    def __init__(self): self.ops=[]
    def init_constraints(self, labels): self.ops.append(("constraints",tuple(labels)))
    def upsert_entity(self, label, id, props=None): self.ops.append(("upsert",label,id,props or {}))
    def upsert_entity_multi(self, labels, id, props=None): self.ops.append(("upsert_multi",tuple(labels),id,props or {}))
    def relate(self, src, rel, dst, **kw): self.ops.append(("rel",src,rel,dst,kw))

def test_routing_and_side_effects():
    w = _FakeWriter()
    c = ProjectorCoordinator(w)
    assert c.handle("case.created", {"case_id":"C1","name":"Demo"})
    assert c.handle("plan.versioned", {"case_id":"C1","plan_id":"P1","version":1})
    assert c.handle("subtask.created", {"plan_id":"P1","sub_id":"T1","title":"Fix tests"})
    assert c.handle("subtask.status_changed", {"sub_id":"T1","status":"in_progress"})
    assert c.handle("decision.made", {"node_id":"D1","kind":"dev.change","summary":"Patch","sub_id":"T1"})
    assert not c.handle("unknown.event", {})

    # quick sanity checks
    assert any(op[0]=="upsert" and op[1]=="Case" and op[2]=="C1" for op in w.ops)
    assert any(op[0]=="rel" and op[1]=="C1" and op[2]=="HAS_PLAN" and op[3]=="P1" for op in w.ops)
    assert any(op[0]=="rel" and op[1]=="P1" and op[2]=="HAS_SUBTASK" and op[3]=="T1" for op in w.ops)
    assert any(op[0]=="upsert" and op[1]=="Subtask" and op[2]=="T1" and op[3].get("last_status")=="in_progress" for op in w.ops)
    assert any(op[0]=="rel" and op[1]=="D1" and op[2]=="AFFECTS" and op[3]=="T1" for op in w.ops)
