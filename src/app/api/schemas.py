from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field

from ..services.model_config import default_model_id


DEFAULT_LLM_MODEL = default_model_id()


class ConvertResponse(BaseModel):
    success: bool
    latex_content: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None


class CompareRequest(BaseModel):
    template_content: str = Field(..., min_length=10, description="Template text")
    document_content: str = Field(..., min_length=10, description="Document text")
    model: str = Field(default=DEFAULT_LLM_MODEL, description="LLM model")
    parallel: bool = Field(default=True, description="Run checks in parallel")


class BibliographyCheckRequest(BaseModel):
    document_content: str = Field(..., min_length=10, description="Document text")
    max_references: int = Field(default=30, ge=1, le=100, description="Maximum references to check")


class ErrorItem(BaseModel):
    section: str
    error_type: Literal["structural", "content", "formatting", "typography"]
    description: str
    severity: Literal["critical", "high", "medium", "low"]


class CompareResponse(BaseModel):
    errors: List[ErrorItem]
    compliance_score: int
    summary: str
    warnings: List[str] = Field(default_factory=list)
    check_id: Optional[str] = None


class BibliographyCandidate(BaseModel):
    source: str
    title: str = ""
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    container: str = ""
    identifiers: dict[str, str] = Field(default_factory=dict)
    url: str = ""
    confidence: float = 0.0


class BibliographyReferenceCheck(BaseModel):
    index: int
    raw: str
    title: str = ""
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    reference_type: str = "unknown"
    identifiers: dict[str, str] = Field(default_factory=dict)
    status: Literal["confirmed", "probable", "suspicious", "not_found", "unparsed"]
    confidence: float = 0.0
    suspicion_score: float = 0.0
    reason: str = ""
    candidates: List[BibliographyCandidate] = Field(default_factory=list)


class BibliographyCheckResponse(BaseModel):
    model: str
    checked_count: int
    summary: str
    warnings: List[str] = Field(default_factory=list)
    references: List[BibliographyReferenceCheck] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="ITPort login or email")
    password: str = Field(..., min_length=1, description="ITPort password")


class UserResponse(BaseModel):
    email: str
    redirect: Optional[str] = None
    role: Literal["admin", "user"] = "user"
    last_login_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse


class ModelResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    usage_limit: Optional[int] = None
    context_window_tokens: Optional[int] = None
    used_count: int = 0
    remaining: Optional[int] = None


class ModelsResponse(BaseModel):
    default_model: str
    models: List[ModelResponse]
    usage_limit_reset_interval_hours: Optional[float] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    size: int
    kind: Literal["docx", "markdown"] = "docx"


class TemplatesResponse(BaseModel):
    templates: List[TemplateResponse]


class TemplateMarkdownResponse(BaseModel):
    id: str
    name: str
    content: str
    size: int


class TemplateMarkdownUpdateRequest(BaseModel):
    content: str = Field(default="", description="Markdown template content")


class UsageResetRequest(BaseModel):
    user_email: Optional[str] = Field(default=None, description="Reset usage for this user only")
    model: Optional[str] = Field(default=None, description="Reset usage for this model only")


class UsageResetResponse(BaseModel):
    reset_records: int


class UsageLimitUpdateRequest(BaseModel):
    user_email: str = Field(..., min_length=1, description="User email")
    model: str = Field(..., min_length=1, description="LLM model")
    available_checks: int = Field(..., ge=0, description="Checks available after saving")


class UsageLimitUpdateResponse(BaseModel):
    user_email: str
    model: str
    usage_limit: int
    used_count: int
    remaining: int


class CheckHistoryItem(BaseModel):
    id: str
    user_email: str
    document_name: str
    template_name: Optional[str] = None
    model_id: str
    compliance_score: int
    errors_count: int
    result: dict[str, Any]
    source_available: bool
    created_at: datetime


class CheckHistoryResponse(BaseModel):
    checks: List[CheckHistoryItem]


class AdminUserResponse(BaseModel):
    email: str
    redirect: Optional[str] = None
    role: Literal["admin", "user"] = "user"
    last_login_at: datetime
    check_count: int = 0
    latest_check_at: Optional[datetime] = None


class AdminUsersResponse(BaseModel):
    users: List[AdminUserResponse]
