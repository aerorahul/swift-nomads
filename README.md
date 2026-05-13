# swift-nomads
A python library and application for swift access to data hosted on NOMADS

## API Naming Convention
Model-specific helper methods use model-prefixed names for readability and clearer adapter mapping.

Examples:
* GFS: `list_gfs_forecast_hours`, `build_gfs_refs`, `default_gfs_cache_path`, `should_refresh_gfs_reference`, `get_or_build_gfs_refs`
* RTOFS: `list_rtofs_forecast_hours`, `build_rtofs_refs`, `default_rtofs_cache_path`, `should_refresh_rtofs_reference`, `get_or_build_rtofs_refs`

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
