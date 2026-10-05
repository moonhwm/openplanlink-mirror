# Cordis插件框架研究引入

> 档号：OTL-20261005-06
> 编纂：砚坚席（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-10-05
> 状态：研究稿（待机主审批后引入）

## 一、Cordis概述

### 1.1 基本信息

| 项目 | 内容 |
|---|---|
| **名称** | Cordis |
| **定位** | 时空可组合性元框架（Meta-Framework of Spatiotemporal Composability） |
| **GitHub** | https://github.com/cordiverse/cordis |
| **Stars** | 9002 |
| **语言** | TypeScript |
| **论文** | arXiv:2608.25512 — "A Programming Paradigm for Spatiotemporal Composability" |
| **文档** | https://deepseek-harness.github.io/deepseek-harness/reference/cordis-primer |
| **状态** | 活跃开发中，API尚未稳定 |

### 1.2 核心问题

Cordis解决的是**动态组合**的形式化基础问题。现代软件——从插件系统到自进化代理框架——越来越需要动态组合能力，但其形式化基础仍然不完善。

Cordis识别了两个正交维度：

| 维度 | 名称 | 含义 |
|---|---|---|
| **时间可组合性** | Temporal Composability | 组件移除时能完全撤销其副作用 |
| **空间可组合性** | Spatial Composability | 能声明并响应式管理组件间依赖 |

### 1.3 核心机制

1. **可逆效应（Revertible Effects）**：每个上下文变换都携带一个逆操作，运行时持有该逆操作——实现单个组件的时间可组合性
2. **反应式协效应（Reactive Coeffects）**：每个上下文变更都根据组件的协效应规范进行分类，驱动组件的激活和停用——实现单个组件的空间可组合性
3. **上下文范式（Context Paradigm）**：将效应上下文和协效应上下文统一为单一上下文类型，所有效应和协效应通过它中介——不同组件的效应互不干扰地交织

## 二、Cordis架构分析

### 2.1 包结构

```
packages/
  ├── core/          # 核心库（context/events/fiber/registry/service）
  ├── create/        # 项目脚手架
  ├── group/         # 组件分组
  ├── hmr/           # 热模块替换
  ├── include/       # 包含机制
  ├── loader/        # 声明式组件加载器
  ├── logger-console/ # 控制台日志
  ├── timer/         # 定时器
  └── utils/         # 工具函数
```

### 2.2 核心概念

| 概念 | 文件 | 职责 |
|---|---|---|
| **Context** | context.ts | 统一的上下文类型，效应和协效应的中介 |
| **Fiber** | fiber.ts | 效应追踪器，管理组件的生命周期和副作用 |
| **Events** | events.ts | 事件系统，5种分发模式（emit/parallel/serial/bail/waterfall） |
| **Registry** | registry.ts | 插件注册表，管理插件的加载/卸载/依赖注入 |
| **Plugin** | registry.ts | 插件定义（Function/Constructor/Object三种形态） |

### 2.3 事件分发模式

Cordis提供5种事件分发模式，这对A2A共振场设计有直接参考价值：

| 模式 | 行为 | A2A映射 |
|---|---|---|
| `emit` | 触发所有监听器，不等待返回 | 广播通知（heartbeat/state_change） |
| `parallel` | 并行触发所有监听器，等待全部完成 | 共振发散（多席位并行响应） |
| `serial` | 串行触发监听器，等待每个完成 | 顺序协商（K1 eid注册流程） |
| `bail` | 触发监听器，第一个非空返回值终止 | 门禁拦截（MFA/钩子验证） |
| `waterfall` | 串行触发，每个监听器的返回值传给下一个 | 共识收敛（多席位意见聚合） |

### 2.4 插件生命周期

```
PENDING → LOADING → ACTIVE → DISPOSING → DISPOSED
```

- **PENDING**：插件已注册但尚未加载
- **LOADING**：正在执行插件的apply函数
- **ACTIVE**：插件已加载，副作用已注册
- **DISPOSING**：正在执行逆操作（撤销副作用）
- **DISPOSED**：插件已完全卸载，所有副作用已撤销

## 三、与A2A治理实验的关联

### 3.1 直接对应关系

| Cordis概念 | A2A治理实验对应 | 启示 |
|---|---|---|
| **时间可组合性** | 席位变更时撤销其所有副作用 | 砚坚席退出时须撤销其对CHANGELOG/事件总线的修改 |
| **空间可组合性** | 席位间依赖声明与响应式管理 | K1 eid registry就是空间可组合性的实现 |
| **可逆效应** | 每个操作携带逆操作 | git commit/revert就是天然的可逆效应 |
| **反应式协效应** | 上下文变更驱动席位激活/停用 | 事件驱动ICRF的反应式机制 |
| **上下文范式** | 统一的效应/协效应中介 | 事件总线就是A2A的上下文中介 |
| **Fiber** | 效应追踪器 | 消费日志+审计日志就是A2A的Fiber |

