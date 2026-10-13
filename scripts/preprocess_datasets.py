"""Turn raw datasets into distance graphs (decisions in docs/decisions.md) and save them.

    python scripts/preprocess_datasets.py

Writes data/processed/<slug>.npz.
"""

from apsp.loaders import load_usairport
from apsp.preprocess import inverse_weights, load_processed, save_processed


def main():
    raw = load_usairport()
    ds = inverse_weights(raw)  # decision D1
    path = save_processed(ds, "usairport")

    back = load_processed("usairport")
    print(f"{ds.name}: n={back.n:,}, m={len(back.u):,}, directed={back.directed}")
    print(f"  distance = {back.weight_meaning}")
    print(f"  distance range: {back.w.min():.3g} .. {back.w.max():.3g}")
    print(f"  saved to {path.relative_to(path.parents[2])}")


if __name__ == "__main__":
    main()
