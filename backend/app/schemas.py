from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class SMSRequest(BaseModel):
    phone: str


class SMSVerifyRequest(BaseModel):
    phone: str
    code: str


class DingtalkCodeRequest(BaseModel):
    code: str


class NicknameUpdate(BaseModel):
    nickname: str


class ProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    assistant_name: Optional[str] = None


class PhoneUpdate(BaseModel):
    phone: str
    code: str


class UserOut(BaseModel):
    id: int
    nickname: str
    avatar: str
    assistant_name: str
    assistant_avatar: str
    phone: Optional[str] = None
    wecom_userid: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    token: str
    user: UserOut


class ConversationCreate(BaseModel):
    title: Optional[str] = "新对话"
    model: Optional[str] = ""
    mcp_ids: Optional[str] = ""
    skill_ids: Optional[str] = ""


class ConversationUpdate(BaseModel):
    title: str


class ConversationMcpUpdate(BaseModel):
    mcp_ids: str


class ConversationSkillUpdate(BaseModel):
    skill_ids: str


class ConversationOut(BaseModel):
    id: int
    title: str
    model: str
    mcp_ids: str
    skill_ids: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AttachmentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    kind: str
    size: int

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    attachments: list[AttachmentOut] = []

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    conversation_id: int
    content: str
    attachment_ids: list[int] = []
    endpoint_id: Optional[int] = None
    model: Optional[str] = None
    web_search: bool = False
    knowledge_base_id: Optional[int] = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str


class EndpointCreate(BaseModel):
    name: str
    base_url: str
    api_key: Optional[str] = ""
    models: Optional[str] = ""  # 逗号分隔
    enabled: Optional[int] = 1
    is_default: Optional[int] = 0


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[str] = None
    enabled: Optional[int] = None
    is_default: Optional[int] = None


class EndpointOut(BaseModel):
    id: int
    name: str
    base_url: str
    api_key_masked: str
    models: str
    enabled: int
    is_default: int

    class Config:
        from_attributes = True


class EndpointPublic(BaseModel):
    id: int
    name: str
    base_url: str
    models: list[str]
    is_default: int


class WecomOut(BaseModel):
    wecom_corp_id: str
    wecom_agent_id: str
    wecom_redirect: str
    wecom_secret_set: bool


class WecomUpdate(BaseModel):
    wecom_corp_id: Optional[str] = None
    wecom_secret: Optional[str] = None
    wecom_agent_id: Optional[str] = None
    wecom_redirect: Optional[str] = None


class DingtalkOut(BaseModel):
    app_key: str
    agent_id: str
    redirect: str
    app_secret_set: bool


class DingtalkUpdate(BaseModel):
    app_key: Optional[str] = None
    app_secret: Optional[str] = None
    agent_id: Optional[str] = None
    redirect: Optional[str] = None


class AdminPasswordChange(BaseModel):
    old_password: str
    new_password: str


class ThemeUpdate(BaseModel):
    theme: str


class DebugUpdate(BaseModel):
    debug_mode: bool


class SystemOut(BaseModel):
    site_title: str
    theme: str
    debug_mode: bool
    favicon_set: bool
    admin_secret_enabled: bool
    admin_secret: str
    assistant_name: str
    assistant_avatar_set: bool


class SystemUpdate(BaseModel):
    site_title: Optional[str] = None
    admin_secret_enabled: Optional[bool] = None
    admin_secret: Optional[str] = None
    assistant_name: Optional[str] = None


class SmsOut(BaseModel):
    provider: str
    access_key_id: str
    sign_name: str
    template_code: str
    region: str
    sdk_app_id: str
    secret_set: bool


class SmsUpdate(BaseModel):
    provider: Optional[str] = None
    access_key_id: Optional[str] = None
    secret: Optional[str] = None
    sign_name: Optional[str] = None
    template_code: Optional[str] = None
    region: Optional[str] = None
    sdk_app_id: Optional[str] = None


class SearchOut(BaseModel):
    provider: str
    base_url: str
    auto: bool
    api_key_set: bool


