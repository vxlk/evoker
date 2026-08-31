cmake_minimum_required(VERSION 3.14)
project(evoker_host_c)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# We can just include the cpp project
add_subdirectory(../cpp ${CMAKE_CURRENT_BINARY_DIR}/cpp_build)

add_library(evoker_client_c src/evoker_client_c.cpp)
target_include_directories(evoker_client_c PUBLIC include)
target_link_libraries(evoker_client_c PRIVATE evoker_host)

# Tests
add_executable(c_integration_test tests/integration_test.c)
target_link_libraries(c_integration_test PRIVATE evoker_client_c)

add_executable(c_error_test tests/c_error_test.c)
target_link_libraries(c_error_test PRIVATE evoker_client_c)

# Examples
add_executable(c_basic_host examples/basic_host.c)
target_link_libraries(c_basic_host PRIVATE evoker_client_c)


enable_testing()
add_test(NAME c_integration_test COMMAND c_integration_test)
add_test(NAME c_error_test COMMAND c_error_test)

