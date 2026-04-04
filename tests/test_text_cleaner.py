"""
tests/test_text_cleaner.py — ASR 垃圾文本清理测试（TODO #3）

覆盖：
- 尾部重复文本检测与清理
- 正常文本不被误清理
- 边界情况（空文本、全重复）
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from text_cleaner import clean_trailing_repeats, clean_text


# ── clean_trailing_repeats ───────────────────────────────────────────────────

def test_CleanTrailingRepeats_RemovesRepeatedSuffix():
    text = "正常内容。正常内容。谢谢大家谢谢大家谢谢大家谢谢大家谢谢大家"
    result = clean_trailing_repeats(text)
    assert result.count("谢谢大家") <= 2


def test_CleanTrailingRepeats_PreservesNormalText():
    text = "这是一段正常的文本，没有重复。每句话都不一样。"
    result = clean_trailing_repeats(text)
    assert result == text


def test_CleanTrailingRepeats_HandlesEmptyString():
    assert clean_trailing_repeats("") == ""


def test_CleanTrailingRepeats_HandlesAllRepeats():
    text = "啊啊啊啊啊啊啊啊啊啊啊啊"
    result = clean_trailing_repeats(text)
    assert len(result) < len(text)


def test_CleanTrailingRepeats_RemovesRepeatedSentences():
    text = "好的内容。这个视频就到这里。这个视频就到这里。这个视频就到这里。这个视频就到这里。这个视频就到这里。"
    result = clean_trailing_repeats(text)
    assert result.count("这个视频就到这里") <= 2


# ── clean_text ───────────────────────────────────────────────────────────────

def test_CleanText_ProcessesSrtContent():
    srt = "1\n00:00:00,000 --> 00:00:05,000\n你好你好你好你好你好你好你好你好你好你好\n"
    result = clean_text(srt, suffix=".srt")
    assert "你好" in result
    assert result.count("你好") < 10


def test_CleanText_ProcessesPlainText():
    text = "正常文本内容\n第二行\n"
    result = clean_text(text, suffix=".txt")
    assert "正常文本内容" in result
