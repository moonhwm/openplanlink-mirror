# spec-spinal_bridge

## 目的
Supabase 脊髓读写

## 输入/输出
消息(from/to/kind/payload) → 入库/读取

## 不变量
key 从 env/凭据文件读不入库；msg_hash=md5[:16]

## 失败模式
网络失败返回错误不抛

## 关键函数
- send
- read
- read_since
- to_cairn

## 验收断言
send 返回 id；read 分页
