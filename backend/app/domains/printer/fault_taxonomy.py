"""统一故障分类与品牌专属代码体系。

设计约束：
- 统一故障大类只用于统计、筛选和路由；
- 错误码解释必须绑定品牌/型号代码体系，禁止跨品牌等价映射；
- 未登记的错误码只返回“需按官方资料确认”，不做推断。
"""

from __future__ import annotations

FAULT_CATEGORIES: dict[str, dict[str, str]] = {
    "paper_feed": {
        "label": "进纸与卡纸",
        "description": "不进纸、卡纸、多张进纸、纸张歪斜、进纸滚轮相关。",
    },
    "ink_supply": {
        "label": "墨盒与供墨",
        "description": "墨盒识别、墨水余量、加墨、墨路与耗材安装相关。",
    },
    "print_quality": {
        "label": "打印质量",
        "description": "断线、条纹、偏色、空白页、喷头堵塞与对齐相关。",
    },
    "connectivity": {
        "label": "连接与网络",
        "description": "USB、Wi-Fi、无线直连、驱动与设备离线相关。",
    },
    "power": {
        "label": "电源与开机",
        "description": "无法开机、自动断电、电源指示灯异常。",
    },
    "scanner": {
        "label": "扫描与复印",
        "description": "扫描无响应、复印偏色、扫描质量相关。",
    },
    "other": {
        "label": "其他",
        "description": "暂未归入上述分类的问题。",
    },
}

# 中文/常用说法 → 统一分类
CATEGORY_ALIASES: dict[str, str] = {
    "paper": "paper_feed",
    "卡纸": "paper_feed",
    "进纸": "paper_feed",
    "纸张": "paper_feed",
    "不进纸": "paper_feed",
    "ink": "ink_supply",
    "墨盒": "ink_supply",
    "墨水": "ink_supply",
    "加墨": "ink_supply",
    "耗材": "ink_supply",
    "打印质量": "print_quality",
    "断线": "print_quality",
    "条纹": "print_quality",
    "偏色": "print_quality",
    "喷头": "print_quality",
    "空白": "print_quality",
    "连接": "connectivity",
    "网络": "connectivity",
    "wifi": "connectivity",
    "wi-fi": "connectivity",
    "无线": "connectivity",
    "离线": "connectivity",
    "驱动": "connectivity",
    "电源": "power",
    "开机": "power",
    "扫描": "scanner",
    "复印": "scanner",
}

BRAND_CODE_SYSTEMS: dict[str, str] = {
    "HP": "HP 错误代码/指示灯",
    "Canon": "Canon Support Code",
    "Epson": "Epson 指示灯组合/消息",
    "Brother": "Brother LED/消息",
}

# 首期型号范围最常见的可核验代码（演示数据集，实际以官方资料为准）
BRAND_ERROR_CODES: dict[str, dict[str, dict[str, str]]] = {
    "HP": {
        "E1": {
            "category": "paper_feed",
            "label": "进纸相关错误",
            "description": "与进纸或纸张路径有关，按当前型号官方说明检查进纸通道。",
        },
        "E2": {
            "category": "paper_feed",
            "label": "纸张尺寸/进纸错误",
            "description": "检查纸张尺寸设置、纸张是否放置平整，并按官方说明处理。",
        },
        "E3": {
            "category": "paper_feed",
            "label": "卡纸",
            "description": "检查进纸盒、出纸区域与后部清理门是否有可见纸张残片。",
        },
        "E4": {
            "category": "paper_feed",
            "label": "卡纸/进纸异常",
            "description": "先按当前型号官方说明检查进纸通道，确认是否有可见纸张残片。",
        },
        "E5": {
            "category": "ink_supply",
            "label": "墨盒/打印头相关错误",
            "description": "按官方说明重新安装墨盒并检查触点，不要自行拆解打印头。",
        },
    },
    "Canon": {
        "E02": {
            "category": "paper_feed",
            "label": "无纸/进纸问题",
            "description": "检查纸张放置和进纸设置，按 Canon Support Code 页面说明处理。",
        },
        "E03": {
            "category": "paper_feed",
            "label": "卡纸",
            "description": "检查出纸口、后端托盘和内部可见纸张残片。",
        },
        "E05": {
            "category": "print_quality",
            "label": "打印头/FINE 墨盒识别问题",
            "description": "按官方说明重新安装 FINE 墨盒并检查触点。",
        },
        "E07": {
            "category": "paper_feed",
            "label": "纸张卡住",
            "description": "按 Canon 官方卡纸处理说明检查纸张路径。",
        },
        "E15": {
            "category": "ink_supply",
            "label": "墨水余量/墨盒错误",
            "description": "按官方说明检查墨盒安装状态和墨水余量。",
        },
    },
    "Epson": {
        "E01": {
            "category": "paper_feed",
            "label": "进纸/纸张错误",
            "description": "按 L3250 用户指南检查纸张放置与进纸状态。",
        },
        "E02": {
            "category": "paper_feed",
            "label": "卡纸",
            "description": "按型号用户指南检查进纸口和内部可见卡纸。",
        },
        "E11": {
            "category": "ink_supply",
            "label": "墨水余量/墨仓状态提示",
            "description": "按用户指南检查墨仓墨量并完成补充墨水流程。",
        },
    },
    "Brother": {
        "PAPER_JAM": {
            "category": "paper_feed",
            "label": "卡纸",
            "description": "按 DCP-T420W 官方卡纸 FAQ 检查纸盒和内部纸张路径。",
        },
        "NO_PAPER": {
            "category": "paper_feed",
            "label": "无纸/不进纸",
            "description": "检查纸张放置、纸盒设置和进纸滚轮。",
        },
        "INK_LOW": {
            "category": "ink_supply",
            "label": "墨水余量不足",
            "description": "按官方说明补充对应颜色墨水。",
        },
    },
}

