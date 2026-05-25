# Python 常见错误模式

## TypeError: unsupported operand type(s) for +: 'int' and 'str'

**原因**：尝试将整数和字符串直接相加，Python 不会自动类型转换。

**错误代码**：
```python
age = 20
print("我今年" + age + "岁")  # TypeError
```

**正确代码**：
```python
age = 20
print("我今年" + str(age) + "岁")  # 方法1：str() 转换
print(f"我今年{age}岁")            # 方法2：f-string（推荐）
```

**引导问题**：`+` 运算符在 Python 中对字符串和数字的行为一样吗？你觉得应该怎么处理？

---

## TypeError: 'NoneType' object is not subscriptable

**原因**：对 `None` 值尝试索引或切片操作，通常是因为函数没有返回值或变量未正确赋值。

**错误代码**：
```python
def find_item(lst, target):
    for item in lst:
        if item == target:
            return item
    # 没有显式 return，返回 None

result = find_item([1, 2, 3], 5)
print(result[0])  # TypeError: 'NoneType' object is not subscriptable
```

**正确代码**：
```python
def find_item(lst, target):
    for item in lst:
        if item == target:
            return item
    return None  # 显式返回 None

result = find_item([1, 2, 3], 5)
if result is not None:
    print(result[0])
else:
    print("未找到")
```

**引导问题**：这个变量的值可能是 `None` 吗？在什么情况下函数会不返回任何值？

---

## ValueError: could not convert string to float: 'abc'

**原因**：尝试将非数字字符串转换为数值类型。

**错误代码**：
```python
user_input = "abc"
number = float(user_input)  # ValueError
```

**正确代码**：
```python
user_input = "abc"
try:
    number = float(user_input)
except ValueError:
    print(f"'{user_input}' 不是有效的数字")
```

**引导问题**：`input()` 返回的是什么类型？如果用户输入的不是数字，直接转换会怎样？

---

## ValueError: too many values to unpack

**原因**：解包时变量数量与值的数量不匹配。

**错误代码**：
```python
a, b = [1, 2, 3]  # ValueError: too many values to unpack
```

**正确代码**：
```python
a, b, c = [1, 2, 3]  # 变量数量匹配

# 或者用 * 收集剩余值
a, *rest = [1, 2, 3]  # a=1, rest=[2, 3]
```

**引导问题**：左边有多少个变量？右边有多少个值？数量一样吗？

---

## IndexError: list index out of range

**原因**：访问的索引超出了列表的有效范围。

**错误代码**：
```python
my_list = [1, 2, 3]
print(my_list[5])  # IndexError: list index out of range
```

**正确代码**：
```python
my_list = [1, 2, 3]
if len(my_list) > 5:
    print(my_list[5])
else:
    print(f"索引 5 超出范围，列表长度为 {len(my_list)}")
```

**引导问题**：这个列表的长度是多少？你访问的索引是多少？Python 的索引从几开始？

---

## KeyError: 'name'

**原因**：尝试访问字典中不存在的键。

**错误代码**：
```python
student = {"name": "Alice", "age": 20}
print(student["grade"])  # KeyError: 'grade'
```

**正确代码**：
```python
student = {"name": "Alice", "age": 20}
print(student.get("grade", "未设置"))  # 返回默认值

# 或者先检查
if "grade" in student:
    print(student["grade"])
```

**引导问题**：字典里有哪些键？你访问的键在其中吗？用什么方法可以安全地访问可能不存在的键？

---

## AttributeError: 'str' object has no attribute 'append'

**原因**：调用了对象不具备的方法或属性。

**错误代码**：
```python
text = "hello"
text.append("!")  # AttributeError: 'str' object has no attribute 'append'
```

**正确代码**：
```python
text = "hello"
text += "!"  # 字符串拼接
# 或者用 join
result = "".join([text, "!"])
```

**引导问题**：这个变量是什么类型？这个类型有哪些方法？`append` 是哪些类型才有的方法？

---

## AttributeError: 'NoneType' object has no attribute 'xxx'

