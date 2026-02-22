# loom-qgis-plugin

## Overview
The `loom-qgis-plugin` is a QGIS plugin designed to enhance the functionality of the QGIS application. This plugin provides users with additional tools and features to improve their geospatial data processing and visualization.

## Installation
To install the `loom-qgis-plugin`, follow these steps:

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/loom-qgis-plugin.git
   ```
2. Navigate to the plugin directory:
   ```
   cd loom-qgis-plugin
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Load the plugin in QGIS:
   - Open QGIS.
   - Go to `Plugins` > `Manage and Install Plugins`.
   - Click on `Install from ZIP` and select the cloned directory.

## Usage
Once installed, you can access the `loom-qgis-plugin` from the QGIS Plugins menu. The plugin provides a dock widget that allows you to interact with its features.

## Configuration

The `ConfigReader` now supports reading configuration options exclusively from a JSON file. The JSON file should contain keys corresponding to the available options. These options are used to initialize the configuration for the program.

### Default JSON Configuration File

Below is an example of a valid JSON configuration file with the default values:

```json
{
  "no-untangle": false,
  "output-stats": false,
  "no-prune": false,
  "same-seg-cross-pen": 4.0,
  "diff-seg-cross-pen": 1.0,
  "sep-pen": 3.0,
  "in-stat-cross-pen-same-seg": 12.0,
  "in-stat-cross-pen-diff-seg": 3.0,
  "in-stat-sep-pen": 9.0,
  "ilp-num-threads": 0,
  "ilp-time-limit": -1.0,
  "ilp-solver": "gurobi",
  "optim-method": "comb-no-ilp",
  "optim-runs": 1,
  "dbg-output-path": ".",
  "output-optgraph": false,
  "write-stats": false,
  "from-dot": false
}
```

### Required and Optional Arguments

#### Required Arguments:
- **`ilp-solver`**: Preferred ILP solver. Must be one of:
  - `gurobi`
  - `glpk`
  - `cbc`

#### Optional Arguments:
- **`no-untangle`**: Disable untangling rules (default: `false`).
- **`output-stats`**: Print stats to stdout (default: `false`).
- **`no-prune`**: Disable pruning rules (default: `false`).
- **`same-seg-cross-pen`**: Penalty for same-segment crossings (default: `4.0`).
- **`diff-seg-cross-pen`**: Penalty for different-segment crossings (default: `1.0`).
- **`sep-pen`**: Penalty for separations (default: `3.0`).
- **`in-stat-cross-pen-same-seg`**: Penalty for same-segment crossings at stations (default: `12.0`).
- **`in-stat-cross-pen-diff-seg`**: Penalty for different-segment crossings at stations (default: `3.0`).
- **`in-stat-sep-pen`**: Penalty for separations at stations (default: `9.0`).
- **`ilp-num-threads`**: Number of threads for the ILP solver (default: `0`).
- **`ilp-time-limit`**: Time limit for ILP solver in seconds (default: `-1.0`).
- **`optim-method`**: Optimization method (default: `"comb-no-ilp"`).
- **`optim-runs`**: Number of optimization runs (default: `1`).
- **`dbg-output-path`**: Path for debug output (default: `"."`).
- **`output-optgraph`**: Output optimization graph to debug path (default: `false`).
- **`write-stats`**: Write stats to output (default: `false`).
- **`from-dot`**: Input is in DOT format (default: `false`).

### How to Use

1. Create a JSON file with the desired configuration (e.g., `config.json`).
2. Pass the JSON file content as a `std::stringstream` to the `ConfigReader::read` function.

## Contributing
Contributions are welcome! If you would like to contribute to the `loom-qgis-plugin`, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your changes to your forked repository.
5. Create a pull request to the main repository.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.