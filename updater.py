import sys
import subprocess
import requests
from pathlib import Path

import time

# depois de chamar o instalador
time.sleep(3)


def download_installer(url: str, out_path: Path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def main():
    if len(sys.argv) < 2:
        print("Installer URL not provided")
        sys.exit(1)

    installer_url = sys.argv[1]

    temp_dir = Path.home() / "AppData" / "Local" / "Temp"
    installer_path = temp_dir / "SekaiTranslator_Setup.exe"

    download_installer(installer_url, installer_path)

    # Executa o instalador
    subprocess.Popen(
        [str(installer_path)],
        shell=True,
    )


if __name__ == "__main__":
    main()

