import re


class ComputedMsid:
    # Global dict of registered computed MSIDs
    msid_classes = []

    # Standard base MSID attributes that must be provided
    msid_attrs = ('times', 'vals', 'bads')

    # Extra MSID attributes that are provided beyond times, vals, bads
    extra_msid_attrs = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Validate class name, msid_attrs, msid_match
        if not cls.__name__.startswith('Comp_'):
            raise ValueError(f'comp class name {cls.__name__} must start with Comp_')

        cls.msid_attrs = ComputedMsid.msid_attrs + cls.extra_msid_attrs

        if not hasattr(cls, 'msid_match'):
            raise ValueError(f'comp {cls.__name__} must define msid_match')

        # Force match to include entire line
        cls.msid_match = cls.msid_match + '$'

        cls.msid_classes.append(cls)

    @classmethod
    def get_matching_comp_cls(cls, msid):
        for comp_cls in ComputedMsid.msid_classes:
            match = re.match(comp_cls.msid_match + '$', msid, re.IGNORECASE)
            if match:
                return comp_cls

        return None

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

    def __call__(self, start, stop, msid):
        match = re.match(self.msid_match, msid, re.IGNORECASE)
        if not match:
            raise RuntimeError(f'unexpected mismatch of {msid} with {self.msid_match}')
        match_args = [arg.lower() for arg in match.groups()]
        msid_attrs = self.get_msid_attrs(start, stop, msid.lower(), match_args)

        if set(msid_attrs) != set(self.msid_attrs):
            raise ValueError(f'computed class did not return expected attributes')

        return msid_attrs

    def get_msid_attrs(self, start, stop, msid, msid_args):
        """Get the attributes required for this MSID.

        TODO: detailed docs here since this is the main user-defined method
        """
        raise NotImplementedError()


class Comp_MUPS_Valve_Temp_Clean(ComputedMsid):
    msid_match = r'(pm2thv1t|pm1thv2t)_clean'
    extra_msid_attrs = ('vals_raw', 'vals_nan', 'vals_corr', 'vals_model', 'source')

    def get_msid_attrs(self, start, stop, msid, msid_args):
        from .mups_valve import fetch_clean_msid

        # Get cleaned MUPS valve temperature data as an MSID object
        dat = fetch_clean_msid(msid_args[0], start, stop,
                               dt_thresh=5.0, median=7, model_spec=None)

        # Convert to dict as required by the get_msids_attrs API
        msid_attrs = {attr: getattr(dat, attr) for attr in self.msid_attrs}

        return msid_attrs
