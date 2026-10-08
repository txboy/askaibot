# 方案：短信验证码可插拔（防刷）+ 后台配置

> 目标：防止机器人刷短信。发送短信前需通过验证码，并做发送间隔（默认 60 秒）冷却。
> 验证码**可插拔**：`builtin`（自建图形验证码）/ `geetest`（极验 v4）/ `tencent`（腾讯云天御）/ `aliyun`（阿里云验证码 2.0），在后台【短信设置页】由用户选择并配置密钥。

## 背景与现状

- `routers/auth.py` 的 `sms_send` 目前无验证码、无冷却，仅将验证码存入内存 `_sms_codes`（键=手机号，值 `{code, expires}`）。
- 项目已含 `tencentcloud-sdk-python`；`Pillow`、`alibabacloud_captcha20230305` 需新增。

## 已核实的第三方接口

- **极验 v4**：`POST http://gcaptcha4.geetest.com/validate?captcha_id=<id>`（form 参数：`lot_number`、`captcha_output`、`pass_token`、`gen_time`、`sign_token`）。`sign_token = HMAC-SHA256(captcha_key, lot_number).hexdigest()`。响应 `result=="success"` 即通过。
- **腾讯云（天御）**：`tencentcloud.captcha.v20221004` 客户端 `DescribeCaptchaResult`（`Ticket`、`Randstr`、`CaptchaAppId`、`CaptchaType`、`UserIp`），`CaptchaCode==0` 通过。
- **阿里云验证码 2.0**：`alibabacloud_captcha20230305` 的 `VerifyIntelligentCaptcha`（`CaptchaType`、`CaptchaVerifyParam`、`SceneId`），`Result.VerifyResult` 为真通过。
- 注：腾讯/阿里官方文档为 JS 渲染，字段名以实施时官方 SDK 生成代码为准。

---

## A. 数据模型（`models.Setting`）
新增列（`main.py._ensure_columns()` 同步加迁移）：
- `sms_captcha_enabled: int default 1`（验证码总开关）
- `sms_captcha_provider: str default 'builtin'`（`builtin|geetest|tencent|aliyun`）
- `sms_cooldown: int default 60`（发送间隔秒）
- 极验：`geetest_captcha_id`、`geetest_captcha_key`
- 腾讯：`tencent_captcha_app_id`、`tencent_captcha_app_secret_key`
- 阿里：`aliyun_captcha_access_key_id`、`aliyun_captcha_access_key_secret`、`aliyun_captcha_scene_id`

## B. 新增 `captcha.py`（可插拔，函数可打桩便于测试）
- `build_challenge(setting) -> dict`：按 `provider` 分派，返回前端初始化所需
  - `builtin` → `{type:'image', captcha_id, image_base64}`（Pillow 生成 4 位图，`_captchas[captcha_id]={code, expires}`，5 分钟过期）
  - `geetest` → `{type:'geetest', captcha_id}`
  - `tencent` → `{type:'tencent', app_id}`
  - `aliyun` → `{type:'aliyun', app_id, scene_id}`
- `verify(setting, payload) -> bool`：按 `provider` 分派
  - `builtin`：比对该图验证码（忽略大小写，一次性使用）
  - `geetest`：计算 `sign_token` 后调用上述校验接口
  - `tencent`：调用腾讯 TAT `DescribeCaptchaResult`
  - `aliyun`：调用阿里 `VerifyIntelligentCaptcha`

## C. `routers/auth.py`
- 新增 `_captchas: dict[str, dict]`（`captcha_id -> {code, expires}`）
- `GET /auth/captcha` → 返回 `captcha.build_challenge(setting)`
- 改造 `sms_send`，顺序：
  1. 若 `setting.sms_captcha_enabled`：取 payload 中 `provider` 对应验证字段 → `captcha.verify(setting, payload)`；失败抛 `HTTPException(400)`，前端刷新验证码
  2. 冷却：`_sms_codes[phone].sent_at` 距今 < `sms_cooldown` 秒 → 抛 `HTTPException(429)`「发送过于频繁」
  3. 生成验证码并写入 `_sms_codes[phone]`，含 `sent_at`
