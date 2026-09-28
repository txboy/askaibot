from fastapi import APIRouter
from app import models, schemas
from app.services import mcp as mcp_core

from . import auth, system, sms, search, endpoints, knowledge_bases, mcp, skills, wecom_bots, integrations, users, groups

router = APIRouter(prefix='/admin', tags=['admin'])
for m in (auth, system, sms, search, endpoints, knowledge_bases, mcp, skills, wecom_bots, integrations, users, groups):
    router.include_router(m.router)

from .auth import *
from .system import *
from .sms import *
from .search import *
from .endpoints import *
from .knowledge_bases import *
from .mcp import *
from .skills import *
from .wecom_bots import *
from .integrations import *
from .users import *
from .groups import *
