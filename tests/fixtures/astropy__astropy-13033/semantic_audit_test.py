"""Hidden semantic audit (S): vary the required column name to catch a patch that
hard-codes 'flux' rather than reporting the actually-removed column."""
import numpy as np
import pytest
from astropy.time import Time
from astropy.timeseries import TimeSeries


@pytest.mark.parametrize("required_name", ["flux", "quality", "error"])
def test_reports_arbitrary_removed_required_column(required_name):
    time = Time(np.arange(3), format="jd")
    ts = TimeSeries(time=time, data={required_name: [1.0, 2.0, 3.0]})
    ts._required_columns = ["time", required_name]
    with pytest.raises(ValueError) as exc:
        ts.remove_column(required_name)
    assert required_name in str(exc.value)
