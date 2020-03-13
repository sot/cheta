class ComputedMsid:
    # Global dict of registered computed MSIDs
    msid_classes = {}

    # Default MSID attributes that are provided
    msid_attrs = ('times', 'vals', 'bads')

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.__name__.startswith('Comp_'):
            raise ValueError(f'comp class name {cls.__name__} must start with Comp_')
        cls.msid_classes[cls.__name__.upper()] = cls

    @property
    def fetch_eng(self):
        from .. import fetch_eng
        return fetch_eng

    @property
    def fetch_sci(self):
        from .. import fetch_sci
        return fetch_sci

    @property
    def fetch_cxc(self):
        from .. import fetch_cxc
        return fetch_cxc

    def __call__(self, start, stop):
        dat = self.get_MSID(start, stop)
        out = {attr: getattr(dat, attr) for attr in self.msid_attrs}
        return out


class Comp_MUPS_Clean:
    msid_attrs = ComputedMsid.msid_attrs + ('vals_raw', 'vals_nan', 'vals_corr',
                                            'vals_model', 'source')

    def get_MSID(self, start, stop):
        from .mups_valve import fetch_clean_msid
        dat = fetch_clean_msid(self.msid.lower(), start, stop,
                               dt_thresh=5.0, median=7, model_spec=None)
        return dat


class Comp_PM2THV1T(Comp_MUPS_Clean, ComputedMsid):
    msid = 'pm2thv1t'


class Comp_PM1THV2T(Comp_MUPS_Clean, ComputedMsid):
    msid = 'pm1thv2t'