### 3.2 对自进化方案的启示

1. **插件即席位**：每个A2A席位可以视为Cordis的一个插件，有独立的加载/卸载生命周期
2. **效应追踪**：砚坚席的每次操作都应携带逆操作——这比git revert更精细，可以追踪到单个文件/单行修改
3. **协效应声明**：席位应声明其依赖（"我需要K1 eid registry才能运作"），当依赖变更时自动激活/停用
4. **HMR（热模块替换）**：席位升级时不需要重启整个系统，只需替换该席位的"模块"

### 3.3 对事件驱动ICRF的启示

Cordis的5种事件分发模式直接映射到ICRF的共振发散/收敛机制：

- **parallel模式** = 共振发散（一个事件触发多席位并行响应）
- **waterfall模式** = 共识收敛（多席位意见串行聚合）
- **bail模式** = 门禁拦截（第一个拒绝即终止）
- **serial模式** = 顺序协商（K1 eid注册的串行流程）

### 3.4 对HarmonyOS 7 IM GUI的启示

Cordis的Fiber状态模型（PENDING/LOADING/ACTIVE/DISPOSING/DISPOSED）直接映射到IM GUI的席位状态可视化：

| Cordis Fiber状态 | IM GUI席位状态 | 视觉表现 |
|---|---|---|
| PENDING | idle | 灰色，等待中 |
| LOADING | thinking | 蓝色脉动，正在加载 |
| ACTIVE | acting | 绿色，活跃运行 |
| DISPOSING | syncing | 黄色，正在同步/清理 |
| DISPOSED | error/offline | 红色/暗灰，已离线 |

## 四、引入方案

### 4.1 引入策略：概念借鉴，不引入代码依赖

**决策**：不直接引入Cordis代码库（TypeScript/Node.js生态，与HarmonyOS ArkTS纯原生约束冲突），而是**借鉴其核心概念和设计模式**，在ArkTS/Python中重新实现。

**理由**：
1. AGENTS.md硬约束：纯ArkTS，零三方依赖
2. Cordis API尚未稳定
3. 概念借鉴比代码依赖更灵活，可根据A2A实际需求调整

### 4.2 借鉴清单

| Cordis概念 | 借鉴方式 | 实装位置 |
|---|---|---|
| 上下文范式 | 在事件总线中统一效应/协效应中介 | event_bus.py |
| 可逆效应 | 每个操作携带逆操作（undo函数） | 操作日志增强 |
| 反应式协效应 | 席位声明依赖，依赖变更触发激活/停用 | 席位注册增强 |
| 5种事件分发模式 | 在事件总线中实现5种分发模式 | event_bus.py |
| Fiber状态模型 | 在IM GUI中实现5状态可视化 | ArkUI组件 |
| HMR | 席位升级时热替换，不重启系统 | 席位管理模块 |

### 4.3 实装优先级

| 优先级 | 借鉴项 | 依赖 | 预计时间 |
|---|---|---|---|
| P0 | 5种事件分发模式 | 事件总线ICRF | 1天 |
| P1 | 可逆效应（操作携带逆操作） | 操作日志增强 | 2天 |
| P1 | Fiber状态模型 | IM GUI开发 | 1天 |
| P2 | 反应式协效应 | 席位注册增强 | 2天 |
| P3 | HMR热替换 | 席位管理模块 | 3天 |

## 五、验证标准

| 编号 | 验证项 | 方法 |
|---|---|---|
| V1 | 5种事件分发模式正确实现 | 每种模式编写测试用例 |
| V2 | 可逆效应：操作后执行逆操作，状态恢复 | 执行操作→执行逆操作→验证状态一致 |
| V3 | Fiber状态模型5状态正确转换 | 模拟席位生命周期→验证状态转换 |
| V4 | 反应式协效应：依赖变更触发激活/停用 | 声明依赖→变更依赖→验证激活/停用 |
| V5 | 概念借鉴不引入代码依赖 | 检查package.json/ohpm依赖列表 |

## 六、论文与文档精读补充

### 6.1 论文元信息

| 项目 | 内容 |
|---|---|
| **标题** | A Programming Paradigm for Spatiotemporal Composability |
| **作者** | Yifan Shi (北京大学 & DeepSeek-AI), Wei Zhang (北京大学), Tianyi Cui (DeepSeek-AI) |
| **提交日期** | 2026-08-26 |
| **分类** | Programming Languages (cs.PL) |
| **arXiv** | 2608.25512 |

