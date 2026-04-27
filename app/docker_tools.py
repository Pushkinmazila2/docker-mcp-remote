"""
Определения MCP-инструментов и их исполнение.
Каждый инструмент — словарь в формате MCP tools/list + функция-обработчик.
"""
from .models import AddServerRequest, ServerAuthType
from . import server_manager, ssh_client

# ── Tool schemas (MCP format) ────────────────────────────────────────────────

TOOL_SCHEMAS = {
    "list_servers": {
        "name": "list_servers",
        "description": "List all configured remote Docker hosts",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "list_containers": {
        "name": "list_containers",
        "description": "List Docker containers on a remote host",
        "inputSchema": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "Server ID from list_servers",
                },
                "all": {
                    "type": "boolean",
                    "description": "Include stopped containers (default: true)",
                    "default": True,
                },
            },
            "required": ["server_id"],
        },
    },
    "start_container": {
        "name": "start_container",
        "description": "Start a Docker container on a remote host",
        "inputSchema": {
            "type": "object",
            "properties": {
                "server_id": {"type": "string", "description": "Server ID"},
                "container": {"type": "string", "description": "Container name or ID"},
            },
            "required": ["server_id", "container"],
        },
    },
    "stop_container": {
        "name": "stop_container",
        "description": "Stop a running Docker container on a remote host",
        "inputSchema": {
            "type": "object",
            "properties": {
                "server_id": {"type": "string", "description": "Server ID"},
                "container": {"type": "string", "description": "Container name or ID"},
            },
            "required": ["server_id", "container"],
        },
    },
    "add_server": {
        "name": "add_server",
        "description": "Add a new remote Docker host. auth_type: 'password' | 'key_path' | 'generate_key'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string"},
                "host":        {"type": "string"},
                "port":        {"type": "integer", "default": 22},
                "username":    {"type": "string"},
                "auth_type":   {"type": "string", "enum": ["password", "key_path", "generate_key"]},
                "password":    {"type": "string"},
                "key_path":    {"type": "string"},
                "description": {"type": "string"},
                "tags":        {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "host", "username", "auth_type"],
        },
    },
}


# ── Tool handlers ────────────────────────────────────────────────────────────

def handle_list_servers(_args: dict) -> dict:
    servers = server_manager.list_servers()
    return {
        "servers": [
            {
                "id": s.id,
                "name": s.name,
                "host": s.host,
                "port": s.port,
                "username": s.username,
                "auth_type": s.auth_type,
                "description": s.description,
                "tags": s.tags,
            }
            for s in servers
        ]
    }


def handle_list_containers(args: dict) -> dict:
    server_id = args["server_id"]
    include_all = args.get("all", True)

    server = server_manager.get_server(server_id)
    if not server:
        raise ValueError(f"Server '{server_id}' not found")

    containers = ssh_client.docker_list_containers(server, all_containers=include_all)
    return {
        "server": server.name,
        "containers": [c.model_dump() for c in containers],
    }


def handle_start_container(args: dict) -> dict:
    server = _get_server(args["server_id"])
    result = ssh_client.docker_start_container(server, args["container"])
    return {"message": f"Started: {result}"}


def handle_stop_container(args: dict) -> dict:
    server = _get_server(args["server_id"])
    result = ssh_client.docker_stop_container(server, args["container"])
    return {"message": f"Stopped: {result}"}


def handle_add_server(args: dict) -> dict:
    req = AddServerRequest(
        name=args["name"],
        host=args["host"],
        port=args.get("port", 22),
        username=args["username"],
        auth_type=ServerAuthType(args["auth_type"]),
        password=args.get("password"),
        key_path=args.get("key_path"),
        description=args.get("description"),
        tags=args.get("tags", []),
    )
    cfg = server_manager.add_server(req)
    response = {
        "id": cfg.id,
        "name": cfg.name,
        "message": "Server added successfully",
    }
    if cfg.auth_type == ServerAuthType.GENERATE_KEY:
        response["note"] = (
            "SSH key pair was generated. "
            "Check server description for the public key — add it to ~/.ssh/authorized_keys on the host."
        )
        response["description"] = cfg.description
    return response


# ── Dispatch table ───────────────────────────────────────────────────────────

HANDLERS = {
    "list_servers":    handle_list_servers,
    "list_containers": handle_list_containers,
    "start_container": handle_start_container,
    "stop_container":  handle_stop_container,
    "add_server":      handle_add_server,
}


def execute_tool(name: str, args: dict) -> dict:
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(args)


def _get_server(server_id: str):
    server = server_manager.get_server(server_id)
    if not server:
        raise ValueError(f"Server '{server_id}' not found")
    return server