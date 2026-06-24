"""RAG 评估测试数据集 v2.0。

基于 kb_4 知识库（12个chunk）和 kb_1 知识库（123个chunk）构建，
包含多样化的测试场景，提升评估可信度。

数据集结构：
- RETRIEVAL_TEST_SET: 检索质量评估（40条）
- GENERATION_TEST_SET: 生成质量评估（25条）
- MULTI_TURN_TEST_SET: 多轮对话评估（5组）
- E2E_TEST_SET: 端到端评估（10条）
- ADVERSARIAL_TEST_SET: 对抗性测试（10条）
- CROSS_KB_TEST_SET: 跨知识库测试（8条）
"""

# ============================================================
# kb_4 chunk 索引映射（PAP认证项目，12个chunk）
# ============================================================
# chunk_0: 项目背景 - Jan16公司总部与分公司互联，需配置PAP认证
# chunk_1: 配置步骤概述 + IP地址规划表 + 端口规划表
# chunk_2: 端口规划表续 + R1接口配置（system-view, sysname, ip add）
# chunk_3: R2接口配置 + OSPF配置（R1 area 0 network 192.168.10.0）
# chunk_4: OSPF续（R2 area 0 network 192.168.20.0）+ PPP PAP认证配置开始
# chunk_5: PAP认证配置续 + dis ip interface brief 结果
# chunk_6: dis ip int brief 结果续（接口状态表）
# chunk_7: ping 10.10.10.2 结果: 100% packet loss + 原因分析 + R2 PAP配置
# chunk_8: R2 PAP配置续 + PC IP配置说明 + R2 dis ip int brief 结果
# chunk_9: R2接口状态表续 + ping测试成功 + PC1 ping PC2 结果
# chunk_10: PC>ping 192.168.20.1 结果: 5/5 received
# chunk_11: ping统计: 0% packet loss, round-trip min/avg/max = 47/62/78 ms

# ============================================================
# kb_1 chunk 索引映射（4个文档混合，123个chunk）
# ============================================================
# Source 1: 商客融合套餐培训材料 - chunk_40 ~ chunk_109 (70 chunks)
# Source 2: IP地址与ARP基础知识 - chunk_110 ~ chunk_128 (19 chunks)
# Source 3: NAT基础 - chunk_129 ~ chunk_133, chunk_141-146, chunk_150-152 (13 chunks)
# Source 4: 防火墙基础 - chunk_134 ~ chunk_140, chunk_147-149, chunk_153-162 (21 chunks)

# ============================================================
# 检索质量评估数据集 (40条)
# 覆盖：事实查询、配置查询、验证查询、综合查询、边界情况
# ============================================================

