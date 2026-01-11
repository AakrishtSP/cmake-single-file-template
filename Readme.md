# CMake Single File Runner

Build and run individual C/C++ files quickly.

## Usage

```bash
python run.py path/to/file.c -- arg1 arg2
```

## VS Code Integration

Install [Code Runner](https://marketplace.visualstudio.com/items?itemName=formulahendry.code-runner) extension, then:

- Press **Ctrl+Alt+N** or click ▶ Run button to build and run
- Automatically uses `run.py` for all C/C++ files
- Output appears in integrated terminal

## Features

- Auto-detects best CMake generator (Ninja Multi-Config → Ninja → Unix Makefiles)
- Falls back to direct compilation if CMake missing or file outside project
- Supports both C and C++ files
- Build output logged to `build_output.log`
- Cross-platform (Linux, macOS, Windows)

## Options

```bash
--help                  Show all options
--list-generators       List available CMake generators
-G, --generator         Choose specific generator
--config                Set build config (Debug/Release)
--cmake-arg             Pass extra args to CMake configure
--build-arg             Pass extra args to CMake build
```
