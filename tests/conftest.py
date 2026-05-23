import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic")
os.environ.setdefault("UNSPLASH_ACCESS_KEY", "test-unsplash")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://localhost/test")
os.environ.setdefault("R2_ACCOUNT_ID", "test-account")
os.environ.setdefault("R2_ACCESS_KEY_ID", "test-key")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "test-secret")
os.environ.setdefault("R2_BUCKET", "test-bucket")
os.environ.setdefault("R2_PUBLIC_BASE", "https://test.sitesnap.app")
os.environ.setdefault("RESEND_API_KEY", "test-resend")
os.environ.setdefault("RESEND_FROM_EMAIL", "test@sitesnap.app")
os.environ.setdefault("RESEND_OPERATOR_EMAIL", "ops@sitesnap.app")
os.environ.setdefault("ADMIN_BEARER_TOKEN", "test-admin")
os.environ.setdefault("ENV", "test")


@pytest.fixture
def anyio_backend():
    return "asyncio"
