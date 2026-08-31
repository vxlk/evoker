cmake_minimum_required(VERSION 3.14)
project(evoker_host_cpp)
set(CMAKE_POLICY_VERSION_MINIMUM 3.1)
cmake_policy(SET CMP0135 NEW)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

# Fetch cpp-httplib (header only)
FetchContent_Declare(
    httplib
    URL https://github.com/yhirose/cpp-httplib/archive/refs/tags/v0.14.1.tar.gz
)
set(HTTPLIB_REQUIRE_OPENSSL ON)
set(CPPHTTPLIB_OPENSSL_SUPPORT ON)
FetchContent_MakeAvailable(httplib)

# Fetch tinyxml2
FetchContent_Declare(
    tinyxml2
    URL https://github.com/leethomason/tinyxml2/archive/refs/tags/9.0.0.tar.gz
)
FetchContent_MakeAvailable(tinyxml2)

# Reproc for process management
FetchContent_Declare(
    reproc
    URL https://github.com/DaanDeMeyer/reproc/archive/refs/tags/v14.2.4.tar.gz
)
set(REPROC++ ON)
set(REPROC_TEST OFF)
FetchContent_MakeAvailable(reproc)

add_library(evoker_host src/evoker_client.cpp)
target_include_directories(evoker_host PUBLIC include)
target_link_libraries(evoker_host PRIVATE httplib::httplib tinyxml2 reproc++)

add_executable(evoker_cpp_host src/main.cpp)
target_link_libraries(evoker_cpp_host PRIVATE evoker_host)

# Example
add_executable(basic_host examples/basic_host.cpp)
target_link_libraries(basic_host PRIVATE evoker_host)

# Tests (Optional Catch2)
# We will use simple assert for standard tests to reduce dependencies here
add_executable(integration_test tests/integration_test.cpp)
target_link_libraries(integration_test PRIVATE evoker_host)

add_executable(cpp_unit_tests tests/unit_tests.cpp src/evoker_client.cpp)
target_link_libraries(cpp_unit_tests PRIVATE tinyxml2 reproc++ reproc httplib::httplib)
target_include_directories(cpp_unit_tests PRIVATE include)
target_compile_definitions(cpp_unit_tests PRIVATE EVOKER_CLIENT_TESTING)

add_executable(cpp_fuzz_test tests/fuzz_test.cpp src/evoker_client.cpp)
target_link_libraries(cpp_fuzz_test PRIVATE tinyxml2 reproc++ reproc httplib::httplib)
target_include_directories(cpp_fuzz_test PRIVATE include)
target_compile_definitions(cpp_fuzz_test PRIVATE EVOKER_CLIENT_TESTING)

add_executable(cpp_error_test tests/error_test.cpp)
target_link_libraries(cpp_error_test PRIVATE evoker_host)
