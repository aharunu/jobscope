"""Authentication and user context dependencies."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.models.user import UserModel
from backend.interfaces.api.dependencies.database import DbSession

logger = logging.getLogger(__name__)

DEV_FALLBACK_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user_id(
    session: DbSession,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    settings: Settings = Depends(get_settings),
) -> uuid.UUID:
    """Resolve current user identity.

    In development/test environments, falls back to a seeded dev user when
    the X-User-Id header is omitted. In production environments, requires an
    explicit and valid user context, raising 401 Unauthorized otherwise.
    """
    is_dev_or_test = (
        settings.environment.lower() in ("development", "test") or settings.debug
    )

    if x_user_id is None:
        if not is_dev_or_test:
            logger.warning("Rejected unauthenticated request in production environment")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required: Missing X-User-Id header.",
            )

        # Development/Test fallback
        user = await session.get(UserModel, DEV_FALLBACK_USER_ID)
        if not user:
            session.add(UserModel(id=DEV_FALLBACK_USER_ID))
            await session.flush()
        return DEV_FALLBACK_USER_ID

    # Parse and validate provided header
    try:
        user_uuid = uuid.UUID(x_user_id.strip())
    except (ValueError, AttributeError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-Id header format. Must be a valid UUID.",
        ) from err

    # Ensure user record exists in database
    user = await session.get(UserModel, user_uuid)
    if not user:
        if is_dev_or_test:
            session.add(UserModel(id=user_uuid))
            await session.flush()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authenticated user '{user_uuid}' not found.",
            )

    return user_uuid


CurrentUserDep = Annotated[uuid.UUID, Depends(get_current_user_id)]
