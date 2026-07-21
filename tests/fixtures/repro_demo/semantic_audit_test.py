"""Hidden semantic audit (S). Varies the required-column name to catch a patch
that hard-codes a single column instead of naming the removed one."""
import pytest

import mod


@pytest.mark.parametrize("col", ["flux", "quality", "error"])
def test_reports_arbitrary_removed_required_column(col):
    mod.REQUIRED = ["time", col]
    with pytest.raises(ValueError) as exc:
        mod.remove_required_column(col)
    assert col in str(exc.value)