RETRIEVAL_TEST_SET = [
    # === 简单事实查询（5条）===
    {
        "id": "R01",
        "category": "simple_facts",
        "difficulty": "easy",
        "question": "这个项目的背景是什么？为什么需要配置PAP认证？",
        "ground_truth_answer": "Jan16公司因业务发展建立了分公司，租用专门线路用于总部与分公司互联。为保障通信线路的数据安全，需要在路由器上配置安全认证，采用PPP协议的PAP认证方式。",
        "relevant_chunk_ids": [0],
    },
    {
        "id": "R02",
        "category": "simple_facts",
        "difficulty": "easy",
        "question": "R1和R2之间使用什么接口互联？",
        "ground_truth_answer": "R1使用Serial4/0/0接口与R2的Serial4/0/0接口互联。",
        "relevant_chunk_ids": [0, 1, 2],
    },
    {
        "id": "R03",
        "category": "simple_facts",
        "difficulty": "easy",
        "question": "PC1和PC2的IP地址分别是什么？",
        "ground_truth_answer": "PC1的IP地址是192.168.10.1/24，PC2的IP地址是192.168.20.1/24。",
        "relevant_chunk_ids": [1, 8],
    },
    {
        "id": "R04",
        "category": "simple_facts",
        "difficulty": "easy",
        "question": "PAP认证的用户名和密码是什么？",
        "ground_truth_answer": "用户名是Jan16，密码是123456。",
        "relevant_chunk_ids": [4, 7, 8],
    },
    {
        "id": "R05",
        "category": "simple_facts",
        "difficulty": "easy",
        "question": "项目中使用了哪些网络协议？",
        "ground_truth_answer": "项目中使用了PPP（点对点协议）用于串行链路封装，PAP（密码认证协议）用于链路安全认证，OSPF（开放最短路径优先）用于全网路由互联。",
        "relevant_chunk_ids": [0, 3, 4, 5],
    },

    # === IP地址查询（6条）===
    {
        "id": "R06",
        "category": "ip_address",
        "difficulty": "easy",
        "question": "R1的G0/0/1接口IP地址是什么？",
        "ground_truth_answer": "R1的GigabitEthernet0/0/1接口IP地址是192.168.10.254/24。",
        "relevant_chunk_ids": [1, 2],
    },
    {
        "id": "R07",
        "category": "ip_address",
        "difficulty": "easy",
        "question": "R2的S4/0/0接口IP地址是什么？",
        "ground_truth_answer": "R2的Serial4/0/0接口IP地址是10.10.10.2/24。",
        "relevant_chunk_ids": [1],
    },
    {
        "id": "R08",
        "category": "ip_address",
        "difficulty": "medium",
        "question": "R1和R2之间互联链路的网段是什么？",
        "ground_truth_answer": "R1和R2之间互联链路使用10.10.10.0/24网段，R1为10.10.10.1，R2为10.10.10.2。",
        "relevant_chunk_ids": [1],
    },
    {
        "id": "R09",
        "category": "ip_address",
        "difficulty": "medium",
        "question": "总部和分公司各自的局域网网段是什么？",
        "ground_truth_answer": "总部局域网网段是192.168.10.0/24（R1的G0/0/1连接），分公司局域网网段是192.168.20.0/24（R2的G0/0/1连接）。",
        "relevant_chunk_ids": [1, 3, 4],
    },
    {
        "id": "R10",
        "category": "ip_address",
        "difficulty": "medium",
        "question": "端口规划表中R1的S4/0/0连接到哪个设备的哪个接口？",
        "ground_truth_answer": "根据端口规划表，R1的S4/0/0接口连接到R2的S4/0/0接口。",
        "relevant_chunk_ids": [1, 2],
    },
    {
        "id": "R11",
        "category": "ip_address",
        "difficulty": "medium",
        "question": "R1的loopback接口IP地址是多少？",
        "ground_truth_answer": "根据文档，R1配置了LoopBack0接口，IP地址为1.1.1.1/32。",
        "relevant_chunk_ids": [2],
    },

    # === 配置命令查询（8条）===
    {
        "id": "R12",
        "category": "config_commands",
        "difficulty": "medium",
        "question": "如何在R1上配置PPP的PAP认证？",
        "ground_truth_answer": "在R1的Serial4/0/0接口下执行命令：link-protocol ppp，然后ppp authentication-mode pap启用PAP认证。同时需要在AAA视图下添加用户名Jan16和密码123456。",
        "relevant_chunk_ids": [4, 5],
    },
    {
        "id": "R13",
        "category": "config_commands",
        "difficulty": "medium",
        "question": "R2作为被认证端，如何配置PAP验证？",
        "ground_truth_answer": "R2在S4/0/0接口下配置PAP方式验证时本地发送的用户名和密码：link-protocol ppp，ppp pap local-user Jan16 password cipher 123456。",
        "relevant_chunk_ids": [7, 8],
    },
    {
        "id": "R14",
        "category": "config_commands",
        "difficulty": "medium",
        "question": "项目中OSPF是如何配置的？",
        "ground_truth_answer": "全网通过OSPF协议互联。R1配置：ospf 1, area 0, network 192.168.10.0 0.0.0.255, network 10.10.10.0 0.0.0.255。R2配置：ospf 1, area 0, network 192.168.20.0 0.0.0.255, network 10.10.10.0 0.0.0.255。",
        "relevant_chunk_ids": [3, 4],
    },
    {
        "id": "R15",
        "category": "config_commands",
        "difficulty": "hard",
        "question": "如何配置R1的接口IP地址？",
        "ground_truth_answer": "进入系统视图system-view，配置接口：interface GigabitEthernet0/0/1，ip address 192.168.10.254 255.255.255.0。interface Serial4/0/0，ip address 10.10.10.1 255.255.255.0。",
        "relevant_chunk_ids": [2],
    },
    {
        "id": "R16",
        "category": "config_commands",
        "difficulty": "hard",
        "question": "AAA视图下如何添加本地用户？",
        "ground_truth_answer": "进入AAA视图：aaa，然后执行local-user Jan16 password cipher 123456创建本地用户。",
        "relevant_chunk_ids": [4],
    },
    {
        "id": "R17",
        "category": "config_commands",
        "difficulty": "hard",
        "question": "如何启用PPP封装？",
        "ground_truth_answer": "在串行接口下执行link-protocol ppp命令启用PPP封装。",
        "relevant_chunk_ids": [5, 7],
    },
    {
        "id": "R18",
        "category": "config_commands",
        "difficulty": "hard",
        "question": "如何重启接口使配置生效？",
        "ground_truth_answer": "在接口视图下先执行shutdown关闭接口，再执行undo shutdown启用接口。",
        "relevant_chunk_ids": [5],
    },
    {
        "id": "R19",
        "category": "config_commands",
        "difficulty": "medium",
        "question": "如何查看接口状态？",
        "ground_truth_answer": "执行display ip interface brief命令查看接口状态，可以看到接口的IP地址、Physical和Protocol状态。",
        "relevant_chunk_ids": [5, 6, 8],
    },

    # === 验证/故障排查查询（8条）===
    {
        "id": "R20",
        "category": "verification",
        "difficulty": "medium",
        "question": "PAP认证配置完成后，如何验证链路是否正常？",
        "ground_truth_answer": "首先查看链路状态（display ip int brief），确认Physical和Protocol都是up状态。然后从PC1 ping PC2（192.168.20.1），如果0% packet loss则说明链路正常。",
        "relevant_chunk_ids": [5, 6, 9, 10, 11],
    },
    {
        "id": "R21",
        "category": "verification",
        "difficulty": "medium",
        "question": "认证未通过时会出现什么现象？",
        "ground_truth_answer": "认证未通过时，链路物理状态正常但链路层协议状态不正常。ping测试会出现100% packet loss，即5 packet(s) transmitted, 0 packet(s) received。",
        "relevant_chunk_ids": [7],
    },
    {
        "id": "R22",
        "category": "verification",
        "difficulty": "medium",
        "question": "认证通过后ping测试的结果是什么？",
        "ground_truth_answer": "认证通过后，PC间正常通信。ping测试结果为5 packet(s) transmitted, 5 packet(s) received, 0.00% packet loss，round-trip min/avg/max = 47/62/78 ms。",
        "relevant_chunk_ids": [10, 11],
    },
    {
        "id": "R23",
        "category": "verification",
        "difficulty": "hard",
        "question": "ping测试100%丢包的原因是什么？",
        "ground_truth_answer": "ping测试100%丢包的原因是PAP认证未通过。需要检查R2的PAP配置是否正确，确保用户名和密码与R1的AAA配置一致。",
        "relevant_chunk_ids": [7],
    },
    {
        "id": "R24",
        "category": "verification",
        "difficulty": "hard",
        "question": "如何判断PAP认证是否成功？",
        "ground_truth_answer": "可以通过两种方式判断：1）执行display ip interface brief，查看Serial4/0/0的Physical和Protocol状态是否都是up；2）从PC1 ping PC2，如果0% packet loss则认证成功。",
        "relevant_chunk_ids": [5, 6, 9, 10, 11],
    },
    {
        "id": "R25",
        "category": "verification",
        "difficulty": "hard",
        "question": "R2的Serial4/0/0接口状态是什么？",
        "ground_truth_answer": "认证通过后，R2的Serial4/0/0接口状态为up/up，即Physical和Protocol都是up状态。",
        "relevant_chunk_ids": [8, 9],
    },
    {
        "id": "R26",
        "category": "verification",
        "difficulty": "hard",
        "question": "PC之间能正常通信吗？延迟是多少？",
        "ground_truth_answer": "PC之间能正常通信。ping测试显示0% packet loss，round-trip min/avg/max = 47/62/78 ms。",
        "relevant_chunk_ids": [10, 11],
    },
    {
        "id": "R27",
        "category": "verification",
        "difficulty": "medium",
        "question": "如何从PC1测试到PC2的连通性？",
        "ground_truth_answer": "在PC1上执行ping 192.168.20.1命令测试到PC2的连通性。正常情况下应该显示5 packet(s) transmitted, 5 packet(s) received, 0.00% packet loss。",
        "relevant_chunk_ids": [10, 11],
    },

    # === 综合理解查询（6条）===
    {
        "id": "R28",
        "category": "comprehensive",
        "difficulty": "hard",
        "question": "请详细介绍一下这个PAP认证项目的完整实施步骤。",
        "ground_truth_answer": "完整实施步骤包括：1）项目背景分析；2）IP地址规划；3）端口规划；4）R1接口配置；5）R2接口配置；6）OSPF配置；7）PPP PAP认证配置；8）验证测试。",
        "relevant_chunk_ids": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    },
    {
        "id": "R29",
        "category": "comprehensive",
        "difficulty": "hard",
        "question": "这个项目的网络拓扑是怎样的？",
        "ground_truth_answer": "总部R1路由器通过S4/0/0串口连接分公司R2路由器，R1的G0/0/1连接SW1和PC1（192.168.10.0/24网段），R2的G0/0/1连接SW2和PC2（192.168.20.0/24网段）。",
        "relevant_chunk_ids": [0, 1],
    },
    {
        "id": "R30",
        "category": "comprehensive",
        "difficulty": "hard",
        "question": "PAP认证的工作原理是什么？",
        "ground_truth_answer": "PAP认证是PPP协议的一种认证方式。被认证方（R2）将用户名和密码发送给认证方（R1），认证方在AAA数据库中验证用户名和密码是否匹配。如果匹配则认证通过，否则认证失败。",
        "relevant_chunk_ids": [0, 4, 5, 7],
    },
    {
        "id": "R31",
        "category": "comprehensive",
        "difficulty": "hard",
        "question": "如果ping测试失败，应该如何排查？",
        "ground_truth_answer": "排查步骤：1）检查接口状态display ip int brief；2）检查PAP认证配置；3）检查OSPF邻居状态；4）检查PC的IP配置和网关设置。",
        "relevant_chunk_ids": [5, 6, 7, 8],
    },
    {
        "id": "R32",
        "category": "comprehensive",
        "difficulty": "medium",
        "question": "R1和R2各自负责什么功能？",
        "ground_truth_answer": "R1是总部路由器，负责连接总部局域网（192.168.10.0/24）和广域网链路，同时作为PAP认证的认证方。R2是分公司路由器，负责连接分公司局域网（192.168.20.0/24）和广域网链路，同时作为PAP认证的被认证方。",
        "relevant_chunk_ids": [0, 1, 4, 7],
    },
    {
        "id": "R33",
        "category": "comprehensive",
        "difficulty": "hard",
        "question": "这个项目中有哪些关键配置点？",
        "ground_truth_answer": "关键配置点包括：1）接口IP地址配置；2）OSPF路由协议配置；3）PPP封装配置；4）PAP认证配置（认证端和被认证端）；5）AAA用户配置。",
        "relevant_chunk_ids": [2, 3, 4, 5, 7],
    },

    # === 边界情况查询（7条）===
    {
        "id": "R34",
        "category": "edge_cases",
        "difficulty": "medium",
        "question": "R1的LoopBack接口有什么作用？",
        "ground_truth_answer": "R1的LoopBack接口（1.1.1.1/32）通常用作OSPF的Router ID或管理用途，是逻辑接口，不会down。",
        "relevant_chunk_ids": [2],
    },
    {
        "id": "R35",
        "category": "edge_cases",
        "difficulty": "hard",
        "question": "为什么使用串行接口而不是以太网接口互联？",
        "ground_truth_answer": "文档中提到租用专门线路用于总部与分公司互联，串行接口（Serial）通常用于广域网专线连接，支持PPP协议封装和PAP认证。",
        "relevant_chunk_ids": [0, 5],
    },
    {
        "id": "R36",
        "category": "edge_cases",
        "difficulty": "hard",
        "question": "PAP认证和CHAP认证有什么区别？",
        "ground_truth_answer": "文档中只提到了PAP认证。PAP是明文传输用户名和密码，而CHAP使用挑战-响应机制更安全。但本文档未涉及CHAP认证的配置。",
        "relevant_chunk_ids": [0, 4, 5],
    },
    {
        "id": "R37",
        "category": "edge_cases",
        "difficulty": "hard",
        "question": "这个项目中有没有配置NAT？",
        "ground_truth_answer": "根据文档，这个项目中没有配置NAT。项目主要关注PPP PAP认证和OSPF路由配置。",
        "relevant_chunk_ids": [0, 1, 2, 3, 4, 5],
    },
    {
        "id": "R38",
        "category": "edge_cases",
        "difficulty": "hard",
        "question": "为什么选择OSPF而不是RIP？",
        "ground_truth_answer": "文档中没有明确说明为什么选择OSPF。但通常OSPF比RIP更适合中大型网络，支持更快的收敛和更灵活的路由策略。",
        "relevant_chunk_ids": [0, 3, 4],
    },
    {
        "id": "R39",
        "category": "edge_cases",
        "difficulty": "medium",
        "question": "密码为什么显示为cipher而不是明文？",
        "ground_truth_answer": "在配置中使用cipher表示密码被加密存储，这是华为设备的安全特性，防止密码被直接查看。",
        "relevant_chunk_ids": [7, 8],
    },
    {
        "id": "R40",
        "category": "edge_cases",
        "difficulty": "hard",
        "question": "这个项目中有没有配置ACL或防火墙规则？",
        "ground_truth_answer": "根据文档，这个项目中没有配置ACL或防火墙规则。项目主要关注PPP PAP认证和OSPF路由配置。",
        "relevant_chunk_ids": [0, 1, 2, 3, 4, 5],
    },
]

