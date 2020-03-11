class StringType:

    def __init__(self):
        self.text = ""

    def __add__(self, other):
        if isinstance(other, StringType):
            t = self.text + other.text
        else:
            t = self.text + other
        new = self.__class__()
        new.text = t
        return new

    def __radd__(self, other):
        if isinstance(other, StringType):
            t = self.text + other.text
        else:
            t = self.text + other
        new = self.__class__()
        new.text = t
        return new

    def __iadd__(self, other):
        if isinstance(other, StringType):
            self.text += other.text
        else:
            self.text += other
        return self

    def __getitem__(self, key):
        new = self.__class__()
        new.text = self.text[key]
        return new

    def __repr__(self):
        return self.text

    def __str__(self):
        return self.text

    def __len__(self):
        return len(self.text)


class IntType(StringType):

    def __add__(self, other):
        if other.isdigit():
            if isinstance(other, StringType):
                t = self.text + other.text
            else:
                t = self.text + other
        else:
            t = self.text
        new = self.__class__()
        new.text = t
        return new

    def __iadd__(self, other):
        if other.isdigit():
            if isinstance(other, IntType):
                self.text += other.text
            else:
                self.text += other
        return self


class PasswordType(StringType):

    def __repr__(self):
        return "*" * len(self.text)

    def __str__(self):
        return "*" * len(self.text)
