import json

from . import models


def _aliyun_send(setting: models.Setting, phone: str, code: str) -> None:
    from alibabacloud_dysmsapi20170525.client import Client as DysmsClient
    from alibabacloud_dysmsapi20170525 import models as sms_models
    from alibabacloud_tea_openapi import models as open_api_models

    config = open_api_models.Config(
        access_key_id=setting.sms_access_key_id,
        access_key_secret=setting.sms_secret,
    )
    config.endpoint = "dysmsapi.aliyuncs.com"
    client = DysmsClient(config)
    req = sms_models.SendSmsRequest(
        phone_numbers=phone,
        sign_name=setting.sms_sign_name,
        template_code=setting.sms_template_code,
        template_param=json.dumps({"code": code}),
    )
    resp = client.send_sms(req)
    body = resp.body
    if not body or body.code != "OK":
        raise RuntimeError(
            f"阿里云短信发送失败: {getattr(body, 'code', '')} {getattr(body, 'message', '')}"
        )


def _tencent_send(setting: models.Setting, phone: str, code: str) -> None:
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.sms.v20210111 import models as sms_models
    from tencentcloud.sms.v20210111 import sms_client

    cred = credential.Credential(setting.sms_access_key_id, setting.sms_secret)
    http_profile = HttpProfile(endpoint="sms.tencentcloudapi.com")
    client_profile = ClientProfile(http_profile=http_profile)
    client = sms_client.SmsClient(
        cred, setting.sms_region or "ap-guangzhou", client_profile
    )

    req = sms_models.SendSmsRequest()
    req.SmsSdkAppId = setting.sms_sdk_app_id
    req.SignName = setting.sms_sign_name
    req.TemplateId = setting.sms_template_code
    req.PhoneNumberSet = ["+86" + phone.lstrip("+")]
    req.TemplateParamSet = [code]
    resp = client.SendSms(req)

    status_set = resp.SendStatusSet or []
    if not status_set:
        raise RuntimeError("腾讯云短信发送失败: 无返回状态")
    status = status_set[0]
    if getattr(status, "Code", "") != "Ok":
        raise RuntimeError(
            f"腾讯云短信发送失败: {getattr(status, 'Code', '')} {getattr(status, 'Message', '')}"
        )


def send_sms(setting: models.Setting, phone: str, code: str) -> None:
    provider = (setting.sms_provider or "").lower()
    if provider == "aliyun":
        _aliyun_send(setting, phone, code)
    elif provider == "tencent":
        _tencent_send(setting, phone, code)
    else:
        raise RuntimeError("未配置短信服务商")
