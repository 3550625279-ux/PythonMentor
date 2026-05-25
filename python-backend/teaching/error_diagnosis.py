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

    TRACEBACK_PATTERN = re.compile(
        r'Traceback \(most recent call last\):\s*'
        r'(?:File "(?P<file>[^"]+)", line (?P<line>\d+), in .+\n'
        r'(?:  .+\n)*)?'
        r'(?P<error_type>\w+(?:Error|Exception))(?:: (?P<error_msg>.*))?',
        re.MULTILINE
    )

    def parse_traceback(self, traceback_text: str) -> ParsedError | None:
        """解析 Python traceback 文本。"""
        match = self.TRACEBACK_PATTERN.search(traceback_text)
        if not match:
            return None

        lines = traceback_text.strip().split('\n')
        last_line = lines[-1] if lines else ""
        error_match = re.match(r'(\w+(?:Error|Exception))(.*)', last_line)

        error_type = error_match.group(1) if error_match else "Unknown"
        error_message = error_match.group(2).strip(": ") if error_match else ""

        return ParsedError(
            error_type=error_type,
            error_message=error_message,
            file_path=match.group("file") or "unknown",
            line_number=int(match.group("line")) if match.group("line") else 0,
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
