import re
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class SaveTargetCompanyInput(BaseModel):
    entity_id: str = Field(..., pattern="^Q[1-9][0-9]{0,11}$")
    company_name: str = Field(..., min_length=1, max_length=200)


class CompanyCompareInput(BaseModel):
    entity_ids: List[str] = Field(..., min_length=2, max_length=4)

    @model_validator(mode="after")
    def unique_entity_ids(self) -> "CompanyCompareInput":
        if len(set(self.entity_ids)) != len(self.entity_ids):
            raise ValueError("Choose each company only once.")
        if any(not re.fullmatch(r"Q[1-9][0-9]{0,11}", value) for value in self.entity_ids):
            raise ValueError("Each company must use a valid Wikidata entity ID.")
        return self


class CompanyResearchAssistantInput(BaseModel):
    entity_id: str = Field(..., pattern="^Q[1-9][0-9]{0,11}$")
    company_name: str = Field(..., min_length=1, max_length=200)
    role_title: str = Field(default="", max_length=160)
    job_description: str = Field(default="", max_length=20_000)


class CompanyRoleOptimizeInput(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    role_title: str = Field(..., min_length=2, max_length=160)
    job_id: str = Field(..., min_length=1, max_length=80)
    resume_id: Optional[str] = Field(default=None, max_length=80)
