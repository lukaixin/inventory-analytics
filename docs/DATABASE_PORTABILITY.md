# DuckDB当前实现与PostgreSQL切换边界

2026-10-24用户在首次PG准备之后决定“先用duckdb实现”，并明确要求保留已下载准备的PG。此决定覆盖之前“本轮必须PG”的要求，Server-first、API、五页和数据语义不变。

## 当前

- 后端进程独占本地持久化`.runtime/inventory.duckdb`，禁止多个uvicorn worker或另一个写入进程同时打开。
- 使用SQLAlchemy通用UUID/JSON/Numeric模型和Alembic迁移；数据库方言、事务锁、连接配置集中在数据层。
- 前端只使用API，不直接访问数据库文件。导入原子化、幂等和版本语义仍是同一合同。
- PG17.11安装包、解压目录、初始化完成但未运行的空集群留存`.runtime`；PG项目数据库尚未创建，没有运行中的PG服务。

## 后续切换步骤

1. 在独立PG数据库上执行PG适配的迁移，检查UUID/JSON/NUMERIC、外键和索引；不替换现有DuckDB文件。
2. 进入维护窗口，停止导入写入，备份DuckDB（先停写并安全关闭文件）和源版本清单。
3. 按表迁移来源、系列、版本、快照、明细、导入批次；保留UUID、Decimal、null、时间和SHA256。当前指针在关联对象落库后写入。
4. 逐版本核对记录数、已知金额小计、未知数、源哈希、时间上下文和当前版本指针。
5. 切换连接与事务锁适配，执行完整API/导入/并发/权限/浏览器回归，通过后切服务。
6. 保留原DuckDB只读备份，失败时切回原文件；不得在两端继续双写。

## 改动范围与限制

合理预期是前端/API和大部分业务计算可复用；连接配置、迁移、数据搬迁、锁/并发和性能验收需要专门工作。当前并未验证PG兼容运行，不能承诺仅改连接串即可切换，也不承诺无停机。未来多用户频繁写入或多进程部署优先评估PG。

DuckDB自身的事务/并发限制与PG不同，通用ORM只能减少差异，无法消除。官方参考：[DuckDB Python SQLAlchemy](https://duckdb.org/docs/stable/clients/python/overview)、[DuckDB并发](https://duckdb.org/docs/stable/connect/concurrency)、[PostgreSQL Windows包](https://www.postgresql.org/download/windows/)。
