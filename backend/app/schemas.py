from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class SMSRequest(BaseModel):
    phone: str
    captcha_id: Optional[str] = None
    captcha: Optional[str] = None
    lot_number: Optional[str] = None
    captcha_output: Optional[str] = None
    pass_token: Optional[str] = None
    gen_time: Optional[str] = None
    ticket: Optional[str] = None
    randstr: Optional[str] = None
    captcha_verify_param: Optional[str] = None


class SMSVerifyRequest(BaseModel):
    phone: str
    code: str


class DingtalkCodeRequest(BaseModel):
    code: str


class FeishuCodeRequest(BaseModel):
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
    scope: Optional[str] = "global"  # global / group
    system_prompt: Optional[str] = ""


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[str] = None
    enabled: Optional[int] = None
    is_default: Optional[int] = None
    scope: Optional[str] = None
    system_prompt: Optional[str] = None
    group_ids: Optional[list[int]] = None


class EndpointOut(BaseModel):
    id: int
    name: str
    base_url: str
    api_key_masked: str
    models: str
    enabled: int
    is_default: int
    scope: str = "global"
    system_prompt: str = ""
    group_ids: list[int] = []

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
    system_prompt: str = ""


class WecomUpdate(BaseModel):
    wecom_corp_id: Optional[str] = None
    wecom_secret: Optional[str] = None
    wecom_agent_id: Optional[str] = None
    wecom_redirect: Optional[str] = None
    system_prompt: Optional[str] = None


class DingtalkOut(BaseModel):
    app_key: str
    agent_id: str
    redirect: str
    app_secret_set: bool
    system_prompt: str = ""


class DingtalkUpdate(BaseModel):
    app_key: Optional[str] = None
    app_secret: Optional[str] = None
    agent_id: Optional[str] = None
    redirect: Optional[str] = None
    system_prompt: Optional[str] = None


class FeishuOut(BaseModel):
    app_id: str
    redirect: str
    app_secret_set: bool
    system_prompt: str = ""


class FeishuUpdate(BaseModel):
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    redirect: Optional[str] = None
    system_prompt: Optional[str] = None


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
    system_prompt: str = ""
    token_limit_daily: Optional[int] = None


class SystemUpdate(BaseModel):
    site_title: Optional[str] = None
    admin_secret_enabled: Optional[bool] = None
    admin_secret: Optional[str] = None
    assistant_name: Optional[str] = None
    system_prompt: Optional[str] = None
    token_limit_daily: Optional[int] = None


class SmsOut(BaseModel):
    provider: str
    access_key_id: str
    sign_name: str
    template_code: str
    region: str
    sdk_app_id: str
    secret_set: bool
    captcha_enabled: bool
    captcha_provider: str
    cooldown: int
    geetest_captcha_id: str
    geetest_key_set: bool
    tencent_captcha_app_id: str
    tencent_key_set: bool
    aliyun_access_key_id: str
    aliyun_secret_set: bool
    aliyun_scene_id: str


class SmsUpdate(BaseModel):
    provider: Optional[str] = None
    access_key_id: Optional[str] = None
    secret: Optional[str] = None
    sign_name: Optional[str] = None
    template_code: Optional[str] = None
    region: Optional[str] = None
    sdk_app_id: Optional[str] = None
    captcha_enabled: Optional[bool] = None
    captcha_provider: Optional[str] = None
    cooldown: Optional[int] = None
    geetest_captcha_id: Optional[str] = None
    geetest_captcha_key: Optional[str] = None
    tencent_captcha_app_id: Optional[str] = None
    tencent_captcha_app_secret_key: Optional[str] = None
    aliyun_access_key_id: Optional[str] = None
    aliyun_access_key_secret: Optional[str] = None
    aliyun_scene_id: Optional[str] = None


class SearchOut(BaseModel):
    provider: str
    base_url: str
    auto: bool
    api_key_set: bool
    scope: str = "global"
    group_ids: list[int] = []


