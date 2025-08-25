"""Provide a singleton class to define data source (CXC or MAUDE or combination)"""

import ast

# Default source of data.
DEFAULT_DATA_SOURCE = "cxc"


class DataSourceMeta(type):
    """
    Metaclass for the data_source class that updates the repr to be more informative
    """

    def __repr__(cls):
        out = super().__repr__()
        return out[:-1] + f" options={cls.options()}" + out[-1]


class data_source(metaclass=DataSourceMeta):
    """
    Context manager and singleton config object for managing telem data_sources(s).
    """

    _data_sources = (DEFAULT_DATA_SOURCE,)
    _allowed = ("cxc", "maude", "MAUDE", "test-drop-half")

    def __init__(self, *data_sources):
        self._new_data_sources = data_sources

    def __enter__(self):
        self._orig_data_sources = self.__class__._data_sources
        self.set(*self._new_data_sources)

    def __exit__(self, type, value, traceback):
        self.__class__._data_sources = self._orig_data_sources

    @classmethod
    def set(cls, *data_sources):
        """
        Set current data sources.

        :param data_sources: one or more sources (str)
        """
        if any(
            data_source.split()[0] not in cls._allowed for data_source in data_sources
        ):
            raise ValueError(
                "data_sources {} not in allowed set {}".format(
                    data_sources, cls._allowed
                )
            )

        if len(data_sources) == 0:
            raise ValueError(
                "must select at least one data source in {}".format(cls._allowed)
            )

        cls._data_sources = data_sources

    @classmethod
    def sources(cls, include_test=True):
        """
        Get tuple of current data sources names.

        :param include_test: include sources that start with 'test'
        :returns: tuple of data source names
        """
        sources = (
            tuple(cls.options())
            if include_test
            else tuple(x for x in cls.options() if not x.startswith("test"))
        )

        return sources

    @classmethod
    def get_msids(cls, source):
        """
        Get the set of MSID names corresponding to ``source`` (e.g. 'cxc' or 'MAUDE')

        :param source: str
        :returns: set of MSIDs
        """
        import cheta.fetch  # noqa: PLC0415

        source = source.split()[0].lower()

        if source == "cxc":
            out = list(cheta.fetch.content.keys())
        elif source == "maude":
            import maude  # noqa: PLC0415

            out = list(maude.MSIDS.keys())
        else:
            raise ValueError('source must be "cxc" or "maude" (case ignored)')

        return set(out)

    @classmethod
    def options(cls):
        """
        Get the data sources and corresponding options as a dict.

        Example::

          >>> data_source.set('cxc', 'maude allow_subset=False')
          >>> data_source.options()
          {'cxc': {}, 'maude': {'allow_subset': False}}

        :returns: dict of data source options
        """

        out = {}
        for source in cls._data_sources:
            vals = source.split()
            name, opts = vals[0], vals[1:]

            # Special case for "MAUDE" which is an alias for "maude
            # allow_subset=False". This sets the default but it could be overridden, for
            # example with "MAUDE allow_subset=True".
            if name == "MAUDE":
                name = "maude"
                opts.insert(0, "allow_subset=False")

            out[name] = {}
            for opt in opts:
                key, val = opt.split("=")
                val = ast.literal_eval(val)
                out[name][key] = val

        return out
