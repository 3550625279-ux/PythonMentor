# Python 常见代码模式

## 模式 1：安全的用户输入处理

处理用户输入时，需要验证和类型转换，不能直接信任输入。

```python
def get_integer(prompt: str) -> int:
    """持续提示用户输入，直到得到一个有效的整数。"""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("请输入一个有效的整数。")

age = get_integer("请输入你的年龄: ")
print(f"你的年龄是 {age}")
```

---

## 模式 2：安全的字典访问

避免 KeyError 的三种方式，根据场景选择。

```python
student = {"name": "Alice", "age": 20}

# 方式 1：in 检查
if "email" in student:
    print(student["email"])

# 方式 2：get() 方法（推荐，可设默认值）
email = student.get("email", "未设置")

# 方式 3：setdefault() —— 不存在则设置并返回
student.setdefault("email", "unknown@example.com")
```

---

## 模式 3：列表过滤与变换

用列表推导式替代 map/filter 组合，更 Pythonic。

```python
numbers = [1, -2, 3, -4, 5, -6, 7, -8, 9, -10]

# 获取正数的平方
result = [x**2 for x in numbers if x > 0]
# [1, 9, 25, 49, 81]

# 等价的 map/filter 写法（更啰嗦）
result = list(map(lambda x: x**2, filter(lambda x: x > 0, numbers)))
```

---

## 模式 4：文件处理与上下文管理器

始终使用 `with` 语句处理文件，确保文件正确关闭。

```python
# 读取并处理 CSV 类数据
def read_scores(filepath: str) -> dict[str, float]:
    """从文件读取学生姓名和分数。"""
    scores = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # 跳过空行和注释
            parts = line.split(",")
            if len(parts) == 2:
                name, score = parts[0].strip(), float(parts[1].strip())
                scores[name] = score
    return scores
```

---

## 模式 5：异常处理的最佳实践

捕获具体的异常类型，不要用裸 except。

```python
import json

def load_config(filepath: str) -> dict:
    """加载 JSON 配置文件，出错时返回默认配置。"""
    default_config = {"debug": False, "port": 8000}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件 {filepath} 不存在，使用默认配置")
        return default_config
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}，使用默认配置")
        return default_config
    except PermissionError:
        print(f"没有权限读取 {filepath}，使用默认配置")
        return default_config
```

---

## 模式 6：计数器模式

用字典统计元素出现次数，或直接用 `collections.Counter`。

```python
from collections import Counter

# 手动实现
words = ["apple", "banana", "apple", "cherry", "banana", "apple"]
count = {}
for word in words:
    count[word] = count.get(word, 0) + 1
# {'apple': 3, 'banana': 2, 'cherry': 1}

# 用 Counter（更简洁）
counter = Counter(words)
print(counter.most_common(2))  # [('apple', 3), ('banana', 2)]
```

---

## 模式 7：缓存/记忆化模式

用字典缓存函数结果，避免重复计算。

```python
# 手动缓存
_cache = {}

def fibonacci(n: int) -> int:
    """带缓存的斐波那契函数。"""
    if n in _cache:
        return _cache[n]
    if n <= 1:
        return n
    result = fibonacci(n - 1) + fibonacci(n - 2)
    _cache[n] = result
    return result

# 更优雅的方式：用 functools.lru_cache
from functools import lru_cache

@lru_cache(maxsize=128)
def fib(n: int) -> int:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

---

## 模式 8：数据分组模式

按条件将数据分成不同组。

```python
students = [
    {"name": "Alice", "score": 85},
    {"name": "Bob", "score": 92},
    {"name": "Charlie", "score": 67},
    {"name": "Diana", "score": 78},
    {"name": "Eve", "score": 95},
]

# 按成绩等级分组
def group_by_grade(students: list[dict]) -> dict[str, list[str]]:
    groups = {"A": [], "B": [], "C": [], "D": [], "F": []}
    for s in students:
        score = s["score"]
        if score >= 90:
            groups["A"].append(s["name"])
        elif score >= 80:
            groups["B"].append(s["name"])
        elif score >= 70:
            groups["C"].append(s["name"])
        elif score >= 60:
            groups["D"].append(s["name"])
        else:
            groups["F"].append(s["name"])
    return groups

# 更通用的方式：用 defaultdict
from collections import defaultdict

def group_by(students: list[dict], key_func) -> dict:
    groups = defaultdict(list)
    for s in students:
        groups[key_func(s)].append(s["name"])
    return dict(groups)

# 使用
result = group_by(students, lambda s: "优秀" if s["score"] >= 90 else "其他")
```

---

## 模式 9：命令行参数解析

用 `argparse` 处理命令行参数。

```python
import argparse

def main():
    parser = argparse.ArgumentParser(description="PythonMentor 命令行工具")
    parser.add_argument("action", choices=["index", "serve", "test"],
                        help="要执行的操作")
    parser.add_argument("--data", type=str, default="./data",
                        help="数据目录路径")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="显示详细输出")

    args = parser.parse_args()

    if args.verbose:
        print(f"操作: {args.action}, 数据目录: {args.data}")

    if args.action == "index":
        print("正在构建索引...")
    elif args.action == "serve":
        print("正在启动服务...")
    elif args.action == "test":
        print("正在运行测试...")

if __name__ == "__main__":
    main()
```

---

## 模式 10：单例模式

确保一个类只有一个实例。

```python
class Database:
    """数据库连接单例。"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, url: str = "localhost"):
        if self._initialized:
            return
        self.url = url
        self._initialized = True
        print(f"连接到数据库: {url}")

# 无论创建多少次，都是同一个实例
db1 = Database("localhost")
db2 = Database("remote")  # 不会打印，因为已经初始化过了
print(db1 is db2)  # True
```

---

## 模式 11：retry 重试模式

网络请求或不稳定操作需要重试机制。

```python
import time

def retry(func, max_attempts: int = 3, delay: float = 1.0):
    """带重试的函数执行器。"""
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            print(f"第 {attempt} 次尝试失败: {e}")
            if attempt < max_attempts:
                time.sleep(delay * attempt)  # 指数退避
            else:
                raise  # 最后一次仍失败则抛出异常

# 使用
result = retry(lambda: fetch_data_from_api(), max_attempts=3)
```

---

## 模式 12：数据验证模式

用简单的函数验证输入数据。

```python
def validate_student(data: dict) -> list[str]:
    """验证学生数据，返回错误列表。"""
    errors = []

    if "name" not in data or not data["name"].strip():
        errors.append("姓名不能为空")

    if "age" not in data:
        errors.append("年龄不能为空")
    elif not isinstance(data["age"], int) or data["age"] < 0 or data["age"] > 150:
        errors.append("年龄必须是 0-150 之间的整数")

    if "email" in data and "@" not in data["email"]:
        errors.append("邮箱格式不正确")

    return errors

# 使用
student = {"name": "Alice", "age": -5, "email": "invalid"}
errors = validate_student(student)
if errors:
    for error in errors:
        print(f"错误: {error}")
else:
    print("数据有效")
```
