import os
import re
import shutil
import subprocess
import sys
import zipfile
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

def get_launchbox_path() -> str | None:
    """Find LaunchBox executable if installed on the user's system."""
    user_home = os.path.expanduser("~")
    candidates = [
        os.path.join(user_home, "LaunchBox", "LaunchBox.exe"),
        r"C:\Users\adria\LaunchBox\LaunchBox.exe",
        r"C:\LaunchBox\LaunchBox.exe",
        r"C:\Program Files\LaunchBox\LaunchBox.exe",
        r"C:\Program Files (x86)\LaunchBox\LaunchBox.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def launch_launchbox(rom_path: str | None = None) -> bool:
    """Launch LaunchBox frontend, optionally pointing to a ROM file."""
    exe = get_launchbox_path()
    if exe and os.path.exists(exe):
        try:
            if rom_path and os.path.exists(rom_path):
                subprocess.Popen([exe, os.path.abspath(rom_path)])
            else:
                subprocess.Popen([exe])
            return True
        except Exception:
            return False
    return False

def get_dosbox_info() -> dict:
    """Return detailed metadata about the DOSBox installation and its origin."""
    try:
        from archivevault.core.settings import settings
        saved = getattr(settings, "dosbox_path", "").strip()
        if saved.lower() == "disabled":
            return {"path": None, "source": "Disabled", "is_launchbox": False, "launchbox_path": get_launchbox_path()}
        if saved and os.path.exists(saved):
            is_lb = "launchbox" in saved.lower()
            return {"path": saved, "source": "LaunchBox" if is_lb else "Custom", "is_launchbox": is_lb, "launchbox_path": get_launchbox_path()}
    except Exception:
        pass

    user_home = os.path.expanduser("~")
    candidates = [
        (os.path.join(user_home, "LaunchBox", "ThirdParty", "DOSBox", "DOSBox.exe"), "LaunchBox"),
        (r"C:\Users\adria\LaunchBox\ThirdParty\DOSBox\DOSBox.exe", "LaunchBox"),
        (r"C:\Program Files\DOSBox-0.74-3\DOSBox.exe", "System"),
        (r"C:\Program Files (x86)\DOSBox-0.74-3\DOSBox.exe", "System"),
        (r"C:\Program Files\DOSBox-0.74\DOSBox.exe", "System"),
        (r"C:\Program Files (x86)\DOSBox-0.74\DOSBox.exe", "System"),
        (r"C:\Program Files\DOSBox\DOSBox.exe", "System"),
        (r"C:\Program Files (x86)\DOSBox\DOSBox.exe", "System"),
        (r"C:\DOSBox\DOSBox.exe", "System"),
    ]
    for c, src in candidates:
        if c and os.path.exists(c):
            return {"path": c, "source": src, "is_launchbox": (src == "LaunchBox"), "launchbox_path": get_launchbox_path()}

    for name in ["dosbox", "dosbox-x", "dosbox-staging"]:
        found = shutil.which(name)
        if found:
            return {"path": found, "source": "System (PATH)", "is_launchbox": False, "launchbox_path": get_launchbox_path()}

    return {"path": None, "source": "Not Found", "is_launchbox": False, "launchbox_path": get_launchbox_path()}

def get_dosbox_path() -> str | None:
    """Find DOSBox or retro emulator executable on the user's system."""
    info = get_dosbox_info()
    return info.get("path")

def get_dosbox_custom_conf_path() -> str:
    """Generate or retrieve a high-resolution scaled configuration for DOSBox (1280x960 4:3 normal3x)."""
    user_home = os.path.expanduser("~")
    app_dir = os.path.join(user_home, ".archivevault")
    os.makedirs(app_dir, exist_ok=True)
    conf_path = os.path.join(app_dir, "dosbox_scaled.conf")

    conf_content = """# ArchiveVault High-Resolution Scaled DOSBox Configuration
[sdl]
fullscreen=false
fulldouble=false
fullresolution=desktop
windowresolution=1280x960
output=overlay
autolock=true
sensitivity=100
waitonerror=true
priority=higher,normal

[dosbox]
language=
machine=svga_s3
captures=capture
memsize=32

[render]
frameskip=0
aspect=true
scaler=normal3x

[cpu]
core=auto
cputype=auto
cycles=auto
cycleup=1000
cycledown=1000

[mixer]
nosound=false
rate=44100
blocksize=1024
prebuffer=20

[midi]
mpu401=intelligent
mididevice=default

[sblaster]
sbtype=sb16
sbbase=220
irq=7
dma=1
hdma=5
sbmixer=true
oplmode=auto
oplemu=default
oplrate=44100

[gus]
gus=false

[speaker]
pcspeaker=true
pcrate=44100
tandy=auto
disney=true

[joystick]
joysticktype=auto
timed=true
autofire=false
swap34=false
buttonwrap=false

[dos]
xms=true
ems=true
umb=true
keyboardlayout=auto

[autoexec]
# Auto-generated by ArchiveVault
"""
    try:
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(conf_content)
    except Exception as e:
        print(f"[DOSBox] Could not write scaled config: {e}")
    return conf_path

def find_dos_executable(directory: str) -> str | None:
    """Find the most likely executable to start a DOS game inside a folder."""
    preferred_names = [
        "play.bat", "run.bat", "start.bat", "go.bat", "game.bat",
        "play.exe", "run.exe", "start.exe", "game.exe", "main.exe",
        "doom.exe", "wolf3d.exe", "duke3d.exe", "prince.exe", "keen.exe", "civ.exe",
        "play.com", "run.com", "start.com", "game.com"
    ]
    ignore_names = {"setup.exe", "install.exe", "setsound.exe", "sound.exe", "sndsetup.exe", "config.exe"}

    files_in_dir = []
    for root, _, files in os.walk(directory):
        for f in files:
            files_in_dir.append((f, os.path.relpath(os.path.join(root, f), directory)))

    # 1. Exact match with preferred game executables
    for pref in preferred_names:
        for fname, rel_p in files_in_dir:
            if fname.lower() == pref:
                return rel_p

    # 2. Look for batch scripts
    for fname, rel_p in files_in_dir:
        if fname.lower().endswith('.bat') and fname.lower() not in ignore_names:
            return rel_p

    # 3. Look for COM executables
    for fname, rel_p in files_in_dir:
        if fname.lower().endswith('.com') and fname.lower() not in ignore_names:
            return rel_p

    # 4. Look for EXE executables
    for fname, rel_p in files_in_dir:
        if fname.lower().endswith('.exe') and fname.lower() not in ignore_names:
            return rel_p

    # 5. Any executable
    for fname, rel_p in files_in_dir:
        if fname.lower().endswith(('.exe', '.com', '.bat')):
            return rel_p

    return None

def extract_dos_zip(zip_path: str) -> str:
    """Extract a DOS zip archive into a dedicated cache folder for execution."""
    user_home = os.path.expanduser("~")
    base_name = os.path.splitext(os.path.basename(zip_path))[0]
    safe_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_")).strip() or "game"
    extract_dir = os.path.join(user_home, ".archivevault", "dos_games", safe_name)
    os.makedirs(extract_dir, exist_ok=True)

    # If empty or not yet extracted
    if not os.listdir(extract_dir):
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

    return extract_dir

def launch_local_dosbox(file_path: str) -> bool:
    """Launch a local DOS game, executable, or directory in high-resolution scaled DOSBox."""
    exe = get_dosbox_path()
    if not exe or not os.path.exists(exe):
        return False

    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        return False

    conf_path = get_dosbox_custom_conf_path()

    try:
        if os.path.isdir(abs_path):
            exe_target = find_dos_executable(abs_path)
            cmd = [exe, "-conf", conf_path, "-c", f'mount c "{abs_path}"', "-c", "c:"]
            if exe_target:
                cmd.extend(["-c", exe_target])
            else:
                cmd.extend(["-c", "dir /w"])
            subprocess.Popen(cmd)
            return True

        elif abs_path.lower().endswith(('.exe', '.com', '.bat')):
            game_dir = os.path.dirname(abs_path)
            file_name = os.path.basename(abs_path)
            subprocess.Popen([
                exe,
                "-conf", conf_path,
                "-c", f'mount c "{game_dir}"',
                "-c", "c:",
                "-c", file_name
            ])
            return True

        elif abs_path.lower().endswith('.zip'):
            # Extract DOS zip to dedicated game folder and launch primary executable
            try:
                extract_dir = extract_dos_zip(abs_path)
                exe_target = find_dos_executable(extract_dir)
                cmd = [exe, "-conf", conf_path, "-c", f'mount c "{extract_dir}"', "-c", "c:"]
                if exe_target:
                    cmd.extend(["-c", exe_target])
                else:
                    cmd.extend(["-c", "dir /w"])
                subprocess.Popen(cmd)
                return True
            except Exception as ex:
                print(f"[DOSBox] Error unzipping game: {ex}")
                game_dir = os.path.dirname(abs_path)
                subprocess.Popen([exe, "-conf", conf_path, "-c", f'mount c "{game_dir}"', "-c", "c:"])
                return True

        elif abs_path.lower().endswith('.conf'):
            subprocess.Popen([exe, "-conf", abs_path])
            return True

        else:
            game_dir = os.path.dirname(abs_path)
            subprocess.Popen([exe, "-conf", conf_path, "-c", f'mount c "{game_dir}"', "-c", "c:"])
            return True

    except Exception as e:
        print(f"[DOSBox] Launch error: {e}")
        return False


