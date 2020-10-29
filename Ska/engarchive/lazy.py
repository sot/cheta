class LazyDict(dict):
    def __init__(self, load_func, *args, **kwargs):
        self._load_func = load_func
        self._args = args
        self._kwargs = kwargs
        self._loaded = False
        super().__init__()

    def load(self):
        if not self._loaded:
            self.update(self._load_func(*self._args, **self._kwargs))
            self._loaded = True

            # Clear these out so pickling always works (pickling a func can fail)
            self._load_func = None
            self._args = None
            self._kwargs = None

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            self.load()
            return super().__getitem__(item)

    def __contains__(self, item):
        self.load()
        return super().__contains__(item)

    def keys(self):
        self.load()
        return super().keys()

    def values(self):
        self.load()
        return super().values()

    def items(self):
        self.load()
        return super().items()

    def __len__(self):
        self.load()
        return super().__len__()

    def get(self, key, default=None, /):
        self.load()
        return super().get(key, default)
