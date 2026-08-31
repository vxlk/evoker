#include <stdio.h>
#include <stdlib.h>
#include "evoker_client_c.h"

int main() {
    const char* plugins_dir = "../../test_assets/plugins";
    const char* src_dir = "../../python/src";
    const char* worker_script = "evoker.worker";
    
#ifdef _WIN32
    _putenv_s("PYTHONPATH", src_dir);
#else
    setenv("PYTHONPATH", src_dir, 1);
#endif

    evoker_client_t* client = evoker_client_create(plugins_dir, NULL, NULL);
    if (!client) {
        printf("Failed to create client\n");
        return 1;
    }

    if (!evoker_client_start_worker(client, "python", worker_script)) {
        printf("Failed to start worker\n");
        return 1;
    }

    char* manifest = evoker_client_scan(client);
    if (manifest) {
        printf("Manifest: %s\n", manifest);
        evoker_client_free_string(manifest);
    } else {
        printf("Scan failed\n");
    }

    char* result = evoker_client_invoke(client, "test_plugin", "hello_world", "{\"name\": \"World\"}");
    if (result) {
        printf("Result: %s\n", result);
        evoker_client_free_string(result);
    } else {
        printf("Invoke failed\n");
    }

    evoker_client_destroy(client);
    return 0;
}