# ============================================================
# 生成质量评估数据集 (25条)
# 覆盖：可回答、不可回答、部分可答、模糊问题
# ============================================================

GENERATION_TEST_SET = [
    # === 可回答问题（12条）===
    {
        "id": "G01",
        "category": "answerable",
        "difficulty": "easy",
        "question": "这个项目的背景是什么？",
        "ground_truth_answer": "Jan16公司因业务发展建立了分公司，需要在总部与分公司之间建立安全的网络连接。通过租用专门线路，在路由器上配置PPP协议的PAP认证来保障数据安全。",
        "expected_behavior": "answerable",
        "key_points": ["Jan16公司", "分公司", "PAP认证", "数据安全"],
    },
    {
        "id": "G02",
        "category": "answerable",
        "difficulty": "medium",
        "question": "如何配置R1的PAP认证？",
        "ground_truth_answer": "在R1的Serial4/0/0接口下执行link-protocol ppp和ppp authentication-mode pap命令启用PAP认证，然后在AAA视图下创建用户名Jan16和密码123456。",
        "expected_behavior": "answerable",
        "key_points": ["Serial4/0/0", "link-protocol ppp", "ppp authentication-mode pap", "AAA", "Jan16", "123456"],
    },
    {
        "id": "G03",
        "category": "answerable",
        "difficulty": "medium",
        "question": "R2的PAP被认证端如何配置？",
        "ground_truth_answer": "R2在S4/0/0接口下先执行link-protocol ppp，再执行ppp pap local-user Jan16 password cipher 123456配置本地PAP用户名和密码。",
        "expected_behavior": "answerable",
        "key_points": ["S4/0/0", "link-protocol ppp", "ppp pap local-user", "Jan16", "123456"],
    },
    {
        "id": "G04",
        "category": "answerable",
        "difficulty": "medium",
        "question": "认证失败时会有什么表现？",
        "ground_truth_answer": "认证失败时链路物理层正常但协议层不正常，ping测试显示100% packet loss。",
        "expected_behavior": "answerable",
        "key_points": ["物理层正常", "协议层不正常", "100% packet loss"],
    },
    {
        "id": "G05",
        "category": "answerable",
        "difficulty": "medium",
        "question": "OSPF在这个项目中是怎么用的？",
        "ground_truth_answer": "全网通过OSPF协议互联，R1和R2各自在area 0中宣告直连网段，实现路由互通。",
        "expected_behavior": "answerable",
        "key_points": ["OSPF", "area 0", "路由互通"],
    },
    {
        "id": "G06",
        "category": "answerable",
        "difficulty": "medium",
        "question": "这个项目的网络拓扑是怎样的？",
        "ground_truth_answer": "总部R1路由器通过S4/0/0串口连接分公司R2路由器，R1的G0/0/1连接SW1和PC1（192.168.10.0/24网段），R2的G0/0/1连接SW2和PC2（192.168.20.0/24网段）。",
        "expected_behavior": "answerable",
        "key_points": ["R1", "R2", "S4/0/0", "G0/0/1", "192.168.10.0/24", "192.168.20.0/24"],
    },
    {
        "id": "G07",
        "category": "answerable",
        "difficulty": "hard",
        "question": "请详细介绍一下这个PAP认证项目的完整实施步骤。",
        "ground_truth_answer": "完整实施步骤包括：1）项目背景分析；2）IP地址规划；3）端口规划；4）R1接口配置；5）R2接口配置；6）OSPF配置；7）PPP PAP认证配置；8）验证测试。",
        "expected_behavior": "answerable",
        "key_points": ["背景", "IP规划", "端口规划", "接口配置", "OSPF", "PAP认证", "验证"],
    },
    {
        "id": "G08",
        "category": "answerable",
        "difficulty": "hard",
        "question": "如果ping测试失败，应该如何排查？",
        "ground_truth_answer": "排查步骤：1）检查接口状态display ip int brief；2）检查PAP认证配置；3）检查OSPF邻居状态；4）检查PC的IP配置和网关设置。",
        "expected_behavior": "answerable",
        "key_points": ["接口状态", "PAP配置", "OSPF", "PC配置"],
    },
    {
        "id": "G09",
        "category": "answerable",
        "difficulty": "hard",
        "question": "简要说明PAP认证的工作原理。",
        "ground_truth_answer": "PAP认证是PPP协议的一种认证方式。被认证方（R2）将用户名和密码发送给认证方（R1），认证方在AAA数据库中验证用户名和密码是否匹配。如果匹配则认证通过，否则认证失败。",
        "expected_behavior": "answerable",
        "key_points": ["PPP协议", "被认证方", "认证方", "用户名密码", "AAA数据库"],
    },
    {
        "id": "G10",
        "category": "answerable",
        "difficulty": "easy",
        "question": "R1的G0/0/1接口IP地址是什么？",
        "ground_truth_answer": "R1的GigabitEthernet0/0/1接口IP地址是192.168.10.254/24。",
        "expected_behavior": "answerable",
        "key_points": ["192.168.10.254", "24"],
    },
    {
        "id": "G11",
        "category": "answerable",
        "difficulty": "easy",
        "question": "R2的S4/0/0接口IP地址是什么？",
        "ground_truth_answer": "R2的Serial4/0/0接口IP地址是10.10.10.2/24。",
        "expected_behavior": "answerable",
        "key_points": ["10.10.10.2", "24"],
    },
    {
        "id": "G12",
        "category": "answerable",
        "difficulty": "medium",
        "question": "认证通过后ping测试的结果是什么？",
        "ground_truth_answer": "认证通过后，PC间正常通信。ping测试结果为5 packet(s) transmitted, 5 packet(s) received, 0.00% packet loss，round-trip min/avg/max = 47/62/78 ms。",
        "expected_behavior": "answerable",
        "key_points": ["5 packet(s)", "0.00% packet loss", "47/62/78 ms"],
    },

    # === 不可回答问题（8条）===
    {
        "id": "G13",
        "category": "unanswerable",
        "difficulty": "easy",
        "question": "公司食堂几点开门？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
        "key_points": [],
    },
    {
        "id": "G14",
        "category": "unanswerable",
        "difficulty": "easy",
        "question": "如何申请年假？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
        "key_points": [],
    },
    {
        "id": "G15",
        "category": "unanswerable",
        "difficulty": "easy",
        "question": "这个项目用了什么编程语言开发？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
        "key_points": [],
    },
    {
        "id": "G16",
        "category": "unanswerable",
        "difficulty": "medium",
        "question": "R1和R2的购买成本是多少？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
        "key_points": [],
    },
    {
        "id": "G17",
        "category": "unanswerable",
        "difficulty": "medium",
        "question": "这个项目是什么时候实施的？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
        "key_points": [],
    },
    {
        "id": "G18",
        "category": "unanswerable",
        "difficulty": "medium",
        "question": "项目的负责人是谁？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
        "key_points": [],
    },
    {
        "id": "G19",
        "category": "unanswerable",
        "difficulty": "hard",
        "question": "这个项目中使用了哪些品牌的设备？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
        "key_points": [],
    },
    {
        "id": "G20",
        "category": "unanswerable",
        "difficulty": "hard",
        "question": "项目的预算有多少？",
        "ground_truth_answer": "",
        "expected_behavior": "unanswerable",
        "key_points": [],
    },

    # === 部分可答/模糊问题（5条）===
    {
        "id": "G21",
        "category": "partial",
        "difficulty": "hard",
        "question": "R1的性能参数是什么？",
        "ground_truth_answer": "文档中没有提到R1的性能参数，只提到了接口配置和IP地址。",
        "expected_behavior": "partial",
        "key_points": ["无性能参数信息"],
    },
    {
        "id": "G22",
        "category": "partial",
        "difficulty": "hard",
        "question": "这个项目的网络带宽是多少？",
        "ground_truth_answer": "文档中没有提到网络带宽信息，只提到了租用专门线路。",
        "expected_behavior": "partial",
        "key_points": ["无带宽信息"],
    },
    {
        "id": "G23",
        "category": "partial",
        "difficulty": "hard",
        "question": "OSPF的Hello时间间隔是多少？",
        "ground_truth_answer": "文档中没有提到OSPF的Hello时间间隔配置，只提到了基本的OSPF配置。",
        "expected_behavior": "partial",
        "key_points": ["无Hello时间配置"],
    },
    {
        "id": "G24",
        "category": "partial",
        "difficulty": "hard",
        "question": "PAP认证的超时时间是多少？",
        "ground_truth_answer": "文档中没有提到PAP认证的超时时间配置。",
        "expected_behavior": "partial",
        "key_points": ["无超时时间配置"],
    },
    {
        "id": "G25",
        "category": "partial",
        "difficulty": "hard",
        "question": "这个项目中有没有配置VLAN？",
        "ground_truth_answer": "文档中没有提到VLAN配置。项目主要关注广域网连接和PAP认证。",
        "expected_behavior": "partial",
        "key_points": ["无VLAN配置"],
    },
]

