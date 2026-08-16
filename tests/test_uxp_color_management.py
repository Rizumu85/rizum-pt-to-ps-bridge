import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SOURCE = PROJECT_ROOT / "ps_plugin" / "src" / "build-psd.js"


class UxpColorManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = BUILD_SOURCE.read_text(encoding="utf-8")

    def test_color_document_is_created_with_the_explicit_profile(self):
        self.assertIn(
            "documentOptions.profile = colorPolicy.photoshop_profile", self.source
        )
        self.assertIn("verifyDocumentColorManagement", self.source)
        self.assertNotIn("convertProfile(", self.source)

    def test_data_document_is_untagged(self):
        self.assertIn(
            "document.colorProfileType = constants.ColorProfileType.NONE",
            self.source,
        )

    def test_save_profile_embedding_follows_the_request_policy(self):
        self.assertIn(
            "embedColorProfile: colorPolicy.embed_profile === true", self.source
        )


if __name__ == "__main__":
    unittest.main()
