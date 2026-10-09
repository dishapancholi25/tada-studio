from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging

from ...services.groups.service import GroupService
from ...api.auth.dependencies import get_current_user, require_active_user

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/groups", tags=["groups"], dependencies=[Depends(require_active_user)]
)
service = GroupService()


class GroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9\s\-]+$")
    description: Optional[str] = Field(None, max_length=500)


class GroupUpdateRequest(BaseModel):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9\s\-]+$"
    )
    description: Optional[str] = Field(None, max_length=500)


class AddMemberRequest(BaseModel):
    user_id: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: str
    email: Optional[str]
    name: Optional[str]


class GroupMemberResponse(BaseModel):
    user_id: str
    user_name: Optional[str]
    user_email: Optional[str]
    added_at: datetime
    is_protected: bool = False


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_system: bool
    created_by_user_id: Optional[str]
    created_by_name: Optional[str]
    member_count: int
    created_at: datetime


class GroupsListResponse(BaseModel):
    groups: List[GroupResponse]
    total_count: int


@router.get("", response_model=GroupsListResponse)
def get_groups(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=100),
    current_user=Depends(get_current_user),
):
    """Get paginated list of groups.

    Args:
        limit: Maximum number of groups to return (1-100, default 50)
        offset: Number of groups to skip (default 0)
        search: Optional search query to filter by group name
        current_user: Current authenticated user

    Returns:
        GroupsListResponse with groups list and total_count
    """
    groups_data, total_count = service.get_groups(limit, offset, search)
    result = []
    for group, member_count, created_by_name in groups_data:
        result.append(
            GroupResponse(
                id=group.id,
                name=group.name,
                description=group.description,
                is_system=group.is_system,
                created_by_user_id=group.created_by_user_id,
                created_by_name=created_by_name,
                member_count=member_count,
                created_at=group.created_at,
            )
        )
    return GroupsListResponse(groups=result, total_count=total_count)


@router.get("/users", response_model=List[UserResponse])
def get_all_users(current_user=Depends(get_current_user)):
    users = service.get_all_users()
    return [UserResponse(id=u.id, email=u.email, name=u.name) for u in users]


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(req: GroupCreateRequest, current_user=Depends(get_current_user)):
    try:
        group = service.create_group(req.name, req.description, current_user)
        return GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            is_system=group.is_system,
            created_by_user_id=group.created_by_user_id,
            created_by_name=None,
            member_count=0,
            created_at=group.created_at,
        )
    except PermissionError as e:
        logger.error(str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating group: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating the group",
        )


@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: str, req: GroupUpdateRequest, current_user=Depends(get_current_user)
):
    try:
        group = service.update_group(group_id, req.name, req.description, current_user)
        return GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            is_system=group.is_system,
            created_by_user_id=group.created_by_user_id,
            created_by_name=None,
            member_count=0,
            created_at=group.created_at,
        )
    except PermissionError as e:
        logger.error(str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{group_id}")
def delete_group(group_id: str, current_user=Depends(get_current_user)):
    try:
        service.delete_group(group_id, current_user)
        return {"success": True}
    except PermissionError as e:
        logger.error(str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
def get_group_members(group_id: str, current_user=Depends(get_current_user)):
    try:
        members = service.get_group_members(group_id)
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=str(e))
    protected_ids = service.get_protected_member_ids(group_id)
    result = []
    for membership, user in members:
        result.append(
            GroupMemberResponse(
                user_id=user.id,
                user_name=user.name,
                user_email=user.email,
                added_at=membership.created_at,
                is_protected=user.id in protected_ids,
            )
        )
    return result


@router.post("/{group_id}/members")
def add_group_member(
    group_id: str, body: AddMemberRequest, current_user=Depends(get_current_user)
):
    try:
        service.manage_members(group_id, [body.user_id], [], current_user)
        return {"success": True}
    except PermissionError as e:
        logger.error(str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{group_id}/members/{user_id}")
def remove_group_member(
    group_id: str, user_id: str, current_user=Depends(get_current_user)
):
    try:
        service.manage_members(group_id, [], [user_id], current_user)
        return {"success": True}
    except PermissionError as e:
        logger.error(str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/users/{user_id}/groups")
def get_user_groups(user_id: str, current_user=Depends(get_current_user)):
    groups = service.get_user_groups(user_id)
    return {"groups": groups}