# ============================================================
# 多轮对话评估数据集 (5组，共20轮)
# ============================================================

MULTI_TURN_TEST_SET = [
    {
        "id": "MT01",
        "description": "渐进式深入：项目概述→协议→命令→验证",
        "turns": [
            {"question": "这个项目是做什么的？", "expected_keywords": ["PAP", "认证", "互联", "安全"]},
            {"question": "R1和R2之间用什么协议？", "expected_keywords": ["PPP", "PAP"]},
            {"question": "认证配置的具体命令是什么？", "expected_keywords": ["ppp authentication-mode pap", "ppp pap local-user"]},
            {"question": "配置完成后怎么验证？", "expected_keywords": ["ping", "packet loss", "dis ip int brief"]},
        ],
    },
    {
        "id": "MT02",
        "description": "指代消解：测试模型对'R2呢'这类省略问句的理解",
        "turns": [
            {"question": "R1的IP地址是多少？", "expected_keywords": ["192.168.10.254", "10.10.10.1"]},
            {"question": "R2呢？", "expected_keywords": ["192.168.20.254", "10.10.10.2"]},
            {"question": "PC之间能通信吗？", "expected_keywords": ["ping", "0%", "packet loss"]},
        ],
    },
    {
        "id": "MT03",
        "description": "故障排查流程：现象→原因→解决",
        "turns": [
            {"question": "ping测试100%丢包是怎么回事？", "expected_keywords": ["认证", "未通过", "PAP"]},
            {"question": "怎么检查认证是否成功？", "expected_keywords": ["display ip int brief", "up/up"]},
            {"question": "如果接口状态不正常怎么办？", "expected_keywords": ["检查配置", "用户名", "密码"]},
            {"question": "配置正确但还是不通呢？", "expected_keywords": ["shutdown", "undo shutdown", "重启"]},
        ],
    },
    {
        "id": "MT04",
        "description": "IP地址规划讨论",
        "turns": [
            {"question": "这个项目的IP地址是怎么规划的？", "expected_keywords": ["192.168.10.0/24", "192.168.20.0/24", "10.10.10.0/24"]},
            {"question": "为什么用这三个网段？", "expected_keywords": ["总部", "分公司", "互联"]},
            {"question": "PC的网关是什么？", "expected_keywords": ["192.168.10.254", "192.168.20.254"]},
        ],
    },
    {
        "id": "MT05",
        "description": "配置步骤顺序讨论",
        "turns": [
            {"question": "配置PAP认证需要哪些步骤？", "expected_keywords": ["接口配置", "PPP", "AAA", "用户名密码"]},
            {"question": "先配置R1还是R2？", "expected_keywords": ["都可以", "顺序"]},
            {"question": "配置完后需要重启接口吗？", "expected_keywords": ["shutdown", "undo shutdown"]},
            {"question": "最后怎么验证？", "expected_keywords": ["ping", "display"]},
        ],
    },
]

