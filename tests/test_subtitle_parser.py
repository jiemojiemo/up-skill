"""
tests/test_subtitle_parser.py — subtitle_parser.py 的单元测试

遵循 unit-test-practices：
- AAA 结构
- 一个测试一个行为
- 命名描述行为，不重复方法名
- 不写注释（测试名即文档）
- 纯函数测试，无 IO 依赖
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from subtitle_parser import parse_srt, parse_vtt, parse_txt, merge_lines, parse_file


# ── parse_srt ────────────────────────────────────────────────────────────────

def test_ParseSrt_RemovesSequenceNumbers():
    srt = "1\n00:00:01,000 --> 00:00:02,000\n你好世界\n"
    result = parse_srt(srt)
    assert result == ["你好世界"]


def test_ParseSrt_RemovesTimecodes():
    srt = "1\n00:00:01,000 --> 00:00:02,000\n测试文本\n"
    result = parse_srt(srt)
    assert "00:00:01,000" not in " ".join(result)


def test_ParseSrt_RemovesHtmlTags():
    srt = "1\n00:00:01,000 --> 00:00:02,000\n<i>斜体文字</i>\n"
    result = parse_srt(srt)
    assert result == ["斜体文字"]


def test_ParseSrt_PreservesMultipleLines():
    srt = (
        "1\n00:00:01,000 --> 00:00:02,000\n第一句\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\n第二句\n"
    )
    result = parse_srt(srt)
    assert result == ["第一句", "第二句"]


def test_ParseSrt_ReturnsEmptyListForEmptyInput():
    result = parse_srt("")
    assert result == []


def test_ParseSrt_SkipsBlankLines():
    srt = "1\n00:00:01,000 --> 00:00:02,000\n\n有内容\n"
    result = parse_srt(srt)
    assert "" not in result


# ── parse_vtt ────────────────────────────────────────────────────────────────

def test_ParseVtt_RemovesWebvttHeader():
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n你好\n"
    result = parse_vtt(vtt)
    assert "WEBVTT" not in result
    assert result == ["你好"]


def test_ParseVtt_RemovesTimecodes():
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n内容\n"
    result = parse_vtt(vtt)
    assert "00:00:01.000" not in " ".join(result)


def test_ParseVtt_RemovesVttTags():
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<b>加粗</b>\n"
    result = parse_vtt(vtt)
    assert result == ["加粗"]


def test_ParseVtt_DecodesHtmlEntities():
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n&amp;符号\n"
    result = parse_vtt(vtt)
    assert result == ["&符号"]


def test_ParseVtt_SkipsNoteLines():
    vtt = "WEBVTT\n\nNOTE 这是注释\n\n00:00:01.000 --> 00:00:02.000\n内容\n"
    result = parse_vtt(vtt)
    assert all("NOTE" not in line for line in result)


# ── parse_txt ────────────────────────────────────────────────────────────────

def test_ParseTxt_ReturnsNonEmptyLines():
    txt = "第一行\n\n第二行\n   \n第三行"
    result = parse_txt(txt)
    assert result == ["第一行", "第二行", "第三行"]


def test_ParseTxt_TrimsWhitespace():
    txt = "  有空格  \n\t制表符\t"
    result = parse_txt(txt)
    assert result == ["有空格", "制表符"]


def test_ParseTxt_ReturnsEmptyListForBlankInput():
    result = parse_txt("   \n\n   ")
    assert result == []


# ── merge_lines ───────────────────────────────────────────────────────────────

def test_MergeLines_JoinsLinesIntoChunks():
    lines = ["第一句", "第二句", "第三句"]
    result = merge_lines(lines, chunk_size=2)
    assert len(result) == 2
    assert result[0] == "第一句 第二句"
    assert result[1] == "第三句"


def test_MergeLines_ReturnsOneChunkWhenLinesFewerThanChunkSize():
    lines = ["a", "b", "c"]
    result = merge_lines(lines, chunk_size=10)
    assert len(result) == 1
    assert result[0] == "a b c"


def test_MergeLines_ReturnsEmptyListForEmptyInput():
    result = merge_lines([], chunk_size=10)
    assert result == []


def test_MergeLines_DefaultChunkSizeIsTen():
    lines = [str(i) for i in range(25)]
    result = merge_lines(lines)
    assert len(result) == 3  # 10 + 10 + 5


# ── parse_file ────────────────────────────────────────────────────────────────

def test_ParseFile_ParsesSrtFileByExtension(tmp_path):
    srt_file = tmp_path / "test.srt"
    srt_file.write_text("1\n00:00:01,000 --> 00:00:02,000\n测试内容\n", encoding="utf-8")
    result = parse_file(srt_file)
    assert "测试内容" in result


def test_ParseFile_ParsesVttFileByExtension(tmp_path):
    vtt_file = tmp_path / "test.vtt"
    vtt_file.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n测试内容\n", encoding="utf-8")
    result = parse_file(vtt_file)
    assert "测试内容" in result


def test_ParseFile_ParsesTxtFileByExtension(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("第一行\n第二行\n", encoding="utf-8")
    result = parse_file(txt_file)
    assert "第一行" in result


def test_ParseFile_DeduplicatesAdjacentIdenticalLines(tmp_path):
    srt_file = tmp_path / "test.srt"
    srt_file.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n重复内容\n\n"
        "2\n00:00:02,000 --> 00:00:03,000\n重复内容\n\n"
        "3\n00:00:03,000 --> 00:00:04,000\n不同内容\n",
        encoding="utf-8"
    )
    result = parse_file(srt_file)
    assert result.count("重复内容") == 1


def test_ParseFile_ReturnsNonEmptyStringForValidFile(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("有内容的文件\n", encoding="utf-8")
    result = parse_file(txt_file)
    assert len(result) > 0
