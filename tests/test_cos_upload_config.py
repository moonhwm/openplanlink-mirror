from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "skills/cross-session-workflow-bridge/vendor/cos_upload.py"


def load():
    spec = importlib.util.spec_from_file_location("cos_config_under_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConfigTests(unittest.TestCase):
    def test_missing_configuration_fails_before_optional_sdk_import(self):
        with patch.dict(os.environ, {}, clear=True):
            module = load()
            with self.assertRaisesRegex(RuntimeError, "COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET"):
                module.main()

    def test_environment_configuration_is_read(self):
        values = {"COS_SECRET_ID": "test-id", "COS_SECRET_KEY": "test-value",
                  "COS_REGION": "test-region", "COS_BUCKET": "test-bucket"}
        with patch.dict(os.environ, values, clear=True):
            module = load()
        self.assertEqual(values["COS_SECRET_ID"], module.SECRET_ID)
        self.assertEqual(values["COS_SECRET_KEY"], module.SECRET_KEY)
        self.assertEqual(values["COS_REGION"], module.REGION)
        self.assertEqual(values["COS_BUCKET"], module.BUCKET)

    def test_sdk_failure_does_not_print_exception_contents(self):
        private_detail = "exception-private-detail"

        class Client:
            def upload_file(self, **kwargs):
                raise RuntimeError(private_detail)

        sdk = SimpleNamespace(CosConfig=lambda **kw: kw, CosS3Client=lambda _: Client())
        with patch.dict(os.environ, {"COS_SECRET_ID": "test-id", "COS_SECRET_KEY": "test-value",
                                     "COS_BUCKET": "test-bucket"}, clear=True):
            module = load()
        with tempfile.TemporaryDirectory(prefix="opl-cos-config-") as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                output = StringIO()
                with patch.dict(sys.modules, {"qcloud_cos": sdk}), redirect_stdout(output):
                    module.main()
                self.assertNotIn(private_detail, output.getvalue())
                self.assertNotIn("test-value", output.getvalue())
                self.assertTrue(Path("cos_urls.txt").exists())
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
