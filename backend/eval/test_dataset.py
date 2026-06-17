"""RAG 评估测试数据集。

基于 kb_9 知识库（网络配置文档：PAP 认证、路由器配置、OSPF 等）构建，
包含 ground truth 答案和相关文档片段索引。
"""

# kb_9 中所有文档片段的索引映射
# chunk 0: 标题 "基于PAP认证的公司与分部安全互联"
# chunk 1: 项目背景 - 公司总部与分公司互联需求
# chunk 2: 项目背景 - 具体要求（R1 S4/0/0, PPP PAP, OSPF）
# chunk 3: 项目规划设计 - PPP封装, PAP认证, AAA视图
# chunk 4-9: IP地址规划表
# chunk 10: 端口规划表
# chunk 11: 项目实施 - R1配置 (system-view, OSPF, PPP PAP)
# chunk 12-13: R2配置 (OSPF area 0)
# chunk 14-15: PPP PAP认证命令 (ppp authentication-mode pap)
# chunk 16-23: 验证阶段 - 链路状态, ping测试, 100% packet loss (认证未通过)
# chunk 24-25: R2配置PAP验证 (ppp pap local-user Jan16 password cipher 123456)
# chunk 26-27: PC IP配置
# chunk 28-37: 项目验证 - 链路正常, ping成功, 0% packet loss

# ============================================================
# 检索质量评估数据集
# 每条记录: {
#   "question": 用户问题,
#   "ground_truth_answer": 标准答案,
#   "relevant_chunk_ids": 相关文档片段索引列表（用于计算召回率/精确率）,
#   "irrelevant_chunk_ids": 不相关片段索引（可选，用于精确率计算）
# }
# ============================================================

RETRIEVAL_TEST_SET = [
    {
        "question": "这个项目的背景是什么？为什么需要配置PAP认证？",
        "ground_truth_answer": "Jan16公司因业务发展建立了分公司，租用专门线路用于总部与分公司互联。为保障通信线路的数据安全，需要在路由器上配置安全认证，采用PPP协议的PAP认证方式。",
        "relevant_chunk_ids": [1, 2, 3],
    },
    {
        "question": "R1和R2之间使用什么接口互联？IP地址分别是多少？",
        "ground_truth_answer": "R1使用S4/0/0接口与R2的S4/0/0接口互联。R1的S4/0/0接口IP为10.10.10.1/24，R2的S4/0/0接口IP为10.10.10.2/24。",
        "relevant_chunk_ids": [2, 4, 5, 6, 7, 8, 9, 10],
    },
    {
        "question": "如何在R1上配置PPP的PAP认证？",
        "ground_truth_answer": "在R1的Serial4/0/0接口下执行命令：[R1-Serial4/0/0]ppp authentication-mode pap。同时需要在AAA视图下添加用户名Jan16和密码123456。",
        "relevant_chunk_ids": [3, 11, 14, 15],
    },
    {
        "question": "R2作为被认证端，如何配置PAP验证？",
        "ground_truth_answer": "R2在S4/0/0接口下配置PAP方式验证时本地发送的用户名和密码：[R2-Serial4/0/0]link-protocol ppp，[R2-Serial4/0/0]ppp pap local-user Jan16 password cipher 123456。",
        "relevant_chunk_ids": [24, 25, 26],
    },
    {
        "question": "项目中OSPF是如何配置的？",
        "ground_truth_answer": "全网通过OSPF协议互联。R1配置：ospf 1, area 0, network 192.168.10.0 0.0.0.255。R2配置：ospf 1, area 0, network 192.168.20.0 0.0.0.255。",
        "relevant_chunk_ids": [2, 11, 12, 13],
    },
    {
        "question": "PAP认证配置完成后，如何验证链路是否正常？",
        "ground_truth_answer": "首先查看链路状态（dis ip int brief），确认Physical和Protocol都是up状态。然后从PC1 ping PC2（192.168.20.1），如果0% packet loss则说明链路正常。认证未通过时会出现100% packet loss。",
        "relevant_chunk_ids": [16, 17, 18, 19, 20, 21, 22, 23, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37],
    },
    {
        "question": "认证未通过时会出现什么现象？",
        "ground_truth_answer": "认证未通过时，链路物理状态正常但链路层协议状态不正常。ping测试会出现100% packet loss，即5 packet(s) transmitted, 0 packet(s) received。",
        "relevant_chunk_ids": [19, 20, 21, 22, 23],
    },
    {
        "question": "PC1和PC2的IP地址分别是什么？",
        "ground_truth_answer": "PC1的IP地址是192.168.10.1/24，PC2的IP地址是192.168.20.1/24。",
        "relevant_chunk_ids": [8, 9, 26, 27],
    },
    {
        "question": "认证通过后ping测试的结果是什么？",
        "ground_truth_answer": "认证通过后，PC间正常通信。ping测试结果为5 packet(s) transmitted, 5 packet(s) received, 0.00% packet loss，round-trip min/avg/max = 47/62/78 ms。",
        "relevant_chunk_ids": [32, 33, 34, 35, 36, 37],
    },
    {
        "question": "R1的G0/0/1接口IP地址是什么？",
        "ground_truth_answer": "R1的GigabitEthernet0/0/1接口IP地址是192.168.10.254/24。",
        "relevant_chunk_ids": [4, 11],
    },
    {
        "question": "端口规划表中R1的S4/0/0连接到哪个设备的哪个接口？",
        "ground_truth_answer": "根据端口规划表，R1的S4/0/0接口连接到R2的S4/0/0接口。",
        "relevant_chunk_ids": [9, 10],
    },
    {
        "question": "这个项目中使用了哪些网络协议？",
        "ground_truth_answer": "项目中使用了PPP（点对点协议）用于串行链路封装，PAP（密码认证协议）用于链路安全认证，OSPF（开放最短路径优先）用于全网路由互联。",
        "relevant_chunk_ids": [1, 2, 3, 11, 12, 13, 14, 15],
    },
]

