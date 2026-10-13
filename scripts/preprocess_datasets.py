"""Turn raw datasets into distance graphs (decisions in docs/decisions.md) and save them.

    python scripts/preprocess_datasets.py

Writes data/processed/<slug>.npz. The steps per dataset are in apsp.preprocess.PIPELINES.
"""

from apsp.preprocess import PIPELINES, build, load_processed, save_processed


def main():
    for slug in PIPELINES:
        _, processed = build(slug)
        path = save_processed(processed, slug)
        back = load_processed(slug)
        print(f"{back.name}: n={back.n:,}, one-way edges={len(back.u):,}, directed={back.directed}")
        print(f"  distance = {back.weight_meaning}")
        print(f"  distance range: {back.w.min():.3g} .. {back.w.max():.3g}")
        print(f"  saved to {path.relative_to(path.parents[2])}")


if __name__ == "__main__":
    main()
