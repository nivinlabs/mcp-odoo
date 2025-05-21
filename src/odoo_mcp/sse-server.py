import json
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from fastapi.responses import EventSourceResponse

from mcp.server.fastmcp import Context, FastMCP, stream_tool,stream_resource
from pydantic import BaseModel, Field

from .odoo_client import OdooClient, get_odoo_client

@dataclass
class AppContext:
    odoo: OdooClient

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    odoo_client = get_odoo_client()
    try:
        yield AppContext(odoo=odoo_client)
    finally:
        pass

mcp = FastMCP(
    "Odoo MCP Server",
    description="MCP Server for interacting with Odoo ERP systems",
    dependencies=["requests"],
    lifespan=app_lifespan,
)

@stream_tool(description="Execute a custom method on an Odoo model with streaming output")
async def execute_method_stream(
    ctx: Context,
    model: str,
    method: str,
    args: List = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[str]:
    odoo = ctx.request_context.lifespan_context.odoo
    args = args or []
    kwargs = kwargs or {}

    yield json.dumps({"status": "starting", "model": model, "method": method})

    try:
        yield json.dumps({"status": "executing", "args": args, "kwargs": kwargs})
        result = odoo.execute_method(model, method, *args, **kwargs)
        await asyncio.sleep(0.1)
        yield json.dumps({"status": "success", "result": result})
    except Exception as e:
        yield json.dumps({"status": "error", "message": str(e)})

@stream_tool(description="Stream holidays search results in real time")
async def stream_search_holidays(
    ctx: Context,
    start_date: str,
    end_date: str,
    employee_id: Optional[int] = None,
) -> AsyncIterator[str]:
    odoo = ctx.request_context.lifespan_context.odoo

    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as ve:
        yield json.dumps({"status": "error", "message": str(ve)})
        return

    yield json.dumps({"status": "fetching"})

    domain = [
        "&",
        ["start_datetime", "<=", f"{end_date} 22:59:59"],
        ["stop_datetime", ">=", f"{start_date} 23:00:00"],
    ]
    if employee_id:
        domain.append(["employee_id", "=", employee_id])

    try:
        holidays = odoo.search_read("hr.leave.report.calendar", domain)
        for holiday in holidays:
            yield json.dumps(holiday)
            await asyncio.sleep(0.05)
        yield json.dumps({"status": "done", "count": len(holidays)})
    except Exception as e:
        yield json.dumps({"status": "error", "message": str(e)})


@stream_resource("odoo://models", description="Stream all available models in the Odoo system")
async def stream_models() -> EventSourceResponse:
    odoo_client = get_odoo_client()
    models = odoo_client.get_models()

    async def event_generator():
        for model in models:
            await asyncio.sleep(0.001)
            yield {"data": json.dumps(model)}
    
    return EventSourceResponse(event_generator())


@stream_resource("odoo://model/{model_name}", description="Stream detailed information about a specific model including fields")
async def stream_model_info(model_name: str) -> EventSourceResponse:
    odoo_client = get_odoo_client()

    async def event_generator():
        try:
            model_info = odoo_client.get_model_info(model_name)
            yield {"event": "info", "data": json.dumps(model_info)}

            fields = odoo_client.get_model_fields(model_name)
            for name, field in fields.items():
                await asyncio.sleep(0.001)
                yield {"event": "field", "data": json.dumps({name: field})}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@stream_resource("odoo://record/{model_name}/{record_id}", description="Stream detailed information of a specific record by ID")
async def stream_record(model_name: str, record_id: str) -> EventSourceResponse:
    odoo_client = get_odoo_client()

    async def event_generator():
        try:
            record_id_int = int(record_id)
            record = odoo_client.read_records(model_name, [record_id_int])
            if not record:
                yield {"event": "error", "data": json.dumps(
                    {"error": f"Record not found: {model_name} ID {record_id}"}
                )}
            else:
                yield {"data": json.dumps(record[0])}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@stream_resource("odoo://search/{model_name}/{domain}", description="Stream records matching a domain")
async def stream_search_records(model_name: str, domain: str) -> EventSourceResponse:
    odoo_client = get_odoo_client()

    async def event_generator():
        try:
            domain_list = json.loads(domain)
            results = odoo_client.search_read(model_name, domain_list, limit=100)
            for record in results:
                await asyncio.sleep(0.001)
                yield {"data": json.dumps(record)}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
