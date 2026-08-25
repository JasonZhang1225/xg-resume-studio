# 贡献指南

欢迎 Issue 与 PR！

## 本地开发

```bat
git clone <你的仓库地址> resume-studio
cd resume-studio
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\pytest -q        :: 运行测试
.venv\Scripts\ruff check .     :: 代码检查
```

## 约定

- 提交前确保 `pytest` 与 `ruff check` 通过
- 不要提交任何运行时数据：`data.db`、`uploads/` 内容、导出的 docx（.gitignore 已覆盖）
- 涉及数据库结构的改动必须走 `database.py` 的 `MIGRATIONS` 列表，禁止只改 SCHEMA
- 涉及删除数据的接口必须：精确主键定位 + 归属校验 + 前端二次确认（参见 reference 教训）
