# Computational Study 2: maximum flow

Compares the **shortest augmenting path** algorithm and the **preflow-push** algorithm (Ahuja,
Magnanti and Orlin, *Network Flows*, Chapter 7) on 14 network datasets.

**Report:** [computational_study_2.ipynb](computational_study_2.ipynb), the report and code in one
notebook ([open in Colab](https://colab.research.google.com/github/absharotry/mmie.7372.001.NetFlow-DyProg.fall26/blob/main/computational-study-2/computational_study_2.ipynb)). Backing detail: the [plan of action](docs/plan_of_action.md) and the
[data model and analysis design](docs/data_modeling.md).

## Data

The `elist*.txt` files are kept locally in `Data/` and are not committed. Checksums and the file
format are in [Data/SOURCES.md](Data/SOURCES.md).

## Setup

From the repository root:

```bash
source .venv/bin/activate
pip install -r computational-study-2/requirements.txt
pip install -e computational-study-2
```
