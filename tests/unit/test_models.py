import pytest
from pydantic import ValidationError

from app.models import CopyOutput, JobStatus, Submission


def test_submission_requires_core_fields():
    s = Submission(
        full_name="Jane Doe",
        email="jane@example.com",
        brand_name="Bloom",
        industry="florist",
        questionnaire={"tone": "warm"},
    )
    assert s.email == "jane@example.com"
    assert s.questionnaire["tone"] == "warm"


def test_submission_rejects_bad_email():
    with pytest.raises(ValidationError):
        Submission(full_name="J", email="not-an-email", brand_name="B", industry="i")


def test_copy_output_validates_full_schema():
    payload = {
        "headline": "Bloom in every season",
        "subheadline": "Hand-tied arrangements from local growers.",
        "primary_cta": "Order now",
        "secondary_cta": "See bouquets",
        "about": {"heading": "Our story", "body": "We started in 2019..."},
        "features": [
            {"icon": "leaf", "title": "Local", "body": "From growers within 50mi."},
            {"icon": "calendar", "title": "Daily", "body": "Cut every morning."},
            {"icon": "heart", "title": "Custom", "body": "We design to your vision."},
        ],
        "social_proof": [{"text": "Stunning.", "author": "Emma"}],
        "footer_tagline": "Made with love.",
        "meta": {
            "title": "Bloom Florist",
            "description": "Hand-tied bouquets.",
            "keywords": ["florist"],
        },
        "palette_hint": "warm-earth",
    }
    c = CopyOutput.model_validate(payload)
    assert len(c.features) == 3
    assert c.palette_hint == "warm-earth"


def test_copy_output_rejects_wrong_feature_count():
    payload = {
        "headline": "x",
        "subheadline": "x",
        "primary_cta": "x",
        "secondary_cta": "x",
        "about": {"heading": "x", "body": "x"},
        "features": [{"icon": "x", "title": "x", "body": "x"}],
        "social_proof": [],
        "footer_tagline": "x",
        "meta": {"title": "x", "description": "x", "keywords": []},
        "palette_hint": "warm-earth",
    }
    with pytest.raises(ValidationError):
        CopyOutput.model_validate(payload)


def test_job_status_string_enum():
    assert JobStatus.QUEUED.value == "queued"
    assert JobStatus.DONE.value == "done"
