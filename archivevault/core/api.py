import html
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

    def search(
        self,
        query: str,
        mediatype: Optional[str] = None,
        sort: Optional[str] = "-downloads",
        page: int = 1,
        rows: int = 30
    ) -> Dict[str, Any]:
        """
        Search Internet Archive items.
        
        :param query: Search keywords or lucene query
        :param mediatype: 'software', 'movies', 'audio', 'texts', 'image', or None for all
        :param sort: Sort field, e.g. '-downloads', '-publicdate', 'titleSorter asc'
        :param page: Page number (1-indexed)
        :param rows: Items per page
        :return: Dict containing total_count, docs list, page, rows
        """
        q = query.strip() if query else ""
        
        # Smart query expansion for vintage records, 78rpm, and vinyl audio
        effective_mediatype = mediatype
        if q and ":" not in q:
            q_lower = q.lower()
            record_triggers = [
                "old records", "old record", "vintage records", "vintage record",
                "vinyl records", "vinyl record", "78rpm", "78 rpm", "antique records",
                "shellac records", "phonograph records"
            ]
            is_record_search = any(trig in q_lower for trig in record_triggers) or q_lower in ("records", "record", "vinyl")
            if is_record_search:
                # Remove matched triggers to extract remaining sub-queries (e.g. "old records jazz" -> "jazz")
                residual = q_lower
                for trig in record_triggers:
                    residual = residual.replace(trig, " ")
                residual = residual.replace("records", " ").replace("record", " ").replace("vinyl", " ").strip()
                
                base_coll = "collection:(georgeblood OR 78rpm OR 78rpm_unfiltered OR album_recordings OR vinylrecords) AND NOT mediatype:collection"
                if residual:
                    q = f"({base_coll}) AND ({residual})"
                else:
                    q = base_coll
                
                if not effective_mediatype or effective_mediatype.lower() == "all":
                    effective_mediatype = "audio"
        
        # Build query string
        parts = []
        if q:
            # If user didn't specify field: prefix, wrap keywords nicely
            if ":" not in q:
                # Search title, description, or general keywords
                parts.append(f"({q})")
            else:
                parts.append(q)
        else:
            parts.append("*")
            
        if effective_mediatype and effective_mediatype.lower() != "all":
            parts.append(f"mediatype:({effective_mediatype.lower()})")
            
        final_query = " AND ".join(parts) if parts else "*"
        
        params = {
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
            "sort[]": sort or "-downloads",
            "rows": rows,
            "page": page,
            "output": "json"
        }
        
        last_error = None
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

        response_obj = data.get("response", {})
        total_count = response_obj.get("numFound", 0)
        raw_docs = response_obj.get("docs", [])
        
        cleaned_docs = []
        for doc in raw_docs:
            ident = doc.get("identifier", "")
            if not ident:
                continue
                
            title = doc.get("title", ident)
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

# Global API instance
ia_api = InternetArchiveAPI()
