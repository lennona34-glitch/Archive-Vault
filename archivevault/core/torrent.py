"""
ArchiveVault Torrent Parser & Processor
Decodes standard bencoded BitTorrent files (.torrent) natively in pure Python without external dependencies,
extracts item identifiers, file hierarchies, and generates high-speed direct Archive.org HTTP resume download links.
"""

import os
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from archivevault.core.utils import format_size


def bdecode(data: bytes, idx: int = 0) -> Tuple[Any, int]:
    """
    Pure-Python recursive bencode parser.
    Decodes integers, byte strings, lists, and dictionaries.
    """
    if idx >= len(data):
        raise ValueError("Unexpected end of bencoded data")

    char = data[idx:idx + 1]

    # Integer: i<digits>e
    if char == b'i':
        end = data.index(b'e', idx)
        return int(data[idx + 1:end]), end + 1

    # List: l<items>e
    elif char == b'l':
        idx += 1
        items = []
        while data[idx:idx + 1] != b'e':
            val, idx = bdecode(data, idx)
            items.append(val)
        return items, idx + 1

    # Dictionary: d<key><value>e
    elif char == b'd':
        idx += 1
        d: Dict[str, Any] = {}
        while data[idx:idx + 1] != b'e':
            key, idx = bdecode(data, idx)
            if isinstance(key, bytes):
                key = key.decode('utf-8', errors='replace')
            val, idx = bdecode(data, idx)
            d[key] = val
        return d, idx + 1

    # Byte String: <length>:<bytes>
    elif char.isdigit():
        colon = data.index(b':', idx)
        length = int(data[idx:colon])
        start = colon + 1
        end = start + length
        return data[start:end], end

    else:
        raise ValueError(f"Invalid bencode byte: {char} at byte offset {idx}")


@dataclass
class TorrentFileEntry:
    path: str
    filename: str
    size_bytes: int
    size_formatted: str
    download_url: str
    extension: str


@dataclass
class TorrentMetadata:
    name: str
    identifier: str
    total_size: int
    total_size_formatted: str
    files: List[TorrentFileEntry] = field(default_factory=list)
    announce: str = ""
    comment: str = ""
    created_by: str = ""
    creation_date: Optional[str] = None
    piece_length: int = 0
    num_pieces: int = 0
    is_full_repository: bool = False


def parse_torrent_bytes(data: bytes) -> TorrentMetadata:
    """
    Parse a .torrent file's byte contents into structured TorrentMetadata.
    """
    meta, _ = bdecode(data)
    info = meta.get("info", {})

    raw_name = info.get("name", b"archive_torrent")
    name = raw_name.decode("utf-8", errors="replace") if isinstance(raw_name, bytes) else str(raw_name)

    # In Archive.org torrents, info['name'] is typically the item identifier
    identifier = name

    # Announce & Comment
    announce_raw = meta.get("announce", b"")
    announce = announce_raw.decode("utf-8", errors="replace") if isinstance(announce_raw, bytes) else str(announce_raw)

    comment_raw = meta.get("comment", b"")
    comment = comment_raw.decode("utf-8", errors="replace") if isinstance(comment_raw, bytes) else str(comment_raw)

    created_by_raw = meta.get("created by", b"")
    created_by = created_by_raw.decode("utf-8", errors="replace") if isinstance(created_by_raw, bytes) else str(created_by_raw)

    creation_date = None
    if "creation date" in meta:
        try:
            ts = meta["creation date"]
            creation_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    piece_len = info.get("piece length", 0)
    pieces = info.get("pieces", b"")
    num_pieces = len(pieces) // 20 if isinstance(pieces, bytes) else 0

    files_list: List[TorrentFileEntry] = []
    total_size = 0

    if "files" in info:
        # Multi-file torrent
        for f in info["files"]:
            length = f.get("length", 0)
            total_size += length

            raw_path_parts = f.get("path", [])
            path_parts = [
                p.decode("utf-8", errors="replace") if isinstance(p, bytes) else str(p)
                for p in raw_path_parts
            ]
            rel_path = "/".join(path_parts)
            fname = path_parts[-1] if path_parts else rel_path

            ext = os.path.splitext(fname)[1].lower()
            safe_path = urllib.parse.quote(rel_path, safe="/")
            dl_url = f"https://archive.org/download/{identifier}/{safe_path}"

            files_list.append(TorrentFileEntry(
                path=rel_path,
                filename=fname,
                size_bytes=length,
                size_formatted=format_size(length),
                download_url=dl_url,
                extension=ext
            ))
    else:
        # Single-file torrent
        length = info.get("length", 0)
        total_size = length
        ext = os.path.splitext(name)[1].lower()
        safe_name = urllib.parse.quote(name, safe="/")
        dl_url = f"https://archive.org/download/{identifier}/{safe_name}"

        files_list.append(TorrentFileEntry(
            path=name,
            filename=name,
            size_bytes=length,
            size_formatted=format_size(length),
            download_url=dl_url,
            extension=ext
        ))

    return TorrentMetadata(
        name=name,
        identifier=identifier,
        total_size=total_size,
        total_size_formatted=format_size(total_size),
        files=files_list,
        announce=announce,
        comment=comment,
        created_by=created_by,
        creation_date=creation_date,
        piece_length=piece_len,
        num_pieces=num_pieces
    )


def parse_torrent_file(file_path: str) -> TorrentMetadata:
    """Read and parse a .torrent file from local disk."""
    with open(file_path, "rb") as f:
        data = f.read()
    return parse_torrent_bytes(data)


def create_torrent_metadata_from_item(item_data: dict) -> TorrentMetadata:
    """
    Constructs a complete TorrentMetadata payload covering the entire Internet Archive repository.
    Used when the auto-generated .torrent file on Internet Archive is missing or incomplete (stale),
    ensuring 100% of all archive files (e.g. 40,000+ MAME ROMs) can be inspected, filtered,
    and downloaded in-app.
    """
    ident = item_data.get("identifier") or item_data.get("metadata", {}).get("identifier", "archive_item")
    name = item_data.get("title") or item_data.get("metadata", {}).get("title", ident)
    raw_files = item_data.get("files", [])

    entries: List[TorrentFileEntry] = []
    total_size = 0

    for f in raw_files:
        fname = f.get("name", "")
        if not fname:
            continue
        # Skip internal IA metadata derivatives that aren't content
        name_lower = fname.lower()
        if any(name_lower.endswith(ext) for ext in ('_files.xml', '_meta.xml', '_meta.sqlite', '.torrent', '.sha1', '.md5')):
            continue

        sz = int(f.get("size_bytes", f.get("size", 0)))
        total_size += sz

        safe_name = urllib.parse.quote(fname, safe="/")
        dl_url = f.get("url") or f"https://archive.org/download/{ident}/{safe_name}"
        ext = os.path.splitext(fname)[1].lower()
        base_name = os.path.basename(fname)

        entries.append(TorrentFileEntry(
            path=fname,
            filename=base_name,
            size_bytes=sz,
            size_formatted=format_size(sz),
            download_url=dl_url,
            extension=ext
        ))

    date_str = item_data.get("publicdate") or item_data.get("date") or None

    return TorrentMetadata(
        name=name,
        identifier=ident,
        total_size=total_size,
        total_size_formatted=format_size(total_size),
        files=entries,
        comment="Complete Multi-File Repository (Internet Archive)",
        creation_date=date_str,
        is_full_repository=True
    )

