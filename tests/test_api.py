import unittest
from archivevault.core.utils import format_size, format_speed, format_eta, extract_identifier, sanitize_filename
from archivevault.core.api import ia_api

class TestCore(unittest.TestCase):
    def test_utils(self):
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(1048576), "1.0 MB")
        self.assertEqual(format_size(1073741824), "1.0 GB")
        self.assertEqual(format_speed(1048576), "1.0 MB/s")
        self.assertEqual(format_eta(65), "1m 05s")
        
        # Test identifier extraction
        self.assertEqual(extract_identifier("msdos_Doom_1993"), "msdos_Doom_1993")
        self.assertEqual(extract_identifier("https://archive.org/details/msdos_Doom_1993"), "msdos_Doom_1993")
        self.assertEqual(extract_identifier("https://archive.org/download/nasa-sp-4308/doc.pdf"), "nasa-sp-4308")
        
        # Test filename sanitize
        self.assertEqual(sanitize_filename("my:file<name>?.iso"), "my_file_name__.iso")

    def test_search(self):
        res = ia_api.search(query="apollo 11", rows=2)
        self.assertIn("docs", res)
        self.assertGreater(len(res["docs"]), 0)
        doc = res["docs"][0]
        self.assertTrue(bool(doc["identifier"]))
        self.assertTrue(bool(doc["title"]))
        print(f"Search successful: found {res['total_count']} items. Sample: {doc['title']}")

    def test_smart_query_builder(self):
        # 1. Atari ST platform expansion
        q_st, mt_st = ia_api.build_smart_query("atari st dungeon master")
        self.assertIn("softwarelibrary_atari_st_games", q_st)
        self.assertIn("dungeon AND master", q_st)
        self.assertEqual(mt_st, "software")

        # 2. Multi-word natural query excludes web crawls and Fightcade replay flood
        q_sf, _ = ia_api.build_smart_query("street fighter", filter_mode="media_only")
        self.assertIn("street AND fighter", q_sf)
        self.assertIn("NOT mediatype:(collection OR web OR data)", q_sf)
        self.assertIn("NOT collection:Fightcade-Archive", q_sf)

        # 3. 78rpm vintage records expansion
        q_rec, mt_rec = ia_api.build_smart_query("78rpm jazz")
        self.assertIn("georgeblood", q_rec)
        self.assertEqual(mt_rec, "audio")

if __name__ == "__main__":
    unittest.main()
