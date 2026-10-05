import unittest
from archivevault.core.torrent import bdecode, parse_torrent_bytes

def _bencode(obj):
    if isinstance(obj, int):
        return f"i{obj}e".encode()
    elif isinstance(obj, str):
        b = obj.encode("utf-8")
        return f"{len(b)}:".encode() + b
    elif isinstance(obj, bytes):
        return f"{len(obj)}:".encode() + obj
    elif isinstance(obj, list):
        return b"l" + b"".join(_bencode(x) for x in obj) + b"e"
    elif isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: kv[0] if isinstance(kv[0], bytes) else kv[0].encode())
        return b"d" + b"".join(_bencode(k) + _bencode(v) for k, v in items) + b"e"

class TestTorrentParser(unittest.TestCase):
    def test_bdecode_primitives(self):
        # Integer
        val, _ = bdecode(b"i42e")
        self.assertEqual(val, 42)

        # Byte string
        val, _ = bdecode(b"4:spam")
        self.assertEqual(val, b"spam")

        # List
        val, _ = bdecode(b"li1ei2e3:fooe")
        self.assertEqual(val, [1, 2, b"foo"])

        # Dict
        val, _ = bdecode(b"d3:bar4:spam3:fooi42ee")
        self.assertEqual(val, {"bar": b"spam", "foo": 42})

    def test_parse_multi_file_torrent(self):
        torrent_dict = {
            "announce": "http://bt1.archive.org:6969/announce",
            "info": {
                "name": "test_archive",
                "piece length": 262144,
                "pieces": b"12345678901234567890",
                "files": [
                    {"length": 1048576, "path": ["track", "1.mp3"]},
                    {"length": 2097152, "path": ["subfolder", "video.mp4"]}
                ]
            }
        }
        raw_torrent = _bencode(torrent_dict)
        meta = parse_torrent_bytes(raw_torrent)
        self.assertEqual(meta.name, "test_archive")
        self.assertEqual(meta.identifier, "test_archive")
        self.assertEqual(len(meta.files), 2)
        self.assertEqual(meta.total_size, 1048576 + 2097152)

        # Check file 1
        f1 = meta.files[0]
        self.assertEqual(f1.filename, "1.mp3")
        self.assertEqual(f1.size_bytes, 1048576)
        self.assertEqual(f1.download_url, "https://archive.org/download/test_archive/track/1.mp3")

        # Check file 2
        f2 = meta.files[1]
        self.assertEqual(f2.filename, "video.mp4")
        self.assertEqual(f2.extension, ".mp4")
        self.assertEqual(f2.download_url, "https://archive.org/download/test_archive/subfolder/video.mp4")

if __name__ == "__main__":
    unittest.main()
