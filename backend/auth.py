# -*- coding: utf-8 -*-
"""RSA授权验证 - 从旧项目迁移。"""
import time
import base64
import json
import subprocess
import platform
import uuid

PUBLIC_KEY_PEM = b"""-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEAnIeay5xAiYU0jlEkPAVzhq7uiVLbUqypQsaKRfZdFuZMJq/1oKq8
g+mN191mbBwTMHqiPCeoACIYDspGpofIMz14PvrVr54u5Gjv4S+Y5JfaN9hydLAj
q5nrhHLpKmnicY6sW5ElgL123+iy55E1DfYTGRJApvkhcbAKv8PG4LSLpokjBZxG
hq0tu9pizFpAoYULvxhdpZ49mstHJrGJxpLencgT+3mSvYP8LH/MbuBqsMs1ottp
Vlmt1hVyCwoXEeBTqSq+fbaI52lG0hqiv9gXiXW6Gf5fD05FXH1lJYowO0bylBSU
S7tgQXUtrQXaNBhL8fAmuF6DK7KBvO9GGwIDAQAB
-----END RSA PUBLIC KEY-----"""

MACHINE_PREFIX = "LA-"


class SecurityManager:
    def __init__(self):
        self.pubkey = None
        try:
            import rsa
            self.pubkey = rsa.PublicKey.load_pkcs1(PUBLIC_KEY_PEM)
        except Exception:
            pass

    def get_machine_id(self) -> str:
        sys_plat = platform.system().lower()
        machine_id = "UNKNOWN"
        try:
            if sys_plat == "windows":
                output = subprocess.check_output(
                    ["wmic", "csproduct", "get", "uuid"],
                    stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                ).decode("utf-8").strip().split("\n")
                if len(output) >= 2:
                    machine_id = output[1].strip()
            elif sys_plat == "darwin":
                output = subprocess.check_output(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]
                ).decode("utf-8")
                for line in output.split("\n"):
                    if "IOPlatformUUID" in line:
                        machine_id = line.split("=")[1].strip().strip('"')
                        break
            else:
                machine_id = str(uuid.getnode())
        except Exception:
            machine_id = str(uuid.getnode())

        clean_id = "".join(filter(str.isalnum, machine_id)).upper()
        return f"{MACHINE_PREFIX}{clean_id}"

    def verify_license(self, license_code: str) -> tuple[bool, str]:
        if not self.pubkey:
            return False, "系统缺失公钥，无法验证！"
        if not license_code:
            return False, "未输入授权码！"

        try:
            import rsa
            clean_code = "".join(license_code.split())
            parts = clean_code.split(".")
            if len(parts) != 2:
                return False, f"授权码格式不正确！"

            payload_bytes = base64.b64decode(parts[0])
            signature = base64.b64decode(parts[1])

            try:
                rsa.verify(payload_bytes, signature, self.pubkey)
            except rsa.VerificationError:
                return False, "签名验证失败！授权码可能被篡改或不完整。"

            payload = json.loads(payload_bytes.decode("utf-8"))
            target_machine = payload.get("m", "")
            exp_time = payload.get("e", 0)

            current_machine = self.get_machine_id()
            if target_machine != current_machine:
                return False, f"该授权码不适用于当前电脑！\n授权码机器: {target_machine}\n当前机器: {current_machine}"

            if int(time.time()) > exp_time:
                import datetime
                exp_str = datetime.datetime.fromtimestamp(exp_time).strftime("%Y-%m-%d")
                return False, f"授权已过期({exp_str})，请索取新的授权码。"

            return True, "验证成功"
        except Exception as e:
            return False, f"验证过程出错: {e}"

    def is_activated(self, license_code: str) -> bool:
        if not license_code:
            return False
        valid, _ = self.verify_license(license_code)
        return valid
