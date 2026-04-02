"""研报生成工具测试"""
import json
import os
import pytest


class TestBuildDataTable:
    def test_basic(self):
        """基本表格生成"""
        from tools.report_generator import build_data_table
        result = build_data_table(
            headers="指标,2024Q4,2025Q1",
            rows="GDP增速,4.9%,5.2%;CPI,0.2%,0.5%"
        )
        assert "html" in result
        assert "markdown" in result
        assert "GDP增速" in result["html"]
        assert "5.2%" in result["html"]
        assert "<table" in result["html"]
        assert "GDP增速" in result["markdown"]

    def test_with_title(self):
        """带标题的表格"""
        from tools.report_generator import build_data_table
        result = build_data_table(
            headers="名称,价格",
            rows="黄金,2400",
            title="大宗商品报价"
        )
        assert "大宗商品报价" in result["html"]

    def test_with_highlight(self):
        """高亮列"""
        from tools.report_generator import build_data_table
        result = build_data_table(
            headers="名称,涨幅,备注",
            rows="测试,10%,无",
            highlight_cols="1"
        )
        html = result["html"]
        # 高亮列应有特殊背景色
        assert "rgba(88,166,255,0.08)" in html


class TestBuildReport:
    def test_creates_file(self, tmp_workspace, monkeypatch):
        """验证 HTML 文件写入"""
        monkeypatch.setattr("tools.report_generator.config.workspace_root",
                            str(tmp_workspace), raising=False)
        # 使 abs_reports_dir 指向临时目录
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "abs_reports_dir",
            property(lambda self: str(tmp_workspace / "reports")),
        )
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(tmp_workspace / "index.json")),
        )

        from tools.report_generator import build_report
        result = build_report(
            title="测试研报",
            content="## 摘要\n\n这是一篇测试研报。\n\n**重点结论**：测试通过。",
            author="测试工程师",
            category="测试分类",
            tags="测试,单元测试",
            filename="test_output"
        )

        assert result["status"] == "success"
        assert result["path"].endswith(".html")
        # 验证文件存在
        out_file = tmp_workspace / "reports" / "test_output.html"
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "测试研报" in content
        assert "<h2" in content


class TestMdToHtml:
    """测试内部 _md_to_html 转换器"""

    def _convert(self, md_text):
        from tools.report_generator import _md_to_html
        return _md_to_html(md_text)

    def test_headings(self):
        html = self._convert("## 二级标题\n\n### 三级标题")
        assert "<h2" in html
        assert "二级标题" in html
        assert "<h3" in html
        assert "三级标题" in html

    def test_bold(self):
        html = self._convert("这是**粗体**文本")
        assert "<strong>粗体</strong>" in html

    def test_italic(self):
        html = self._convert("这是*斜体*文本")
        assert "<em>斜体</em>" in html

    def test_inline_code(self):
        html = self._convert("使用 `pip install` 安装")
        assert "<code>pip install</code>" in html

    def test_table(self):
        md = "| 指标 | 数值 |\n| --- | --- |\n| GDP | 5.0% |"
        html = self._convert(md)
        assert "<table>" in html
        assert "GDP" in html
        assert "5.0%" in html

    def test_unordered_list(self):
        html = self._convert("- 第一项\n- 第二项\n- 第三项")
        assert "<ul>" in html
        assert "<li>" in html
        assert "第一项" in html

    def test_ordered_list(self):
        html = self._convert("1. 第一\n2. 第二")
        assert "<ol>" in html

    def test_blockquote(self):
        html = self._convert("> 引用内容")
        assert "<blockquote>" in html
        assert "引用内容" in html

    def test_code_block(self):
        html = self._convert("```python\nprint('hello')\n```")
        assert "<pre>" in html
        assert "<code" in html

    def test_horizontal_rule(self):
        html = self._convert("---")
        assert "<hr>" in html

    def test_link(self):
        html = self._convert("[链接](https://example.com)")
        assert '<a href="https://example.com">链接</a>' in html


class TestDoRegisterReport:
    def test_register(self, tmp_workspace, monkeypatch):
        """注册新研报后 index.json 正确更新"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(tmp_workspace / "index.json")),
        )

        from tools.report_generator import do_register_report
        result = do_register_report(
            title="新研报",
            category="宏观研究",
            tags="GDP,CPI",
            summary="测试摘要",
            path="reports/new.html",
            author="测试",
            date="2026-01-01",
        )

        assert result["status"] == "success"
        assert "id" in result

        # 验证 index.json 已更新
        idx = json.loads((tmp_workspace / "index.json").read_text(encoding="utf-8"))
        if isinstance(idx, dict):
            reports = idx.get("reports", [])
        else:
            reports = idx
        assert any(r["title"] == "新研报" for r in reports)
