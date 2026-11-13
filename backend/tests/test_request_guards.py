import os
import unittest

from fastapi import HTTPException

from app.services.request_guards import (
    SlidingWindowLimiter,
    paid_openai_enabled,
    require_paid_openai,
)


class PaidOpenaiFlagTest(unittest.TestCase):
    def test_defaults_to_enabled(self):
        os.environ.pop("PAID_OPENAI_ENABLED", None)
        self.assertTrue(paid_openai_enabled())

    def test_require_blocks_when_disabled(self):
        os.environ["PAID_OPENAI_ENABLED"] = "false"
        try:
            with self.assertRaises(HTTPException) as raised:
                require_paid_openai()
            self.assertEqual(raised.exception.status_code, 403)
            self.assertNotIn("OPENAI_API_KEY", raised.exception.detail)
        finally:
            os.environ.pop("PAID_OPENAI_ENABLED", None)


class SlidingWindowLimiterTest(unittest.TestCase):
    def test_allows_under_limit_then_blocks(self):
        limiter = SlidingWindowLimiter(max_calls=2, window_seconds=60)
        limiter.check()
        limiter.check()
        with self.assertRaises(HTTPException) as raised:
            limiter.check()
        self.assertEqual(raised.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()
