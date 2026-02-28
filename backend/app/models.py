"""Pydantic models for Semflow course data."""

from pydantic import BaseModel, Field


class Course(BaseModel):
    """Single course from the catalog."""

    catalogue: str = Field(
        ...,
        description="Catalog term, e.g. '2024/fall' or '2024/spring'",
    )
    subject: str = Field(
        ...,
        description="Subject code, e.g. 'CS', 'MATH'",
    )
    course_number: str = Field(
        ...,
        description="Course number within the subject, e.g. '125', '225'",
        alias="courseNumber",
    )
    title: str = Field(
        ...,
        description="Course title",
    )
    description: str = Field(
        default="",
        description="Course description from catalog",
    )
    prerequisites: str = Field(
        default="",
        description="Prerequisite text or requirement description",
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "catalogue": "2024/fall",
                "subject": "CS",
                "courseNumber": "125",
                "title": "Introduction to Computer Science",
                "description": "Basic concepts...",
                "prerequisites": "MATH 220 or MATH 221 or equivalent.",
            }
        }


class SubjectSummary(BaseModel):
    """Subject code and optional label from catalog."""

    id: str = Field(..., description="Subject code, e.g. 'CS', 'MATH'")
    href: str = Field(default="", description="API link to subject courses")
    label: str = Field(default="", description="Human-readable subject name")


class CatalogTerm(BaseModel):
    """Year and semester identifying a catalog."""

    year: str = Field(..., description="4-digit year, e.g. '2024'")
    semester: str = Field(
        ...,
        description="One of 'spring', 'summer', 'fall'",
    )

    @property
    def catalogue(self) -> str:
        return f"{self.year}/{self.semester}"
