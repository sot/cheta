from collections import OrderedDict


class LazyDict(OrderedDict):
    def __init__(self, load_func, *args, **kwargs):
        self._load_func = load_func
        self._args = args
        self._kwargs = kwargs
        self._loaded = False
        self._loading = False
        super(LazyDict, self).__init__()

    def load(self):
        if not self._loading and not self._loaded:
            vals = OrderedDict(self._load_func(*self._args, **self._kwargs))

            # update() calls methods like __contains__ so need to disable loading.
            self._loading = True
            self.update(vals)
            self._loading = False

            self._loaded = True

    def __getitem__(self, item):
        self.load()
        return super(LazyDict, self).__getitem__(item)

    def __contains__(self, item):
        self.load()
        return super(LazyDict, self).__contains__(item)

    def keys(self):
        self.load()
        return super(LazyDict, self).keys()

    def values(self):
        self.load()
        return super(LazyDict, self).values()

    def items(self):
        self.load()
        return super(LazyDict, self).items()

    def __len__(self):
        self.load()
        return super(LazyDict, self).__len__()
