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
  "loom": {
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
  },
  "octi": {
    "abortAfter": 0,
    "optimMode": "heur",
    "hananIters": 1,
    "heurLocSearchIters": 100,
    "ilpCacheThreshold": "inf",
    "ilpCacheDir": ".",
    "obstaclePath": "",
    "deg2Heur": false,
    "enfGeoPen": 0.0,
    "maxGrDist": 3.0,
    "restrLocSearch": false,
    "edgeOrderMethod": "all",
    "baseGraphType": "octilinear",
    "pens": {
      "densityPen": 10.0,
      "verticalPen": 0.0,
      "horizontalPen": 0.0,
      "diagonalPen": 0.5,
      "p_0": 0.0,
      "p_135": 1.0,
      "p_90": 1.5,
      "p_45": 2.0,
      "ndMovePen": 0.5
    },
    "skipOnError": false,
    "retryOnError": false,
    "gridSize": "100%"
  },
  "topo": {
    "max-aggr-dist": 50,
    "write-stats": false,
    "no-infer-restrs": false,
    "infer-restr-max-dist": 50,
    "max-comp-dist": 10000,
    "sample-dist": 5,
    "max-length-dev": 500,
    "turn-restr-full-turn-angle": 0,
    "turn-restr-full-turn-pen": 0,
    "random-colors": false,
    "write-components": false,
    "write-components-path": "",
    "smooth": 0,
    "aggr-stats": false
  },
  "transitmap": {
    "render-engine": "svg",
    "line-width": 20,
    "line-spacing": 10,
    "outline-width": 1,
    "render-dir-markers": false,
    "labels": false,
    "line-label-textsize": 40,
    "station-label-textsize": 60,
    "no-deg2-labels": false,
    "zoom": "14",
    "mvt-path": ".",
    "random-colors": false,
    "tight-stations": false,
    "no-render-stations": false,
    "no-render-node-connections": false,
    "render-node-fronts": false,
    "print-stats": false
  }
}
```

### loom (algorithm) configuration

#### Required
- `ilp-solver`: Preferred ILP solver. Must be one of: `gurobi`, `glpk`, `cbc`.

#### Optional (defaults shown)
- `no-untangle` (bool, default: `false`): Disable untangling rules.
- `output-stats` (bool, default: `false`): Print stats to stdout.
- `no-prune` (bool, default: `false`): Disable pruning rules.
- `same-seg-cross-pen` (number, default: `4.0`): Penalty for same-segment crossings.
- `diff-seg-cross-pen` (number, default: `1.0`): Penalty for different-segment crossings.
- `sep-pen` (number, default: `3.0`): Penalty for separations.
- `in-stat-cross-pen-same-seg` (number, default: `12.0`): Penalty for same-segment crossings at stations.
- `in-stat-cross-pen-diff-seg` (number, default: `3.0`): Penalty for different-segment crossings at stations.
- `in-stat-sep-pen` (number, default: `9.0`): Penalty for separations at stations.
- `ilp-num-threads` (int, default: `0`): Number of threads for the ILP solver (0 = solver default).
- `ilp-time-limit` (number, default: `-1.0`): ILP time limit in seconds (-1 = infinite).
- `optim-method` (string, default: `"comb-no-ilp"`): Optimization method.
- `optim-runs` (int, default: `1`): Number of optimization runs.
- `dbg-output-path` (string, default: `"."`): Path for debug output.
- `output-optgraph` (bool, default: `false`): Write optimization graph to debug path.
- `write-stats` (bool, default: `false`): Write stats to output.
- `from-dot` (bool, default: `false`): Input is in DOT format.

How to use
1. Create a JSON file containing a top-level "loom" object with the above keys (e.g., `config.json`).
2. Read the file and pass its contents as a std::stringstream to `ConfigReader::read`.

### octi (algorithm) configuration

#### Required
- `optimMode` (string, default: `"heur"`): Optimization mode. Must be one of:
  - `heur`: Heuristic optimization.
  - `ilp`: Integer Linear Programming optimization.

#### Optional (defaults shown)
- `abortAfter` (int, default: `0`): Abort after a certain number of iterations.
- `hananIters` (int, default: `1`): Number of Hanan grid iterations.
- `heurLocSearchIters` (int, default: `100`): Maximum local search iterations.
- `ilpCacheThreshold` (number, default: `"inf"`): ILP solve cache threshold.
- `ilpCacheDir` (string, default: `"."`): Directory for ILP cache.
- `obstaclePath` (string, default: `""`): Path to GeoJSON file containing obstacle polygons.
- `deg2Heur` (bool, default: `false`): Disable contraction of degree-2 nodes.
- `enfGeoPen` (number, default: `0.0`): Penalty for enforcing lines to follow input geo course.
- `maxGrDist` (number, default: `3.0`): Maximum grid distance for station candidates.
- `restrLocSearch` (bool, default: `false`): Restrict local search to maximum grid distance.
- `edgeOrderMethod` (string, default: `"all"`): Method for initial edge ordering. Options:
  - `num-lines`
  - `length`
  - `adj-nd-deg`
  - `adj-nd-ldeg`
  - `growth-deg`
  - `growth-ldeg`
  - `all`
- `baseGraphType` (string, default: `"octilinear"`): Base graph type. Options:
  - `ortholinear`
  - `octilinear`
  - `hexalinear`
  - `chulloctilinear`
  - `pseudoorthoradial`
  - `quadtree`
  - `octihanan`
- `pens` (object): Penalty configuration:
  - `densityPen` (number, default: `10.0`): Penalty for density.
  - `verticalPen` (number, default: `0.0`): Penalty for vertical edges.
  - `horizontalPen` (number, default: `0.0`): Penalty for horizontal edges.
  - `diagonalPen` (number, default: `0.5`): Penalty for diagonal edges.
  - `p_0` (number, default: `0.0`): Penalty for 0-degree bends.
  - `p_135` (number, default: `1.0`): Penalty for 135-degree bends.
  - `p_90` (number, default: `1.5`): Penalty for 90-degree bends.
  - `p_45` (number, default: `2.0`): Penalty for 45-degree bends.
  - `ndMovePen` (number, default: `0.5`): Penalty for node movement.
- `skipOnError` (bool, default: `false`): Skip graph on error.
- `retryOnError` (bool, default: `false`): Retry with reduced grid size on error.
- `gridSize` (string, default: `"100%"`): Grid cell length, either exact or percentage of input adjacent station distance.

How to use:
1. Create a JSON file containing a top-level "octi" object with the above keys (e.g., `config.json`).
2. Read the file and pass its contents as a `std::stringstream` to `ConfigReader::read`.

### transitmap (algorithm) configuration

#### Required
- `render-engine` (string, default: `"svg"`): Render engine. Must be one of:
  - `svg`: Scalable Vector Graphics.
  - `mvt`: Mapbox Vector Tiles.

#### Optional (defaults shown)
- `line-width` (number, default: `20`): Width of a single transit line.
- `line-spacing` (number, default: `10`): Spacing between transit lines.
- `outline-width` (number, default: `1`): Width of line outlines.
- `render-dir-markers` (bool, default: `false`): Render line direction markers.
- `labels` (bool, default: `false`): Render labels.
- `line-label-textsize` (number, default: `40`): Text size for line labels.
- `station-label-textsize` (number, default: `60`): Text size for station labels.
- `no-deg2-labels` (bool, default: `false`): Disable labels for degree-2 stations.
- `zoom` (string, default: `"14"`): Zoom level for MVT tiles, specified as a range or comma-separated values.
- `mvt-path` (string, default: `"."`): Path for MVT tiles.
- `random-colors` (bool, default: `false`): Use random colors for missing colors.
- `tight-stations` (bool, default: `false`): Disable expansion of node fronts for stations.
- `no-render-stations` (bool, default: `false`): Disable rendering of stations.
- `no-render-node-connections` (bool, default: `false`): Disable rendering of inner node connections.
- `render-node-fronts` (bool, default: `false`): Enable rendering of node fronts.
- `print-stats` (bool, default: `false`): Write stats to stdout.

How to use:
1. Create a JSON file containing a top-level "transitmap" object with the above keys (e.g., `config.json`).
2. Read the file and pass its contents as a `std::stringstream` to `ConfigReader::read`.

### topo (algorithm) configuration

#### Required
- `max-aggr-dist` (number, default: `50`): Maximum distance between segments.

#### Optional (defaults shown)
- `write-stats` (bool, default: `false`): Write statistics to the output file.
- `no-infer-restrs` (bool, default: `false`): Disable inference of turn restrictions.
- `infer-restr-max-dist` (number, default: `[max-aggr-dist]`): Maximum distance for considering edges for turn restrictions.
- `max-comp-dist` (number, default: `10000`): Maximum distance between nodes in a component, in meters.
- `sample-dist` (number, default: `5`): Sample length for map construction, in pseudometers.
- `max-length-dev` (number, default: `500`): Maximum distance deviation for turn restriction inference.
- `turn-restr-full-turn-angle` (number, default: `0`): Turn angles smaller than this will count as a full turn.
- `turn-restr-full-turn-pen` (number, default: `0`): Penalty for full turns during turn restriction inference.
- `random-colors` (bool, default: `false`): Use random colors for missing colors.
- `write-components` (bool, default: `false`): Write graph component IDs to edge attributes.
- `write-components-path` (string, default: `""`): Path to write graph components as separate files.
- `smooth` (number, default: `0`): Smooth output graph edge geometries.
- `aggr-stats` (bool, default: `false`): Aggregate statistics with existing input.

How to use:
1. Create a JSON file containing a top-level "topo" object with the above keys (e.g., `config.json`).
2. Read the file and pass its contents as a `std::stringstream` to `ConfigReader::read`.

## Contributing
Contributions are welcome! If you would like to contribute to the `loom-qgis-plugin`, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your changes to your forked repository.
5. Create a pull request to the main repository.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.