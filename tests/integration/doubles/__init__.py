"""Test doubles for vendor API integration testing."""

from .fake_jira import JiraFake
from .spy_transport import SpyTransport
from .stub_jira import JiraStub
from .stub_qtest import QTestStub
from .stub_zephyr import ZephyrStub
from .vcr_replay import VCRReplay, VCRTransport

__all__ = [
    "JiraStub",
    "ZephyrStub",
    "QTestStub",
    "JiraFake",
    "SpyTransport",
    "VCRReplay",
    "VCRTransport",
]
