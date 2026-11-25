import asyncio
import pytest
from fastapi import HTTPException
from app.readonly_api import app,READ_TOOLS,call_tool


def test_gateway_has_no_inference_or_review_write_routes():
    paths=app.openapi()['paths']
    assert '/inference/run' not in paths and '/inference/jobs' not in paths and '/chat' not in paths
    assert 'submit_review' not in READ_TOOLS and 'request_review' not in READ_TOOLS
    assert '/status/overview' in paths and '/tools/{tool_name}' in paths


def test_gateway_blocks_write_before_parsing_request():
    with pytest.raises(HTTPException) as error:asyncio.run(call_tool('submit_review',None))
    assert error.value.status_code==403
