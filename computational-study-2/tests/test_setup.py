"""Phase 0 smoke test: the package is importable and the core libraries load."""


def test_package_imports():
    import maxflow

    assert maxflow.__version__


def test_core_libraries_import():
    import matplotlib  # noqa: F401  (figures)
    import networkx  # noqa: F401  (correctness oracle, never a timed contender)
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import scipy.stats  # noqa: F401  (paired statistics in the robustness phase)
