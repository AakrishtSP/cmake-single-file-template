#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PREFERRED_GENERATORS = [
    "Ninja Multi-Config",
    "Ninja",
    "Unix Makefiles",
    "MinGW Makefiles",
    "Visual Studio 17 2022",
]

DEFAULT_CONFIG = os.environ.get("CMAKE_BUILD_CONFIG", "Debug")
LOG_FILE = Path("build_output.log")
PREFERRED_COMPILERS_C = ["cc", "gcc", "clang", "cl"]
PREFERRED_COMPILERS_CXX = ["c++", "g++", "clang++", "cl"]


def fail(message: str, code: int = 1) -> None:
    print(message)
    sys.exit(code)


def fail_with_log(message: str, log_file: Path, code: int = 1) -> None:
    print(message)
    print(f"---- build log ({log_file}) ----")
    if log_file.exists():
        try:
            print(log_file.read_text(encoding="utf-8"))
        except OSError:
            print("(failed to read log)")
    else:
        print("(log file not found)")
    print("---- end log ----")
    sys.exit(code)


def read_capabilities() -> dict:
    try:
        result = subprocess.run(
            ["cmake", "-E", "capabilities"],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return {}


def choose_generator(preferred: list[str]) -> str | None:
    data = read_capabilities()
    available = {g.get("name") for g in data.get("generators", [])}
    for candidate in preferred:
        if candidate in available:
            return candidate
    return None


def choose_compiler(preferred: list[str]) -> str | None:
    for compiler in preferred:
        if shutil.which(compiler):
            return compiler
    return None


def is_multi_config(generator: str) -> bool:
    name = generator.lower()
    return "multi-config" in name or "visual studio" in name


def configure_build(generator: str, log_file: Path, build_config: str, extra_args: list[str]) -> None:
    cmd = [
        "cmake",
        "-S",
        ".",
        "-B",
        "build",
        "-G",
        generator,
        "-Wno-dev",
    ]
    # Only pass a config to single-config generators
    if not is_multi_config(generator):
        cmd.extend(["-DCMAKE_BUILD_TYPE=" + build_config])
    # Pass any additional user-specified CMake configure args
    if extra_args:
        cmd.extend(extra_args)
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"Configuring with generator: {generator}\n")
        subprocess.run(cmd, check=True, stdout=log, stderr=log)


def build_target(target: str, generator: str, log_file: Path, build_config: str, extra_args: list[str]) -> None:
    cmd = ["cmake", "--build", "build", "--target", target]
    if is_multi_config(generator):
        cmd.extend(["--config", build_config])
    # Pass any additional user-specified CMake build args
    if extra_args:
        cmd.extend(extra_args)
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"Building target: {target}\n")
        subprocess.run(cmd, check=True, stdout=log, stderr=log)


def direct_compile(file_path: str, compiler: str, log_file: Path, is_c: bool) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="c-run-" if is_c else "cpp-run-"))
    output = temp_dir / ("a.exe" if os.name == "nt" else "a.out")

    if compiler == "cl":
        std_flag = "/std:c17" if is_c else "/std:c++20"
        lang_flag = "/TC" if is_c else "/TP"
        cmd = [compiler, file_path, lang_flag, std_flag, "/Fe" + str(output), "/nologo"]
    else:
        std_flag = "-std=c17" if is_c else "-std=c++20"
        cmd = [compiler, file_path, std_flag, "-O0", "-g", "-o", str(output)]

    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"Compiling with {compiler}\n")
        subprocess.run(cmd, check=True, stdout=log, stderr=log)

    return output


def exe_path(target: str, generator: str) -> Path:
    base = Path("build")
    if is_multi_config(generator):
        base = base / DEFAULT_CONFIG
    suffix = ".exe" if os.name == "nt" else ""
    return base / f"{target}{suffix}"


def normalize_target_in_project(file_path: Path, project_root: Path) -> str:
    # Build target name matching CMakeLists: relative path with '/' -> '_' and suffix with extension
    try:
        rel = file_path.resolve().relative_to(project_root.resolve())
    except Exception:
        # If not relative, return a name that will surely not exist
        rel = file_path.name
    posix_no_ext = Path(rel).with_suffix("").as_posix()
    base = posix_no_ext.replace("/", "_")
    ext = file_path.suffix.lower().lstrip(".")
    return f"{base}_{ext}" if ext else base