class SearchUpdate(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    auto: Optional[bool] = None


class KnowledgeBaseCreate(BaseModel):
    name: str
    provider: Optional[str] = "dify"
    base_url: str
    api_key: Optional[str] = ""
    dataset_ids: Optional[str] = ""
    top_k: Optional[int] = 5
    mode: Optional[str] = "frontend"
    description: Optional[str] = ""
    enabled: Optional[int] = 1


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    dataset_ids: Optional[str] = None
    top_k: Optional[int] = None
    mode: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[int] = None


class KnowledgeBaseOut(BaseModel):
    id: int
    name: str
    provider: str
    base_url: str
    api_key_masked: str
    dataset_ids: str
    top_k: int
    mode: str
    description: str
    enabled: int

    class Config:
        from_attributes = True


class KnowledgeBasePublic(BaseModel):
    id: int
    name: str
    provider: str
    description: str


class KnowledgeBaseTestRequest(BaseModel):
    provider: Optional[str] = "dify"
    base_url: str
    api_key: Optional[str] = ""
    dataset_ids: Optional[str] = ""
    top_k: Optional[int] = 5
    query: str


class WecomBotCreate(BaseModel):
    name: str
    provider: Optional[str] = "wecom"
    corp_id: Optional[str] = ""
    secret: Optional[str] = ""
    agent_id: Optional[str] = ""
    token: Optional[str] = ""
    aes_key: Optional[str] = ""
    kb_ids: Optional[str] = ""
    mcp_ids: Optional[str] = ""
    skill_ids: Optional[str] = ""
    web_search: Optional[int] = 0
    endpoint_id: Optional[int] = None
    model: Optional[str] = ""
    enabled: Optional[int] = 1


class WecomBotUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    corp_id: Optional[str] = None
    secret: Optional[str] = None
    agent_id: Optional[str] = None
    token: Optional[str] = None
    aes_key: Optional[str] = None
    kb_ids: Optional[str] = None
    mcp_ids: Optional[str] = None
    skill_ids: Optional[str] = None
    web_search: Optional[int] = None
    endpoint_id: Optional[int] = None
    model: Optional[str] = None
    enabled: Optional[int] = None


class WecomBotOut(BaseModel):
    id: int
    name: str
    provider: str
    corp_id: str
    agent_id: str
    token_masked: str
    aes_key_set: bool
    kb_ids: str
    mcp_ids: str
    skill_ids: str
    web_search: int
    endpoint_id: Optional[int] = None
    model: str
    enabled: int
    callback_url: str

    class Config:
        from_attributes = True


class AdminUserOut(BaseModel):
    id: int
    nickname: str
    phone: Optional[str] = None
    created_at: datetime
    conversation_count: int
    last_active: Optional[datetime] = None
    total_tokens: int
    today_tokens: int


class SettingOut(BaseModel):
    base_url: str
    api_key_masked: str
    default_model: str
    wecom_corp_id: str
    wecom_agent_id: str
    wecom_redirect: str


class SettingUpdate(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    wecom_corp_id: Optional[str] = None
    wecom_secret: Optional[str] = None
    wecom_agent_id: Optional[str] = None
    wecom_redirect: Optional[str] = None


class McpServerCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    transport: Optional[str] = "http"
    url: Optional[str] = ""
    headers: Optional[str] = "{}"
    command: Optional[str] = ""
    args: Optional[str] = "[]"
    env: Optional[str] = "{}"
    mode: Optional[str] = "llm"
    enabled: Optional[int] = 1


class McpServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    transport: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[str] = None
    command: Optional[str] = None
    args: Optional[str] = None
    env: Optional[str] = None
    mode: Optional[str] = None
    enabled: Optional[int] = None


class McpToolOut(BaseModel):
    name: str
    description: str
    input_schema: dict


class McpServerOut(BaseModel):
    id: int
    name: str
    description: str
    transport: str
    url: str
    headers_masked: str
    command: str
    args: str
    env_set: bool
    mode: str
    enabled: int
    tools: list[McpToolOut] = []

    class Config:
        from_attributes = True


class McpServerPublic(BaseModel):
    id: int
    name: str
    description: str
    tool_count: int = 0


class SkillToolOut(BaseModel):
    name: str
    description: str
    command: str
    input_schema: dict


class SkillOut(BaseModel):
    id: int
    name: str
    description: str
    scope: str
    enabled: int
    tools: list[SkillToolOut] = []
    user_ids: list[int] = []

    class Config:
        from_attributes = True


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    enabled: Optional[int] = None
    user_ids: Optional[list[int]] = []


class SkillPublic(BaseModel):
    id: int
    name: str
    description: str
    tools: list[SkillToolOut] = []


class SkillTestRequest(BaseModel):
    tool: str
    args: dict = {}
