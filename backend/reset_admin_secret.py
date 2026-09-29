"""命令行工具：清除后台随机地址设置。

开启「后台随机地址」后，只有携带正确 ?r= 参数才能访问后台。
如果忘记随机参数导致无法进入后台，可执行本脚本一键重置：
关闭随机后台地址开关并清空随机参数，之后可直接通过 /admin 访问。

用法（在 backend/ 目录下执行）::

    python reset_admin_secret.py

脚本会读取环境变量 DATABASE_URL（默认 sqlite:///./app.db），
与应用共用同一数据库。
"""

import sys

from app.common import get_setting
from app.database import get_sessionlocal

_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure:
    _reconfigure(encoding="utf-8")


def main() -> None:
    db = get_sessionlocal()()
    try:
        setting = get_setting(db)
        setting.admin_secret_enabled = 0
        setting.admin_secret = ""
        db.commit()
        db.refresh(setting)
        print("[OK] 已清除后台随机地址设置")
        print(f"   admin_secret_enabled = {setting.admin_secret_enabled}")
        print(f"   admin_secret         = {setting.admin_secret!r}")
        print("现在可直接访问 /admin 进入后台。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
