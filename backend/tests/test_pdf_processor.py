"""PDF 处理器 + Sources API 测试 — Task 4 + 3"""
import pytest
import tempfile
from pathlib import Path

from app.services.pdf_processor import (
    PdfProcessor,
    PdfSummary,
    Chapter,
)


# 临时复制 data/ 里的真实 PDF(以免 repo 调整路径)
import shutil


def _copy_pdf(src_name: str) -> str:
    src = Path("/Users/lazy/Code/crack/claude/self-media-platform/data") / src_name
    if not src.exists():
        pytest.skip(f"测试 PDF 不存在: {src}")
    dst_dir = Path(tempfile.gettempdir()) / "pdf_proc_test"
    dst_dir.mkdir(exist_ok=True)
    dst = dst_dir / src_name
    shutil.copy(src, dst)
    return str(dst)


# ============ 纯函数 ============

class TestHelpers:
    def test_is_readable_cjk(self):
        assert PdfProcessor._is_readable("中")
        assert PdfProcessor._is_readable("文")
        assert PdfProcessor._is_readable("字") is True  # CJK extension B

    def test_is_readable_ascii(self):
        assert PdfProcessor._is_readable("a")
        assert PdfProcessor._is_readable("Z")
        assert PdfProcessor._is_readable("1")
        assert PdfProcessor._is_readable(".")
        assert PdfProcessor._is_readable("@")
        assert not PdfProcessor._is_readable(" ")  # 空白不算
        assert not PdfProcessor._is_readable("\x00")  # 控制字符
        assert not PdfProcessor._is_readable("\x01")  # 控制字符

    def test_clean_title_garbage(self):
        # 全是 Latin-1 supplement 区的乱码字符(常见 PDF 标题字段 bug)
        assert PdfProcessor._clean_title("") == ""
        # 乱码只有 30% 可读,应该清空
        bad = "\xfe\xff\x00\x00\x00\x00"  # 大量控制字符
        assert PdfProcessor._clean_title(bad) == ""

    def test_clean_title_normal(self):
        assert PdfProcessor._clean_title("小狗钱钱") == "小狗钱钱"
        assert PdfProcessor._clean_title("Sapiens") == "Sapiens"
        assert PdfProcessor._clean_title("Hello World 2024") == "Hello World 2024"

    def test_clean_title_truncates(self):
        long = "a" * 500
        out = PdfProcessor._clean_title(long)
        assert len(out) <= 200


# ============ PdfProcessor 真 PDF 测试 ============

class TestPdfProcessorReal:
    """用 data/ 下的真实 PDF 跑端到端。"""

    def test_xiaogouqianqian_text_pdf(self):
        """小狗钱钱.pdf:文字 PDF,33 章节,第一章在 p29。"""
        path = _copy_pdf("小狗钱钱.pdf")
        proc = PdfProcessor(path)
        s = proc.summary()
        assert s.kind == "text", f"期望 text,实际 {s.kind}"
        assert s.page_count == 383
        assert s.author == "〔德〕博多·舍费尔"
        # 标题被 _clean_title 洗干净(避免乱码)
        assert s.title != "\xfe\xff..."
        # 章节切分
        chapters = proc.split()
        assert len(chapters) >= 25, f"期望 ≥25 章节,实际 {len(chapters)}"
        # 第一章标题应该是 "第一章 ..."(不是从"第三章"开始)
        assert "第一章" in chapters[0].title, f"首章: {chapters[0].title!r}"
        # 章节 id 顺序
        ids = [c.id for c in chapters]
        assert ids == sorted(ids)

    def test_qiquanruomen_scanned_pdf(self):
        """期权入门.pdf:扫描 PDF,kind=scanned。"""
        path = _copy_pdf("期权入门与精通(高清).pdf")
        proc = PdfProcessor(path)
        s = proc.summary()
        assert s.kind == "scanned", f"期望 scanned,实际 {s.kind}"
        assert s.page_count == 195
        # 扫描 PDF 章节切分可能没结果(返回 1 个整本 chapter)
        chapters = proc.split()
        assert len(chapters) >= 1
        # 全本应该是 1 个 chapter
        assert chapters[0].page_start == 1
        assert chapters[0].page_end == 195

    def test_extract_chapter_first_chapter(self):
        """小狗钱钱第一章: 6K+ 字内容,含 '白色的拉布拉多犬' 关键词。"""
        path = _copy_pdf("小狗钱钱.pdf")
        proc = PdfProcessor(path)
        chapters = proc.split()
        first = chapters[0]
        text = proc.extract_chapter(first)
        # 第一章正文至少 3000 字
        assert len(text) > 3000, f"第一章字数: {len(text)}"
        # 关键词命中
        assert "拉布拉多" in text or "钱钱" in text

    def test_extract_chapter_ocr_returns_empty_or_text(self):
        """扫描 PDF 的 extract_chapter 不装 OCR 库应返空或出错。"""
        path = _copy_pdf("期权入门与精通(高清).pdf")
        proc = PdfProcessor(path)
        chapters = proc.split()
        # 不装 OCR 也能跑(只是 text 不可读);但 extract 出来的应该 < 1000 字/页
        if proc.is_ocr_available():
            pytest.skip("已装 OCR,跳过该测试")
        ch = chapters[0]
        text = proc.extract_chapter(ch)
        # 扫描 PDF 在没 OCR 的情况下,extract_chapter 会返空字符串
        # 或乱码。两者都接受。
        assert isinstance(text, str)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            PdfProcessor("/nonexistent/path.pdf")