class SearchUpdate(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    auto: Optional[bool] = None
    scope: Optional[str] = None
    group_ids: Optional[list[int]] = None


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
    scope: Optional[str] = "global"


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
    scope: Optional[str] = None
    group_ids: Optional[list[int]] = None


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
    scope: str = "global"
    group_ids: list[int] = []

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
    system_prompt: Optional[str] = ""


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
    system_prompt: Optional[str] = None


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
    system_prompt: str = ""

    class Config:
        from_attributes = True


class AdminUserOut(BaseModel):
    id: int
    nickname: str
    phone: Optional[str] = None
    platform: str = ""
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    created_at: datetime
    conversation_count: int
    last_active: Optional[datetime] = None
    total_tokens: int
    today_tokens: int
    token_limit_daily: Optional[int] = None
    token_limit_effective: Optional[int] = None


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
    scope: Optional[str] = "global"


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
    scope: Optional[str] = None
    group_ids: Optional[list[int]] = None


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
    scope: str = "global"
    group_ids: list[int] = []
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
    group_ids: list[int] = []

    class Config:
        from_attributes = True


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    enabled: Optional[int] = None
    user_ids: Optional[list[int]] = []
    group_ids: Optional[list[int]] = []


class SkillPublic(BaseModel):
    id: int
    name: str
    description: str
    tools: list[SkillToolOut] = []


class SkillTestRequest(BaseModel):
    tool: str
    args: dict = {}


class GroupGrantMap(BaseModel):
    endpoint: list[int] = []
    knowledge_base: list[int] = []
    mcp: list[int] = []
    search: list[int] = []
    skill: list[int] = []


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    member_ids: list[int] = []
    grants: GroupGrantMap = GroupGrantMap()


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    member_ids: Optional[list[int]] = None
    grants: Optional[GroupGrantMap] = None


class GroupOut(BaseModel):
    id: int
    name: str
    description: str
    member_ids: list[int] = []
    member_count: int = 0
    grants: GroupGrantMap = GroupGrantMap()

    class Config:
        from_attributes = True


class AgreementCreate(BaseModel):
    title: str
    content: str = ""
    enabled: int = 1
    required: int = 1


class AgreementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    enabled: Optional[int] = None
    required: Optional[int] = None


class AgreementOut(BaseModel):
    id: int
    title: str
    content: str
    enabled: int
    required: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgreementPublic(BaseModel):
    id: int
    title: str
    content: str
    required: int


class AgreeRequest(BaseModel):
    agreement_ids: list[int] = []


class AdminMe(BaseModel):
    username: str
    role: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None


class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    token_limit_daily: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    token_limit_daily: Optional[int] = None


class DepartmentOut(BaseModel):
    id: int
    name: str
    description: str
    member_count: int = 0
    admin_id: Optional[int] = None
    admin_username: Optional[str] = None
    token_limit_daily: Optional[int] = None
    created_at: datetime


class AdminCreate(BaseModel):
    username: str
    password: str
    role: str = "dept"
    department_id: Optional[int] = None


class AdminUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None


class AdminOut(BaseModel):
    id: int
    username: str
    role: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None


class AuditLogOut(BaseModel):
    id: int
    admin_username: str
    admin_role: str
    department_id: Optional[int] = None
    action: str
    target_type: str
    target_id: int
    summary: str
    ip: str
    user_agent: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditPage(BaseModel):
    total: int
    items: list[AuditLogOut]


class QuotaInfo(BaseModel):
    limit: Optional[int] = None
    used: int
    remaining: Optional[int] = None


class DbConfigIn(BaseModel):
    type: str
    path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    override: bool = False


class DbInfoOut(BaseModel):
    type: str
    database: str
    host: str
    port: str
    username: str
    configured: bool
    drivers: dict[str, bool]


class DbTestResult(BaseModel):
    ok: bool
    message: str
    dialect: str


class DbSwitchResult(BaseModel):
    ok: bool
    message: str
    dialect: str
    backup: Optional[dict] = None


class DbBackupResult(BaseModel):
    ok: bool
    message: str
    path: str = ""
