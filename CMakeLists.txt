cmake_minimum_required(VERSION 3.25)

project(CMAKE_SINGLE_FILE LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

# CONFIGURE_DEPENDS tells CMake to re-run if you add/remove files
file(GLOB_RECURSE ALL_SOURCES CONFIGURE_DEPENDS "*.cpp" "*.cxx" "*.cc" "*.c")
# Exclude generated/build tree artifacts from being treated as sources
list(FILTER ALL_SOURCES EXCLUDE REGEX "/(build|cmake-build[^/]*)/")
list(FILTER ALL_SOURCES EXCLUDE REGEX "/CMakeFiles/")

foreach(SOURCE_FILE ${ALL_SOURCES})
    # Create a deterministic, unique name based on path and extension
    file(RELATIVE_PATH REL_SRC ${CMAKE_SOURCE_DIR} ${SOURCE_FILE})
    string(REPLACE "/" "_" SAFE_NAME ${REL_SRC})
    get_filename_component(BASE_NAME ${SAFE_NAME} NAME_WE)
    get_filename_component(FILE_EXT ${SAFE_NAME} EXT)
    string(REPLACE "." "" EXT_NO_DOT ${FILE_EXT})

    # Always suffix with extension to avoid collisions between .c and .cpp of same basename
    set(EXE_NAME "${BASE_NAME}_${EXT_NO_DOT}")

    add_executable(${EXE_NAME} ${SOURCE_FILE})

    message(STATUS "Added executable target: ${EXE_NAME}")
endforeach()