- `_sms_codes` 条目由 `{code, expires}` 变 `{code, expires, sent_at}`；`sent_at` 缺失视为无冷却历史（兼容旧测试）。`sms_verify` 成功仍 `pop`，登录后立即重发不设限。
- 发送失败（`send_sms` 抛错）仍 `pop` 相关条目，避免误锁。

## D. `schemas.py`
- `SMSRequest` 增可选项：`captcha_id`、`captcha`、`lot_number`、`captcha_output`、`pass_token`、`gen_time`、`ticket`、`randstr`、`captcha_verify_param`
- `SmsOut` 增：`captcha_enabled: bool`、`captcha_provider: str`、`cooldown: int`，及各厂商密钥 `*_set: bool`
- `SmsUpdate` 增对应可配字段（密钥留空不修改）

## E. `routers/admin.py` `_sms_out` / `update_sms`
透传 `captcha_enabled`、`captcha_provider`、`cooldown` 与各厂商密钥（`*_set` 标记）。

## F. `routers/uploads.py` `get_sms_enabled`
返回增加 `captcha_enabled`、`captcha_provider`、`cooldown`。

## G. 前端
- `api.js`：新增 `captcha()`；`adminGetSms`/`adminSaveSms` 读取/写入新字段。
- `Login.vue`（手机登录面板）：
  - 进入手机 tab 时 `GET /auth/captcha`，按 `type` 渲染：
    - `image`：显示验证码图 + 输入框，点击图片可刷新
    - `geetest/tencent/aliyun`：动态加载对应 SDK（`gt4.js` / `tcaptcha.js` / `AWSC.js`）并初始化，成功回调把结果存入状态
  - `sendCode` 携带对应验证字段；成功后启动 `cooldown` 秒倒计时，按钮置灰 `重新发送(Ns)`；验证失败刷新验证码。
- `Admin.vue`（`active==='sms'`）：「防刷设置」卡片——验证码开关、类型下拉（自建图片/极验/腾讯云/阿里云）、发送间隔（秒）、按类型条件显示密钥输入框（留空不修改）。

## H. 依赖
`requirements.txt` 新增：`Pillow>=10.0`、`alibabacloud_captcha20230305>=1.0.0`（`tencentcloud-sdk-python` 已有）。

## I. 测试
- `test_captcha_builtin.py`：`GET /auth/captcha` 返回图/ID；`sms_send` 开关验证码；无/错验证码 400；验证码一次性使用；冷却 429、超时可发、验证成功重置；关闭验证码时免验证码。
- `test_captcha_geetest.py`：mock httpx 校验调用，断言 `sign_token`（HMAC-SHA256）与参数、success/fail 分支。
- `test_captcha_tencent_aliyun.py`：mock 厂商 SDK 调用边界，断言正确分发。
- 兼容 `test_profile.py`（直接写 `_sms_codes`，仍读 `code/expires`）。

## 关于字体（builtin 图形验证码路径）

- **避免** Arial/Calibri/Times 等系统常用字体；**捆绑一个 OCR 区分度高的免费 TTF**（如 DejaVu Sans 变形版 / Bungee / captcha 库字体），并随机在 2~3 个字体间轮换。
- 关键在 **Pillow `Image.transform`（PERSPECTIVE/QUAD）透视扭曲 + 随机弧线噪声 + 随机大小/旋转**；字体只是其中一环。真正强防御仍建议切第三方滑块验证码。

## 开放项 / 风险（实现时确认）

- 腾讯/阿里官方校验文档为 JS 渲染，其 SDK 的精确字段与调用方式需实现时按官方生成代码核对。
- 前端 SDK 动态加载在无对应厂商密钥 / 无法访问外网的离线环境会退化或无法初始化（此时建议配置为 builtin）。