def main() -> None:
    LOG_FILE.write_text("", encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Configure, build, and run a single C/C++ file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("file", help="Path to the .c or .cpp file to build")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the built executable")
    parser.add_argument("-G", "--generator", help="CMake generator to use (overrides auto selection)")
    parser.add_argument("--config", help="Build configuration (e.g., Debug, Release). Overrides CMAKE_BUILD_CONFIG.")
    parser.add_argument("--cmake-arg", action="append", default=[], help="Extra argument to pass to CMake configure (repeatable)")
    parser.add_argument("--build-arg", action="append", default=[], help="Extra argument to pass to CMake build (repeatable)")
    parser.add_argument("--list-generators", action="store_true", help="List available CMake generators and exit")
    parser.add_argument("--print-binary", action="store_true", help="Print the binary path and exit (useful for debugging)")
    parsed = parser.parse_args()

    file_path = parsed.file
    exec_args = parsed.args

    project_root = Path.cwd().resolve()
    file_abs = Path(file_path).resolve()
    try:
        file_abs.relative_to(project_root)
        in_project = True
    except ValueError:
        in_project = False

    binary: Path | None = None
    cleanup_dir: Path | None = None

    # Early exit: list generators
    if parsed.list_generators:
        caps = read_capabilities()
        gens = [g.get("name") for g in caps.get("generators", [])]
        if not gens:
            print("No generators found. Ensure CMake is installed and on PATH.")
        else:
            print("Available CMake generators:")
            for name in gens:
                print(f"- {name}")
        sys.exit(0)

    is_c = Path(file_path).suffix.lower() == ".c"
    build_config = parsed.config or DEFAULT_CONFIG

    # Early exit: print binary path for debug integration
    if parsed.print_binary:
        project_root_temp = Path.cwd().resolve()
        file_abs_temp = Path(file_path).resolve()
        try:
            file_abs_temp.relative_to(project_root_temp)
            target_temp = normalize_target_in_project(file_abs_temp, project_root_temp)
            # Determine which generator would be used to know the binary path
            gen_temp = parsed.generator or choose_generator(PREFERRED_GENERATORS)
            if gen_temp:
                print(str(exe_path(target_temp, gen_temp).resolve()))
            else:
                print("(no generator available)")
        except ValueError:
            print("(file outside project)")
        sys.exit(0)

    if shutil.which("cmake") is None:
        print("CMake is not installed or not on PATH; falling back to direct compilation.")
        compiler_list = PREFERRED_COMPILERS_C if is_c else PREFERRED_COMPILERS_CXX
        compiler = choose_compiler(compiler_list)
        if not compiler:
            fail("No compiler found. Looked for: " + ", ".join(compiler_list))

        try:
            binary = direct_compile(file_path, compiler, LOG_FILE, is_c)
            cleanup_dir = binary.parent
        except subprocess.CalledProcessError as err:
            fail_with_log(f"Compilation failed with exit code {err.returncode}. Logs at {LOG_FILE}.", LOG_FILE, err.returncode)
    else:
        if not in_project:
            print("Warning: the provided file is outside this project; falling back to direct compilation.")
            compiler_list = PREFERRED_COMPILERS_C if is_c else PREFERRED_COMPILERS_CXX
            compiler = choose_compiler(compiler_list)
            if not compiler:
                fail("No compiler found. Looked for: " + ", ".join(compiler_list))

            try:
                binary = direct_compile(file_path, compiler, LOG_FILE, is_c)
                cleanup_dir = binary.parent
            except subprocess.CalledProcessError as err:
                fail_with_log(f"Compilation failed with exit code {err.returncode}. Logs at {LOG_FILE}.", LOG_FILE, err.returncode)
        else:
            target = normalize_target_in_project(file_abs, project_root)
            generator = parsed.generator or choose_generator(PREFERRED_GENERATORS)
            if not generator:
                fail("No suitable CMake generator found. Tried: " + ", ".join(PREFERRED_GENERATORS))

            try:
                configure_build(generator, LOG_FILE, build_config, parsed.cmake_arg)
                build_target(target, generator, LOG_FILE, build_config, parsed.build_arg)
            except subprocess.CalledProcessError as err:
                fail_with_log(f"CMake failed with exit code {err.returncode}. Logs at {LOG_FILE}.", LOG_FILE, err.returncode)

            binary = exe_path(target, generator)
            if not binary.exists():
                fail(f"Built binary not found at {binary}")

    print(f"--- Executing: {binary}")
    if exec_args:
        print(f"--- Arguments: {' '.join(exec_args)}")
    print("-------------------------------\n")

    try:
        subprocess.run([str(binary), *exec_args], check=True)
    except subprocess.CalledProcessError as err:
        fail(f"Executable returned non-zero exit code {err.returncode}", err.returncode)
    finally:
        if cleanup_dir and cleanup_dir.exists():
            try:
                shutil.rmtree(cleanup_dir)
            except OSError:
                pass


if __name__ == "__main__":
    main()
