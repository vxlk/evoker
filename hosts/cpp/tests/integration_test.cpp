#include <iostream>
#include <cstdlib>
#include <filesystem>
#include "evoker_client.hpp"

#ifndef EVOKER_TEST_ASSETS
#define EVOKER_TEST_ASSETS "../../test_assets"
#endif

int main() {
    std::filesystem::path plugins_dir = std::filesystem::path(EVOKER_TEST_ASSETS) / "plugins";
    std::string worker_script = "evoker.worker";

    evoker::PluginClient client(plugins_dir.string());
    
#define ALWAYS_ASSERT(cond) do { if (!(cond)) { std::cerr << "Assertion failed: " << #cond << std::endl; client.stop_worker(); std::abort(); } } while(0)

    std::cout << "Starting C++ integration test..." << std::endl;
    bool started = client.start_worker("python", worker_script);
    ALWAYS_ASSERT(started && "Failed to start worker");

    auto manifest = client.scan();
    ALWAYS_ASSERT(manifest.contains("test_plugin") && "Scan did not return test_plugin");

    nlohmann::json kwargs = {{"name", "C++ Developer"}};
    auto result = client.invoke("test_plugin", "hello_world", kwargs);
    
    ALWAYS_ASSERT(result.is_string() && result.get<std::string>() == "Hello, C++ Developer!");

    std::cout << "Integration test passed successfully!" << std::endl;
    return 0;
}
