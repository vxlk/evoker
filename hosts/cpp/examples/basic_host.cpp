#include <iostream>
#include <filesystem>
#include "evoker_client.hpp"

int main() {
    std::filesystem::path current = std::filesystem::current_path();
    std::filesystem::path plugins_dir = current / ".." / ".." / "test_assets" / "plugins";
    std::filesystem::path src_dir = current / ".." / ".." / "python" / "src";
    std::string worker_script = "evoker.worker";

    if (!std::filesystem::exists(plugins_dir)) {
        plugins_dir = current / ".." / "test_assets" / "plugins";
        src_dir = current / ".." / "python" / "src";
    }

#ifdef _WIN32
    _putenv_s("PYTHONPATH", src_dir.string().c_str());
#else
    setenv("PYTHONPATH", src_dir.string().c_str(), 1);
#endif

    evoker::PluginClient client(plugins_dir.string());
    
    std::cout << "Starting worker..." << std::endl;
    if (!client.start_worker("python", worker_script)) {
        std::cerr << "Failed to start worker" << std::endl;
        return 1;
    }

    std::cout << "Scanning plugins..." << std::endl;
    auto manifest = client.scan();
    std::cout << "Manifest: " << manifest.dump(2) << std::endl;

    std::cout << "Invoking test_plugin..." << std::endl;
    auto result = client.invoke("test_plugin", "hello_world", {{"name", "World"}});
    std::cout << "Result: " << result.dump() << std::endl;

    return 0;
}
