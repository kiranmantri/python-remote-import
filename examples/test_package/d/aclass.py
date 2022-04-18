class SomeUselessClass:
    attr1 = "1"
    attr2 = "two"
    attr3 = "3"

    def __init__(self):
        self.attr4 = "the attribute 4 was created in the constructor"

    def __repr__(self):
        return f"attr1={self.attr1},\nattr2={self.attr2},\nattr3={self.attr3},\nattr4={self.attr4}"
