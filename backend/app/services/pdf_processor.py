"""
PDF 章节切割 — Task 4

支持:
  - 文字 PDF(用 pypdf 直接抽)
  - 扫描 PDF(用 pytesseract + pdf2image 跑 OCR,可选用)
  - 大纲 / 目录检测(TOC bookmark 优先,正则兜底)
  - 输出 List[Chapter]: {id, title, page_start, page_end, content_preview}

用法:
  proc = PdfProcessor(pdf_path="/path/to/book.pdf")
  summary = proc.summary()       # {kind: "text"|"scanned", page_count, has_toc}
  chapters = proc.split()        # List[Chapter]
  text = proc.extract_chapter(chapter)  # 提取单章全文
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any


# ============ 章节标题常见 pattern ============
# 中文:第X章 / 第X节 / 第X讲 / 第X部分 / 第X课
# 英文:Chapter X / Section X / Part X / Unit X
# 数字:Chapter 1 / Chapter One / 一、二、
_CHAPTER_PATTERNS = [
    re.compile(r'^\s*第[一二三四五六七八九十百千零0-9]+[章讲部分节课]\s*[\.、:：]?\s*[一-龥A-Za-z0-9].*'),
    re.compile(r'^\s*第[一二三四五六七八九十百千零0-9]+[章讲部分节课]\s*$'),
    re.compile(r'^\s*(Chapter|CHAPTER|chapter)\s+\d+\s*[\.、:：]?.*'),
    re.compile(r'^\s*(Section|SECTION|section|Unit|UNIT|unit)\s+\d+\s*[\.、:：]?.*'),
    re.compile(r'^\s*(Part|PART|part)\s+[IVX0-9]+\s*[\.、:：]?.*'),
    re.compile(r'^\s*[一二三四五六七八九十]+[、,]\s*[一-龥]'),  # 一、xxxx
    re.compile(r'^\s*\d+\.\d+\s+[一-龥A-Za-z]'),  # 1.1 xxxx
    re.compile(r'^\s*\d+\s+[一-龥A-Za-z]'),       # 1 xxxx (短)
]

# 排除伪章节:目录条目、参考文献、附录里有"第X章"但不真的开始内容
# 这些通常:行尾有 ". . . . 1" 之类页码对齐
_DOT_LEADER = re.compile(r'[\.·・]{3,}\s*\d+\s*$')
# 排除 "X-Y" 形式 (1-3 之类)
_RANGE = re.compile(r'^\s*\d+\s*[-—–]\s*\d+\s*[\.、:：]?.*$')

# 用于"扫描 PDF"判断
_TEXT_CHARS_PER_PAGE_MIN = 50  # 少于 50 字 / 页 视为扫描


@dataclass
class Chapter:
    id: str
    title: str
    page_start: int  # 1-indexed
    page_end: int    # inclusive
    char_count: int = 0
    method: str = "text"  # text | ocr
    preview: str = ""     # 前 200 字

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PdfSummary:
    path: str
    page_count: int
    kind: str           # "text" | "scanned" | "encrypted" | "unknown"
    has_toc: bool
    toc_entries: int = 0
    title: str = ""
    author: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PdfProcessor:
    """PDF 处理器:摘要 / 章节切分 / 单章文本提取"""

    def __init__(self, pdf_path: str | Path):
        self.path = Path(pdf_path)
        if not self.path.exists():
            raise FileNotFoundError(f"PDF not found: {self.path}")

    # ============ 摘要:kind / 是否有 TOC / 元数据 ============

    def summary(self) -> PdfSummary:
        from pypdf import PdfReader
        try:
            reader = PdfReader(str(self.path))
        except Exception as e:
            return PdfSummary(
                path=str(self.path), page_count=0,
                kind="encrypted" if "encrypt" in str(e).lower() else "unknown",
                has_toc=False,
            )
        meta = reader.metadata or {}
        page_count = len(reader.pages)
        # 试抽第 10-40 页文字(跳过封面/扉页/TOC 区域,扫正文)
        # 期权入门.pdf:扫描 PDF — 文字层是 PDF 字体编码后的乱码(225 chars/p 看着像文字但实际是 unprintable)
        # 小狗钱钱.pdf:真文字 — 真的 CJK 字符(avg > 200 真的可读)
        # 启发式:不仅数总字符,还数"可读字符"(CJK + ASCII 字母数字 + 常见标点)的占比
        sample_start = min(10, page_count)
        sample_end = min(40, page_count)
        sample_pages = max(1, sample_end - sample_start)
        total_chars = 0
        readable_chars = 0
        for i in range(sample_start, sample_end):
            try:
                txt = reader.pages[i].extract_text() or ""
            except Exception:
                continue
            total_chars += len(txt)
            readable_chars += sum(1 for c in txt if self._is_readable(c))
        avg_total = total_chars / sample_pages
        avg_readable = readable_chars / sample_pages
        # 判定:平均每页至少有 100 个可读字符 + 可读占比 > 60% 才算"文字"
        kind = "text" if (avg_readable >= 200 and readable_chars / max(1, total_chars) >= 0.7) else "scanned"
        # 调试信息(标准库 logging 不方便,直接 stderr 注释)
        # import sys; print(f"DEBUG: {self.path.name} total={avg_total:.0f}/p readable={avg_readable:.0f}/p ratio={readable_chars/max(1,total_chars):.0%} kind={kind}", file=sys.stderr)
        # TOC 检测
        toc = self._read_toc(reader)
        # 标题:尝试 /Title,否则空(很多 PDF metadata 的 title 是编码乱码)
        # 用启发式:如果 title 里可打印 ASCII + CJK 字符占比 > 50%,才用
        raw_title = str(meta.get("/Title", "") or "").strip()
        title = self._clean_title(raw_title)
        return PdfSummary(
            path=str(self.path), page_count=page_count, kind=kind,
            has_toc=bool(toc), toc_entries=len(toc),
            title=title,
            author=str(meta.get("/Author", "") or "").strip(),
        )

    @staticmethod
    def _is_readable(c: str) -> bool:
        """判定字符是否"可读" — CJK / 假名 / ASCII 字母数字 / 常见中文标点。"""
        if not c or c.isspace():
            return False
        if c.isascii():
            # ASCII:字母 / 数字 / 常见标点算可读,控制字符不算
            return c.isalnum() or c in '.,;:!?()[]{}\'"-/\\@#$%^&*+<>=_~`|·'
        # 非 ASCII:CJK / 假名 / 韩文 / 全角标点
        if '一' <= c <= '鿿':  # CJK
            return True
        if '぀' <= c <= 'ヿ':  # 假名
            return True
        if '가' <= c <= '힯':  # 韩文
            return True
        if '＀' <= c <= '￯':  # 全角
            return True
        return False

    @staticmethod
    def _clean_title(raw: str) -> str:
        """清理 PDF metadata 标题里的乱码(很多 PDF 标题字段是 UTF-16 字节流被错误解码)。"""
        if not raw:
            return ""
        # 启发式:数"可读字符"(CJK + 假名 + ASCII 字母数字 + 常见标点) vs 总字符
        # 阈值 0.7 — 真实标题 90%+, 乱码标题 < 50%
        readable = sum(
            1 for c in raw
            if ('一' <= c <= '鿿')             # CJK
            or ('぀' <= c <= 'ヿ')            # 假名
            or ('가' <= c <= '힯')            # 韩文
            or c.isalnum()                     # ASCII 字母/数字
        )
        if len(raw) == 0 or readable / len(raw) < 0.7:
            return ""
        return raw[:200]

    @staticmethod
    def _read_toc(reader) -> List[Dict[str, Any]]:
        """读 PDF 大纲(TOC bookmark)。返 [{"title", "page"}]。"""
        try:
            outline = reader.outline
        except Exception:
            return []
        # outline 是树形(可能有嵌套),用 BFS 拍平
        flat: List[Dict[str, Any]] = []

        def walk(node, depth: int = 0):
            if isinstance(node, list):
                for n in node:
                    walk(n, depth)
                return
            # 单个 outline item
            title = ""
            page = 0
            try:
                title = str(node.title).strip() if hasattr(node, "title") else ""
                if hasattr(node, "page") and node.page is not None:
                    try:
                        page = int(node.page)
                    except Exception:
                        page = 0
            except Exception:
                pass
            if title and page > 0:
                flat.append({"title": title, "page": page, "depth": depth})

        walk(outline)
        return flat

    # ============ 章节切分 ============

    def split(self, max_chapter_pages: int = 100) -> List[Chapter]:
        """主入口:返回 List[Chapter]。每个 chapter 含 page_start / page_end / 预览。

        策略:
        1. 优先用 PDF TOC
        2. 没 TOC 用正则匹配每页第一行
        3. 啥都没找到:整本当 1 个 chapter
        """
        from pypdf import PdfReader
        try:
            reader = PdfReader(str(self.path))
        except Exception as e:
            raise ValueError(f"无法读取 PDF(可能加密或损坏): {e}")

        page_count = len(reader.pages)
        toc = self._read_toc(reader)
        if toc and len(toc) >= 2:
            return self._chapters_from_toc(toc, page_count)
        # TOC 不够 → 正则扫描
        return self._chapters_from_regex(reader, page_count, max_chapter_pages)

    def _chapters_from_toc(self, toc: List[Dict[str, Any]], page_count: int) -> List[Chapter]:
        """从 PDF 大纲构建 chapter 列表。连续两 TOC 间的页 = 一个 chapter。"""
        from pypdf import PdfReader
        reader = PdfReader(str(self.path))
        chapters: List[Chapter] = []
        for i, entry in enumerate(toc):
            start = max(1, int(entry["page"]))
            end = int(toc[i + 1]["page"]) - 1 if i + 1 < len(toc) else page_count
            if end < start:
                end = start
            end = min(end, page_count)
            # 提取预览(首 200 字)
            preview = ""
            char_count = 0
            for p in range(start - 1, end):
                try:
                    txt = reader.pages[p].extract_text() or ""
                    if not preview:
                        preview = txt[:200]
                    char_count += len(txt)
                except Exception:
                    pass
            chapters.append(Chapter(
                id=f"ch{i+1:03d}",
                title=entry["title"],
                page_start=start,
                page_end=end,
                char_count=char_count,
                method="text",
                preview=preview.strip(),
            ))
        return chapters

    def _chapters_from_regex(
        self, reader, page_count: int, max_chapter_pages: int
    ) -> List[Chapter]:
        """无 TOC 时,扫每页第一行(去页眉/页脚),匹章节 pattern。

        启发式:
          - 跳过封面/TOC/前言区(前 toc_end 页 = 1/16 最多 10)
          - 一页只取第一个匹配(章节标题通常在页顶)
          - 排除:点行符页码、范围行(目录条目)
          - 相邻匹配过近(<2 页)只取第一个
          - 用正则尽可能抓出每个新章节(同名出现在不同页时都接受)
        """
        # toc_end 紧凑:大多数 PDF 的前言/TOC 在前 5-10 页
        toc_end = min(10, max(2, page_count // 16))
        candidates: List[Dict[str, Any]] = []  # {page, title}

        for p_idx in range(page_count):
            page_no = p_idx + 1
            # 跳过封面/前言/TOC 区
            if page_no <= toc_end:
                continue
            try:
                txt = reader.pages[p_idx].extract_text() or ""
            except Exception:
                continue
            lines = [l.strip() for l in txt.split("\n") if l.strip()]
            if not lines:
                continue
            # 排除目录页(满是点行)
            if any(_DOT_LEADER.search(l) for l in lines[:20]):
                continue
            # 取前 5 行(覆盖页眉/标题/起始)
            for line in lines[:5]:
                if not line or len(line) > 80:
                    continue
                if _DOT_LEADER.search(line) or _RANGE.match(line):
                    continue
                for pat in _CHAPTER_PATTERNS:
                    if pat.match(line):
                        title = line[:60].strip()
                        candidates.append({"page": page_no, "title": title})
                        break
                else:
                    continue
                break  # 一页只取第一个匹配

        # 去重:(同标题在 TOC 区)只保留第一个;相邻 <2 页也丢
        filtered: List[Dict[str, Any]] = []
        for c in candidates:
            if filtered and c["page"] - filtered[-1]["page"] < 2:
                continue
            filtered.append(c)

        if not filtered:
            # 啥都没找到 → 整本当 1 chapter
            preview = ""
            char_count = 0
            for p_idx in range(min(3, page_count)):
                try:
                    t = reader.pages[p_idx].extract_text() or ""
                    if not preview:
                        preview = t[:200]
                    char_count += len(t)
                except Exception:
                    pass
            return [Chapter(
                id="ch001",
                title=self.path.stem,
                page_start=1,
                page_end=page_count,
                char_count=char_count,
                method="text",
                preview=preview.strip(),
            )]

        # 构建 chapter 区间
        chapters: List[Chapter] = []
        for i, c in enumerate(filtered):
            start = int(c["page"])
            end = int(filtered[i + 1]["page"]) - 1 if i + 1 < len(filtered) else page_count
            if end < start:
                end = start
            end = min(end, page_count)
            preview = ""
            char_count = 0
            for p in range(start - 1, end):
                try:
                    t = reader.pages[p].extract_text() or ""
                    if not preview:
                        preview = t[:200]
                    char_count += len(t)
                except Exception:
                    pass
            chapters.append(Chapter(
                id=f"ch{i+1:03d}",
                title=c["title"],
                page_start=start,
                page_end=end,
                char_count=char_count,
                method="text",
                preview=preview.strip(),
            ))
        return chapters

    # ============ 单章全文提取 ============

    def extract_chapter(self, chapter: Chapter) -> str:
        """提取一章的全文。"""
        from pypdf import PdfReader
        reader = PdfReader(str(self.path))
        parts: List[str] = []
        for p in range(chapter.page_start - 1, min(chapter.page_end, len(reader.pages))):
            try:
                parts.append(reader.pages[p].extract_text() or "")
            except Exception:
                parts.append("")
        return "\n\n".join(parts).strip()

    # ============ 扫描 PDF OCR(可选, 需 pytesseract + pdf2image) ============

    def is_ocr_available(self) -> bool:
        try:
            import pytesseract  # noqa
            import pdf2image  # noqa
            return True
        except ImportError:
            return False

    def extract_chapter_ocr(self, chapter: Chapter, dpi: int = 200) -> str:
        """用 OCR 提取扫描 PDF 的章节全文(慢, 仅在 is_ocr_available() 时用)。"""
        import pytesseract
        from pdf2image import convert_from_path
        images = convert_from_path(
            str(self.path),
            dpi=dpi,
            first_page=chapter.page_start,
            last_page=chapter.page_end,
        )
        parts: List[str] = []
        for img in images:
            try:
                # 简中 OCR 用 chi_sim, 英文用 eng
                txt = pytesseract.image_to_string(img, lang="chi_sim+eng")
            except Exception:
                txt = ""
            parts.append(txt)
        return "\n\n".join(parts).strip()