**原因**：变量值为 `None`，却尝试调用其方法。

**错误代码**：
```python
def get_name():
    pass  # 没有返回值，默认返回 None

name = get_name()
print(name.upper())  # AttributeError
```

**正确代码**：
```python
def get_name():
    return "Alice"  # 确保有返回值

name = get_name()
if name is not None:
    print(name.upper())
```

**引导问题**：函数真的返回了值吗？你可以在调用方法前打印这个变量，看看它的值是什么。

---

## NameError: name 'x' is not defined

**原因**：使用了未定义的变量，可能是拼写错误或变量在错误的作用域中。

**错误代码**：
```python
print(count)  # NameError: name 'count' is not defined
```

**正确代码**：
```python
count = 0  # 先定义变量
print(count)
```

**引导问题**：这个变量在使用之前定义了吗？是不是拼写错了？它是否定义在了另一个函数内部？

---

## NameError: name 'true' is not defined

**原因**：Python 的布尔值首字母大写，写成小写会被当作变量名。

**错误代码**：
```python
flag = true  # NameError: name 'true' is not defined
```

**正确代码**：
```python
flag = True  # 首字母大写
```

**引导问题**：Python 中的布尔值怎么写？和 JavaScript 有什么不同？

---

## ImportError: cannot import name 'xxx' from 'module'

**原因**：尝试从模块中导入不存在的名称。

**错误代码**：
```python
from math import square_root  # ImportError: cannot import name 'square_root'
```

**正确代码**：
```python
from math import sqrt  # 正确的函数名是 sqrt
```

**引导问题**：你确定这个函数名正确吗？可以用 `dir(math)` 或 `help(math)` 查看模块中有哪些函数。

---

## ModuleNotFoundError: No module named 'xxx'

**原因**：Python 找不到指定的模块，可能是未安装或路径问题。

**错误代码**：
```python
import numpy  # ModuleNotFoundError: No module named 'numpy'
```

**正确代码**：
```bash
# 在终端中安装
pip install numpy
```

**引导问题**：这个模块安装了吗？你用的是哪个 Python 环境？可以用 `pip list` 检查已安装的包。

---

## SyntaxError: invalid syntax

**原因**：代码不符合 Python 语法规则，通常是拼写错误、缺少符号或使用了其他语言的语法。

**错误代码**：
```python
if x = 5:  # SyntaxError: 应该用 == 而不是 =
    print("x is 5")

print("Hello"   # SyntaxError: 缺少右括号
```

**正确代码**：
```python
if x == 5:  # 比较用 ==
    print("x is 5")

print("Hello")  # 括号配对
```

**引导问题**：报错指向的那一行，有没有缺少括号、引号？是不是把 `==` 写成了 `=`？

---

## IndentationError: expected an indented block

**原因**：Python 用缩进表示代码块，缺少缩进或缩进不一致会报错。

**错误代码**：
```python
def greet(name):
print(f"Hello, {name}")  # IndentationError: 缺少缩进
```

**正确代码**：
```python
def greet(name):
    print(f"Hello, {name}")  # 函数体需要缩进
```

**引导问题**：函数体、循环体、条件分支的代码是否都正确缩进了？有没有混用 Tab 和空格？

---

## IndentationError: unindent does not match any outer indentation level

**原因**：缩进层级不匹配，通常是混用了 Tab 和空格。

**错误代码**：
```python
def foo():
    if True:
        print("a")
      print("b")  # IndentationError: 缩进层级不一致
```

**正确代码**：
```python
def foo():
    if True:
        print("a")
    print("b")  # 与 if 语句同级
```

**引导问题**：检查一下缩进，是不是 Tab 和空格混用了？VSCode 可以显示空白字符。

---

## ZeroDivisionError: division by zero

**原因**：除数为零。

**错误代码**：
```python
result = 10 / 0  # ZeroDivisionError
```

**正确代码**：
```python
divisor = 0
if divisor != 0:
    result = 10 / divisor
else:
    print("除数不能为零")

# 或者用 try/except
try:
    result = 10 / divisor
except ZeroDivisionError:
    print("除数不能为零")
```

