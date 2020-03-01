def zero_args(func):

    def new(self, *args, **kwargs):
        return func(self)

    return new
