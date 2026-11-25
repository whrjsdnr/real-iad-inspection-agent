import json
from app.tools import query_error_stats,get_case_evidence


def test_agent_registry_rejects_arbitrary_code_and_keeps_evidence_readable(monkeypatch,seeded_session):
    monkeypatch.setenv('AGENT_MOCK','1')
    import agent
    assert json.loads(agent.run_tool('execute_sql',{'sql':'DELETE FROM reviews'}))['error']
    assert json.loads(agent.run_tool('eval',{'javascript':'alert(1)'}))['error']
    monkeypatch.setattr(agent,'TOOL_FUNCS',{'query_error_stats':lambda **kw:query_error_stats(**kw,session=seeded_session)})
    out=json.loads(agent.run_tool('query_error_stats',{'item':'toothbrush','metric':'part_miss_rate','group_by':['part_id']}))
    assert out['rows']
    first=out['rows'][0]
    evidence=get_case_evidence(stat_key=first['stat_key'],session=seeded_session)
    assert evidence['count']==first['den']
    assert all('product_id' in case for case in evidence['cases'])
