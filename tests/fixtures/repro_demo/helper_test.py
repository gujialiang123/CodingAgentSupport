"""C2 helper reproduction test (H). Issue-level oracle: the error must name the
removed required column. Contains no maintainer-chosen exact message string."""
import pytest

from mod import remove_required_column


def test_error_names_removed_required_column():
    with pytest.raises(ValueError) as exc:
        remove_required_column("flux")
    assert "flux" in str(exc.value)
