"""品牌与型号中心 API（用户端 + 管理端）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_knowledge_manager
from app.core.database import get_db
from app.domains.printer.fault_taxonomy import (
    category_label,
    known_codes_for_brand,
    list_categories,
)
from app.domains.printer.registry import SUPPORT_STATUS_LABELS
from app.models.printer_brand import ModelCapability, PrinterBrand, ProductModel, UserDevice
from app.models.repair_knowledge import KnowledgeSource, RepairKnowledge
from app.models.user import User
from app.schemas.product import (
    BrandCreate,
    BrandUpdate,
    CapabilityCreate,
    CapabilityUpdate,
    DeviceAdd,
    ModelCreate,
    ModelUpdate,
)

router = APIRouter(prefix="/api/products", tags=["品牌型号"])
admin_router = APIRouter(
    prefix="/api/admin/products",
    tags=["管理端-品牌型号"],
    dependencies=[Depends(get_knowledge_manager)],
)

REVIEWED = ("approved", "published")


def brand_payload(db: Session, brand: PrinterBrand) -> dict:
    model_count = db.query(ProductModel).filter(ProductModel.brand_id == brand.id).count()
    active_count = (
        db.query(ProductModel)
        .filter(ProductModel.brand_id == brand.id, ProductModel.support_status == "active")
        .count()
    )
    return {
        "id": brand.id,
        "brand_code": brand.brand_code,
        "name": brand.name,
        "status": brand.status,
        "description": brand.description,
        "model_count": model_count,
        "active_model_count": active_count,
    }


def model_payload(db: Session, model: ProductModel, detail: bool = False) -> dict:
    brand = db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
    capabilities = (
        db.query(ModelCapability)
        .filter(ModelCapability.model_id == model.model_id)
        .order_by(ModelCapability.fault_category)
        .all()
    )
    published_count = (
        db.query(RepairKnowledge)
        .filter(
            RepairKnowledge.brand_code == (brand.brand_code if brand else None),
            RepairKnowledge.review_status.in_(REVIEWED),
            RepairKnowledge.model_scope.in_([model.model_id, model.series, "*", "ALL"]),
        )
        .count()
    )
    payload = {
        "id": model.id,
        "model_id": model.model_id,
        "brand_code": brand.brand_code if brand else None,
        "brand_name": brand.name if brand else None,
        "series": model.series,
        "model_code": model.model_code,
        "name": model.name,
        "aliases": model.aliases or [],
        "region": model.region,
        "technology": model.technology,
        "supported_features": model.supported_features or [],
        "support_status": model.support_status,
        "support_status_label": SUPPORT_STATUS_LABELS.get(
            model.support_status, model.support_status
        ),
        "knowledge_coverage": published_count,
        "capabilities": [
            {
                "id": cap.id,
                "fault_category": cap.fault_category,
                "fault_category_label": category_label(cap.fault_category),
                "code_system": cap.code_system,
                "verified_status": cap.verified_status,
                "supported_features": cap.supported_features or [],
                "notes": cap.notes,
            }
            for cap in capabilities
        ],
        "fault_categories": [
            {
                "fault_category": cap.fault_category,
                "label": category_label(cap.fault_category),
                "verified_status": cap.verified_status,
            }
            for cap in capabilities
        ],
        "release_note": model.release_note,
    }
    if detail:
        sources = (
            db.query(KnowledgeSource)
            .filter(
                KnowledgeSource.brand_code == (brand.brand_code if brand else None),
                or_(
                    KnowledgeSource.model_scope.is_(None),
                    KnowledgeSource.model_scope.in_([model.model_id, model.series]),
                ),
            )
            .all()
        )
        payload["sources"] = [
            {
                "source_key": source.source_key,
                "title": source.title,
                "url": source.url,
                "source_type": source.source_type,
                "authority_level": source.authority_level,
                "version": source.version,
            }
            for source in sources
        ]
        payload["error_codes"] = known_codes_for_brand(brand.brand_code if brand else None)
    return payload


@router.get("/brands")
def list_brands(db: Session = Depends(get_db)):
    brands = db.query(PrinterBrand).order_by(PrinterBrand.id).all()
    return [brand_payload(db, brand) for brand in brands]


@router.get("/fault-categories")
def get_fault_categories():
    return list_categories()


@router.get("/models")
def list_models(
    brand: str | None = Query(None),
    series: str | None = Query(None),
    region: str | None = Query(None),
    q: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
):
    query = db.query(ProductModel)
    if brand:
        brand_row = db.query(PrinterBrand).filter(PrinterBrand.brand_code == brand.upper()).first()
        if brand_row:
            query = query.filter(ProductModel.brand_id == brand_row.id)
        else:
            return []
    if series:
        query = query.filter(ProductModel.series.like(f"%{series}%"))
    if region:
        query = query.filter(ProductModel.region == region)
    if status:
        query = query.filter(ProductModel.support_status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            ProductModel.name.like(like)
            | ProductModel.model_code.like(like)
            | ProductModel.series.like(like)
            | ProductModel.model_id.like(like)
        )
    models = query.order_by(ProductModel.brand_id, ProductModel.id).limit(limit).all()
    return [model_payload(db, model) for model in models]


@router.get("/models/{model_id}")
def get_model(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="型号不存在")
    return model_payload(db, model, detail=True)


@router.get("/models/{model_id}/capabilities")
def get_capabilities(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="型号不存在")
    payload = model_payload(db, model)
    return payload["capabilities"]


@router.get("/models/{model_id}/error-codes")
def get_error_codes(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="型号不存在")
    brand = db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
    capability = (
        db.query(ModelCapability)
        .filter(ModelCapability.model_id == model.model_id, ModelCapability.code_system.isnot(None))
        .first()
    )
    return {
        "brand_code": brand.brand_code if brand else None,
        "code_system": capability.code_system if capability else None,
        "codes": known_codes_for_brand(brand.brand_code if brand else None),
    }


# ==================== 用户设备 ====================


def _device_payload(db: Session, device: UserDevice) -> dict:
    model = db.query(ProductModel).filter(ProductModel.model_id == device.model_id).first()
    return {
        "id": device.id,
        "model_id": device.model_id,
        "is_current": device.is_current,
        "model": model_payload(db, model) if model else None,
    }


@router.get("/devices")
def list_devices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    devices = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == current_user.id)
        .order_by(UserDevice.is_current.desc(), UserDevice.id)
        .all()
    )
    return [_device_payload(db, device) for device in devices]


@router.post("/devices")
def add_device(
    data: DeviceAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = db.query(ProductModel).filter(ProductModel.model_id == data.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="型号不存在")
    device = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == current_user.id, UserDevice.model_id == data.model_id)
        .first()
    )
    if not device:
        device = UserDevice(user_id=current_user.id, model_id=data.model_id)
        db.add(device)
        db.flush()
    if data.set_current:
        db.query(UserDevice).filter(UserDevice.user_id == current_user.id).update(
            {"is_current": False}
        )
        device.is_current = True
    db.commit()
    db.refresh(device)
    return _device_payload(db, device)


@router.delete("/devices/{model_id}")
def remove_device(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == current_user.id, UserDevice.model_id == model_id)
        .first()
    )
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    db.delete(device)
    if device.is_current:
        other = (
            db.query(UserDevice)
            .filter(UserDevice.user_id == current_user.id, UserDevice.model_id != model_id)
            .first()
        )
        if other:
            other.is_current = True
    db.commit()
    return {"message": "已移除"}


@router.post("/devices/{model_id}/current")
def set_current_device(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == current_user.id, UserDevice.model_id == model_id)
        .first()
    )
    if not device:
        raise HTTPException(status_code=404, detail="请先添加该设备")
    db.query(UserDevice).filter(UserDevice.user_id == current_user.id).update({"is_current": False})
    device.is_current = True
    db.commit()
    db.refresh(device)
    return _device_payload(db, device)


# ==================== 管理端 ====================


@admin_router.get("/brands")
def admin_list_brands(db: Session = Depends(get_db)):
    brands = db.query(PrinterBrand).order_by(PrinterBrand.id).all()
    return [brand_payload(db, brand) for brand in brands]


@admin_router.post("/brands")
def create_brand(data: BrandCreate, db: Session = Depends(get_db)):
    code = data.brand_code.strip().upper()
    if db.query(PrinterBrand).filter(PrinterBrand.brand_code == code).first():
        raise HTTPException(status_code=400, detail="品牌代码已存在")
    brand = PrinterBrand(
        brand_code=code,
        name=data.name,
        status=data.status,
        description=data.description,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand_payload(db, brand)


@admin_router.put("/brands/{brand_id}")
def update_brand(brand_id: int, data: BrandUpdate, db: Session = Depends(get_db)):
    brand = db.query(PrinterBrand).filter(PrinterBrand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")
    for field in ("name", "status", "description"):
        value = getattr(data, field)
        if value is not None:
            setattr(brand, field, value)
    db.commit()
    db.refresh(brand)
    return brand_payload(db, brand)


def _active_requirements(db: Session, model: ProductModel) -> list[str]:
    issues = []
    verified = (
        db.query(ModelCapability)
        .filter(
            ModelCapability.model_id == model.model_id,
            ModelCapability.verified_status == "verified",
        )
        .count()
    )
    if verified == 0:
        issues.append("至少需要一个已验证的型号能力映射")
    published = (
        db.query(RepairKnowledge)
        .filter(
            RepairKnowledge.review_status.in_(REVIEWED),
            RepairKnowledge.model_scope.in_([model.model_id, model.series, "*", "ALL"]),
        )
        .count()
    )
    if published == 0:
        issues.append("至少需要一条已发布且适用于该型号的知识")
    brand = db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
    sources = (
        db.query(KnowledgeSource)
        .filter(KnowledgeSource.brand_code == (brand.brand_code if brand else None))
        .count()
    )
    if sources == 0:
        issues.append("至少需要登记一个官方知识来源")
    return issues


@admin_router.post("/models")
def create_model(data: ModelCreate, db: Session = Depends(get_db)):
    brand = (
        db.query(PrinterBrand).filter(PrinterBrand.brand_code == data.brand_code.upper()).first()
    )
    if not brand:
        raise HTTPException(status_code=400, detail="品牌不存在")
    if db.query(ProductModel).filter(ProductModel.model_id == data.model_id).first():
        raise HTTPException(status_code=400, detail="型号 ID 已存在")
    if data.support_status not in SUPPORT_STATUS_LABELS:
        raise HTTPException(status_code=400, detail="无效的支持状态")
    model = ProductModel(
        model_id=data.model_id,
        brand_id=brand.id,
        series=data.series,
        model_code=data.model_code,
        name=data.name,
        aliases=data.aliases,
        region=data.region,
        technology=data.technology,
        supported_features=data.supported_features,
        support_status="planned" if data.support_status == "active" else data.support_status,
        release_note=data.release_note,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    if data.support_status == "active":
        issues = _active_requirements(db, model)
        if issues:
            model.support_status = "building"
            db.commit()
            return {
                "model": model_payload(db, model),
                "warning": "未满足启用条件，已保存为资料建设中",
                "issues": issues,
            }
    return model_payload(db, model)


@admin_router.put("/models/{model_id}")
def update_model(model_id: str, data: ModelUpdate, db: Session = Depends(get_db)):
    model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="型号不存在")
    for field in (
        "series",
        "model_code",
        "name",
        "aliases",
        "region",
        "technology",
        "supported_features",
        "release_note",
    ):
        value = getattr(data, field)
        if value is not None:
            setattr(model, field, value)
    if data.support_status is not None:
        if data.support_status not in SUPPORT_STATUS_LABELS:
            raise HTTPException(status_code=400, detail="无效的支持状态")
        if data.support_status == "active":
            issues = _active_requirements(db, model)
            if issues:
                raise HTTPException(
                    status_code=400,
                    detail={"message": "未满足型号启用门槛", "issues": issues},
                )
        model.support_status = data.support_status
    db.commit()
    db.refresh(model)
    return model_payload(db, model)


@admin_router.delete("/models/{model_id}")
def delete_model(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="型号不存在")
    db.query(ModelCapability).filter(ModelCapability.model_id == model_id).delete()
    db.delete(model)
    db.commit()
    return {"message": "已删除"}


@admin_router.post("/models/{model_id}/capabilities")
def create_capability(model_id: str, data: CapabilityCreate, db: Session = Depends(get_db)):
    model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="型号不存在")
    exists = (
        db.query(ModelCapability)
        .filter(
            ModelCapability.model_id == model_id,
            ModelCapability.fault_category == data.fault_category,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="该故障类别能力已存在")
    cap = ModelCapability(
        model_id=model_id,
        fault_category=data.fault_category,
        code_system=data.code_system,
        supported_features=data.supported_features,
        source_id=data.source_id,
        verified_status=data.verified_status,
        notes=data.notes,
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)
    return model_payload(db, model)


@admin_router.put("/capabilities/{capability_id}")
def update_capability(capability_id: int, data: CapabilityUpdate, db: Session = Depends(get_db)):
    cap = db.query(ModelCapability).filter(ModelCapability.id == capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="能力映射不存在")
    for field in ("code_system", "supported_features", "source_id", "verified_status", "notes"):
        value = getattr(data, field)
        if value is not None:
            setattr(cap, field, value)
    db.commit()
    model = db.query(ProductModel).filter(ProductModel.model_id == cap.model_id).first()
    return model_payload(db, model)


@admin_router.delete("/capabilities/{capability_id}")
def delete_capability(capability_id: int, db: Session = Depends(get_db)):
    cap = db.query(ModelCapability).filter(ModelCapability.id == capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="能力映射不存在")
    db.delete(cap)
    db.commit()
    return {"message": "已删除"}
