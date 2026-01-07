import sys
import time
import subprocess
from pathlib import Path

import requests


def download_installer(url: str, out_path: Path):
    """
    Baixa o instalador do GitHub Releases.
    """
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()

    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def main():
    # Espera receber a URL do instalador
    if len(sys.argv) < 2:
        print("Installer URL not provided")
        sys.exit(1)

    installer_url = sys.argv[1]

    # Pasta TEMP do usuário
    temp_dir = Path.home() / "AppData" / "Local" / "Temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    installer_path = temp_dir / "SekaiTranslator_Setup.exe"

    # Baixa o instalador
    try:
        download_installer(installer_url, installer_path)
    except Exception as e:
        print(f"Failed to download installer: {e}")
        sys.exit(1)

    # 🔒 Garante que o app principal já morreu completamente
    time.sleep(3)

    # Executa o instalador em modo UPDATE (sem desinstalar)
    try:
        subprocess.Popen(
            [
                str(installer_path),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
            ],
            shell=True,
        )
    except Exception as e:
        print(f"Failed to launch installer: {e}")
        sys.exit(1)

    # Sai do updater
    sys.exit(0)


if __name__ == "__main__":
    main()
