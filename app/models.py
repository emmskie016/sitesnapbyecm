from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

PaletteHint = Literal["warm-earth", "cool-modern", "bold-vibrant", "muted-elegant"]
Archetype = Literal["service", "hospitality", "portfolio"]


class Submission(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    brand_name: str = Field(min_length=1, max_length=200)
    industry: str = Field(min_length=1, max_length=200)
    questionnaire: dict = Field(default_factory=dict)


class JobStatus(StrEnum):
    QUEUED = "queued"
    CLASSIFYING = "classifying"
    WRITING_COPY = "writing_copy"
    FETCHING_IMAGES = "fetching_images"
    RENDERING = "rendering"
    PUBLISHING = "publishing"
    NOTIFYING = "notifying"
    DONE = "done"
    FAILED = "failed"


STATUS_PROGRESS: dict[JobStatus, int] = {
    JobStatus.QUEUED: 0,
    JobStatus.CLASSIFYING: 10,
    JobStatus.WRITING_COPY: 30,
    JobStatus.FETCHING_IMAGES: 50,
    JobStatus.RENDERING: 70,
    JobStatus.PUBLISHING: 90,
    JobStatus.NOTIFYING: 95,
    JobStatus.DONE: 100,
    JobStatus.FAILED: 0,
}


class AboutBlock(BaseModel):
    heading: str
    body: str


class FeatureBlock(BaseModel):
    icon: str
    title: str
    body: str


class SocialProof(BaseModel):
    text: str
    author: str


class MetaBlock(BaseModel):
    title: str
    description: str
    keywords: list[str] = Field(default_factory=list)


class CopyOutput(BaseModel):
    headline: str
    subheadline: str
    primary_cta: str
    secondary_cta: str
    about: AboutBlock
    features: list[FeatureBlock] = Field(min_length=3, max_length=3)
    social_proof: list[SocialProof]
    footer_tagline: str
    meta: MetaBlock
    palette_hint: PaletteHint


class ClassifyOutput(BaseModel):
    archetype: Archetype
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class ImageSlot(BaseModel):
    slot: str
    url: str
    photo_id: str
    attribution_html: str
