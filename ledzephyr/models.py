"""Data models for ledzephyr."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TeamSource(str, Enum):
    """Source for team identification."""
    COMPONENT = "component"
    LABEL = "label"
    GROUP = "group"


class ProjectMetrics(BaseModel):
    """Metrics for a project within a time window."""
    
    project_key: str = Field(..., description="Jira project key")
    time_window: str = Field(..., description="Time window (e.g., '7d', '30d')")
    
    # Test counts
    total_tests: int = Field(0, description="Total number of tests")
    zephyr_tests: int = Field(0, description="Tests in Zephyr Scale")
    qtest_tests: int = Field(0, description="Tests in qTest")
    
    # Ratios and percentages
    adoption_ratio: float = Field(0.0, description="qTest adoption ratio (qtest_tests / total_tests)")
    coverage_parity: float = Field(0.0, description="Coverage parity percentage")
    defect_link_rate: float = Field(0.0, description="Defect linking rate percentage")
    
    # User activity
    active_users: int = Field(0, description="Number of active users")
    
    # Team breakdown
    team_metrics: Dict[str, "TeamMetrics"] = Field(
        default_factory=dict, 
        description="Metrics broken down by team"
    )
    
    # Trend data (4-week comparison)
    trend_data: Optional["TrendData"] = Field(None, description="4-week trend comparison")


class TeamMetrics(BaseModel):
    """Metrics for a specific team."""
    
    team_name: str = Field(..., description="Team name")
    team_source: TeamSource = Field(..., description="Source of team identification")
    
    # Test counts
    total_tests: int = Field(0, description="Total number of tests for this team")
    zephyr_tests: int = Field(0, description="Tests in Zephyr Scale for this team")
    qtest_tests: int = Field(0, description="Tests in qTest for this team")
    
    # Ratios
    adoption_ratio: float = Field(0.0, description="qTest adoption ratio for this team")
    coverage_parity: float = Field(0.0, description="Coverage parity for this team")
    defect_link_rate: float = Field(0.0, description="Defect linking rate for this team")
    
    # Activity
    active_users: int = Field(0, description="Active users in this team")


class TrendData(BaseModel):
    """4-week trend data for metrics."""
    
    week_1: Dict[str, float] = Field(default_factory=dict, description="Most recent week")
    week_2: Dict[str, float] = Field(default_factory=dict, description="2 weeks ago")
    week_3: Dict[str, float] = Field(default_factory=dict, description="3 weeks ago")
    week_4: Dict[str, float] = Field(default_factory=dict, description="4 weeks ago")
    
    # Calculated trends
    adoption_trend: float = Field(0.0, description="Adoption ratio trend (week 1 - week 4)")
    coverage_trend: float = Field(0.0, description="Coverage parity trend (week 1 - week 4)")
    activity_trend: float = Field(0.0, description="User activity trend (week 1 - week 4)")


class JiraProject(BaseModel):
    """Jira project information."""
    
    key: str = Field(..., description="Project key")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    lead: Optional[str] = Field(None, description="Project lead")
    
    # Components for team identification
    components: List[str] = Field(default_factory=list, description="Project components")


class TestCase(BaseModel):
    """Test case information."""
    
    id: str = Field(..., description="Test case ID")
    key: str = Field(..., description="Test case key")
    summary: str = Field(..., description="Test case summary")
    project_key: str = Field(..., description="Project key")
    
    # Team identification
    component: Optional[str] = Field(None, description="Component")
    labels: List[str] = Field(default_factory=list, description="Labels")
    assignee: Optional[str] = Field(None, description="Assignee")
    
    # Source system
    source_system: str = Field(..., description="Source system (zephyr/qtest)")
    
    # Metadata
    created: datetime = Field(..., description="Creation date")
    updated: datetime = Field(..., description="Last update date")
    status: str = Field(..., description="Test case status")
    
    # Execution data
    last_execution: Optional[datetime] = Field(None, description="Last execution date")
    execution_status: Optional[str] = Field(None, description="Last execution status")
    
    # Defect linking
    linked_defects: List[str] = Field(default_factory=list, description="Linked defect keys")


class APIConnectionStatus(BaseModel):
    """API connection status."""
    
    service: str = Field(..., description="Service name")
    connected: bool = Field(..., description="Connection status")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    error: Optional[str] = Field(None, description="Error message if connection failed")
    last_checked: datetime = Field(default_factory=datetime.now, description="Last check time")


# Forward reference resolution
ProjectMetrics.model_rebuild()