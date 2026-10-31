import html
import os
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple
import requests

from archivevault.core.settings import settings
from archivevault.core.utils import format_size

USER_AGENT = "ArchiveVault/1.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

class ArchiveSession(requests.Session):
    """
    Custom requests.Session that preserves Internet Archive Authorization headers
    across cross-host 302 redirects (e.g. archive.org -> dn*.ca.archive.org or ia*.us.archive.org).
    Standard requests strips the Authorization header on any hostname change.
    """
    def rebuild_auth(self, prepared_request, response):
        super().rebuild_auth(prepared_request, response)
        url = (prepared_request.url or "").lower()
        if "archive.org" in url:
            access = settings.s3_access_key.strip()
            secret = settings.s3_secret_key.strip()
            if access and secret:
                prepared_request.headers["Authorization"] = f"LOW {access}:{secret}"
            if settings.cookies.strip():
                prepared_request.headers["Cookie"] = settings.cookies.strip()

class InternetArchiveAPI:
    """Client for interacting with the Internet Archive Search, Metadata, and Download APIs."""
    
    BASE_URL = "https://archive.org"
    SEARCH_URL = f"{BASE_URL}/advancedsearch.php"
    METADATA_URL = f"{BASE_URL}/metadata"
    DOWNLOAD_URL = f"{BASE_URL}/download"
    IMG_URL = f"{BASE_URL}/services/img"
    S3_URL = "https://s3.us.archive.org"

    def __init__(self):
        self.session = ArchiveSession()

    def get_session(self) -> requests.Session:
        return self.session

    def get_headers(self, custom_access: str = "", custom_secret: str = "", custom_cookie: str = "") -> Dict[str, str]:
        """Construct headers with User-Agent and authentication (S3 keys and/or cookies)."""
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
        
        access = custom_access or settings.s3_access_key
        secret = custom_secret or settings.s3_secret_key
        cookie = custom_cookie or settings.cookies
        
        if access and secret:
            headers["Authorization"] = f"LOW {access.strip()}:{secret.strip()}"
            
        if cookie:
            headers["Cookie"] = cookie.strip()
            
        return headers

    @staticmethod
    def build_smart_query(
        query: str,
        mediatype: Optional[str] = None,
        filter_mode: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Transform a natural user search or Lucene query into a high-precision
        Internet Archive Solr query, expanding retro platforms, vintage records,
        and multi-word titles while filtering out web-crawl and replay spam.
        """
        q = query.strip() if query else ""
        effective_mediatype = mediatype
        effective_filter = filter_mode

        # Unwrap legacy filter wrappers if passed inline (e.g. "(atari st) AND NOT mediatype:collection")
        if q:
            m_not_col = re.match(r"^\(([^:()]+)\)\s+AND\s+NOT\s+mediatype:collection$", q, flags=re.IGNORECASE)
            if m_not_col:
                q = m_not_col.group(1).strip()
                if not effective_filter:
                    effective_filter = "media_only"
            else:
                m_only_col = re.match(r"^\(([^:()]+)\)\s+AND\s+mediatype:collection$", q, flags=re.IGNORECASE)
                if m_only_col:
                    q = m_only_col.group(1).strip()
                    if not effective_filter:
                        effective_filter = "collections_only"

        # Detect whether user explicitly entered advanced Lucene syntax
        has_lucene_syntax = bool(
            re.search(r"\b(collection|title|mediatype|creator|subject|identifier|year|date|format|description|language):", q, flags=re.IGNORECASE)
            or re.search(r"\s+(AND|OR|NOT)\s+", q)
            or '"' in q
            or "[" in q
        )

        if q and not has_lucene_syntax:
            q_lower = q.lower()

            # 1. Smart query expansion for vintage records, 78rpm, and vinyl audio
            record_triggers = [
                "old records", "old record", "vintage records", "vintage record",
                "vinyl records", "vinyl record", "78rpm", "78 rpm", "antique records",
                "shellac records", "phonograph records"
            ]
            is_record_search = any(trig in q_lower for trig in record_triggers) or q_lower in ("records", "record", "vinyl")
            if is_record_search:
                residual = q_lower
                for trig in record_triggers:
                    residual = residual.replace(trig, " ")
                residual = residual.replace("records", " ").replace("record", " ").replace("vinyl", " ").strip()

                base_coll = "collection:(georgeblood OR 78rpm OR 78rpm_unfiltered OR album_recordings OR vinylrecords) AND NOT mediatype:collection"
                if residual:
                    res_words = [w for w in re.findall(r"[a-z0-9]+", residual) if w]
                    if res_words:
                        res_and = " AND ".join(res_words)
                        q = f"({base_coll}) AND (title:({res_and}) OR creator:({res_and}) OR subject:({res_and}))"
                    else:
                        q = base_coll
                else:
                    q = base_coll

                if not effective_mediatype or effective_mediatype.lower() == "all":
                    effective_mediatype = "audio"
                has_lucene_syntax = True

        if q and not has_lucene_syntax:
            q_lower = re.sub(r"\s+", " ", q.lower()).strip()

            # 2. Smart Retro Platform, Arcade & ROM Set Expansion
            platform_rules = [
                (
                    ["atari st", "atarist", "atari ste", "atari falcon"],
                    "(collection:(softwarelibrary_atari_st_games OR softwarelibrary_atarist) OR title:(atari AND st))",
                    "software"
                ),
                (
                    ["atari 2600", "atari 7800", "atari 800", "atari xl", "atari xe"],
                    "(collection:(consolelivingroom_atari2600 OR consolelivingroom_atari7800 OR softwarelibrary_atari) OR title:(atari AND (2600 OR 7800 OR 800)))",
                    "software"
                ),
                (
                    ["commodore amiga", "amiga cd32", "amiga 500", "amiga 1200", "amiga"],
                    "(collection:(softwarelibrary_amiga_games OR softwarelibrary_amiga) OR title:amiga)",
                    None
                ),
                (
                    ["zx spectrum", "sinclair spectrum", "sinclair zx", "spectrum games", "zx81"],
                    "(collection:softwarelibrary_zx_spectrum OR title:(zx AND spectrum))",
                    "software"
                ),
                (
                    ["commodore 64", "c64", "c-64", "vic-20", "vic20"],
                    "(collection:softwarelibrary_c64 OR title:(c64 OR commodore))",
                    "software"
                ),
                (
                    ["amstrad cpc", "amstrad 464", "amstrad 6128", "amstrad"],
                    "(collection:softwarelibrary_cpc OR title:amstrad)",
                    "software"
                ),
                (
                    ["ms-dos", "msdos", "dos games", "pc dos"],
                    "(collection:softwarelibrary_msdos_games OR title:msdos)",
                    "software"
                ),
                (
                    ["mame roms", "mame romset", "mame reference", "mame chd", "mame"],
                    "(title:mame AND mediatype:software)",
                    "software"
                ),
                (
                    ["internet arcade", "arcade games", "coin-op", "arcade"],
                    "(collection:internetarcade OR (title:arcade AND mediatype:software))",
                    "software"
                ),
                (
                    ["tosec"],
                    "(collection:tosec OR title:tosec)",
                    "software"
                ),
                (
                    ["no-intro", "nointro", "romset", "rom sets", "rom pack", "rom packs"],
                    "(identifier:(ni-romsets OR retro-roms-best-set OR tiny-best-set-go) OR title:(nointro OR romset OR \"rom set\" OR \"best set\"))",
                    "software"
                ),
                (
                    ["sega genesis", "mega drive", "megadrive"],
                    "(collection:sega_genesis_library OR title:(genesis OR \"mega drive\"))",
                    "software"
                ),
                (
                    ["scummvm"],
                    "(title:scummvm OR subject:scummvm)",
                    "software"
                ),
            ]

            matched_clause = None
            suggested_mt = None
            residual = q_lower
            padded = f" {q_lower} "

            for triggers, clause, def_mt in platform_rules:
                for trig in triggers:
                    if f" {trig} " in padded:
                        matched_clause = clause
                        suggested_mt = def_mt
                        residual = padded.replace(f" {trig} ", " ", 1).strip()
                        break
                if matched_clause:
                    break

            if matched_clause:
                # Check if user asked for games/roms specifically or manuals/magazines
                filler_words = {"games", "game", "roms", "rom", "files", "pack", "collection", "archive"}
                raw_res_tokens = [w for w in re.findall(r"[a-z0-9]+", residual) if w]
                wants_software = any(w in ("games", "game", "roms", "rom") for w in raw_res_tokens)
                wants_texts = any(w in ("magazine", "magazines", "manual", "manuals", "book", "books") for w in raw_res_tokens)

                clean_res_tokens = [w for w in raw_res_tokens if w not in filler_words]
                stop_words = {"the", "of", "and", "in", "on", "for", "to", "a", "an"}
                if len(clean_res_tokens) > 1:
                    filtered_res = [w for w in clean_res_tokens if w not in stop_words]
                    if filtered_res:
                        clean_res_tokens = filtered_res

                if clean_res_tokens:
                    and_expr = " AND ".join(clean_res_tokens)
                    q = f"({matched_clause}) AND (title:({and_expr}) OR identifier:({and_expr}))"
                else:
                    q = matched_clause

                if not effective_mediatype or effective_mediatype.lower() == "all":
                    if wants_texts:
                        effective_mediatype = "texts"
                    elif wants_software or suggested_mt:
                        effective_mediatype = suggested_mt or "software"

                has_lucene_syntax = True

        if q and not has_lucene_syntax:
            # 3. General Multi-Word / Single-Word High-Precision Search
            tokens = [w for w in re.findall(r"[a-zA-Z0-9]+", q.lower()) if w]
            stop_words = {"the", "of", "and", "in", "on", "for", "to", "a", "an"}
            if len(tokens) > 1:
                non_stop = [w for w in tokens if w not in stop_words]
                if non_stop:
                    tokens = non_stop

            if tokens:
                and_expr = " AND ".join(tokens)
                if effective_filter == "collections_only":
                    q = f"(title:({and_expr}) OR identifier:({and_expr}) OR subject:({and_expr}))"
                else:
                    q = f"(title:({and_expr}) OR identifier:({and_expr}) OR creator:({and_expr}))"
            else:
                q = f"({q})"

        # Assemble final query parts
        parts = [q if q else "*"]

        if effective_mediatype and effective_mediatype.lower() != "all":
            if f"mediatype:{effective_mediatype.lower()}" not in q.lower() and f"mediatype:({effective_mediatype.lower()}" not in q.lower():
                parts.append(f"mediatype:({effective_mediatype.lower()})")

        if effective_filter == "collections_only":
            if "mediatype:collection" not in q.lower():
                parts.append("mediatype:collection")
        elif effective_filter == "media_only":
            if "mediatype:collection" not in q.lower():
                parts.append("NOT mediatype:(collection OR web OR data)")
        else:
            # Always exclude raw WARC web crawls and internal data blobs unless explicitly requested
            if "mediatype:web" not in q.lower() and "mediatype:(collection or web" not in q.lower():
                parts.append("NOT mediatype:(web OR data)")

        # Exclude automated Fightcade replay spam unless user explicitly searched fightcade
        if "fightcade" not in q.lower():
            parts.append("NOT collection:Fightcade-Archive")

        final_query = " AND ".join(parts) if parts else "*"
        return final_query, effective_mediatype

    def search(
        self,
        query: str,
        mediatype: Optional[str] = None,
        sort: Optional[str] = "-downloads",
        page: int = 1,
        rows: int = 30,
        filter_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search Internet Archive items.
        
        :param query: Search keywords or lucene query
        :param mediatype: 'software', 'movies', 'audio', 'texts', 'image', or None for all
        :param sort: Sort field, e.g. '-downloads', '-publicdate', 'titleSorter asc', or '' for relevance
        :param page: Page number (1-indexed)
        :param rows: Items per page
        :param filter_mode: 'media_only', 'collections_only', or 'all'
        :return: Dict containing total_count, docs list, page, rows
        """
        final_query, effective_mediatype = self.build_smart_query(
            query=query,
            mediatype=mediatype,
            filter_mode=filter_mode
        )
        
        params: Dict[str, Any] = {
            "q": final_query,
            "fl[]": [
                "identifier",
                "title",
                "mediatype",
                "year",
                "downloads",
                "creator",
                "publicdate"
            ],
            "rows": rows,
            "page": page,
            "output": "json"
        }
        if sort is None:
            params["sort[]"] = "-downloads"
        elif sort and sort != "relevance":
            params["sort[]"] = sort

        data = self._execute_search_request(params)
        response_obj = data.get("response", {})
        total_count = response_obj.get("numFound", 0)

        # Automatic broad fallback if strict title/identifier/creator query returned 0 hits on a natural query
        if total_count == 0 and query and ":" not in query:
            tokens = [w for w in re.findall(r"[a-zA-Z0-9]+", query.lower()) if w]
            if tokens:
                and_expr = " AND ".join(tokens)
                fallback_parts = [
                    f"(title:({and_expr}) OR subject:({and_expr}) OR description:({and_expr}))",
                    "NOT mediatype:(web OR data)",
                    "NOT collection:Fightcade-Archive"
                ]
                if effective_mediatype and effective_mediatype.lower() != "all":
                    fallback_parts.append(f"mediatype:({effective_mediatype.lower()})")
                if filter_mode == "media_only":
                    fallback_parts.append("NOT mediatype:collection")
                elif filter_mode == "collections_only":
                    fallback_parts.append("mediatype:collection")
                params["q"] = " AND ".join(fallback_parts)
                data = self._execute_search_request(params)
                response_obj = data.get("response", {})
                total_count = response_obj.get("numFound", 0)

        raw_docs = response_obj.get("docs", [])
        
        # Known spam / broken / adult test identifiers to keep default feeds clean
        blocked_ids = {
            "sex_madness",
            "dr.sex",
            "hisnewjobcharleschaplin-1915",
            "johnnyabbotssexadventuresi",
            "porno_mine_2_1994_de_bond_emc-gb",
            "diagnostic_test_cartridge_1984_atari_ntsc",
        }

        cleaned_docs = []
        for doc in raw_docs:
            ident = doc.get("identifier", "")
            if not ident or ident.lower() in blocked_ids:
                continue
                
            title = doc.get("title", ident)
            if isinstance(title, list):
                title = title[0] if title else ident
            # Clean html tags from description if present
            desc = doc.get("description", "")
            if isinstance(desc, list):
                desc = " ".join(desc)
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = html.unescape(desc).strip()
            if len(desc) > 300:
                desc = desc[:297] + "..."
                
            creator = doc.get("creator", "")
            if isinstance(creator, list):
                creator = ", ".join(creator)
                
            cleaned_docs.append({
                "identifier": ident,
                "title": title or ident,
                "mediatype": doc.get("mediatype", "unknown"),
                "year": str(doc.get("year", "") or ""),
                "downloads": doc.get("downloads", 0),
                "description": desc,
                "creator": creator,
                "thumbnail_url": f"{self.IMG_URL}/{ident}",
                "details_url": f"{self.BASE_URL}/details/{ident}"
            })
            
        return {
            "total_count": total_count,
            "docs": cleaned_docs,
            "page": page,
            "rows": rows
        }

    def _execute_search_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        last_error = None
        data = None
        for attempt in range(2):
            try:
                resp = self.session.get(
                    self.SEARCH_URL,
                    params=params,
                    headers=self.get_headers(),
                    timeout=35
                )
                if resp.status_code in (502, 503, 504) and attempt == 0:
                    time.sleep(1.5)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except (requests.exceptions.RequestException, ValueError) as e:
                last_error = e
                if attempt == 0:
                    time.sleep(1.5)
                    continue
                print(f"[IA API] Search error: {e}")
                raise RuntimeError(f"Archive.org search is busy or timed out: {e}")
        if data is None:
            raise RuntimeError(f"Archive.org search request failed: {last_error}")
        return data

    def get_item_metadata(self, identifier: str) -> Dict[str, Any]:
        """
        Fetch full item metadata and file list for an identifier.
        """
        ident = identifier.strip()
        url = f"{self.METADATA_URL}/{ident}"
        
        try:
            resp = self.session.get(url, headers=self.get_headers(), timeout=25)
            resp.raise_for_status()
            data = resp.json()
            
            if not data or not isinstance(data, dict):
                raise ValueError(f"Item '{ident}' not found or returned empty data.")
                
            raw_meta = data.get("metadata", {})
            raw_files = data.get("files", [])
            
            # Extract basic info
            title = raw_meta.get("title", ident)
            if isinstance(title, list):
                title = title[0]
                
            desc = raw_meta.get("description", "")
            if isinstance(desc, list):
                desc = "\n".join(desc)
            desc = re.sub(r'<br\s*/?>', '\n', desc, flags=re.IGNORECASE)
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = html.unescape(desc).strip()
            
            creator = raw_meta.get("creator", "")
            if isinstance(creator, list):
                creator = ", ".join(creator)
                
            date = str(raw_meta.get("date", "") or raw_meta.get("publicdate", "") or "")
            mediatype = raw_meta.get("mediatype", "data")
            collections = raw_meta.get("collection", [])
            if isinstance(collections, str):
                collections = [collections]
                
            # Process files
            files = []
            total_size_bytes = 0
            
            for f in raw_files:
                fname = f.get("name", "")
                if not fname:
                    continue
                    
                try:
                    fsize = int(f.get("size", 0))
                except (ValueError, TypeError):
                    fsize = 0
                    
                total_size_bytes += fsize
                
                # Direct download link (properly quoted for spaces/special chars)
                encoded_name = urllib.parse.quote(fname)
                download_url = f"{self.DOWNLOAD_URL}/{ident}/{encoded_name}"
                
                fmt = f.get("format", "")
                source = f.get("source", "original") # 'original' vs 'derivative'
                
                files.append({
                    "name": fname,
                    "size_bytes": fsize,
                    "size_formatted": format_size(fsize),
                    "format": fmt or self._guess_format(fname),
                    "source": source,
                    "download_url": download_url,
                    "md5": f.get("md5", ""),
                    "crc32": f.get("crc32", ""),
                    "sha1": f.get("sha1", ""),
                    "mtime": f.get("mtime", "")
                })
                
            # Sort files: originals first, then by name
            files.sort(key=lambda x: (0 if x["source"] == "original" else 1, x["name"].lower()))
            
            return {
                "identifier": ident,
                "title": title or ident,
                "description": desc,
                "creator": creator,
                "date": date,
                "mediatype": mediatype,
                "collections": collections,
                "thumbnail_url": f"{self.IMG_URL}/{ident}",
                "details_url": f"{self.BASE_URL}/details/{ident}",
                "total_size_bytes": total_size_bytes,
                "total_size_formatted": format_size(total_size_bytes),
                "files_count": len(files),
                "files": files,
                "server": data.get("server", ""),
                "d1": data.get("d1", ""),
                "d2": data.get("d2", "")
            }
        except requests.exceptions.RequestException as e:
            print(f"[IA API] Metadata error: {e}")
            raise RuntimeError(f"Failed to fetch metadata for '{ident}': {e}")

    def test_credentials(
        self,
        access_key: str,
        secret_key: str,
        cookie: str = ""
    ) -> Tuple[bool, str]:
        """
        Verify if the given credentials or cookies are accepted by Internet Archive.
        """
        if not access_key and not secret_key and not cookie:
            return False, "No credentials provided."
            
        headers = self.get_headers(custom_access=access_key, custom_secret=secret_key, custom_cookie=cookie)
        
        try:
            # Test S3 endpoint
            resp = self.session.get(self.S3_URL, headers=headers, timeout=12)
            if resp.status_code == 200:
                # Parse display name if present
                content = resp.text
                if "<DisplayName>" in content:
                    m = re.search(r'<DisplayName>(.*?)</DisplayName>', content)
                    display_name = m.group(1) if m else "IA User"
                    if display_name and "Readable ID" not in display_name:
                        return True, f"Authentication successful! Logged in as: {display_name}"
                return True, "Authentication verified! Keys are active and recognized."
            elif resp.status_code == 403:
                return False, "Authentication failed: Invalid S3 Access or Secret key."
            else:
                return True, f"Server responded with status {resp.status_code}."
        except Exception as e:
            return False, f"Connection test failed: {e}"

    @staticmethod
    def _guess_format(filename: str) -> str:
        """Fallback format guesser from filename extension."""
        ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "FILE"
        return ext

    def check_identifier_available(self, identifier: str) -> Tuple[bool, str]:
        """
        Check if an Internet Archive item identifier is available or already in use.
        Returns (is_available, status_message).
        """
        clean_id = identifier.strip()
        if not clean_id:
            return False, "Identifier cannot be empty."
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{4,99}$", clean_id):
            return False, "Identifier must be 5-100 characters (letters, numbers, hyphens, underscores)."

        try:
            resp = self.session.get(f"{self.METADATA_URL}/{clean_id}", timeout=10)
            if resp.status_code == 404:
                return True, "Identifier is available!"
            if resp.status_code == 200:
                data = resp.json()
                if not data or not data.get("metadata") or data.get("is_empty"):
                    return True, "Identifier is available!"
                meta = data.get("metadata", {})
                title = meta.get("title", clean_id)
                return False, f"Identifier already exists ('{title}'). New files will be added to this item."
            return True, f"Server responded with status {resp.status_code}."
        except Exception as e:
            return True, f"Could not verify identifier: {e} (assuming available)"

    def upload_file(
        self,
        identifier: str,
        file_path: str,
        target_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Any] = None,
        cancel_check: Optional[Any] = None
    ) -> Tuple[bool, str]:
        """
        Upload a file to Internet Archive via the S3-compatible API.
        Creates the item if it does not exist when metadata is provided.
        """
        if not settings.s3_access_key or not settings.s3_secret_key:
            return False, "Internet Archive S3 Access & Secret Keys are required to upload. Configure them in Settings."

        if not os.path.exists(file_path):
            return False, f"File not found on disk: {file_path}"

        clean_id = identifier.strip()
        filename = target_name or os.path.basename(file_path)
        encoded_filename = urllib.parse.quote(filename)
        url = f"{self.S3_URL}/{clean_id}/{encoded_filename}"

        headers = self.get_headers()
        headers["x-amz-auto-make-bucket"] = "1"
        headers["x-archive-keep-old-version"] = "0"
        headers["Content-Type"] = "application/octet-stream"

        if metadata:
            for k, v in metadata.items():
                if v:
                    safe_v = str(v).encode("ascii", "xmlcharrefreplace").decode("ascii")
                    headers[f"x-archive-meta-{k}"] = safe_v

        file_size = os.path.getsize(file_path)

        class ProgressStream:
            def __init__(self, path, total_sz, cb, c_check):
                self.f = open(path, "rb")
                self.total = total_sz
                self.cb = cb
                self.cancel_check = c_check
                self.uploaded = 0

            def read(self, size=-1):
                if self.cancel_check and self.cancel_check():
                    self.f.close()
                    raise InterruptedError("Upload cancelled by user.")
                chunk = self.f.read(size)
                if chunk:
                    self.uploaded += len(chunk)
                    if self.cb:
                        self.cb(self.uploaded, self.total)
                return chunk

            def close(self):
                self.f.close()

            def __len__(self):
                return self.total

        stream = None
        try:
            stream = ProgressStream(file_path, file_size, progress_callback, cancel_check)
            resp = self.session.put(url, headers=headers, data=stream, timeout=900)
            if resp.status_code in (200, 201):
                return True, f"Successfully uploaded '{filename}' to {clean_id}!"
            else:
                err_text = resp.text[:250] if resp.text else f"HTTP {resp.status_code}"
                return False, f"Upload error (HTTP {resp.status_code}): {err_text}"
        except InterruptedError:
            return False, "Upload cancelled."
        except Exception as e:
            return False, f"Upload failed: {e}"
        finally:
            if stream:
                stream.close()

# Global API instance
ia_api = InternetArchiveAPI()
