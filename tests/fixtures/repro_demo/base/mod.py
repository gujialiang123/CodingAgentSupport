"""Minimal stand-in for the astropy TimeSeries required-column bug."""

REQUIRED = ["time", "flux"]


def remove_required_column(name):
    if name in REQUIRED:
        # BUG: the message does not name the column that was removed.
        raise ValueError(
            "object is invalid - expected 'time' as the first column but found 'time'"
        )
    return [c for c in REQUIRED if c != name]
