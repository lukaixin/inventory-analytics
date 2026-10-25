# 本地运行、部署选择与迁移边界

2026-10-24 用户明确调整：先使用 DuckDB，已准备的 PostgreSQL 资产保留待以后使用。本轮不启动 PostgreSQL，也不进行企业部署。

## 当前路径：DuckDB + 单后端进程

数据库文件为 `.runtime/inventory.duckdb`，测试使用独立文件；配置在忽略的 `.env`。SQLAlchemy URL由 `bootstrap-local.ps1` 生成绝对路径，因此从项目根目录或backend目录运行均一致。API仅监听 `127.0.0.1:8170`，一个uvicorn进程负责所有写入；不能使用多worker或另一个写进程同时打开数据库。

在项目根目录运行：

```powershell
# 创建本地配置（已有配置不覆盖）
pwsh -File scripts/bootstrap-local.ps1
# 依赖与前端构建完成后，迁移、导入样例、启动
pwsh -File scripts/start.ps1 -Migrate -Seed
# 平时启动，无需重复seed
pwsh -File scripts/start.ps1
# HTTP活性、真实DB readiness、数据集和OpenAPI检查
pwsh -File scripts/check.ps1
# 停止本项目API（保留数据库）
pwsh -File scripts/stop.ps1
# 关闭API后备份文件并检查可读性
pwsh -File scripts/backup.ps1
```

应用地址 `http://127.0.0.1:8170`，API文档 `/docs`，readiness `/health/ready`。已构建的 `frontend/dist` 由后端同源托管；开发前端可另在frontend目录运行 `npm run dev`（5177）。开发前端不是第二个数据库写入进程。

启动、停止脚本记录并验证PID、创建时间和命令行；Windows venv使用解释器子进程时，停止脚本会先验证并停止该子进程。8170被不认识的进程占用时拒绝覆盖。迁移/seed必须在API停止后执行；启动脚本对已运行API拒绝迁移。无需用`--reload`或多worker。

## 本轮实测

- DuckDB Alembic migration启动检查成功；seed在停API后连续执行成功。
- 应用启动、停止和重启已经实测；根页面、`/health/live`、`/health/ready`、`/api/v1/datasets`、`/openapi.json`均HTTP200。
- PowerShell脚本语法通过；具体数据与业务验收以项目验收报告为准。
- 当前没有运行PG服务。初始化中途用户改选DuckDB前，PG空集群已完成initdb，但未启动，未创建项目开发/测试数据库。临时V:映射已经移除。

## PostgreSQL保留资产（休眠）

用户明确要求保留本机已下载和准备的PG：

- `.runtime/postgresql-17.11.zip`：EDB官方Windows二进制包，381531864字节。
- `.runtime/pgsql/`：解压的PostgreSQL17.11程序。
- `.runtime/pgdata/`：未启动的空集群。
- `.runtime/postgres-settings.env`：先前生成的私有随机凭据，不输出、不提交。
- `scripts/bootstrap-postgres.ps1`、`start-postgres.ps1`、`postgres-common.ps1`：后续候选脚本；默认拒绝执行，必须显式ActivatePostgres，并先评审迁移/配置。不是当前运行流程的一部分。

下载来源：[PostgreSQL Windows页面](https://www.postgresql.org/download/windows/) → [EDB二进制包](https://www.enterprisedb.com/download-postgresql-binaries)。本次下载SHA256为`80379B2C04D51C30225532E0AE04509899141E9957ED096FE749D7FD9DF8F82F`，用于后续同包完整性核验；并非另行获得的官方签名证明。

Windows中文路径下PG initdb曾遇到UTF8路径编码错误；候选脚本保留ASCII盘符别名方案，但下次启用前仍需修复/复验盘符映射检查。物理文件始终保留在本项目。当前DuckDB不使用任何盘符映射，也不安装系统服务或改系统PATH。

## 将来切换PG

SQLAlchemy模型和API隔离降低迁移成本，但不是只改URL就保证完成：需要验证PG迁移、JSON/UUID/Numeric类型、约束和事务并发差异，导出DuckDB数据、导入PG并逐表核对，复验导入幂等及权限，再切换应用连接。切换之前保留DuckDB文件和备份，不覆盖旧库。正式切换还需要业务/IT确认身份与部署。

`compose.yaml`只保留`future-postgres` profile下的数据库候选服务，映射到127.0.0.1:55438，当前不拉镜像、不启动容器。配置静态校验可以使用：

```powershell
docker compose --env-file .runtime/postgres-settings.env --profile future-postgres config --quiet
```

Docker Engine运行、镜像拉取、PG服务和整应用容器部署均未验证。不要使用`docker compose down -v`。正式PG应用应使用最小权限角色，不能直接以候选容器初始化角色上线。

## 备份、更新与恢复

停止API→确认无其他写进程→CHECKPOINT→复制DuckDB文件→以只读连接检查备份。`backup.ps1`写入`.runtime/backups`，不会覆盖已有备份。恢复需要先停API，选择独立备份文件验证内容后再切换DATABASE_URL；不得自动替换现有数据库。此处的可读检查不等于完整恢复演练。

更新顺序：保存未提交改动→停API→备份→依赖/构建→迁移→启动→readiness→业务核对。应用版本回退不等于数据库回退；迁移不兼容时使用独立备份/副本验证后恢复，不执行自动清库。

日志在`.runtime/backend.out.log`和`.runtime/backend.err.log`。`.runtime`、`.env`及实际数据不进入Git、发布包或镜像。开发样例不会自动写入生产。

## IT待确认

服务器Windows/Linux和CPU、Docker能力、磁盘与备份、并发写入规模、是否采用PG托管、反向代理/TLS、SSO及数据授权、上传限制、运维账户、RPO/RTO。当前正式身份未实现，后端生产模式拒绝启动；不得暴露到内网/公网。服务器未知期间保留原生进程和容器化方向，不承诺已经生产就绪。

## 常见故障

- DuckDB锁冲突：先停其他写进程，不删除数据库或锁相关文件；迁移/seed与API不能并行。
- readiness失败：检查迁移、数据库文件路径和日志，不打印敏感配置。
- 8170占用：先确认PID归属，不自动杀其他进程。
- 前端空白：先构建frontend/dist，确认API根页面和/assets返回200。
