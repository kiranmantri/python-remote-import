import test_package.b
import test_package.c.sub_c


def main():
    print(f"Value of from module b: {test_package.b.value}")
    print(f"Value of from sub module c: {test_package.c.sub_c.value}")


def sum(a: int, b: int) -> int:
    return a + b


def some_function() -> str:
    return "60"