# ============================================================
# 生成质量评估数据集（Ragas 格式）
# ============================================================

GENERATION_TEST_SET = [
    {
        "question": "这个项目的背景是什么？",
        "ground_truth_answer": "Jan16公司因业务发展建立了分公司，需要在总部与分公司之间建立安全的网络连接。通过租用专门线路，在路由器上配置PPP协议的PAP认证来保障数据安全。",
        "expected_behavior": "answerable",
    },
    {
        "question": "如何配置R1的PAP认证？",
        "ground_truth_answer": "在R1的Serial4/0/0接口下执行ppp authentication-mode pap命令启用PAP认证，然后在AAA视图下创建用户名Jan16和密码123456。",
        "expected_behavior": "answerable",
    },
    {
        "question": "R2的PAP被认证端如何配置？",
        "ground_truth_answer": "R2在S4/0/0接口下先执行link-protocol ppp，再执行ppp pap local-user Jan16 password cipher 123456配置本地PAP用户名和密码。",
        "expected_behavior": "answerable",
    },
    {
        "question": "认证失败时会有什么表现？",
        "ground_truth_answer": "认证失败时链路物理层正常但协议层不正常，ping测试显示100% packet loss。",
        "expected_behavior": "answerable",
    },
    {
        "question": "OSPF在这个项目中是怎么用的？",
        "ground_truth_answer": "全网通过OSPF协议互联，R1和R2各自在area 0中宣告直连网段，实现路由互通。",
        "expected_behavior": "answerable",
    },
    {
        "question": "这个项目的网络拓扑是怎样的？",
        "ground_truth_answer": "总部R1路由器通过S4/0/0串口连接分公司R2路由器，R1的G0/0/1连接SW1和PC1（192.168.10.0/24网段），R2的G0/0/1连接SW2和PC2（192.168.20.0/24网段）。",
        "expected_behavior": "answerable",
    },
    {
        "question": "公司食堂几点开门？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
    },
    {
        "question": "如何申请年假？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
    },
    {
        "question": "这个项目用了什么编程语言开发？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
    },
    {
        "question": "PAP认证的用户名和密码分别是什么？",
        "ground_truth_answer": "用户名是Jan16，密码是123456。",
        "expected_behavior": "answerable",
    },
]

# ============================================================
# 多轮对话评估数据集
# ============================================================

MULTI_TURN_TEST_SET = [
    {
        "turns": [
            {"question": "这个项目是做什么的？", "expected_keywords": ["PAP", "认证", "互联", "安全"]},
            {"question": "R1和R2之间用什么协议？", "expected_keywords": ["PPP", "PAP"]},
            {"question": "认证配置的具体命令是什么？", "expected_keywords": ["ppp authentication-mode pap", "ppp pap local-user"]},
            {"question": "配置完成后怎么验证？", "expected_keywords": ["ping", "packet loss", "dis ip int brief"]},
        ],
        "description": "渐进式深入：项目概述→协议→命令→验证",
    },
    {
        "turns": [
            {"question": "R1的IP地址是多少？", "expected_keywords": ["192.168.10.254", "10.10.10.1"]},
            {"question": "R2呢？", "expected_keywords": ["192.168.20.254", "10.10.10.2"]},
            {"question": "PC之间能通信吗？", "expected_keywords": ["ping", "0%", "packet loss"]},
        ],
        "description": "指代消解：测试模型对'R2呢'这类省略问句的理解",
    },
]

# ============================================================
# 端到端评估数据集
# ============================================================

E2E_TEST_SET = [
    {
        "question": "请详细介绍一下这个PAP认证项目的完整实施步骤。",
        "checklist": {
            "mentions_background": True,
            "mentions_ip_planning": True,
            "mentions_pap_config": True,
            "mentions_ospf_config": True,
            "mentions_verification": True,
            "structured_answer": True,
        },
    },
    {
        "question": "如果ping测试失败，应该如何排查？",
        "checklist": {
            "mentions_check_interface_status": True,
            "mentions_check_auth_config": True,
            "mentions_practical_steps": True,
        },
    },
    {
        "question": "简要说明PAP认证的工作原理。",
        "checklist": {
            "mentions_username_password": True,
            "mentions_authenticator_and_peer": True,
            "concise": True,
        },
    },
]