# ============================================================
# 端到端评估数据集 (10条)
# ============================================================

E2E_TEST_SET = [
    {
        "id": "E01",
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
        "id": "E02",
        "question": "如果ping测试失败，应该如何排查？",
        "checklist": {
            "mentions_check_interface_status": True,
            "mentions_check_auth_config": True,
            "mentions_practical_steps": True,
        },
    },
    {
        "id": "E03",
        "question": "简要说明PAP认证的工作原理。",
        "checklist": {
            "mentions_username_password": True,
            "mentions_authenticator_and_peer": True,
            "concise": True,
        },
    },
    {
        "id": "E04",
        "question": "这个项目的网络拓扑是怎样的？",
        "checklist": {
            "mentions_r1_r2_connection": True,
            "mentions_pc_networks": True,
            "mentions_ip_addresses": True,
        },
    },
    {
        "id": "E05",
        "question": "R1和R2的配置有什么区别？",
        "checklist": {
            "mentions_authenticator_vs_peer": True,
            "mentions_config_differences": True,
            "structured_comparison": True,
        },
    },
    {
        "id": "E06",
        "question": "OSPF在这个项目中起什么作用？",
        "checklist": {
            "mentions_routing": True,
            "mentions_area_0": True,
            "mentions_network_advertisement": True,
        },
    },
    {
        "id": "E07",
        "question": "认证通过和认证失败的表现有什么不同？",
        "checklist": {
            "mentions_interface_status": True,
            "mentions_ping_result": True,
            "clear_comparison": True,
        },
    },
    {
        "id": "E08",
        "question": "这个项目中有哪些关键配置点？",
        "checklist": {
            "mentions_ip_config": True,
            "mentions_ospf_config": True,
            "mentions_pap_config": True,
            "mentions_aaa_config": True,
        },
    },
    {
        "id": "E09",
        "question": "如何验证PAP认证是否配置成功？",
        "checklist": {
            "mentions_display_command": True,
            "mentions_ping_test": True,
            "mentions_expected_result": True,
        },
    },
    {
        "id": "E10",
        "question": "R1的LoopBack接口有什么作用？",
        "checklist": {
            "mentions_loopback_nature": True,
            "mentions_possible_uses": True,
            "concise": True,
        },
    },
]

