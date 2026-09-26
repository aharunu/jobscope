"""Greenhouse ATS adapter package."""

from backend.infrastructure.ats.greenhouse.adapter import (
    GreenhouseAdapter,
    extract_greenhouse_board_token,
)

__all__ = ["GreenhouseAdapter", "extract_greenhouse_board_token"]
