"""Catalog use-cases.

The service depends only on ports; concrete repositories and the unit of work
are injected as factories at composition time (see the module ``register``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.catalog.application.dto import (
    ActiveIngredientOutput,
    CreateDrugInput,
    CreateIngredientInput,
    DrugIngredientInput,
    DrugIngredientRef,
    DrugOutput,
    PriceHistoryOutput,
)
from pharmacy_os.modules.catalog.domain import (
    ActiveIngredient,
    CatalogError,
    Drug,
    DrugIngredient,
    DrugUnit,
    DuplicateIngredientError,
    DuplicateUnitError,
    InvalidIngredientError,
    RxClass,
)
from pharmacy_os.modules.catalog.domain.ports import ActiveIngredientRepository, DrugRepository

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], DrugRepository]
IngredientRepoFactory = Callable[[UnitOfWork], ActiveIngredientRepository]


class CatalogService:
    def __init__(
        self,
        uow_factory: UowFactory,
        repo_factory: RepoFactory,
        ingredient_repo_factory: IngredientRepoFactory,
        audit: AuditLogger,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._ingredient_repo_factory = ingredient_repo_factory
        self._audit = audit

    async def create_drug(self, data: CreateDrugInput, ctx: RequestContext) -> DrugOutput:
        """Create a drug (with its units and ingredients) for the caller's tenant.

        Raises :class:`ValidationError` on a duplicate unit/ingredient, :class:`NotFoundError`
        when an *ingredients[].ingredient_id* doesn't reference an existing active ingredient,
        and :class:`ConflictError` when *data.barcode* is already registered.
        """
        require_permission(ctx, "catalog.create")
        drug = Drug(
            name=data.name,
            rx_class=RxClass(data.rx_class),
            base_unit=data.base_unit,
            registration_no=data.registration_no,
            atc_code=data.atc_code,
            form=data.form,
            strength=data.strength,
            barcode=data.barcode,
            sale_price=data.sale_price,
        )
        try:
            for u in data.units:
                drug.add_unit(
                    DrugUnit(unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
                )
        except DuplicateUnitError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            if data.barcode and await repo.by_barcode(data.barcode) is not None:
                raise ConflictError(f"Barcode '{data.barcode}' đã tồn tại")

            ingredient_repo = self._ingredient_repo_factory(uow)
            try:
                for i in data.ingredients:
                    if await ingredient_repo.get(i.ingredient_id) is None:
                        raise NotFoundError(f"Không tìm thấy hoạt chất {i.ingredient_id}")
                    drug.add_ingredient(
                        DrugIngredient(ingredient_id=i.ingredient_id, amount=i.amount, unit=i.unit)
                    )
            except (DuplicateIngredientError, InvalidIngredientError) as exc:
                raise ValidationError(str(exc)) from exc

            await repo.add(drug)
            await uow.commit()
        await self._record(ctx, AuditAction.CATALOG_DRUG_CREATED, drug.id)
        return DrugOutput.of(drug)

    async def replace_drug_ingredients(
        self, drug_id: UUID, ingredients: Sequence[DrugIngredientInput], ctx: RequestContext
    ) -> DrugOutput:
        """Đặt lại toàn bộ danh sách hoạt chất của một thuốc — sửa nhầm, bổ sung thiếu.

        Cho tới 2026-07-30 **không có đường nào** sửa được hoạt chất của một thuốc đã tạo:
        `create_drug` là use-case duy nhất, router chỉ có `POST`, repository chỉ có
        `add`/`get`. Nghĩa là dược sĩ nhập sai một hoạt chất thì cảnh báo dị ứng sai người
        vĩnh viễn, nhập thiếu thì im lặng vĩnh viễn — trên đúng tính năng chạm an toàn
        bệnh nhân.

        Quyền là ``catalog.update``, **không** phải ``catalog.read``: đọc danh mục là việc
        thường ngày của mọi vai ở quầy, còn sửa hoạt chất đổi hành vi cảnh báo của toàn
        chuỗi. Cũng không dùng chung ``catalog.create``: tạo sai thì thuốc mới chưa ai bán,
        sửa sai thì mọi cảnh báo đang chạy trên thuốc đó đổi hành vi ngay.

        Raises :class:`NotFoundError` khi thuốc không thuộc tenant hoặc một
        ``ingredient_id`` không có trong danh mục hoạt chất, :class:`ValidationError` khi
        danh sách trùng hoạt chất hoặc hàm lượng/đơn vị không hợp lệ.
        """
        require_permission(ctx, "catalog.update")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drug = await repo.get(drug_id)
            if drug is None:
                raise NotFoundError(f"Không tìm thấy thuốc {drug_id}")
            so_luong_truoc = len(drug.ingredients)

            ingredient_repo = self._ingredient_repo_factory(uow)
            try:
                moi = [
                    DrugIngredient(ingredient_id=i.ingredient_id, amount=i.amount, unit=i.unit)
                    for i in ingredients
                ]
            except InvalidIngredientError as exc:
                raise ValidationError(str(exc)) from exc
            # Kiểm hoạt chất tồn tại trước khi đổi aggregate. Đảo thứ tự này KHÔNG làm
            # hỏng dữ liệu — đã đo bằng đột biến 30/07, bộ test vẫn xanh — vì aggregate bị
            # vứt đi khi exception ném ra, chưa kịp tới `save_ingredients`. Giữ thứ tự này
            # là để tính đúng đắn không phụ thuộc vào việc "không có gì ghi ở giữa", một
            # tính chất mà lần sửa sau có thể phá mà không ai nhận ra.
            for i in moi:
                if await ingredient_repo.get(i.ingredient_id) is None:
                    raise NotFoundError(f"Không tìm thấy hoạt chất {i.ingredient_id}")
            try:
                drug.replace_ingredients(moi)
            except DuplicateIngredientError as exc:
                raise ValidationError(str(exc)) from exc

            await repo.save_ingredients(drug)
            await uow.commit()

        await self._record(
            ctx,
            AuditAction.CATALOG_DRUG_INGREDIENTS_REPLACED,
            drug.id,
            count_before=str(so_luong_truoc),
            count_after=str(len(drug.ingredients)),
        )
        return DrugOutput.of(drug)

    async def set_drug_price(
        self,
        drug_id: UUID,
        new_price: Decimal,
        reason: str | None,
        ctx: RequestContext,
    ) -> DrugOutput:
        """Đặt lại giá bán niêm yết của một thuốc, ghi luôn một dòng lịch sử giá.

        Cho tới 2026-07-31 **không có đường nào** đổi giá sau khi tạo thuốc: `create_drug`
        nhận `sale_price` một lần rồi thôi, router không có `PUT`/`PATCH` nào chạm giá.
        Đặt sai một lần là sai vĩnh viễn — cùng hình dạng với ca hoạt chất ngày 30/07.

        Quyền là ``catalog.update`` — **cấp chuỗi**, không phải quyền của quầy. Giá là
        quyết định của chủ chuỗi (Chain chốt 2026-07-31), và `catalog.update` sẵn có đúng
        ranh giới đó: `_BRANCH_PHARMACIST_PERMISSIONS` loại trừ nó tường minh. Thêm một
        quyền mới ở đây sẽ tạo ra tầng phân quyền thứ hai cho cùng một khái niệm.

        **Đòi lý do khi đổi giá đã có, không đòi khi đặt giá lần đầu.** Một mã nhập từ nhà
        phân phối chưa có giá thì lần đầu chốt giá không có gì để giải thích; còn đổi giá
        của một mã **đang bán** là thay đổi thứ khách nhìn thấy trên kệ, và Điều 107.4
        Luật Dược buộc giá đó phải niêm yết được.

        Raises :class:`NotFoundError` khi thuốc không thuộc tenant; :class:`ValidationError`
        khi giá không hợp lệ, trùng giá cũ, hoặc đổi giá mà thiếu lý do.
        """
        require_permission(ctx, "catalog.update")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drug = await repo.get(drug_id)
            if drug is None:
                raise NotFoundError(f"Không tìm thấy thuốc {drug_id}")
            if drug.sale_price is not None and not (reason or "").strip():
                raise ValidationError("Đổi giá một mã đang có giá thì phải ghi lý do")
            try:
                change = drug.set_sale_price(new_price, reason=(reason or None))
            except CatalogError as exc:
                raise ValidationError(str(exc)) from exc
            await repo.save_price(drug, change, ctx.user_id, datetime.now(UTC))
            await uow.commit()

        await self._record(
            ctx,
            AuditAction.CATALOG_DRUG_PRICE_CHANGED,
            drug.id,
            old_price="(chưa có)" if change.old_price is None else str(change.old_price),
            new_price=str(change.new_price),
        )
        return DrugOutput.of(drug)

    async def drug_price_history(
        self, drug_id: UUID, ctx: RequestContext, *, limit: int = 50
    ) -> list[PriceHistoryOutput]:
        """Lịch sử giá của một thuốc, mới nhất trước.

        Quyền ``catalog.read`` chứ không ``catalog.update``: giá niêm yết là thứ **phải**
        công khai tại nơi bán theo Điều 107.4, nên lịch sử của nó không phải bí mật với
        người trong nhà thuốc. Ai được *đổi* mới là chuyện cấp chuỗi.
        """
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            if await repo.get(drug_id) is None:
                raise NotFoundError(f"Không tìm thấy thuốc {drug_id}")
            records = await repo.price_history(drug_id, limit=limit)
        return [PriceHistoryOutput.of(r) for r in records]

    async def get_drug(self, drug_id: UUID, ctx: RequestContext) -> DrugOutput:
        """Return one drug by id, scoped to the tenant; 404 if not found."""
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drug = await repo.get(drug_id)
        if drug is None:
            raise NotFoundError(f"Không tìm thấy thuốc {drug_id}")
        return DrugOutput.of(drug)

    async def drug_names(self, drug_ids: Sequence[UUID], ctx: RequestContext) -> dict[UUID, str]:
        """Resolve many drug ids to display names in one query.

        Exists for read models that hold ids and need labels — the analytics dashboard
        and reorder screen (docs/19 §4–§5). Deliberately **not** ``NotFoundError`` on an
        unknown id: those screens summarise a period that may pre-date a drug's removal,
        and one stale id must not fail the whole response. Missing ids are absent from
        the returned mapping.
        """
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            return await repo.names_by_ids(drug_ids)

    async def get_drug_ingredients(
        self, drug_id: UUID, ctx: RequestContext
    ) -> list[DrugIngredientRef]:
        """Resolve a drug's active ingredients to ``(ingredient_id, name)`` pairs.

        Catalog owns the ``drug_id → ingredients`` mapping; the cross-module safety
        checks (clinical interactions match by name, CRM allergies by ingredient_id)
        both read through here. Raises :class:`NotFoundError` if the drug doesn't
        exist for the tenant, or if a referenced ingredient is missing (a
        data-integrity fault the ``drug_ingredients`` FK should prevent).
        """
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drug = await repo.get(drug_id)
            if drug is None:
                raise NotFoundError(f"Không tìm thấy thuốc {drug_id}")
            ingredient_repo = self._ingredient_repo_factory(uow)
            refs: list[DrugIngredientRef] = []
            for di in drug.ingredients:
                ingredient = await ingredient_repo.get(di.ingredient_id)
                if ingredient is None:
                    raise NotFoundError(f"Không tìm thấy hoạt chất {di.ingredient_id}")
                refs.append(DrugIngredientRef(ingredient_id=di.ingredient_id, name=ingredient.name))
        return refs

    async def create_ingredient(
        self, data: CreateIngredientInput, ctx: RequestContext
    ) -> ActiveIngredientOutput:
        """Create a global active ingredient. Raises :class:`ConflictError` on duplicate name."""
        require_permission(ctx, "catalog.create")
        try:
            ingredient = ActiveIngredient(name=data.name, name_en=data.name_en)
        except InvalidIngredientError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            ingredient_repo = self._ingredient_repo_factory(uow)
            if await ingredient_repo.find_by_name(data.name) is not None:
                raise ConflictError(f"Hoạt chất '{data.name}' đã tồn tại")
            await ingredient_repo.add(ingredient)
            await uow.commit()
        return ActiveIngredientOutput.of(ingredient)

    async def list_ingredients(self, ctx: RequestContext) -> list[ActiveIngredientOutput]:
        """List all global active ingredients (reference data, not tenant-scoped)."""
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            ingredient_repo = self._ingredient_repo_factory(uow)
            ingredients = await ingredient_repo.list()
        return [ActiveIngredientOutput.of(i) for i in ingredients]

    async def list_drugs(
        self,
        ctx: RequestContext,
        *,
        search: str | None = None,
        ids: Sequence[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DrugOutput]:
        """List the tenant's drugs (name-ordered), paginated by limit/offset.

        ``search`` = substring of the name (case-insensitive) or an exact barcode;
        ``ids`` = a known set, which is how a screen labels a page of rows holding
        drug ids with one request rather than one per row (Sprint 10, D3). Both are
        filters on the same read — no new permission, ``catalog.read`` throughout.
        """
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drugs = await repo.list(search=search, ids=ids, limit=limit, offset=offset)
        return [DrugOutput.of(d) for d in drugs]

    async def _record(
        self, ctx: RequestContext, action: AuditAction, drug_id: UUID, **extra: str
    ) -> None:
        """Append one audit row — metadata only, never drug/pricing content.

        ``extra`` chỉ nhận **số đếm/cờ**, không nhận nội dung: xem ghi chú ở
        :attr:`AuditAction.CATALOG_DRUG_INGREDIENTS_REPLACED` về lý do chép danh sách hoạt
        chất vào sổ audit là sai (NĐ 356/2025 Điều 4.2).
        """
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type="drug",
                target_id=str(drug_id),
            ).with_context(**ctx.audit_meta, branch_id=str(ctx.branch_id), **extra)
        )
