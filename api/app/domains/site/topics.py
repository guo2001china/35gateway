from __future__ import annotations


TOPIC_ORDER = ["gateway", "routing", "pricing-guide", "self-hosted", "async-tasks", "catalog-api"]


TOPIC_PAGES = {
    "gateway": {
        "slug": "openai-compatible-api-gateway",
        "page_title": "什么是 OpenAI-compatible API gateway | 35m.ai",
        "page_description": "解释什么是 OpenAI-compatible API gateway，以及它为什么适合统一接入文本、图片、视频模型和保留价格、成功率、耗时可见。",
        "eyebrow": "Answer page",
        "title_lines": ["什么是", "OpenAI-compatible API gateway"],
        "lead": "它不是一个换皮代理，也不是简单把多个供应商藏到后面。更准确地说，它是一层兼容 OpenAI 风格请求的模型接入层，让团队可以保持熟悉的接口形状，同时把结果和运行信息继续留在自己的系统里。",
        "direct_answer": "OpenAI-compatible API gateway 是一层接受 OpenAI 风格请求、再把它们路由到不同模型和供应商的接入层。它的价值不只是兼容，更在于把统一入口、可见价格、可见成功率和部署选择放进同一套操作路径里。",
        "facts": [
            {"label": "Interface", "text": "请求格式保持熟悉，接入阻力更低"},
            {"label": "Visibility", "text": "价格、成功率、耗时不必在调用后消失"},
            {"label": "Control", "text": "托管、自托管、代理环境都能落地"},
        ],
        "actions": [
            {"label": "打开 API 文档", "route": "docs", "primary": True},
            {"label": "查看部署方式", "route": "deploy", "primary": False},
        ],
        "sections": [
            {
                "title": "它解决的不是“换模型”本身",
                "description": "真正的痛点通常不是把一个 endpoint 改成另一个，而是让团队在更多模型和供应商之间保持一致的接入方式，同时避免结果成为黑盒。",
                "bullets": [
                    "保持 OpenAI-compatible 请求结构，降低第一条接入链路的迁移成本。",
                    "让价格、成功率、耗时继续停留在平台输出里，而不是散落到别处。",
                    "把模型接入层从前端业务代码里抽离，避免每个项目都自己重做一遍。",
                ],
            },
            {
                "title": "为什么不是直接对接每家供应商",
                "description": "直接对接当然可以，但团队一旦同时使用文本、图片、视频模型，接口形状、计价口径、任务状态和网络环境就会迅速分裂。",
                "bullets": [
                    "每多一家供应商，认证、重试、路由和观测都会再复制一次。",
                    "图片和视频接口常常不是同步返回，任务查询和下载链路也要单独接。",
                    "当预算和稳定性开始重要时，缺少统一可见性会让决策变慢。",
                ],
            },
            {
                "title": "35m.ai 在这层里的角色",
                "description": "35m.ai 更像一个“兼容接口 + 运行可见性 + 部署选择”的组合层，而不是只负责转发的轻代理。",
                "bullets": [
                    "统一暴露文本、图片、视频模型的入口形状。",
                    "支持请求前预计费，让高成本请求先做预算判断。",
                    "保留 hosted、自托管和代理环境三种落地方式，适合小团队逐步长大。",
                ],
            },
        ],
        "faq": [
            {
                "q": "它只是一个代理吗？",
                "a": "不是。代理只解决转发；gateway 更关注统一接口、路由策略、结果可见性和后续部署选择。",
            },
            {
                "q": "用了 gateway 之后还需要理解供应商吗？",
                "a": "需要，但顺序会变。团队可以先通过统一入口跑通链路，再深入理解不同供应商的差异。",
            },
            {
                "q": "什么时候不需要这层？",
                "a": "如果你只用单一供应商、单一模型类型，而且没有观测和部署要求，直接对接会更简单。",
            },
        ],
        "related": ["routing", "pricing-guide", "self-hosted"],
        "card_title": "OpenAI-compatible API gateway",
        "card_summary": "为什么兼容接口只是第一步，真正的价值在统一入口和结果可见性。",
    },
    "routing": {
        "slug": "ai-model-routing",
        "page_title": "什么是 AI model routing | 35m.ai",
        "page_description": "解释什么是 AI model routing、为什么路由策略对统一接入重要，以及 35m.ai 如何把模型路由做成可理解的页面与接口。",
        "eyebrow": "Routing",
        "title_lines": ["什么是", "AI model routing"],
        "lead": "模型路由不是“随机选一家供应商”。更准确地说，它是在同一套业务请求下，决定哪条模型路径最合适，并把这个决定保持为可解释的信息。",
        "direct_answer": "AI model routing 是根据模型能力、可用性、价格、时延或部署约束，把一次请求定向到最合适执行路径的过程。路由真正有价值的前提，不是自动化本身，而是用户还能看懂它为什么这样做。",
        "facts": [
            {"label": "Decision", "text": "模型路由本质上是在同一个请求下做路径选择"},
            {"label": "Signal", "text": "可用性、价格、时延和环境约束都可能影响结果"},
            {"label": "Visibility", "text": "路由如果不可解释，就很难被团队信任"},
        ],
        "actions": [
            {"label": "查看模型目录", "route": "models", "primary": True},
            {"label": "查看价格页", "route": "pricing", "primary": False},
        ],
        "sections": [
            {
                "title": "路由不是为了“花哨”",
                "description": "团队真正需要路由，通常是因为不同模型和供应商在价格、成功率、延迟和网络条件上都有差异，而不是因为想做一个复杂系统。",
                "bullets": [
                    "同一种模型能力，在不同供应商之间可能对应不同的成本和可用性。",
                    "图片和视频工作流的延迟差异更明显，错误恢复也更重要。",
                    "如果没有明确规则，路由只会变成新的黑盒。",
                ],
            },
            {
                "title": "为什么 route group 很重要",
                "description": "route group 给团队一个中间层，让模型不必直接绑死到某个供应商。页面和目录接口也因此能同时解释“模型名”和“路由归属”。",
                "bullets": [
                    "模型可以通过 route group 暴露成更稳定的业务入口。",
                    "供应商变化时，不需要每次都回到业务代码层面修改。",
                    "静态页能解释范围，动态目录能继续解释更细的执行差异。",
                ],
            },
            {
                "title": "35m.ai 里路由如何可见",
                "description": "35m.ai 不把路由只藏在内部配置里，而是尽量通过模型目录、价格信息和结果信号把它变成用户可读的系统行为。",
                "bullets": [
                    "模型页解释 route group 和入口关系。",
                    "价格与延迟信息帮助团队理解为什么某条路径值得被选择。",
                    "部署页继续解释 hosted、自托管和代理环境对路由的影响。",
                ],
            },
        ],
        "faq": [
            {
                "q": "模型路由一定要动态吗？",
                "a": "不一定。很多团队先从静态 route group 开始，再逐步增加更细的策略和可用性判断。",
            },
            {
                "q": "有 fallback 就等于路由做好了吗？",
                "a": "不等于。fallback 只是失败后的备选，真正的路由还包括前置选择、成本判断和结果解释。",
            },
            {
                "q": "路由会不会把供应商差异完全藏掉？",
                "a": "不应该。更好的做法是把业务入口统一起来，同时保留供应商差异的可见层。",
            },
        ],
        "related": ["gateway", "pricing-guide", "catalog-api"],
        "card_title": "AI model routing",
        "card_summary": "为什么路由不是黑盒自动化，而是需要让用户理解的路径选择。",
    },
    "pricing-guide": {
        "slug": "transparent-ai-pricing",
        "page_title": "什么是 transparent AI pricing | 35m.ai",
        "page_description": "解释什么是透明 AI 定价、为什么请求前预计费很重要，以及为什么静态价格页和动态目录需要同时存在。",
        "eyebrow": "Pricing answer",
        "title_lines": ["什么是", "transparent AI pricing"],
        "lead": "透明定价不等于“把一个价格表丢出来”。更重要的是，让团队在调用前能估算、调用后能解释，并知道哪些价格是静态口径，哪些是动态结果。",
        "direct_answer": "transparent AI pricing 指的是，团队不仅能看到价格，还能理解这个价格处在什么口径、什么时候生效、调用前能不能先估算、调用后又该如何复盘。真正的透明不是数字本身，而是上下文。",
        "facts": [
            {"label": "Before request", "text": "高成本请求应该先估算，而不是先执行"},
            {"label": "After request", "text": "结果回来后要能解释价格和时延，而不是只留一个响应"},
            {"label": "Layering", "text": "静态价格页和动态目录承担的职责不一样"},
        ],
        "actions": [
            {"label": "查看价格页", "route": "pricing", "primary": True},
            {"label": "查看模型目录", "route": "models", "primary": False},
        ],
        "sections": [
            {
                "title": "为什么透明定价不是一张表",
                "description": "文本、图片、视频的价格单位并不一样，而且动态执行结果也会让“真实成本”与静态展示之间存在层次。",
                "bullets": [
                    "文本通常以 token 计价，图片按图，视频按秒或任务维度。",
                    "供应商和执行模式不同，最终成本的解释方式也会不同。",
                    "没有上下文的价格表，往往无法真正帮助预算决策。",
                ],
            },
            {
                "title": "为什么要先看预计费",
                "description": "如果一个请求本身就很贵，那么“先估算再创建”不是锦上添花，而是预算控制的起点。",
                "bullets": [
                    "图片和视频能力更适合先估算，再决定是否真正执行。",
                    "请求前预计费让价格判断前置，而不是在请求完成后追悔。",
                    "这一步也让平台可以把价格可见性纳入正式工作流，而不是临时说明文档。",
                ],
            },
            {
                "title": "为什么静态页和动态层都要有",
                "description": "静态价格页适合解释口径、单位和基础逻辑；动态目录适合继续承接供应商差异、实时状态和更细的结果事实。",
                "bullets": [
                    "静态页更适合 SEO、AEO 和第一次理解。",
                    "动态层更适合继续解释更细的执行差异。",
                    "两层并存，才不会让页面既太空又太重。",
                ],
            },
        ],
        "faq": [
            {
                "q": "估算价格会和最终价格完全一样吗？",
                "a": "不一定。估算的价值是先给预算判断，最终价格还会受到分辨率、时长、模式或执行结果影响。",
            },
            {
                "q": "为什么图片和视频价格更需要被单独解释？",
                "a": "因为它们不像文本那样天然按 token 理解，单位和影响因子更容易让用户困惑。",
            },
            {
                "q": "价格页能完全替代动态目录吗？",
                "a": "不能。价格页适合解释框架，动态目录适合继续提供更细的事实层。",
            },
        ],
        "related": ["gateway", "routing", "catalog-api"],
        "card_title": "Transparent AI pricing",
        "card_summary": "为什么真正的透明不是一张表，而是调用前估算和调用后解释。",
    },
    "self-hosted": {
        "slug": "self-hosted-ai-api-gateway",
        "page_title": "什么是 self-hosted AI API gateway | 35m.ai",
        "page_description": "解释什么是 self-hosted AI API gateway、为什么团队会选择自托管，以及托管与自托管之间哪些能力应保持一致。",
        "eyebrow": "Deployment answer",
        "title_lines": ["什么是", "self-hosted AI API gateway"],
        "lead": "自托管不只是“把服务放到自己的机器上”。更重要的是，团队希望继续掌控密钥、出站链路、环境边界和部署节奏，同时又不想放弃统一接口和结果可见性。",
        "direct_answer": "self-hosted AI API gateway 是部署在自己环境里的模型接入层。它通常用于让团队掌控 API Key、网络出口、环境隔离和升级节奏，同时保留统一接口和对结果、价格、状态的可见性。",
        "facts": [
            {"label": "Control", "text": "密钥、网络出口和运行环境都由团队自己掌控"},
            {"label": "Parity", "text": "托管与自托管最好保持同一套接口形状"},
            {"label": "Fit", "text": "它更像运维和合规选择，而不是更酷的默认选项"},
        ],
        "actions": [
            {"label": "查看部署页", "route": "deploy", "primary": True},
            {"label": "打开 API 文档", "route": "docs", "primary": False},
        ],
        "sections": [
            {
                "title": "为什么团队会走向自托管",
                "description": "最常见的原因不是“能不能自己搭”，而是希望把敏感信息、网络路径和上线节奏拉回自己的控制范围。",
                "bullets": [
                    "管理 API Key 和供应商配置的生命周期。",
                    "控制出站链路，尤其在受限网络环境里更重要。",
                    "让部署节奏和业务系统、合规流程保持一致。",
                ],
            },
            {
                "title": "托管和自托管不该是两套产品",
                "description": "更健康的做法是让托管版和自托管版尽量共用同一套接口和页面结构，只把运维责任和环境控制权区分开。",
                "bullets": [
                    "业务代码不应该因为部署模式变化就重写一遍。",
                    "营销页和帮助页最好仍然是静态优先，方便独立部署。",
                    "接口形状、价格说明和模型目录最好尽量保持一致。",
                ],
            },
            {
                "title": "35m.ai 的自托管语境",
                "description": "35m.ai 并不是把“自托管”当作炫技，而是把它作为 hosted 之外的另一条真实落地路径，并继续照顾代理与国内网络环境。",
                "bullets": [
                    "自托管与代理部署可以一起考虑，而不是二选一。",
                    "部署页先帮助团队做模式判断，再进入更细的镜像和环境变量层。",
                    "这类页面对 SEO 和 GEO 也更友好，因为问题本身很明确。",
                ],
            },
        ],
        "faq": [
            {
                "q": "自托管以后接口会变吗？",
                "a": "理想情况不该变。更好的系统应该让部署模式变化尽量不影响业务调用方式。",
            },
            {
                "q": "自托管还需要托管版官网吗？",
                "a": "需要。营销和发现层静态化，产品与数据层动态化，仍然是更健康的拆法。",
            },
            {
                "q": "代理部署和自托管是什么关系？",
                "a": "它们不是同一件事。自托管更关注控制权，代理部署更关注出站环境和网络适配。",
            },
        ],
        "related": ["gateway", "async-tasks", "catalog-api"],
        "card_title": "Self-hosted AI API gateway",
        "card_summary": "为什么自托管不是炫技，而是控制密钥、网络和部署节奏的一条真实路径。",
    },
    "async-tasks": {
        "slug": "async-task-api",
        "page_title": "什么是 async task API | 35m.ai",
        "page_description": "解释什么是 async task API、为什么视频和长时任务更适合异步接口，以及状态查询和结果下载应该怎样被设计。",
        "eyebrow": "Task API",
        "title_lines": ["什么是", "async task API"],
        "lead": "不是所有模型请求都适合同步返回。尤其是视频生成、较长图片任务或更重的多阶段工作流，更合理的做法是创建任务、查询状态、再下载结果。",
        "direct_answer": "async task API 是一种先创建任务、再查询状态、最后获取结果的接口形态。它常用于执行时间更长、成本更高、失败恢复更复杂的模型能力，尤其适合视频和其他长时生成工作流。",
        "facts": [
            {"label": "Lifecycle", "text": "创建任务、查询状态、获取结果是异步接口的基本路径"},
            {"label": "Fit", "text": "长时、高成本、可恢复性要求高的任务更适合异步"},
            {"label": "Clarity", "text": "任务 id、状态语义和下载路径必须设计清楚"},
        ],
        "actions": [
            {"label": "查看部署页", "route": "deploy", "primary": True},
            {"label": "查看模型目录", "route": "models", "primary": False},
        ],
        "sections": [
            {
                "title": "为什么视频接口通常走异步",
                "description": "视频任务天然更长、更贵，也更容易受到排队、超时和重试影响。同步等待经常既慢又难解释。",
                "bullets": [
                    "异步任务更适合把创建、等待、完成拆成更稳定的三个阶段。",
                    "轮询状态比一直卡着一个连接更容易被客户端管理。",
                    "失败恢复、重试和结果下载也更适合独立表达。",
                ],
            },
            {
                "title": "一个好的 async task API 该长什么样",
                "description": "异步接口的关键不是“有任务 id”而已，而是状态是否稳定、语义是否清楚、结果何时可以被安全消费。",
                "bullets": [
                    "创建任务时立即返回任务 id 和初始状态。",
                    "状态查询接口保持统一语义，而不是每个模型各说各话。",
                    "结果下载路径和失败原因需要可读，而不是继续成为黑盒。",
                ],
            },
            {
                "title": "35m.ai 里的任务型能力",
                "description": "35m.ai 把异步任务视为统一工作流的一部分，而不是某个视频模型的私有行为。这样页面、目录和接口说明才能一起解释同一件事。",
                "bullets": [
                    "视频模型的首页示例会先强调任务链路，而不是假装它和文本调用完全一样。",
                    "状态查询和结果下载继续通过统一任务接口承接。",
                    "价格、时延和部署路径仍然要和任务语义放在一起看。",
                ],
            },
        ],
        "faq": [
            {
                "q": "异步任务只适合视频吗？",
                "a": "不只适合视频，但视频是最典型的场景。任何执行时间更长、更贵或需要状态管理的任务都可能适合异步。",
            },
            {
                "q": "轮询状态是不是很笨？",
                "a": "不一定。对很多团队来说，统一且可控的轮询反而比零散 webhook 更容易落地。",
            },
            {
                "q": "异步接口会让开发更复杂吗？",
                "a": "会多一层状态管理，但它换来的是更稳的长任务处理和更清楚的失败恢复。",
            },
        ],
        "related": ["self-hosted", "routing", "catalog-api"],
        "card_title": "Async task API",
        "card_summary": "为什么长时视频和生成任务更适合创建任务、查状态、再取结果。",
    },
    "catalog-api": {
        "slug": "model-catalog-api",
        "page_title": "什么是 model catalog API | 35m.ai",
        "page_description": "解释什么是 model catalog API、为什么静态模型页和动态目录接口需要并存，以及如何用 /v1/models 和 provider 对比接口承接更细事实。",
        "eyebrow": "Catalog answer",
        "title_lines": ["什么是", "model catalog API"],
        "lead": "模型目录不只是“列一个名字清单”。更实用的目录接口应该既能支持静态可抓取页面，也能继续提供模型、路由、供应商和入口这些更细的动态事实。",
        "direct_answer": "model catalog API 是一层专门提供模型范围、公开模型名、调用入口、路由组和进一步查询路径的目录接口。它的价值在于把“页面上先看懂范围”和“系统里再看更细事实”分成两个协同层次。",
        "facts": [
            {"label": "Scope", "text": "静态模型页负责范围说明和第一次理解"},
            {"label": "Live facts", "text": "目录接口继续承接路由、入口和供应商差异"},
            {"label": "Layering", "text": "页面和 API 并存，抓取与产品都更健康"},
        ],
        "actions": [
            {"label": "查看模型页", "route": "models", "primary": True},
            {"label": "打开 API 文档", "route": "docs", "primary": False},
        ],
        "sections": [
            {
                "title": "为什么模型目录不能只有静态页面",
                "description": "静态页面适合解释主题和范围，但一旦涉及供应商状态、细粒度入口或更深的差异，就需要目录接口继续承接。",
                "bullets": [
                    "静态页面帮助用户先知道“这里能接什么”。",
                    "目录接口帮助系统继续知道“这些模型现在属于哪类入口和路由组”。",
                    "两层分工明确，比把所有事实堆在一个页面里更稳。",
                ],
            },
            {
                "title": "为什么目录接口也不能替代页面",
                "description": "单纯给一个 JSON 并不能替代对主题的解释。用户和搜索系统都需要先看到结构化文本，再决定是否深入接口层。",
                "bullets": [
                    "静态页更适合 SEO、AEO 和第一次理解。",
                    "目录接口更适合程序化消费和动态细节查询。",
                    "如果只剩 JSON，品牌和认知层会非常弱。",
                ],
            },
            {
                "title": "35m.ai 的目录层怎么分工",
                "description": "35m.ai 把静态模型页、公开模型目录和更细的 provider 对比接口拆开，让不同层次的用户都能在合适位置拿到信息。",
                "bullets": [
                    "模型页先解释模型范围、公开模型名、路由组和调用入口。",
                    "GET /v1/models 继续提供程序可读的目录层。",
                    "provider 对比接口继续承接更深的供应商事实。",
                ],
            },
        ],
        "faq": [
            {
                "q": "静态模型页的数据会实时变化吗？",
                "a": "不一定。静态页主要承担解释范围和入口的职责，实时变化更适合放在目录接口层。",
            },
            {
                "q": "什么时候应该直接读 /v1/models？",
                "a": "当你需要程序化消费模型列表、入口或路由信息时，直接读目录接口更合适。",
            },
            {
                "q": "provider 差异应该放在哪？",
                "a": "更适合放在专门的对比或 provider 明细接口里，而不是把首页和模型页变成运营控制台。",
            },
        ],
        "related": ["routing", "gateway", "pricing-guide"],
        "card_title": "Model catalog API",
        "card_summary": "为什么静态模型页和动态目录接口都需要存在，而且承担不同职责。",
    },
}
