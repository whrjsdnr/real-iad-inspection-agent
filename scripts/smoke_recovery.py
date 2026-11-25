"""Direct API-handler and agent-tool smoke check (no live HTTP or LLM claim)."""
import asyncio
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['AGENT_MOCK'] = '1'

from app.api import health, list_tools, call_tool
from migrate import migrate

class Request:
    async def json(self):
        return {'item':'toothbrush','metric':'part_miss_rate','group_by':['part_id']}

async def main():
    migrate()
    import agent
    stats = await call_tool('query_error_stats', Request())
    assert isinstance(stats, dict) and 'rows' in stats, stats
    tool = json.loads(agent.run_tool('get_training_status', {'item':'toothbrush'}))
    assert 'error' not in tool, tool
    result = {'transport':'direct_handlers_no_socket', 'health':health(),
              'tools':list_tools()['tools'], 'stats_rows':len(stats['rows']),
              'agent_direct_tool':tool, 'live_uvicorn':'blocked: socket PermissionError',
              'live_ollama':'not verified: sockets blocked'}
    Path('reports/recovery_smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ == '__main__': asyncio.run(main())
