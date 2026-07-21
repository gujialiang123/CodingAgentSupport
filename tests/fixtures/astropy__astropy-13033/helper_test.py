"""Canonical C2 helper (H) for astropy__astropy-13033.

Issue-level oracle only: removing a required column must raise ValueError whose
message identifies the removed required column. It must NOT assert the exact
maintainer-chosen message format (that string is hidden in the official test)."""
import numpy as np
import pytest
from astropy.time import Time
from astropy.timeseries import TimeSeries


def test_error_identifies_removed_required_column():
    time = Time(np.arange(3), format="jd")
    ts = TimeSeries(time=time, data={"flux": [1.0, 2.0, 3.0]})
    ts._required_columns = ["time", "flux"]
    with pytest.raises(ValueError) as exc:
        ts.remove_column("flux")
    assert "flux" in str(exc.value)
