from pydantic import BaseModel, ConfigDict, Field, model_validator


class SalaryOfferInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=120)
    company: str = Field(default="", max_length=120)
    role: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    currency: str = Field(..., pattern="^[A-Za-z]{3}$")
    annual_base: float = Field(default=0, ge=0, le=1_000_000_000_000)
    annual_variable: float = Field(default=0, ge=0, le=1_000_000_000_000)
    annual_bonus: float = Field(default=0, ge=0, le=1_000_000_000_000)
    annual_equity: float = Field(default=0, ge=0, le=1_000_000_000_000)
    benefits: list[str] = Field(default_factory=list, max_length=30)
    conditions: str = Field(default="", max_length=4000)
    growth_notes: str = Field(default="", max_length=2000)


class SalaryOfferComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=2, max_length=120)
    offer_ids: list[str] = Field(..., min_length=2, max_length=2)

    @model_validator(mode="after")
    def require_distinct_offers(self) -> "SalaryOfferComparisonInput":
        if self.offer_ids[0] == self.offer_ids[1]:
            raise ValueError("Choose two distinct saved offers.")
        if any(not offer_id.strip() for offer_id in self.offer_ids):
            raise ValueError("Offer identifiers cannot be blank.")
        self.title = self.title.strip()
        return self


class SalaryCalculatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = Field(..., pattern="^[A-Za-z]{3}$")
    annual_fixed: float = Field(..., ge=0, le=1_000_000_000_000)
    annual_variable: float = Field(default=0, ge=0, le=1_000_000_000_000)
    annual_bonus: float = Field(default=0, ge=0, le=1_000_000_000_000)
    annual_equity: float = Field(default=0, ge=0, le=1_000_000_000_000)
    annual_tax_rate_percent: float = Field(default=0, ge=0, le=75)
    monthly_deductions: float = Field(default=0, ge=0, le=1_000_000_000)


class SalaryGrowthInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = Field(..., pattern="^[A-Za-z]{3}$")
    current_annual_compensation: float = Field(..., gt=0, le=1_000_000_000_000)
    annual_growth_rate_percent: float = Field(..., ge=0, le=100)
    years: int = Field(default=3, ge=1, le=10)


class SalaryReadinessInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_written_offer: bool = False
    has_reliable_benchmark: bool = False
    has_documented_impact: bool = False
    has_target_and_floor: bool = False
    has_reviewed_total_compensation: bool = False


class SalaryNegotiationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: str = Field(..., pattern="^(strategy|recruiter_script|manager_script)$")
    role: str = Field(..., min_length=2, max_length=160)
    company: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    currency: str = Field(..., pattern="^[A-Za-z]{3}$")
    current_offer: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    target_compensation: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    experience: str = Field(default="", max_length=1200)
    achievements: str = Field(default="", max_length=3000)
    priorities: str = Field(default="", max_length=1500)


class SalaryEstimateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., min_length=2, max_length=120)
    location: str = Field(default="", max_length=120)
    currency: str | None = Field(default=None, pattern="^[A-Za-z]{3}$")
    company: str = Field(default="", max_length=120)
    experience_level: str = Field(default="", max_length=80)
    skills: list[str] = Field(default_factory=list, max_length=30)


class SalaryOfferExplainInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extracted_text: str = Field(..., min_length=30, max_length=30_000)
