"""品牌与型号注册中心：别名解析、支持状态和型号边界校验。"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.printer_brand import ModelCapability, PrinterBrand, ProductModel

BRAND_ALIASES: dict[str, tuple[str, ...]] = {
    "HP": ("hp", "惠普", "hewlett packard"),
    "Canon": ("canon", "佳能"),
    "Epson": ("epson", "爱普生"),
    "Brother": ("brother", "兄弟", "brother industries"),
}

SUPPORT_STATUS_LABELS = {
    "planned": "规划中",
    "building": "资料建设中",
    "pilot": "试运行",
    "active": "已支持",
    "suspended": "暂停服务",
}

SUPPORTED_FOR_DIAGNOSIS = {"active", "pilot"}


def detect_brand(text: str | None) -> str | None:
    """从用户文本中识别品牌代码。"""
    if not text:
        return None
    lowered = text.lower()
    for brand_code, aliases in BRAND_ALIASES.items():
        if brand_code.lower() in lowered or any(alias in lowered for alias in aliases):
            return brand_code
    return None


def get_brand(db: Session, brand_code: str | None) -> PrinterBrand | None:
    if not brand_code:
        return None
    return db.query(PrinterBrand).filter(PrinterBrand.brand_code == brand_code.upper()).first()


def _brand_code_of(db: Session, model: ProductModel) -> str:
    brand = db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
    return brand.brand_code if brand else ""


def _model_matches_text(model: ProductModel, text: str) -> bool:
    lowered = text.lower().strip()
    if not lowered:
        return False
    haystacks = [model.model_id, model.model_code or "", model.name or "", model.series or ""]
    aliases = model.aliases or []
    if isinstance(aliases, list):
        haystacks.extend(str(alias) for alias in aliases)
    return any(
        lowered in str(item).lower() or str(item).lower() in lowered for item in haystacks if item
    )


def resolve_model(
    db: Session,
    text: str | None = None,
    brand_code: str | None = None,
    model_id: str | None = None,
    region: str | None = None,
) -> dict:
    """解析用户描述或显式 model_id。

    返回 {"model", "brand", "confidence", "candidates", "requires_confirmation"}。
    置信度不足时调用方应要求用户确认，不能直接进入型号专属诊断。
    """
    if model_id:
        model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
        if model:
            brand = db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
            return {
                "model": model,
                "brand": brand,
                "confidence": 1.0,
                "candidates": [model],
                "requires_confirmation": False,
            }
        return {
            "model": None,
            "brand": None,
            "confidence": 0.0,
            "candidates": [],
            "requires_confirmation": True,
        }

    text = (text or "").strip()
    brand_code = (brand_code or detect_brand(text) or "").upper() or None

    query = db.query(ProductModel)
    if brand_code:
        brand = get_brand(db, brand_code)
        if brand:
            query = query.filter(ProductModel.brand_id == brand.id)
    if region:
        query = query.filter(ProductModel.region == region)

    models = query.all()
    if not models:
        return {
            "model": None,
            "brand": get_brand(db, brand_code),
            "confidence": 0.0,
            "candidates": [],
            "requires_confirmation": True,
        }

    # 1. model_id / model_code 精确匹配
    normalized = text.lower()
    for model in models:
        if normalized == model.model_id.lower() or (
            model.model_code and normalized == model.model_code.lower()
        ):
            return _result(db, model, 1.0, [model], False)

    # 2. 型号别名精确匹配
    for model in models:
        aliases = model.aliases or []
        if any(normalized == str(alias).lower() for alias in aliases):
            return _result(db, model, 0.9, [model], False)

    # 3. 包含匹配（型号代码、名称、系列、别名）
    candidates = [model for model in models if _model_matches_text(model, text)]
    if len(candidates) == 1:
        return _result(db, candidates[0], 0.7, candidates, False)
    if len(candidates) > 1:
        # 多个候选时选择 active 优先，但仍要求用户确认
        active = [m for m in candidates if m.support_status == "active"]
        chosen = (active or candidates)[0]
        return _result(db, chosen, 0.5, candidates, True)

    return {
        "model": None,
        "brand": get_brand(db, brand_code),
        "confidence": 0.0,
        "candidates": [],
        "requires_confirmation": True,
    }


def _result(
    db: Session,
    model: ProductModel,
    confidence: float,
    candidates: list[ProductModel],
    requires_confirmation: bool,
) -> dict:
    brand = db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
    return {
        "model": model,
        "brand": brand,
        "confidence": confidence,
        "candidates": candidates,
        "requires_confirmation": requires_confirmation,
    }


def require_model(db: Session, model_id: str | None) -> ProductModel:
    if not model_id:
        raise ValueError("尚未确认打印机型号")
    model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
    if not model:
        raise ValueError("型号不存在")
    return model


def is_diagnosis_supported(model: ProductModel | None) -> bool:
    return bool(model and model.support_status in SUPPORTED_FOR_DIAGNOSIS)


def support_status_label(status: str | None) -> str:
    return SUPPORT_STATUS_LABELS.get(status or "", status or "未知")


def model_scope_matches(model: ProductModel, model_scope: str | None) -> bool:
    """知识条目是否适用于该型号：精确型号、系列或通配。"""
    if not model_scope:
        return False
    scope = model_scope.strip().lower()
    if scope in {"*", "all", "通用"}:
        return True
    if scope == model.model_id.lower():
        return True
    if model.series and scope == model.series.lower():
        return True
    aliases = [str(alias).lower() for alias in (model.aliases or [])]
    return scope in aliases


def get_capabilities(db: Session, model_id: str) -> list[ModelCapability]:
    return (
        db.query(ModelCapability)
        .filter(ModelCapability.model_id == model_id)
        .order_by(ModelCapability.fault_category)
        .all()
    )


def supports_fault_category(db: Session, model: ProductModel, category: str | None) -> bool:
    if not category:
        return False
    capability = (
        db.query(ModelCapability)
        .filter(
            ModelCapability.model_id == model.model_id,
            ModelCapability.fault_category == category,
        )
        .first()
    )
    return bool(capability and capability.verified_status in {"verified", "active"})


def extract_error_code(text: str | None) -> str | None:
    """从用户文本中提取常见错误码/灯态描述。"""
    if not text:
        return None
    patterns = [
        r"\b(E\d{1,2})\b",  # HP / Epson / Canon E 系列
        r"\b(?:support\s*code\s*)?(E\d{2})\b",
        r"\b(5\d{3})\b",  # Canon 5100 类
        r"\b(\d{2}[A-Z]?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None
