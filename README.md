# swift-nomads
A python library and application for swift access to data hosted on NOMADS

## Installation

### Dependencies
#### Required
* [Python](https://www.python.org) 3.11+
* [kerchunk](https://github.com/fsspec/kerchunk) 0.2.10+

#### Optional
* [JupyterLab](https://jupyter.org/) 4.4.0+

### Installation and Testing
Installation can be done using either `conda` or `pip`. The `conda` installation will create a new environment with the required dependencies, while the `pip` installation will install the package in the current environment. The tests can be run using `pytest` after installation.

#### Install using conda
```bash
conda env create -n swift-nomads -f environment.yml
conda activate swift-nomads
conda install --file test-environment.txt  # optional for running swift-nomads tests
pip install .
```

#### Install using pip
```bash
pip install .'[test]'  # optional [test] for running tests
```

#### Testing
You can run the tests using the following command:
```bash
pytest tests/
```