# ============================================================
# 对抗性测试数据集 (10条)
# 测试模型是否会被诱导编造信息
# ============================================================

ADVERSARIAL_TEST_SET = [
    {
        "id": "A01",
        "category": "hallucination_induction",
        "question": "R1和R2之间使用了OSPF的哪些特殊区域类型？",
        "expected_behavior": "should_say_not_mentioned",
        "trap": "诱导模型编造stub/nssa等区域类型，实际文档只提到area 0",
    },
    {
        "id": "A02",
        "category": "hallucination_induction",
        "question": "PAP认证使用了什么加密算法？",
        "expected_behavior": "should_say_no_encryption_or_not_mentioned",
        "trap": "诱导模型编造加密算法，PAP实际上是明文传输",
    },
    {
        "id": "A03",
        "category": "hallucination_induction",
        "question": "这个项目中配置了哪些ACL规则？",
        "expected_behavior": "should_say_no_acl",
        "trap": "诱导模型编造ACL规则，实际文档没有ACL配置",
    },
    {
        "id": "A04",
        "category": "hallucination_induction",
        "question": "R1和R2之间的带宽是多少？",
        "expected_behavior": "should_say_not_mentioned",
        "trap": "诱导模型编造带宽数值，实际文档没有提到带宽",
    },
    {
        "id": "A05",
        "category": "hallucination_induction",
        "question": "OSPF的DR/BDR选举结果是什么？",
        "expected_behavior": "should_say_not_mentioned_or_not_applicable",
        "trap": "诱导模型编造DR/BDR信息，点对点链路不选举DR/BDR",
    },
    {
        "id": "A06",
        "category": "hallucination_induction",
        "question": "这个项目中使用了哪些QoS策略？",
        "expected_behavior": "should_say_no_qos",
        "trap": "诱导模型编造QoS策略，实际文档没有QoS配置",
    },
    {
        "id": "A07",
        "category": "hallucination_induction",
        "question": "R1的CPU和内存使用率是多少？",
        "expected_behavior": "should_say_not_mentioned",
        "trap": "诱导模型编造性能数据，实际文档没有这类信息",
    },
    {
        "id": "A08",
        "category": "hallucination_induction",
        "question": "这个项目中配置了HSRP还是VRRP？",
        "expected_behavior": "should_say_neither",
        "trap": "诱导模型编造冗余协议，实际文档没有配置",
    },
    {
        "id": "A09",
        "category": "hallucination_induction",
        "question": "PAP认证的重试次数是多少？",
        "expected_behavior": "should_say_not_mentioned",
        "trap": "诱导模型编造重试次数，实际文档没有提到",
    },
    {
        "id": "A10",
        "category": "hallucination_induction",
        "question": "这个项目中配置了SNMP监控吗？",
        "expected_behavior": "should_say_no_or_not_mentioned",
        "trap": "诱导模型编造SNMP配置，实际文档没有SNMP配置",
    },
]

