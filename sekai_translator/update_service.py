import requests
from packaging.version import Version


# 🔴 TROQUE PELO SEU REPOSITÓRIO REAL
VERSION_URL = (
    "https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPO/main/version.json"
)


class UpdateInfo:
    def __init__(self, version: str, url: str):
        self.version = version
        self.url = url


class UpdateService:

    @staticmethod
    def check(current_version: str) -> UpdateInfo | None:
        try:
            r = requests.get(VERSION_URL, timeout=5)
            r.raise_for_status()
            data = r.json()

            latest = data.get("version")
            url = data.get("url")

            if not latest or not url:
                return None

            if Version(latest) > Version(current_version):
                return UpdateInfo(latest, url)

        except Exception:
            return None

        return None
