import logging
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import get_auth_level, get_allowed_tools, check_tool_access, verify_web_token
from .docker_tools import TOOL_SCHEMAS, execute_tool
from .models import MCPRequest, MCPResponse, AuthLevel, AddServerRequest
from . import server_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Docker MCP Hub", version="0.1.0")


# ── Helpers ──────────────────────────────────────────────────────────────────

def mcp_error(id_, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def mcp_result(id_, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


# ── MCP handler (shared logic) ───────────────────────────────────────────────

async def handle_mcp(request: Request, auth_level: AuthLevel) -> JSONResponse:
    allowed = get_allowed_tools(auth_level)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(mcp_error(None, -32700, "Parse error"))

    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params") or {}

    logger.info(f"[{auth_level}] method={method}")

    # ── initialize ────────────────────────────────────────────────────────────
    if method == "initialize":
        return JSONResponse(mcp_result(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "docker-mcp-hub", "version": "0.1.0"},
        }))

    # ── notifications/initialized (no response needed) ────────────────────────
    if method == "notifications/initialized":
        return JSONResponse(status_code=204, content=None)

    # ── tools/list ────────────────────────────────────────────────────────────
    if method == "tools/list":
        tools = [TOOL_SCHEMAS[name] for name in allowed if name in TOOL_SCHEMAS]
        return JSONResponse(mcp_result(req_id, {"tools": tools}))

    # ── tools/call ────────────────────────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments") or {}

        if tool_name not in allowed:
            return JSONResponse(mcp_error(req_id, -32603,
                f"Tool '{tool_name}' is not available for your access level"))

        try:
            result = execute_tool(tool_name, tool_args)
            return JSONResponse(mcp_result(req_id, {
                "content": [{"type": "text", "text": str(result)}],
                "isError": False,
            }))
        except ValueError as e:
            return JSONResponse(mcp_error(req_id, -32602, str(e)))
        except Exception as e:
            logger.error(f"Tool error: {e}", exc_info=True)
            return JSONResponse(mcp_error(req_id, -32603, f"Internal error: {e}"))

    return JSONResponse(mcp_error(req_id, -32601, f"Method not found: {method}"))


# ── MCP routes ───────────────────────────────────────────────────────────────

@app.post("/mcp/user")
async def mcp_user(request: Request, authorization: Optional[str] = Header(None)):
    level = get_auth_level(authorization)
    # User path принимает только уровень user (не admin)
    if level != AuthLevel.USER:
        raise HTTPException(403, "This endpoint is for user tokens only")
    return await handle_mcp(request, AuthLevel.USER)


@app.post("/mcp/admin")
async def mcp_admin(request: Request, authorization: Optional[str] = Header(None)):
    level = get_auth_level(authorization)
    if level != AuthLevel.ADMIN:
        raise HTTPException(403, "This endpoint requires admin token")
    return await handle_mcp(request, AuthLevel.ADMIN)


# ── Web UI API ───────────────────────────────────────────────────────────────

@app.get("/api/servers")
async def api_list_servers(authorization: Optional[str] = Header(None)):
    verify_web_token(authorization)
    servers = server_manager.list_servers()
    return [s.model_dump(exclude={"password"}) for s in servers]


@app.post("/api/servers")
async def api_add_server(req: AddServerRequest, authorization: Optional[str] = Header(None)):
    verify_web_token(authorization)
    cfg = server_manager.add_server(req)
    return cfg.model_dump(exclude={"password"})


@app.delete("/api/servers/{server_id}")
async def api_delete_server(server_id: str, authorization: Optional[str] = Header(None)):
    verify_web_token(authorization)
    ok = server_manager.remove_server(server_id)
    if not ok:
        raise HTTPException(404, "Server not found")
    return {"message": "Deleted"}


# ── Web UI ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def web_ui():
    from pathlib import Path
    html_path = Path(__file__).parent / "web" / "index.html"
    return HTMLResponse(content=html_path.read_text())


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}