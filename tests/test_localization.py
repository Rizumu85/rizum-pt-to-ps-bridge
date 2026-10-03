import json
import string
import unittest

from sp_plugin.rizum_sp_to_ps import localization


PAINTER_LANGUAGES = {"de", "en", "es", "fr", "it", "ja", "ko", "pt", "zh"}


def _placeholders(template):
    return sorted(
        name for _text, name, _spec, _conversion in string.Formatter().parse(template) if name
    )


class LocalizationTests(unittest.TestCase):
    def test_catalogs_cover_exactly_painters_languages(self):
        self.assertEqual(set(localization.supported_languages()), PAINTER_LANGUAGES)
        files = {
            localization.normalize_language(path.stem).split("_", 1)[0]
            for path in localization.I18N_DIR.glob("*.json")
        }
        self.assertEqual(files, PAINTER_LANGUAGES)

    def test_every_catalog_has_exactly_the_english_keys(self):
        english = set(localization.FALLBACK_TEXT)
        for path in sorted(localization.I18N_DIR.glob("*.json")):
            with self.subTest(catalog=path.name):
                catalog = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(set(catalog), english)

    def test_english_catalog_matches_the_fallback_text(self):
        catalog = json.loads((localization.I18N_DIR / "en.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog, localization.FALLBACK_TEXT)

    def test_placeholders_match_english_in_every_catalog(self):
        for path in sorted(localization.I18N_DIR.glob("*.json")):
            catalog = json.loads(path.read_text(encoding="utf-8"))
            for key, english in localization.FALLBACK_TEXT.items():
                with self.subTest(catalog=path.name, key=key):
                    self.assertTrue(catalog[key].strip())
                    self.assertEqual(_placeholders(catalog[key]), _placeholders(english))

    def test_language_resolves_by_exact_code_then_root_then_english(self):
        self.assertEqual(localization.resolve_language("", "ja_JP"), "ja")
        self.assertEqual(localization.resolve_language("zh", "en_US"), "zh")
        self.assertEqual(localization.resolve_language("custom", "de_DE"), "de")
        self.assertEqual(localization.resolve_language("", ""), "en")
        self.assertEqual(localization.resolve_language("pt_BR"), "pt")
        self.assertEqual(localization.resolve_language("zh-CN"), "zh_cn")

    def test_text_formats_values_in_the_requested_language(self):
        self.assertEqual(
            localization.text("channels_selected", language="en", selected=2, total=5),
            "2 of 5 channels selected",
        )
        self.assertEqual(
            localization.text("channels_selected", language="zh", selected=2, total=5),
            localization.CATALOGS["zh"]["channels_selected"].format(selected=2, total=5),
        )
        self.assertNotEqual(
            localization.text("export", language="zh"),
            localization.text("export", language="en"),
        )

    def test_unknown_key_falls_back_to_the_key(self):
        self.assertEqual(localization.text("no_such_key", language="ja"), "no_such_key")


if __name__ == "__main__":
    unittest.main()
