# collab技能：A2A跨席位握手协议

> 编写时间：2026-09-23
> 编写席位：砚坚（CodeArts GLM-5.2-sft-harmony）
> 适用场景：A2A网络中多AI席位间的协作通信

## 1. A2A网络架构

### 五席位定义

| 席位 | 运行环境 | 模型 | 职责 |
|------|---------|------|------|
| 砚坚 | CodeArts Agent | GLM-5.2-sft-harmony | 端侧UI、播报交互、Push封装（挂帅席/神经中枢） |
| 顾权 | Kimi Code | - | 取数、策略、监测、服务端出数 |
| Moon | ZCode | GLM-5.3-Flash / GLM-5.3 | 自主燃烧、知识资产产出 |
| 薪传席 | 待定 | - | 待定义 |
| 机主白秉烛 | Kimi Work | - | 协调者、裁决者 |

### 分区主权

| 目录 | 主权席 | 职责 |
|------|--------|------|
| harmony-app/ | 砚坚（CodeArts） | 端侧UI、播报交互、Push封装 |
| quant-lab/ | 顾权（Kimi Code） | 取数、策略、监测、服务端出数 |
| 接口边界 | AGENTS.md + AlertItem.ets | AlertFeed JSON契约 |

## 2. 握手协议

### 串行纪律

同一时间只允许一个AI席位在本工程写代码。开工前：
1. `git status` —— 有未提交改动先读CHANGELOG判断是谁的活
2. 读CHANGELOG.md最后一条
3. 干完立即`git add -A && git commit`，并在CHANGELOG.md追加条目

### CHANGELOG条目格式

```
## YYYY-MM-DD HH:MM · [席位名]（[运行环境]）· [简述]

- **起因**：[为什么改]
- **改了什么**：[具体改动列表]
- **为什么**：[每个改动的理由]
- **如何验证**：[验证步骤V1-Vn]
- **遗留**：[未完成事项编号列表]
```

### 越界规则

任何一方要动对方目录或改AlertItem/AlertFeed契约，须先在CHANGELOG.md写明意图并停机主确认。

## 3. 物理桥接层

### 幻16桥接架构

- 5个agent + 12个工具资产
- MFV-0.1协议（Message Format Version 0.1）
- K3范式对齐
- 哈希约定：md5[:16]

### 桥接脚本消息格式

```json
{
  "id": "[md5_hash_first_16_chars]",
  "from": "[席位名]",
  "to": "[目标席位名]",
  "kind": "[消息类型]",
  "payload": "[消息内容]",
  "ts": "[ISO时间戳]"
}
```

### 心跳机制

- 定期发送心跳消息验证通路
- 心跳消息kind为"heartbeat"
- 收到心跳回复确认通路可用

## 4. 冲突处理

### 仲裁层级

1. CHANGELOG.md最后一条优先
2. AGENTS.md约束为最高规则
3. 机主白秉烛裁决为最终裁定

### 常见冲突场景

| 场景 | 处理方式 |
|------|---------|
| 两个席位同时修改同一文件 | 后提交者负责合并，CHANGELOG记录合并 |
| 一方修改了AlertFeed契约 | 必须停机主确认，否则回退 |
| 一方修改了对方目录 | 立即回退，CHANGELOG记录违规 |

---

*本技能文档由砚坚席位于2026-09-23编写，基于A2A网络协作实战经验提炼。*