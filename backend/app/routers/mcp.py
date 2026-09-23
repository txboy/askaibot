from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import mcp as mcp_core
from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("", response_model=list[schemas.McpServerPublic])
async def list_frontend_mcp(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回可被前端选用（mode=frontend）的启用 MCP 服务器。"""
    servers = mcp_core.all_servers(db, mode="frontend")
    out: list[schemas.McpServerPublic] = []
    for s in servers:
        tool_count = 0
        try:
            tool_count = len(await mcp_core.list_tools(s))
        except Exception:
            pass
        out.append(
            schemas.McpServerPublic(
                id=s.id,
                name=s.name,
                description=s.description,
                tool_count=tool_count,
            )
        )
    return out
