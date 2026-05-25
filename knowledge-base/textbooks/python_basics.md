# Python 基础知识

## 变量与数据类型

Python 是动态类型语言，变量不需要声明类型。常见基本类型包括：
- `int`：整数，如 `42`、`-7`
- `float`：浮点数，如 `3.14`、`-0.5`
- `str`：字符串，如 `"hello"`、`'world'`
- `bool`：布尔值，`True` 或 `False`
- `NoneType`：空值，用 `None` 表示

可以用 `type()` 函数查看变量类型：
```python
x = 42
print(type(x))  # <class 'int'>
```

## 变量命名规则

变量名只能包含字母、数字和下划线，不能以数字开头。Python 区分大小写。
```python
my_name = "Alice"    # 合法
_count = 10          # 合法
2nd_value = 5        # 不合法，不能以数字开头
my-name = "Bob"      # 不合法，不能包含连字符
```

## 字符串操作

字符串是不可变的序列类型。常用操作：
```python
s = "Hello, World!"
print(len(s))        # 13，获取长度
print(s[0])          # 'H'，索引访问
print(s[0:5])        # 'Hello'，切片
print(s.lower())     # 'hello, world!'，转小写
print(s.upper())     # 'HELLO, WORLD!'，转大写
print(s.replace("World", "Python"))  # 'Hello, Python!'
print(s.split(", ")) # ['Hello', 'World!']，按分隔符分割
```

## f-string 格式化

f-string 是 Python 3.6+ 推荐的字符串格式化方式：
```python
name = "Alice"
age = 20
print(f"我叫{name}，今年{age}岁")
print(f"明年{age + 1}岁")
print(f"PI 约等于{3.14159:.2f}")  # 保留2位小数
```

## 列表（list）

列表是有序、可变的序列，可以存储不同类型的元素：
```python
fruits = ["apple", "banana", "cherry"]
fruits.append("date")       # 末尾添加
fruits.insert(1, "blueberry")  # 指定位置插入
fruits.remove("banana")     # 删除指定元素
popped = fruits.pop()       # 弹出末尾元素
print(len(fruits))          # 列表长度
print("apple" in fruits)    # True，检查是否包含
```

## 列表推导式

列表推导式是创建列表的简洁方式：
```python
# 基本形式
squares = [x**2 for x in range(10)]  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# 带条件过滤
evens = [x for x in range(20) if x % 2 == 0]  # [0, 2, 4, ..., 18]

# 带变换
words = ["hello", "world"]
upper_words = [w.upper() for w in words]  # ['HELLO', 'WORLD']
```

## 元组（tuple）

元组是有序、不可变的序列。一旦创建不能修改：
```python
point = (3, 4)
x, y = point  # 解包
print(x)      # 3

# 单元素元组需要逗号
single = (42,)   # 这是元组
not_tuple = (42)  # 这是整数
```

## 字典（dict）

字典是键值对集合，键必须是不可变类型（str、int、tuple 等）：
```python
student = {"name": "Alice", "age": 20, "grades": [85, 90, 78]}

# 访问
print(student["name"])           # "Alice"
print(student.get("email", ""))  # ""，键不存在返回默认值

# 修改和添加
student["age"] = 21
student["email"] = "alice@example.com"

# 遍历
for key, value in student.items():
    print(f"{key}: {value}")
```

## 集合（set）

集合是无序、不重复的元素集合，常用于去重和集合运算：
```python
a = {1, 2, 3, 4}
b = {3, 4, 5, 6}
print(a | b)   # {1, 2, 3, 4, 5, 6}，并集
print(a & b)   # {3, 4}，交集
print(a - b)   # {1, 2}，差集

# 列表去重
numbers = [1, 2, 2, 3, 3, 3]
unique = list(set(numbers))  # [1, 2, 3]（顺序可能变化）
```

## 条件语句（if/elif/else）

Python 用缩进表示代码块，不需要花括号：
```python
score = 85
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "D"
```

## 三元表达式

条件表达式的简洁写法：
```python
x = 10
result = "正数" if x > 0 else "非正数"

# 等价于
if x > 0:
    result = "正数"
else:
    result = "非正数"
```

## for 循环

```python
# 遍历列表
for fruit in ["apple", "banana", "cherry"]:
    print(fruit)

# 遍历范围
for i in range(5):       # 0, 1, 2, 3, 4
    print(i)

for i in range(2, 10, 3):  # 2, 5, 8（起始, 终止, 步长）
    print(i)

# 遍历字典
for key, value in {"a": 1, "b": 2}.items():
    print(f"{key}={value}")
```

## while 循环

