#include <iostream>

int main(int argc, char** argv) {
    std::cout << "Hello, CMake Single File Template!" << std::endl;
    for (int i = 0; i < argc; i++) {
        std::cout << "Arg " << i << ": " << argv[i] << std::endl;
    }
    return 0;
}