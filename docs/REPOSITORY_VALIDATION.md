# 仓库首次交接验证

日期：2026-10-25。适用版本：首次GitHub私有仓库源码提交。

## 已执行

- 从Git暂存区导出独立干净源码，不包含本机`.env`、数据库、`data/private/`、`evidence/`或依赖目录。
- 用干净源码和全新隔离DuckDB运行Alembic及pytest：**27 passed，1 skipped**。唯一跳过项需要不随仓库分发的私有历史转录副本；本机存在副本时仍执行原勾稽断言。
- 干净源码中执行`npm ci`及`npm run build`：通过。
- 根、backend、frontend三级AGENTS及真实接入交接文档均在提交范围。
- 暂存文件检查未发现运行库、私有数据、截图、导出、备份或PG凭据；有限凭据模式扫描无命中，不视为完整安全审计。
- 前一功能轮的完整本机测试为28 passed；浏览器、规则、权限、筛选、重试和持久化验收摘要见项目状态。详细本机证据不随源码上传。

## 可重跑

按README初始化后执行：

```powershell
pwsh -File scripts/test.ps1
Push-Location frontend
npm run build
Pop-Location
```

无私有历史文件时出现上述一个skip是预期行为，不要为消除skip复制企业资料进Git或伪造历史证据。

Python测试复用了本机已有venv中的锁定依赖；本次没有证明全新系统Python安装、Linux运行或PostgreSQL迁移。当前演示数据继续保留；真实接入、mock退场与正式数据验收见[REAL_DATA_ONBOARDING.md](REAL_DATA_ONBOARDING.md)。