**引导问题**：除数是从哪里来的？在什么情况下它可能是零？

---

## FileNotFoundError: [Errno 2] No such file or directory

**原因**：尝试打开不存在的文件。

**错误代码**：
```python
with open("nonexistent.txt") as f:  # FileNotFoundError
    content = f.read()
```

**正确代码**：
```python
import os

file_path = "nonexistent.txt"
if os.path.exists(file_path):
    with open(file_path) as f:
        content = f.read()
else:
    print(f"文件 {file_path} 不存在")
```

**引导问题**：文件路径正确吗？文件名有没有拼写错误？当前工作目录是哪里？

---

## PermissionError: [Errno 13] Permission denied

**原因**：没有足够的权限访问文件或目录。

**错误代码**：
```python
with open("/root/secret.txt") as f:  # PermissionError
    content = f.read()
```

**正确代码**：
```python
try:
    with open("/root/secret.txt") as f:
        content = f.read()
except PermissionError:
    print("没有权限访问该文件")
```

**引导问题**：你有读取/写入这个文件的权限吗？文件是否被其他程序占用？

---

## RecursionError: maximum recursion depth exceeded

**原因**：递归调用层数过深，通常是缺少终止条件。

**错误代码**：
```python
def countdown(n):
    print(n)
    countdown(n - 1)  # 没有终止条件，无限递归

countdown(5)  # RecursionError
```

**正确代码**：
```python
def countdown(n):
    if n <= 0:  # 终止条件
        return
    print(n)
    countdown(n - 1)

countdown(5)
```

**引导问题**：你的递归函数有终止条件吗？在什么情况下递归会停止？

---

## StopIteration

**原因**：迭代器耗尽后继续调用 `next()`。

**错误代码**：
```python
it = iter([1, 2, 3])
print(next(it))  # 1
print(next(it))  # 2
print(next(it))  # 3
print(next(it))  # StopIteration
```

**正确代码**：
```python
it = iter([1, 2, 3])
try:
    while True:
        print(next(it))
except StopIteration:
    pass  # 迭代结束

# 或者直接用 for 循环
for item in [1, 2, 3]:
    print(item)
```

**引导问题**：迭代器中还有元素吗？用 `for` 循环是不是更方便？

---

## UnicodeDecodeError: 'utf-8' codec can't decode byte

**原因**：尝试用 UTF-8 编码读取非 UTF-8 文件。

**错误代码**：
```python
with open("file.txt") as f:  # UnicodeDecodeError
    content = f.read()
```

**正确代码**：
```python
# 指定正确的编码
with open("file.txt", encoding="gbk") as f:
    content = f.read()

# 或者忽略无法解码的字符
with open("file.txt", encoding="utf-8", errors="ignore") as f:
    content = f.read()
```

**引导问题**：这个文件是什么编码的？Windows 中文系统常见的是 GBK 编码。

---

## TypeError: list object is not callable

**原因**：用变量名覆盖了内置函数名，之后尝试调用该函数时出错。

**错误代码**：
```python
list = [1, 2, 3]      # 用 list 作为变量名，覆盖了内置函数
result = list("hello") # TypeError: 'list' object is not callable
```

**正确代码**：
```python
my_list = [1, 2, 3]    # 用不同的变量名
result = list("hello")  # 现在可以正常使用内置函数
```

**引导问题**：你有没有用 `list`、`dict`、`str`、`int` 等作为变量名？这会覆盖 Python 的内置函数。

---

## TypeError: 'tuple' object does not support item assignment

**原因**：元组是不可变的，不能修改其中的元素。

**错误代码**：
```python
point = (3, 4)
point[0] = 10  # TypeError: 'tuple' object does not support item assignment
```

**正确代码**：
```python
# 如果需要修改，使用列表
point = [3, 4]
point[0] = 10

# 或者创建新的元组
point = (3, 4)
new_point = (10,) + point[1:]  # (10, 4)
```

**引导问题**：元组和列表有什么区别？为什么元组不允许修改元素？
