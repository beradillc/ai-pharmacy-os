"""IAM HTTP endpoints: /auth (public) and /users, /roles (permission-guarded).

The ``/auth`` router takes no ``get_context`` dependency — those endpoints run
*before* an identity exists. ``/auth/me`` and ``/auth/change-password`` do need one
and take it explicitly.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from pharmacy_os.core.config import Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.http import client_ip_of, user_agent_of
from pharmacy_os.core.security import RateLimiter, RateLimitRule
from pharmacy_os.modules.iam.application import AuthService, IamService, StepUpResult
from pharmacy_os.modules.iam.interface.schemas import (
    AssignRoleRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    ResetPasswordRequest,
    ResetTwoFactorRequest,
    RoleAssignmentResponse,
    RoleResponse,
    SessionResponse,
    SetUserActiveRequest,
    StepUpFields,
    SwitchBranchRequest,
    TwoFactorActivateResponse,
    TwoFactorCodeRequest,
    TwoFactorDisableRequest,
    TwoFactorEnrollResponse,
    TwoFactorLoginRequest,
    TwoFactorStatusResponse,
    UserResponse,
)

ContextDep = Callable[..., Awaitable[RequestContext]]
"""``get_context`` là **async** kể từ audit B-07: nó phải tra CSDL để xác nhận cặp
``(tenant, chi nhánh)`` là có thật. FastAPI tự await, nên route không phải đổi gì."""


def _auth(request: Request) -> AuthService:
    service: AuthService = request.app.state.container.resolve(AuthService)
    return service


def _iam(request: Request) -> IamService:
    service: IamService = request.app.state.container.resolve(IamService)
    return service


def _throttle(request: Request, endpoint: str) -> None:
    """Từ chối 429 khi một IP bắn quá hạn mức vào endpoint xác thực (F-9).

    Chạy **trước** khi chạm tới mật khẩu hay CSDL: một request bị chặn ở đây không
    tốn một lần băm bcrypt nào, nên chi phí của kẻ tấn công cao hơn chi phí của
    người bị tấn công — điều kiện tối thiểu để một cơ chế phòng thủ có ích.

    Khoá đếm là ``(IP, endpoint)`` chứ không phải ``(IP, tài khoản)``: nếu đếm theo
    tài khoản thì bắn vào 100 tài khoản khác nhau từ một IP vẫn lọt, mà đó chính là
    hình dạng của cuộc tấn công cần chặn (kiểm toán C-11).
    """
    settings: Settings = request.app.state.container.resolve(Settings)
    if not settings.security.rate_limit_enabled:
        return
    limiter: RateLimiter = request.app.state.rate_limiter
    ip = client_ip_of(request) or "unknown"
    verdict = limiter.check(
        f"{endpoint}:{ip}",
        RateLimitRule(
            max_events=settings.security.rate_limit_login_attempts,
            window_seconds=settings.security.rate_limit_login_window_seconds,
        ),
    )
    if not verdict.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Quá nhiều lượt thử từ địa chỉ này. Vui lòng chờ rồi thử lại.",
            headers={"Retry-After": str(verdict.retry_after_seconds)},
        )


def build_auth_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["iam"])

    @router.post("/login", response_model=SessionResponse)
    async def login(
        request: Request, body: LoginRequest, service: AuthService = Depends(_auth)
    ) -> SessionResponse:
        _throttle(request, "login")
        # The IP comes from the socket, never the body: a failed-login burst is only
        # traceable if the origin cannot be chosen by whoever is causing it.
        data = body.to_input()
        data.client_ip = client_ip_of(request)
        data.user_agent = user_agent_of(request)
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
    async def me(
        service: AuthService = Depends(_auth),
        ctx: RequestContext = Depends(get_context),
    ) -> MeResponse:
        """Định danh + quyền (bản gốc), **kèm** tên/email/lần đăng nhập cuối (M-03).

        Trước 2026-08-01 route này chỉ đọc ``ctx`` nên không chạm CSDL. Nay nó đọc một
        hàng ``users`` — đổi này có chủ đích: không có nó thì màn *Tài khoản của tôi* buộc
        phải gọi ``GET /users``, tức là đòi ``iam.user.read``, tức là **thu ngân không xem
        được tên của chính mình**.
        """
        p = await service.profile(ctx)
        return MeResponse(
            user_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            permissions=sorted(ctx.permissions),
            email=p.email,
            full_name=p.full_name,
            last_login_at=p.last_login_at,
            must_change_password=p.must_change_password,
        )

    # --- two-factor -----------------------------------------------------------
    #
    # ``/2fa/login`` is the only one of these that takes no context: it *completes*
    # an authentication, so no identity exists yet. The rest act on the caller's own
    # account and need one. There is deliberately no endpoint to read a secret or a
    # backup code back — both are shown exactly once, at the moment they are issued.

    @router.post("/2fa/login", response_model=SessionResponse)
    async def two_factor_login(
        request: Request, body: TwoFactorLoginRequest, service: AuthService = Depends(_auth)
    ) -> SessionResponse:
        """Step 2: exchange the challenge from ``/auth/login`` plus a code for a session."""
        # Cùng hạn mức với /auth/login, và ở đây còn cần hơn: mã TOTP chỉ có 6 chữ số,
        # nên bề mặt đoán mò hẹp hơn mật khẩu nhiều bậc. Thử thách tự nó đã cháy sau 5
        # lần sai, nhưng cháy-rồi-xin-cái-mới là một vòng lặp không tốn gì của kẻ tấn
        # công nếu không có gì giới hạn theo IP.
        _throttle(request, "2fa-login")
        data = body.to_input()
        data.client_ip = client_ip_of(request)
        data.user_agent = user_agent_of(request)
        return SessionResponse.of(await service.complete_two_factor_login(data))

    @router.post("/2fa/enroll", response_model=TwoFactorEnrollResponse)
    async def enroll_two_factor(
        service: AuthService = Depends(_auth),
        ctx: RequestContext = Depends(get_context),
    ) -> TwoFactorEnrollResponse:
        """Issue a secret. Nothing changes about logging in until it is activated."""
        return TwoFactorEnrollResponse.of(await service.enroll_two_factor(ctx))

    @router.post("/2fa/activate", response_model=TwoFactorActivateResponse)
    async def activate_two_factor(
        body: TwoFactorCodeRequest,
        service: AuthService = Depends(_auth),
        ctx: RequestContext = Depends(get_context),
    ) -> TwoFactorActivateResponse:
        """Prove the secret was stored correctly, switch it on, and hand back the
        backup codes — the only time they are ever shown."""
        return TwoFactorActivateResponse.of(await service.activate_two_factor(ctx, body.code))

    @router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
    async def disable_two_factor(
        body: TwoFactorDisableRequest,
        service: AuthService = Depends(_auth),
        ctx: RequestContext = Depends(get_context),
    ) -> Response:
        await service.disable_two_factor(ctx, body.current_password, body.code)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/2fa", response_model=TwoFactorStatusResponse)
    async def two_factor_status(
        service: AuthService = Depends(_auth),
        ctx: RequestContext = Depends(get_context),
    ) -> TwoFactorStatusResponse:
        return TwoFactorStatusResponse.of(await service.two_factor_status(ctx))

    return router


#: Thông điệp 403 khi step-up trượt. Cố ý KHÔNG nói trượt vì mật khẩu hay vì mã —
#: người bấm hợp lệ biết mình vừa nhập gì, còn kẻ dò thì không nên được kể thêm.
_STEP_UP_DENIED = "Xác thực lại thất bại — thao tác này cần mật khẩu và mã 2FA của chính bạn"


async def _require_step_up(auth: AuthService, ctx: RequestContext, body: StepUpFields) -> None:
    """Chặn thao tác cho tới khi người GỌI chứng minh lại danh tính (audit B-05).

    Vì sao hai endpoint hạ phòng thủ của người khác lại cần chính cơ chế đó: chuỗi tấn
    công kiểm toán dựng ra chỉ cần **một phiên đang mở** của tài khoản có
    ``iam.user.write`` — máy quầy bỏ trống, đúng mối đe doạ mà step-up sinh ra để chống.
    Từ đó: gỡ 2FA của dược sĩ → đặt lại mật khẩu của họ → đăng nhập như họ, **không còn
    yếu tố thứ hai** → ký sổ kiểm soát đặc biệt. Bảo đảm của TT18 Điều 15.1.d khi đó
    rút xuống thành "tin phiên đăng nhập của quản trị viên".

    Lệnh break-glass ở máy chủ (``seeds.reset_two_factor``) vẫn KHÔNG cần step-up, và
    đó không phải mâu thuẫn: ai chạy được nó đã có credential CSDL. Lập luận ấy đúng cho
    CLI và **không** áp dụng cho một endpoint chỉ cần access token — §7bb đã dùng nhầm
    nó cho cả hai.
    """
    result = await auth.verify_step_up(ctx, body.current_password, body.totp_code)
    if result is not StepUpResult.OK:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_STEP_UP_DENIED)


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
        auth: AuthService = Depends(_auth),
        ctx: RequestContext = Depends(get_context),
    ) -> Response:
        """Đặt lại mật khẩu người khác. Đòi step-up của **người gọi** — xem
        :func:`_require_step_up`: đây là bước thứ hai của chuỗi tấn công B-05."""
        await _require_step_up(auth, ctx, body)
        await service.reset_password(user_id, body.new_password, ctx)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post("/users/{user_id}/2fa/reset", status_code=status.HTTP_204_NO_CONTENT)
    async def reset_two_factor(
        user_id: UUID,
        body: ResetTwoFactorRequest,
        service: IamService = Depends(_iam),
        auth: AuthService = Depends(_auth),
        ctx: RequestContext = Depends(get_context),
    ) -> Response:
        """Clear another user's second factor after they lost their device.

        Requires ``iam.user.write``, so in practice ``system_admin`` only. Deliberately
        does **not** revoke sessions or force a password change: this lowers a defence,
        it does not touch the credential, so an in-progress shift is not interrupted.

        Cannot rescue the last remaining administrator — nobody would hold the
        permission to call it. That case is covered by the server-side break-glass
        command (``python -m seeds.reset_two_factor``), not by this endpoint.

        Đòi **step-up của người gọi** kể từ 2026-07-28 (audit B-05): trước đó endpoint
        này gỡ được yếu tố thứ hai của người khác mà không cần yếu tố thứ hai nào của
        chính mình — yếu hơn hẳn thứ nó đang bảo vệ.
        """
        await _require_step_up(auth, ctx, body)
        await service.reset_two_factor(user_id, ctx)
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
