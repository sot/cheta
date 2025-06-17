import ast

# Default source of data.
DEFAULT_DATA_SOURCE = "cxc"


class data_source:
    """
    Context manager and quasi-singleton configuration object for managing the
    data_source(s) used for fetching telemetry.
    """

    _data_sources = (DEFAULT_DATA_SOURCE,)
    _allowed = ("cxc", "maude", "test-drop-half")

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
        if include_test:
            sources = cls._data_sources
        else:
            sources = [x for x in cls._data_sources if not x.startswith("test")]

        return tuple(source.split()[0] for source in sources)

    @classmethod
    def get_msids(cls, source):
        """
        Get the set of MSID names corresponding to ``source`` (e.g. 'cxc' or 'maude')

        :param source: str
        :returns: set of MSIDs
        """
        import cheta.fetch  # noqa: PLC0415

        source = source.split()[0]

        if source == "cxc":
            out = list(cheta.fetch.content.keys())
        elif source == "maude":
            import maude  # noqa: PLC0415

            out = list(maude.MSIDS.keys())
        else:
            raise ValueError('source must be "cxc" or "msid"')

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
            out[name] = {}
            for opt in opts:
                key, val = opt.split("=")
                val = ast.literal_eval(val)
                out[name][key] = val

        return out