### 6.2 论文摘要精读

论文摘要的核心论证链：

1. **问题识别**：现代软件（从插件系统到自进化代理框架）越来越需要动态组合，但形式化基础不完善
2. **两个正交维度**：
   - **时间可组合性**（Temporal Composability）：组件移除时能完全撤销其副作用
   - **空间可组合性**（Spatial Composability）：能声明并响应式管理组件间依赖
3. **解决方案**：
   - **可逆效应**（Revertible Effects）：每个上下文变换携带逆操作，运行时持有该逆操作 → 时间可组合性
   - **反应式协效应**（Reactive Coeffects）：每个上下文变更根据组件协效应规范分类，驱动激活/停用 → 空间可组合性
4. **统一**：将效应上下文和协效应上下文统一为单一上下文类型 → **上下文范式**（Context Paradigm）
5. **实现**：Cordis元框架——核心库（效应追踪+协效应解析）+声明式组件加载器（配置调和+HMR）

### 6.3 官方文档精读（cordis-primer）

从 https://deepseek-harness.github.io/deepseek-harness/reference/cordis-primer 获取的核心内容：

**五个核心概念**：

1. **插件是实现Service的对象**——可以是带`inject`和`apply(ctx)`字段的函数，也可以是`Service`子类，生命周期由Cordis挂载到上下文
2. **上下文是服务的容器**——一个服务占据稳定的`ctx.<key>`（如`ctx.tools`、`ctx.llm`、`ctx.sessions`），其他插件通过key查找服务而非导入实现
3. **通过inject声明服务依赖**——插件声明所需服务后等待就绪才启动，加载顺序通过服务依赖表达而非手动编排
4. **类型化事件用于通信**——5种分发模式（emit/waterfall/parallel/serial/bail）
5. **注册是可逆的副作用**——通过`ctx.effect()`或`ctx.on()`安装，reload和teardown时按预期撤销

**5种分发模式详细语义**：

| 模式 | await? | 分发顺序 | 返回值? | 语义 |
|---|---|---|---|---|
| `emit` | 否 | 监听器按注册顺序观察 | 否 | 纯通知，监听者观察事件 |
| `waterfall` | 否 | 监听器按注册顺序观察 | 是 | 瀑布式中间件，每个监听器可包装下游结果 |
| `parallel` | 是 | 所有监听器并行观察 | 否 | 并行扇出，等待全部完成 |
| `serial` | 是 | 监听器按注册顺序观察 | 是 | 按序执行，等待每个完成 |
| `bail` | 否 | 按注册顺序，直到首个bail值 | 是 | 门禁拦截，首个非空返回终止 |

**Waterfall语义详解**：
- `ctx.waterfall`是环绕中间件，监听器接收`(...args, next)`
- 调用`next()`执行下游监听器，下游返回值通过`next()`返回当前层
- 不调用`next()`直接返回则短路——对单决策事件，短路是设计意图
- 策略监听器拥有决策权时可不调用`next()`直接返回；标注/观察监听器必须委托

**实践规则**：
- 将行为封装为插件：工具流水线→`ctx.tools`，模型流式输出→`ctx.llm`，agent协调→`ctx.agents`
- 拦截和策略优先使用事件；直接能力调用优先使用服务方法
- 每个注册都应有对应的disposer（资源释放函数）

### 6.4 对A2A治理实验的深化启示

1. **Waterfall = 共识收敛的最佳模式**：A2A协商中的多席位意见聚合应采用waterfall模式——每个席位包装下游意见，最终收敛为单一决策
2. **Bail = 门禁拦截的最佳模式**：MFA验证、钩子检查等应采用bail模式——第一个拒绝即终止
3. **Parallel = 共振发散的最佳模式**：一个事件触发多席位并行响应应采用parallel模式
4. **可逆效应 = 审计回滚的基础**：每个操作携带逆操作，使得任何变更都可以被精确回滚——这是K4审计排程的理论基础
5. **反应式协效应 = 席位依赖管理**：席位声明其依赖（如"砚坚席需要事件总线才能运作"），当依赖变更时自动激活/停用

## 七、遗留事项

1. Cordis论文全文精读——PDF已下载（2.2MB），但当前模型不支持PDF输入，须通过其他方式提取全文
2. Cordis的配置调和（configuration reconciliation）机制——官方文档提到Loader配置，须深入研究
3. Cordis的isolate/intercept机制——与A2A席位隔离的映射关系
4. 时空可组合性在分布式环境（幻16+本地）下的适用性验证
5. Waterfall模式在事件总线ICRF中的具体实现——当前event_bus.py仅有原型，须细化