from __future__ import annotations

import re

from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.site.doc_links import model_api_doc_href
from app.domains.site.info_pages import INFO_PAGES
from app.domains.site.navigation import localized_path, route_href
from app.domains.site.topics import TOPIC_PAGES


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _category_label(category: str) -> str:
    return {"text": "文本", "image": "图片", "video": "视频"}.get(category, category)


def _fallback_model_summary(*, category: str, route_group: str, endpoint: str) -> str:
    category_label = _category_label(category or "text")
    route_group = route_group or "-"
    endpoint = endpoint or "-"
    return f"{category_label}模型，在 35m.ai 上通过 {endpoint} 提供统一接入，当前路由组为 {route_group}。"


def _localized_model_summary(*, summary: str, category: str, route_group: str, endpoint: str) -> str:
    summary = summary.strip()
    if not summary:
        return _fallback_model_summary(category=category, route_group=route_group, endpoint=endpoint)
    return summary if _has_cjk(summary) else _fallback_model_summary(
        category=category,
        route_group=route_group,
        endpoint=endpoint,
    )


def _platform_snapshot():
    return get_platform_config_snapshot()


def group_models() -> dict[str, list[dict[str, str]]]:
    snapshot = _platform_snapshot()
    groups: dict[str, list[dict[str, str]]] = {"text": [], "image": [], "video": []}
    for model in snapshot.list_public_models():
        category = model.category
        if category not in groups:
            continue
        route = snapshot.get_primary_route(model.public_model_code, public_only=True)
        if route is None:
            continue
        create_endpoint = str(route.endpoints.get("create") or "-")
        groups[category].append(
            {
                "model_code": model.public_model_code,
                "display_name": model.display_name,
                "route_group": route.route_group,
                "endpoint": create_endpoint,
                "summary": _localized_model_summary(
                    summary=model.summary,
                    category=category,
                    route_group=route.route_group,
                    endpoint=create_endpoint,
                ),
            }
        )
    return groups


def _topic_illustration(topic_key: str) -> dict[str, str]:
    labels = {
        "gateway": "展示统一入口和多模型输出的网关示意图",
        "routing": "展示一条请求被路由到最优路径的示意图",
        "pricing-guide": "展示文本、图片、视频三类计价单位的示意图",
        "self-hosted": "展示托管与自托管边界的部署示意图",
        "async-tasks": "展示创建任务、查询状态、获取结果的异步流程图",
        "catalog-api": "展示静态目录页与动态目录接口协作关系的示意图",
    }
    return {
        "path": f"/illustrations/{topic_key}.svg",
        "alt": labels[topic_key],
    }