```python
count = 0
while count < 5:
    print(count)
    count += 1

# break 和 continue
while True:
    user_input = input("输入 quit 退出: ")
    if user_input == "quit":
        break
    if user_input == "":
        continue  # 跳过空输入
    print(f"你输入了: {user_input}")
```

## 函数定义

```python
def greet(name: str, greeting: str = "你好") -> str:
    """问候函数。

    Args:
        name: 被问候者的名字
        greeting: 问候语，默认为"你好"

    Returns:
        格式化的问候字符串
    """
    return f"{greeting}, {name}!"

print(greet("Alice"))           # "你好, Alice!"
print(greet("Bob", "早上好"))    # "早上好, Bob!"
```

## 可变参数（*args 和 **kwargs）

```python
def sum_all(*args):
    """接收任意数量的位置参数。"""
    return sum(args)

print(sum_all(1, 2, 3))  # 6

def print_info(**kwargs):
    """接收任意数量的关键字参数。"""
    for key, value in kwargs.items():
        print(f"{key}: {value}")

print_info(name="Alice", age=20)
```

## Lambda 表达式

Lambda 是匿名函数，适合简短的一次性使用：
```python
# 基本语法
square = lambda x: x**2
print(square(5))  # 25

# 常用于排序
students = [("Alice", 85), ("Bob", 90), ("Charlie", 78)]
students.sort(key=lambda s: s[1])  # 按成绩排序

# 常用于 map/filter
numbers = [1, 2, 3, 4, 5]
squared = list(map(lambda x: x**2, numbers))  # [1, 4, 9, 16, 25]
evens = list(filter(lambda x: x % 2 == 0, numbers))  # [2, 4]
```

## 类（class）

```python
class Dog:
    """狗类。"""

    species = "Canis familiaris"  # 类属性

    def __init__(self, name: str, age: int):
        """初始化方法。"""
        self.name = name    # 实例属性
        self.age = age

    def bark(self) -> str:
        """实例方法。"""
        return f"{self.name}: 汪汪！"

    def __str__(self) -> str:
        """字符串表示。"""
        return f"Dog({self.name}, {self.age}岁)"

dog = Dog("旺财", 3)
print(dog)          # Dog(旺财, 3岁)
print(dog.bark())   # 旺财: 汪汪！
```

## 继承

```python
class Animal:
    def __init__(self, name: str):
        self.name = name

    def speak(self):
        raise NotImplementedError("子类必须实现 speak 方法")

class Cat(Animal):
    def speak(self):
        return f"{self.name}: 喵~"

class Dog(Animal):
    def speak(self):
        return f"{self.name}: 汪！"

animals = [Cat("小花"), Dog("旺财")]
for animal in animals:
    print(animal.speak())
```

## 异常处理（try/except）

```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("不能除以零！")
except (ValueError, TypeError) as e:
    print(f"值或类型错误: {e}")
else:
    print("没有异常时执行")
finally:
    print("无论如何都会执行")
```

## 自定义异常

```python
class AgeError(Exception):
    """自定义年龄异常。"""
    def __init__(self, age: int, message: str = "年龄不合法"):
        self.age = age
        self.message = message
        super().__init__(self.message)

def set_age(age: int):
    if age < 0 or age > 150:
        raise AgeError(age, f"年龄 {age} 不在合理范围内")
    return age

try:
    set_age(200)
except AgeError as e:
    print(f"错误: {e}，传入的年龄是 {e.age}")
```

## 文件读写

```python
# 写入文件
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n")
    f.write("第二行\n")

# 读取整个文件
with open("output.txt", "r", encoding="utf-8") as f:
    content = f.read()

# 逐行读取
with open("output.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.strip())  # strip() 去掉末尾换行符

# 追加写入
with open("output.txt", "a", encoding="utf-8") as f:
    f.write("追加的内容\n")
```

## 模块导入

```python
# 导入整个模块
import math
print(math.sqrt(16))  # 4.0

# 导入特定函数
from math import sqrt, pi
print(sqrt(16))  # 4.0

# 别名
import numpy as np
from datetime import datetime as dt

# 导入自定义模块
# 假设项目结构:
# my_project/
#   utils.py
#   main.py
# 在 main.py 中:
# from utils import helper_function
```

## 包（package）

包是包含 `__init__.py` 文件的目录：
```
my_package/
    __init__.py      # 可以为空，标识这是一个包
    module_a.py
    module_b.py
    sub_package/
        __init__.py
        module_c.py
```

```python
from my_package.module_a import func_a
from my_package.sub_package.module_c import func_c
```

## 切片操作

