import re
from dataclasses import dataclass

@dataclass
class ParsedError:
    error_type: str        # TypeError, ValueError, ...
    error_message: str     # 完整错误消息
    file_path: str         # 出错文件
    line_number: int       # 出错行号
    traceback_text: str    # 原始 traceback

class ErrorDiagnosis:
    """Python 错误诊断模块 — 解析 traceback，生成诊断上下文。"""

    FILE_LINE_PATTERN = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+)')

    def parse_traceback(self, traceback_text: str) -> ParsedError | None:
        """解析 Python traceback 文本。

        从最后一行提取错误类型/消息，从底部向上找最后一个 File/line
        （即错误实际发生的内层帧）。
        """
        if not traceback_text or "Error" not in traceback_text and "Exception" not in traceback_text:
            return None

        lines = traceback_text.strip().split('\n')
        if not lines:
            return None

        # 错误类型/消息 — 最后一行
        last_line = lines[-1].strip()
        error_match = re.match(r'(\w+(?:Error|Exception))(.*)', last_line)
        error_type = error_match.group(1) if error_match else "Unknown"
        error_message = error_match.group(2).strip(": ") if error_match else ""

        # 文件/行号 — 从下往上找最后一个 File "..." line N（内层帧）
        file_path = "unknown"
        line_number = 0
        for line in reversed(lines):
            fl_match = self.FILE_LINE_PATTERN.search(line)
            if fl_match:
                file_path = fl_match.group("file")
                line_number = int(fl_match.group("line"))
                break

        return ParsedError(
            error_type=error_type,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
            traceback_text=traceback_text,
        )

    def build_diagnosis_context(self, error: ParsedError, code: str = "") -> str:
        """构建诊断上下文，注入 system prompt。
        注意：不再硬编码引导问题，由 LLM 根据具体错误生成合适的引导。"""
        context = f"错误类型: {error.error_type}\n"
        context += f"错误消息: {error.error_message}\n"
        if error.file_path:
            context += f"文件: {error.file_path}\n"
        if error.line_number:
            context += f"行号: {error.line_number}\n"
        if code:
            context += f"\n相关代码:\n```\n{code}\n```\n"
        return context