SYMPTOM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "paper_feed": (
        "卡纸",
        "不进纸",
        "进纸",
        "纸张",
        "纸卡",
        "多张",
        "歪斜",
        "paper jam",
        "feed",
    ),
    "ink_supply": ("墨盒", "墨水", "加墨", "油墨", "墨量", "缺墨", "ink", "cartridge", "toner"),
    "print_quality": (
        "断线",
        "条纹",
        "偏色",
        "颜色",
        "空白",
        "喷头",
        "打印质量",
        "模糊",
        "quality",
        "stripe",
        "nozzle",
    ),
    "connectivity": (
        "wifi",
        "wi-fi",
        "无线",
        "网络",
        "连接",
        "离线",
        "驱动",
        "usb",
        "network",
        "offline",
        "connect",
    ),
    "power": ("电源", "开机", "断电", "不通电", "power", "boot"),
    "scanner": ("扫描", "复印", "scan", "copy"),
}


def list_categories() -> list[dict]:
    """返回统一故障分类列表，供前端筛选使用。"""
    return [
        {"code": code, "label": meta["label"], "description": meta["description"]}
        for code, meta in FAULT_CATEGORIES.items()
    ]


def category_label(code: str | None) -> str:
    if not code:
        return "未分类"
    return FAULT_CATEGORIES.get(code, {}).get("label", code)


def normalize_category(value: str | None) -> str | None:
    """把统一分类码、中文标签或常见说法归一化。"""
    if not value:
        return None
    text = value.strip().lower()
    if text in FAULT_CATEGORIES:
        return text
    if text in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[text]
    for code, meta in FAULT_CATEGORIES.items():
        if text == meta["label"].lower():
            return code
    return None


def classify_symptom(text: str | None) -> str | None:
    """基于关键词给出故障大类，仅供路由；证据不足时仍会澄清。"""
    if not text:
        return None
    lowered = text.lower()
    best: tuple[int, str] | None = None
    for category, keywords in SYMPTOM_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in lowered)
        if hits and (best is None or hits > best[0]):
            best = (hits, category)
    return best[1] if best else None


def _brand_key(brand_code: str | None) -> str | None:
    if not brand_code:
        return None
    target = brand_code.upper()
    for key in BRAND_CODE_SYSTEMS:
        if key.upper() == target:
            return key
    return None


def code_system_for(brand_code: str | None) -> str | None:
    key = _brand_key(brand_code)
    return BRAND_CODE_SYSTEMS.get(key) if key else None


def lookup_error_code(brand_code: str, code: str | None) -> dict | None:
    """按品牌查询错误码，禁止跨品牌映射。"""
    if not brand_code or not code:
        return None
    key = _brand_key(brand_code)
    codes = BRAND_ERROR_CODES.get(key, {}) if key else {}
    normalized = code.strip().upper()
    if normalized in codes:
        return {"brand_code": brand_code.upper(), "code": normalized, **codes[normalized]}
    # 允许 HP 的 E4 以 e4 输入；其他品牌保持原样
    for item_code, value in codes.items():
        if item_code.upper() == normalized:
            return {"brand_code": brand_code.upper(), "code": item_code, **value}
    return None


def known_codes_for_brand(brand_code: str | None) -> list[dict]:
    key = _brand_key(brand_code)
    codes = BRAND_ERROR_CODES.get(key, {}) if key else {}
    return [
        {"code": code, "category": meta["category"], "label": meta["label"]}
        for code, meta in codes.items()
    ]
