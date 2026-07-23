"""IAM HTTP endpoints: /auth (public) and /users, /roles (permission-guarded).

The ``/auth`` router takes no ``get_context`` dependency — those endpoints run
*before* an identity exists. ``/auth/me`` and ``/auth/change-password`` do need one
and take it explicitly.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.http import client_ip_of
from pharmacy_os.modules.iam.application import AuthService, IamService
from pharmacy_os.modules.iam.interface.schemas import (
    AssignRoleRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    ResetPasswordRequest,
    RoleAssignmentResponse,
    RoleResponse,
    SessionResponse,
    SetUserActiveRequest,
    SwitchBranchRequest,
    UserResponse,
)

ContextDep = Callable[..., RequestContext]


def _auth(request: Request) -> AuthService:
    service: AuthService = request.app.state.container.resolve(AuthService)
    return service


def _iam(request: Request) -> IamService:
    service: IamService = request.app.state.container.resolve(IamService)
    return service


def build_auth_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["iam"])

    @router.post("/login", response_model=SessionResponse)
    async def login(
        request: Request, body: LoginRequest, service: AuthService = Depends(_auth)
    ) -> SessionResponse:
        # The IP comes from the socket, never the body: a failed-login burst is only
        # traceable if the origin cannot be chosen by whoever is causing it.
        data = body.to_input()
        data.client_ip = client_ip_of(request)
        return SessionResponse.of(await service.login(data))

    @router.post("/refresh", response_model=SessionResponse)
    async def refresh(
        body: RefreshRequest, service: AuthService = Depends(_auth)
    ) -> SessionResponse:
        return SessionResponse.of(await service.refresh(body.refresh_token))

    @router.post("/switch-branch", response_model=SessionResponse)
    async def switch_branch(
        body: SwitchBranchRequest, service: AuthService = Depends(_auth)
    ) -> SessionResponse:
        return SessionResponse.of(
            await service.refresh(body.refresh_token, branch_id=body.branch_id)
        )

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(body: RefreshRequest, service: AuthService = Depends(_auth)) -> Response:
        await service.logout(body.refresh_token)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
    async def change_password(
        body: ChangePasswordRequest,
        service: AuthService = Depends(_auth),
        ctx: RequestContext = Depends(get_context),
    ) -> Response:
        await service.change_password(ctx, body.to_input())
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/me", response_model=MeResponse)
    async def me(ctx: RequestContext = Depends(get_context)) -> MeResponse:
        return MeResponse(
            user_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            permissions=sorted(ctx.permissions),
        )

    return router


def build_admin_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(tags=["iam"])

    @router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    async def create_user(
        body: CreateUserRequest,
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
    ) -> UserResponse:
        return UserResponse.of(await service.create_user(body.to_input(), ctx))

    @router.get("/users", response_model=list[UserResponse])
    async def list_users(
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[UserResponse]:
        users = await service.list_users(ctx, limit=limit, offset=offset)
        return [UserResponse.of(u) for u in users]

    @router.get("/users/{user_id}", response_model=UserResponse)
    async def get_user(
        user_id: UUID,
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
    ) -> UserResponse:
        return UserResponse.of(await service.get_user(user_id, ctx))

    @router.put("/users/{user_id}/active", response_model=UserResponse)
    async def set_user_active(
        user_id: UUID,
        body: SetUserActiveRequest,
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
    ) -> UserResponse:
        return UserResponse.of(await service.set_user_active(user_id, active=body.active, ctx=ctx))

    @router.post("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
    async def reset_password(
        user_id: UUID,
        body: ResetPasswordRequest,
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
    ) -> Response:
        await service.reset_password(user_id, body.new_password, ctx)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/users/{user_id}/roles", response_model=list[RoleAssignmentResponse])
    async def list_assignments(
        user_id: UUID,
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
    ) -> list[RoleAssignmentResponse]:
        items = await service.list_assignments(user_id, ctx)
        return [RoleAssignmentResponse.of(a) for a in items]

    @router.post(
        "/users/{user_id}/roles",
        response_model=RoleAssignmentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def assign_role(
        user_id: UUID,
        body: AssignRoleRequest,
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
    ) -> RoleAssignmentResponse:
        return RoleAssignmentResponse.of(await service.assign_role(user_id, body.to_input(), ctx))

    @router.delete("/users/{user_id}/roles/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def revoke_role(
        user_id: UUID,
        assignment_id: UUID,
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
    ) -> Response:
        await service.revoke_role(user_id, assignment_id, ctx)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/roles", response_model=list[RoleResponse])
    async def list_roles(
        service: IamService = Depends(_iam),
        ctx: RequestContext = Depends(get_context),
    ) -> list[RoleResponse]:
        return [RoleResponse.of(r) for r in await service.list_roles(ctx)]

    return router
