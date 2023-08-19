# lexz
Remapping Variable Using Abstract Syntax Tree [(AST)](https://docs.python.org/3/library/ast.html) 

# Demo
### Input

```python
class HelloWorld:
    def __init__(self) -> None:
        self.a = 3

        class HelloWorld2:
            def __init__(selx) -> None:
                selx.a = 3
                self.oke = 8
                for i in range(10):
                    self.for_ = i

            async def xyz(self, a, *x):
                self.j = 4
                print("test")
                async for i in range(10):
                    self.tesx = i
                async with open("test3.py", "r") as f:
                    print(f.read())
                lambda ho: 123

```

### Result Graphviz( Dot Graph )
![image](https://raw.githubusercontent.com/krypton-byte/lexz/master/assets/output.svg)
