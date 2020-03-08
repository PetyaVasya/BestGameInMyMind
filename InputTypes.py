class StringType:

    def __init__(self):
        self.text = ""

    def __add__(self, other: str):
        self.text += other
        return self

    def __radd__(self, other):
        return self.text + other

    def __iadd__(self, other: str):
        self.text += other

    def __getitem__(self, key):
        return self.text[key]

    def __repr__(self):
        return self.text

    def __str__(self):
        return self.text


class IntType(StringType):

    def __add__(self, other: str):
        if other.isdigit():
            self.text += other
        return self

    def __iadd__(self, other: str):
        if other.isdigit():
            self.text += other
        return self


class Password(StringType):

    def __repr__(self):
        return "*" * len(self.text)

    def __str__(self):
        return "*" * len(self.text)


a = Password() + "asdasdasd"
print(a)