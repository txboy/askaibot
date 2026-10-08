from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services import mcp as mcp_core
from app.services import groups as groups_core
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("", response_model=list[schemas.McpServerPublic])
async def list_frontend_mcp(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回可被前端选用（mode=frontend）且当前用户可见的启用 MCP 服务器。"""
    servers = mcp_core.all_servers(db, mode="frontend")
    servers = groups_core.filter_accessible(
        db, user.id if user else None, "mcp", servers
    )
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