# ============================================================
# 跨知识库测试数据集 (8条)
# 测试模型能否正确区分不同知识库的内容
# ============================================================

CROSS_KB_TEST_SET = [
    {
        "id": "CK01",
        "category": "cross_kb",
        "question": "IP地址192.168.10.254属于哪个网段？",
        "expected_kb": "kb_4",
        "ground_truth_answer": "根据PAP认证项目文档，192.168.10.254/24属于总部局域网网段192.168.10.0/24。",
        "relevant_chunk_ids": [1, 2],
    },
    {
        "id": "CK02",
        "category": "cross_kb",
        "question": "什么是ARP协议？",
        "expected_kb": "kb_1",
        "ground_truth_answer": "ARP（Address Resolution Protocol）是地址解析协议，用于将IP地址解析为MAC地址。",
        "relevant_chunk_ids": [119, 120, 121, 122, 123, 124, 125, 126, 127, 128],
    },
    {
        "id": "CK03",
        "category": "cross_kb",
        "question": "NAT有哪几种类型？",
        "expected_kb": "kb_1",
        "ground_truth_answer": "NAT有五种类型：静态NAT、动态NAT、NAPT、Easy IP、NAT Server。",
        "relevant_chunk_ids": [150, 151, 152],
    },
    {
        "id": "CK04",
        "category": "cross_kb",
        "question": "防火墙的Trust区域是什么？",
        "expected_kb": "kb_1",
        "ground_truth_answer": "Trust区域是防火墙的内网区域，通常连接内部受信任的网络。",
        "relevant_chunk_ids": [134, 135, 136, 137, 138, 139, 140],
    },
    {
        "id": "CK05",
        "category": "cross_kb",
        "question": "如何配置PAP认证？",
        "expected_kb": "kb_4",
        "ground_truth_answer": "在串行接口下执行link-protocol ppp和ppp authentication-mode pap命令，在AAA视图下创建用户名和密码。",
        "relevant_chunk_ids": [4, 5, 7, 8],
    },
    {
        "id": "CK06",
        "category": "cross_kb",
        "question": "同网段IP如何计算？",
        "expected_kb": "kb_1",
        "ground_truth_answer": "同网段IP计算使用按位与运算，通过子网掩码判断两个IP是否在同一网段。",
        "relevant_chunk_ids": [110, 111, 112, 113, 114, 115, 116, 117, 118],
    },
    {
        "id": "CK07",
        "category": "cross_kb",
        "question": "OSPF协议是怎么配置的？",
        "expected_kb": "kb_4",
        "ground_truth_answer": "在路由器上执行ospf 1，进入area 0，使用network命令宣告直连网段。",
        "relevant_chunk_ids": [3, 4],
    },
    {
        "id": "CK08",
        "category": "cross_kb",
        "question": "防火墙在护网中起什么作用？",
        "expected_kb": "kb_1",
        "ground_truth_answer": "防火墙在护网中起到会话记录与溯源、横向移动阻断、NGFW威胁检测等作用。",
        "relevant_chunk_ids": [147, 148, 149],
    },
]
