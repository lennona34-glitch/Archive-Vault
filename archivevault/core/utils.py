import os
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse

def format_size(num_bytes: int | float | None) -> str:
    """Format bytes into human-readable string (B, KB, MB, GB, TB)."""
    if num_bytes is None:
        return "Unknown"
    try:
        num = float(num_bytes)
    except (ValueError, TypeError):
        return "Unknown"
    
    if num < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if num < 1024.0 or unit == 'PB':
            if unit == 'B':
                return f"{num:.0f} {unit}"
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"

def format_speed(bytes_per_sec: float | None) -> str:
    """Format speed in bytes/sec into human-readable string."""
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "--"
    return f"{format_size(bytes_per_sec)}/s"

def format_eta(seconds: float | None) -> str:
    """Format ETA in seconds into human-readable format."""
    if seconds is None or seconds <= 0 or seconds > 86400 * 30:
        return "--"
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    mins, s = divmod(secs, 60)
    if mins < 60:
        return f"{mins}m {s:02d}s"
    hours, m = divmod(mins, 60)
    if hours < 24:
        return f"{hours}h {m:02d}m"
    days, h = divmod(hours, 24)
    return f"{days}d {h}h"

def sanitize_filename(filename: str) -> str:
    """Strip or replace invalid Windows filename characters."""
    # Windows forbidden characters: < > : " / \ | ? *
    clean = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Strip leading/trailing dots and spaces
    clean = clean.strip('. ')
    return clean or "unnamed_file"

def extract_identifier(input_str: str) -> str:
    """
    Extract IA identifier from a string which could be a raw identifier,
    or a URL like https://archive.org/details/{id} or https://archive.org/download/{id}/...
    """
    input_str = input_str.strip()
    if not input_str:
        return ""
    
    # Check if it's a URL
    if "archive.org" in input_str:
        parsed = urlparse(input_str)
        path = parsed.path.strip("/")
        parts = path.split("/")
        # Cases: details/IDENTIFIER or download/IDENTIFIER or metadata/IDENTIFIER
        if len(parts) >= 2 and parts[0] in ("details", "download", "metadata", "embed"):
            return parts[1]
        elif len(parts) == 1 and parts[0]:
            return parts[0]
            
    # Direct identifier check (alphanumeric, underscores, hyphens, periods)
    # Match clean identifier string
    match = re.match(r'^[a-zA-Z0-9_\-\.]+', input_str)
    if match:
        return match.group(0)
    return input_str

def open_containing_folder(file_path: str) -> bool:
    """Open the file's containing folder safely in Windows Explorer without freezing on huge sets."""
    abs_path = os.path.abspath(file_path)
    parent = os.path.dirname(abs_path) if os.path.isfile(abs_path) or not os.path.isdir(abs_path) else abs_path
    if not os.path.exists(parent):
        parent = os.path.dirname(parent)
    if os.path.exists(parent):
        try:
            if sys.platform == 'win32':
                os.startfile(parent)
            else:
                subprocess.Popen(['xdg-open', parent])
            return True
        except Exception:
            return False
    return False

def open_file(file_path: str) -> bool:
    """Open the file with its default Windows application."""
    abs_path = os.path.abspath(file_path)
    if os.path.exists(abs_path):
        try:
            if sys.platform == 'win32':
                os.startfile(abs_path)
            else:
                subprocess.Popen(['xdg-open', abs_path])
            return True
        except Exception:
            return False
    return False

def get_7zip_path() -> str | None:
    """Find 7-Zip File Manager executable if installed."""
    candidates = [
        r"C:\Program Files\7-Zip\7zFM.exe",
        r"C:\Program Files (x86)\7-Zip\7zFM.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def open_with_7zip(file_path: str) -> bool:
    """Open an archive with 7-Zip File Manager."""
    exe = get_7zip_path()
    if exe and os.path.exists(file_path):
        try:
            subprocess.Popen([exe, os.path.abspath(file_path)])
            return True
        except Exception:
            return False
    return False

def get_dosbox_path() -> str | None:
    """Find DOSBox or retro emulator executable on the user's system."""
    try:
        from archivevault.core.settings import settings
        if getattr(settings, "dosbox_path", None) and os.path.exists(settings.dosbox_path):
            return settings.dosbox_path
    except Exception:
        pass

    user_home = os.path.expanduser("~")
    candidates = [
        os.path.join(user_home, "LaunchBox", "ThirdParty", "DOSBox", "DOSBox.exe"),
        r"C:\Program Files\DOSBox-0.74-3\DOSBox.exe",
        r"C:\Program Files (x86)\DOSBox-0.74-3\DOSBox.exe",
        r"C:\Program Files\DOSBox-0.74\DOSBox.exe",
        r"C:\Program Files (x86)\DOSBox-0.74\DOSBox.exe",
        r"C:\Program Files\DOSBox\DOSBox.exe",
        r"C:\Program Files (x86)\DOSBox\DOSBox.exe",
        r"C:\DOSBox\DOSBox.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c

    for name in ["dosbox", "dosbox-x", "dosbox-staging"]:
        found = shutil.which(name)
        if found:
            return found
    return None

def launch_local_dosbox(file_path: str) -> bool:
    """Launch a local DOS game, executable, or directory in DOSBox."""
    exe = get_dosbox_path()
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        return False

    if exe and os.path.exists(exe):
        try:
            if os.path.isdir(abs_path):
                subprocess.Popen([exe, "-c", f'mount c "{abs_path}"', "-c", "c:"])
            elif abs_path.lower().endswith(('.exe', '.com', '.bat')):
                game_dir = os.path.dirname(abs_path)
                file_name = os.path.basename(abs_path)
                subprocess.Popen([exe, "-c", f'mount c "{game_dir}"', "-c", "c:", "-c", file_name])
            elif abs_path.lower().endswith('.conf'):
                subprocess.Popen([exe, "-conf", abs_path])
            else:
                game_dir = os.path.dirname(abs_path)
                subprocess.Popen([exe, "-c", f'mount c "{game_dir}"', "-c", "c:"])
            return True
        except Exception as e:
            print(f"[DOSBox] Launch error: {e}")
            return False
    return False

