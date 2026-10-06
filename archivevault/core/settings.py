import configparser
import json
import os
import sys

DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "InternetArchive")

def get_app_data_dir() -> str:
    """Returns the persistent application configuration directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        app_dir = os.path.join(base, "ArchiveVault")
    else:
        app_dir = os.path.join(os.path.expanduser("~"), ".config", "archivevault")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

class Settings:
    """Application settings manager with persistence to disk."""
    
    def __init__(self):
        self.app_dir = get_app_data_dir()
        self.config_file = os.path.join(self.app_dir, "settings.json")
        self.queue_file = os.path.join(self.app_dir, "queue.json")
        
        # Default values
        self.s3_access_key: str = ""
        self.s3_secret_key: str = ""
        self.cookies: str = ""
        self.download_dir: str = DEFAULT_DOWNLOAD_DIR
        self.max_concurrent_downloads: int = 2
        self.chunk_size_kb: int = 256
        self.auto_resume_startup: bool = False
        self.create_item_subfolders: bool = True
        self.theme: str = "dark"
        self.dosbox_path: str = ""
        self.mame_path: str = ""
        
        self.load()
        self._check_and_import_ia_cli_config()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.s3_access_key = data.get("s3_access_key", self.s3_access_key)
                    self.s3_secret_key = data.get("s3_secret_key", self.s3_secret_key)
                    self.cookies = data.get("cookies", self.cookies)
                    self.download_dir = data.get("download_dir", self.download_dir)
                    self.max_concurrent_downloads = data.get("max_concurrent_downloads", self.max_concurrent_downloads)
                    self.chunk_size_kb = data.get("chunk_size_kb", self.chunk_size_kb)
                    self.auto_resume_startup = data.get("auto_resume_startup", self.auto_resume_startup)
                    self.create_item_subfolders = data.get("create_item_subfolders", self.create_item_subfolders)
                    self.theme = data.get("theme", self.theme)
                    self.dosbox_path = data.get("dosbox_path", self.dosbox_path)
                    self.mame_path = data.get("mame_path", self.mame_path)

                    # Auto-heal: If user pasted their 16-char S3 secret key into the Cookie field
                    if not self.s3_secret_key and self.cookies:
                        c_clean = self.cookies.strip()
                        if len(c_clean) == 16 and "=" not in c_clean and ";" not in c_clean and c_clean.isalnum():
                            print(f"[Settings] Auto-migrating 16-char S3 Secret Key from cookie field")
                            self.s3_secret_key = c_clean
                            self.cookies = ""
                            self.save()
            except Exception as e:
                print(f"[Settings] Error loading settings: {e}")

    def save(self):
        try:
            data = {
                "s3_access_key": self.s3_access_key,
                "s3_secret_key": self.s3_secret_key,
                "cookies": self.cookies,
                "download_dir": self.download_dir,
                "max_concurrent_downloads": self.max_concurrent_downloads,
                "chunk_size_kb": self.chunk_size_kb,
                "auto_resume_startup": self.auto_resume_startup,
                "create_item_subfolders": self.create_item_subfolders,
                "theme": self.theme,
                "dosbox_path": self.dosbox_path,
                "mame_path": self.mame_path
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Settings] Error saving settings: {e}")

    def _check_and_import_ia_cli_config(self):
        """Auto-import keys if user has configured the official ia CLI before."""
        if self.s3_access_key and self.s3_secret_key:
            return  # Already configured
            
        candidates = [
            os.path.join(os.path.expanduser("~"), ".ia"),
            os.path.join(os.path.expanduser("~"), ".config", "ia.ini"),
            os.path.join(os.environ.get("USERPROFILE", ""), ".ia")
        ]
        for c in candidates:
            if c and os.path.exists(c):
                try:
                    parser = configparser.ConfigParser()
                    parser.read(c)
                    if parser.has_section("s3"):
                        acc = parser.get("s3", "access", fallback="")
                        sec = parser.get("s3", "secret", fallback="")
                        if acc and sec:
                            self.s3_access_key = acc
                            self.s3_secret_key = sec
                            print(f"[Settings] Auto-imported IA credentials from {c}")
                            self.save()
                            break
                except Exception as e:
                    print(f"[Settings] Error inspecting IA config candidate {c}: {e}")

# Global singleton
settings = Settings()
