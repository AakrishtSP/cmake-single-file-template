cmake_minimum_required(VERSION 3.25)

project(CMAKE_SINGLE_FILE LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# CONFIGURE_DEPENDS tells CMake to re-run if you add/remove files
file(GLOB_RECURSE ALL_SOURCES CONFIGURE_DEPENDS "*.cpp" "*.cxx" "*.cc" "*.c")

foreach(SOURCE_FILE ${ALL_SOURCES})
    # This creates a unique name based on the path (e.g., Comments_comment)
    file(RELATIVE_PATH REL_SRC ${CMAKE_SOURCE_DIR} ${SOURCE_FILE})
    string(REPLACE "/" "_" SAFE_NAME ${REL_SRC})
    string(REPLACE ".cpp" "" EXE_NAME ${SAFE_NAME})

    add_executable(${EXE_NAME} ${SOURCE_FILE})

    message(STATUS "Added executable target: ${EXE_NAME}")
endforeach()