切片语法：`sequence[start:stop:step]`
```python
lst = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
print(lst[2:5])     # [2, 3, 4]
print(lst[:3])      # [0, 1, 2]
print(lst[7:])      # [7, 8, 9]
print(lst[::2])     # [0, 2, 4, 6, 8]，步长为2
print(lst[::-1])    # [9, 8, 7, ..., 0]，反转
print(lst[-3:])     # [7, 8, 9]，最后3个
```

## enumerate 和 zip

```python
# enumerate 同时获取索引和值
fruits = ["apple", "banana", "cherry"]
for i, fruit in enumerate(fruits):
    print(f"{i}: {fruit}")

# zip 并行遍历多个序列
names = ["Alice", "Bob", "Charlie"]
scores = [85, 90, 78]
for name, score in zip(names, scores):
    print(f"{name}: {score}")
```

## 常用内置函数

```python
numbers = [3, 1, 4, 1, 5, 9, 2, 6]

print(len(numbers))     # 8，长度
print(max(numbers))     # 9，最大值
print(min(numbers))     # 1，最小值
print(sum(numbers))     # 31，求和
print(sorted(numbers))  # [1, 1, 2, 3, 4, 5, 6, 9]，排序（返回新列表）
print(reversed(numbers))  # 反转迭代器
print(list(reversed(numbers)))  # [6, 2, 9, 5, 1, 4, 1, 3]

# 类型转换
print(int("42"))       # 42
print(float("3.14"))   # 3.14
print(str(100))        # "100"
print(list("hello"))   # ['h', 'e', 'l', 'l', 'o']
```

## 海象运算符（:=）

Python 3.8+ 的赋值表达式，可以在表达式内部赋值：
```python
# 传统写法
line = input("输入: ")
while line != "quit":
    print(f"你输入了: {line}")
    line = input("输入: ")

# 使用海象运算符
while (line := input("输入: ")) != "quit":
    print(f"你输入了: {line}")

# 在列表推导式中使用
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
results = [y for x in data if (y := x**2) > 20]  # [25, 36, 49, 64, 81, 100]
```

## 类型提示（Type Hints）

Python 3.5+ 支持类型提示，提高代码可读性：
```python
from typing import Optional, Union

def process(data: list[int], flag: bool = False) -> Optional[str]:
    """处理数据。"""
    if not data:
        return None
    return str(sum(data))

# Union 表示可以是多种类型
def get_value(key: str) -> Union[int, str]:
    ...

# Python 3.10+ 可以用 | 替代 Union
def get_value(key: str) -> int | str:
    ...
```

## 上下文管理器（with 语句）

```python
# 文件操作是最常见的上下文管理器
with open("file.txt") as f:
    content = f.read()
# 离开 with 块后文件自动关闭

# 自定义上下文管理器
class Timer:
    import time

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start
        print(f"耗时: {self.elapsed:.2f} 秒")

with Timer():
    sum(range(1000000))
```

## 生成器（generator）

生成器是惰性求值的迭代器，适合处理大量数据：
```python
# 生成器函数（使用 yield）
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# 使用生成器
fib = fibonacci()
for _ in range(10):
    print(next(fib))  # 0, 1, 1, 2, 3, 5, 8, 13, 21, 34

# 生成器表达式（类似列表推导式，但用圆括号）
squares_gen = (x**2 for x in range(1000000))  # 不会立即占用内存
print(sum(squares_gen))
```

## 装饰器（decorator）

装饰器是在不修改原函数的情况下扩展函数功能的方式：
```python
import time

def timer(func):
    """计时装饰器。"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} 耗时: {elapsed:.4f} 秒")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(1)
    return "完成"

slow_function()  # slow_function 耗时: 1.0012 秒
```

## 常见数据序列化

```python
import json

# JSON 序列化
data = {"name": "Alice", "scores": [85, 90, 78]}
json_str = json.dumps(data, ensure_ascii=False, indent=2)
print(json_str)

# JSON 反序列化
parsed = json.loads(json_str)
print(parsed["name"])  # Alice

# 读写 JSON 文件
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open("data.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
```

## 字符串常用方法补充

```python
s = "  Hello, World!  "
print(s.strip())       # "Hello, World!"，去除首尾空白
print(s.lstrip())      # "Hello, World!  "，去除左侧空白
print(s.rstrip())      # "  Hello, World!"，去除右侧空白

print("hello world".title())    # "Hello World"
print("hello world".capitalize())  # "Hello world"

print("hello".center(20, "-"))  # "-------hello--------"
print(",".join(["a", "b", "c"]))  # "a,b,c"
print("a,b,c".split(","))       # ['a', 'b', 'c']

# 字符串检查
print("hello123".isalnum())   # True
print("hello".isalpha())      # True
print("123".isdigit())        # True
print("  ".isspace())         # True
print("hello".startswith("he"))  # True
print("hello".endswith("lo"))    # True
```