def topic_cards(keys: list[str]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for key in keys:
        topic = TOPIC_PAGES[key]
        illustration = _topic_illustration(key)
        cards.append(
            {
                "href": localized_path(key),
                "title": str(topic["card_title"]),
                "summary": str(topic["card_summary"]),
                "cta": "查看回答",
                "illustration_path": illustration["path"],
                "illustration_alt": illustration["alt"],
            }
        )
    return cards


def topic_page_content(topic_key: str) -> dict[str, object]:
    topic = TOPIC_PAGES[topic_key]
    details_section = {
        "kicker": "展开说明",
        "title": "把这个问题拆成三个更容易判断的部分。",
        "lead": "答案页不追求大而全，而是先给直接回答，再把为什么重要、为什么不能简化、35m.ai 怎么处理这件事拆开讲清楚。",
    }
    faq_section = {
        "kicker": "常见问题",
        "title": "继续把常见误解讲清楚。",
        "lead": "如果用户已经理解主答案，这一组问题通常就是他们下一步会继续确认的边界。",
    }
    related_section = {
        "kicker": "相关问题",
        "title": "继续看这些相关问题。",
        "lead": "把主题做成彼此可连接的答案页，会比把所有解释塞回首页更利于理解和搜索发现。",
    }
    return {
        **topic,
        "illustration": _topic_illustration(topic_key),
        "answer_label": "直接回答",
        "details_section": details_section,
        "faq_section": faq_section,
        "related_section": related_section,
        "sections": [{**section, "bullets": list(section["bullets"][:2])} for section in topic["sections"]],
        "faq": list(topic["faq"][:2]),
        "actions": [
            {"label": str(action["label"]), "href": route_href(str(action["route"])), "primary": bool(action["primary"])}
            for action in topic["actions"]
        ],
        "related_cards": topic_cards(list(topic["related"])),
    }


def info_page_content(page_key: str) -> dict[str, object]:
    page = dict(INFO_PAGES[page_key])
    if page_key == "support":
        actions = [
            {"label": "打开 API 文档", "href": "/docs", "primary": True},
            {"label": "查看模型目录", "href": localized_path("models"), "primary": False},
            {"label": "商务合作", "href": localized_path("contact"), "primary": False},
        ]
        page["related_cards"] = topic_cards(list(page.get("related") or []))
    else:
        actions = [
            {"label": "打开 API 文档", "href": "/docs", "primary": True},
            {"label": "查看模型目录", "href": localized_path("models"), "primary": False},
        ]
    return {**page, "actions": actions}


def home_content() -> dict[str, object]:
    hero_models = [
        {"model_code": "gpt-5.4", "label": "GPT-5.4", "type": "text", "route_group": "openai"},
        {"model_code": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "type": "text", "route_group": "openai"},
        {"model_code": "DeepSeek-V3.2", "label": "DeepSeek-V3.2", "type": "text", "route_group": "openai"},
        {"model_code": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "type": "text", "route_group": "openai"},
        {"model_code": "glm-4.7-flash", "label": "GLM 4.7 Flash", "type": "text", "route_group": "openai"},
        {"model_code": "nano-banana", "label": "Nano Banana", "type": "image", "route_group": "banana"},
        {"model_code": "veo-3.1", "label": "Veo 3.1", "type": "video", "route_group": "veo31"},
        {"model_code": "doubao-seedream-5.0-lite", "label": "Seedream 5.0 Lite", "type": "image", "route_group": "seedream"},
        {"model_code": "gpt-5.4-pro", "label": "GPT-5.4 Pro", "type": "responses", "route_group": "responses"},
        {"model_code": "gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro", "type": "text", "route_group": "openai"},
        {"model_code": "veo-3", "label": "Veo 3", "type": "video", "route_group": "veo3"},
        {"model_code": "nano-banana-2", "label": "Nano Banana 2", "type": "image", "route_group": "banana"},
    ]

    return {
        "page_title": "35m.ai | 文本、图片、视频模型统一接入",
        "page_description": "OpenAI-compatible 模型接入层。统一接入文本、图片、视频模型，价格、成功率、耗时可见，并支持托管与自托管部署。",
        "hero_eyebrow": "你的私人算力中心，一人公司｜龙虾🦞专用",
        "hero_title_lines": ["只提供 99.99% 的稳定大模型"],
        "hero_typewriter_lines": [
            "甚至很多免费模型！",
            "可使用自己的 Key 混合使用",
            "可以自己部署",
            "可以托管",
            "可以直接对接 API",
            "现在开始，30秒接入！",
        ],
        "hero_actions": [
            {"label": "控制台", "href": "/login", "primary": False, "console_entry": True},
            {"label": "打开 API 文档", "href": "/docs", "primary": True},
            {"label": "查看模型目录", "href": localized_path("models"), "primary": False},
        ],
        "hero_models": [
            {
                **item,
                "href": model_api_doc_href(model_code=item["model_code"], route_group=item["route_group"]),
            }
            for item in hero_models
        ],
        "hero_enterprise": {
            "title": "企业试用",
            "note": "适合需要 API 对接、自托管、代理部署或定制集成的团队。",
            "tags": ["API 对接", "自托管", "代理部署", "定制集成"],
            "action": {"label": "联系商务", "href": localized_path("contact")},
        },
        "hero_case_quotes": [
            {"who": "短剧工作室 · 张老师", "quote": "稳的一批，非常可以！"},
            {"who": "IT 公司 · 张总", "quote": "企业按需付费，成本确实降不少。"},
            {"who": "跨境电商团队 · 王经理", "quote": "图片和视频都能一起跑，效率高很多。"},
            {"who": "本地生活服务商 · 李总", "quote": "先看价格和耗时，再决定怎么跑，心里有底。"},
            {"who": "MCN 团队 · 陈老师", "quote": "批量起图和短视频都顺，出片速度明显快了。"},
            {"who": "独立开发者 · 刘工", "quote": "一个接口接起来，后面维护轻松太多。"},
            {"who": "教培内容团队 · 赵老师", "quote": "素材生成稳定，预算也比以前更可控。"},
            {"who": "游戏工作室 · 周制作", "quote": "概念图和宣传视频能统一调度，很省心。"},
        ],
    }


def models_content() -> dict[str, object]:
    return {
        "page_title": "35m.ai | 模型总览",
        "page_description": "35m.ai 模型与价格总页：统一展示文本、图片、视频模型的公开模型名、路由组、调用入口和价格口径。",
        "catalog_section": {
            "categories": [
                {"key": "image", "title": "图片", "summary": ""},
                {"key": "video", "title": "视频", "summary": ""},
                {"key": "text", "title": "文本", "summary": ""},
            ],
        },
    }

def deploy_content() -> dict[str, object]:
    return {
        "page_title": "35m.ai Deploy | API 对接、自托管、代理部署、定制集成",
        "page_description": "35m.ai 支持 API 对接、自托管、代理部署、定制集成。按你的网络和团队方式选择模式，直接联系商务经理。",
        "modes": [
            {
                "key": "api",
                "title": "API 对接",
                "description": "直接按统一接口接入文本、图片、视频模型，最快开始真实调用。",
                "tags": ["最快开始", "统一接口", "直接联调"],
                "highlight": True,
            },
            {
                "key": "self-hosted",
                "title": "自托管",
                "description": "部署到你自己的服务器、私有云或隔离环境里。",
                "tags": ["密钥自管", "私有环境", "隔离部署"],
            },
            {
                "key": "proxy",
                "title": "代理部署",
                "description": "适合受限网络、多出口或香港机房这类真实环境。",
                "tags": ["代理网关", "出海链路", "网络适配"],
            },
            {
                "key": "custom",
                "title": "定制集成",
                "description": "按你现有系统、流程和业务限制做定制接入。",
                "tags": ["系统对接", "权限流程", "交付要求"],
            },
        ],
        "modal": {
            "eyebrow": "商务",
            "title": "联系商务经理",
            "default_note": "把你的目标模型、网络环境和接入方式一起发过来，会更快进入对接。",
            "qr_alt": "商务经理二维码",
            "placeholder": "商务经理二维码待配置",
            "contact_pending": "联系方式待配置",
            "save_hint": "手机端可长按保存二维码，再用微信识别。",
        },
    }
