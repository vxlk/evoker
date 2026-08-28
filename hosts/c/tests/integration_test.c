#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "evoker_client_c.h"

int main() {
    // Relative paths from build directory (hosts/c/build)
    const char* plugins_dir = "../../test_assets/plugins";
    const char* src_dir = "../../python/src";
    const char* worker_script = "plugin_host.worker";

    // Try alternate path if it doesn't exist (if run from root or hosts/c)
    FILE* f = fopen("../../test_assets/plugins/test_plugin/manifest.json", "r");
    if (!f) {
        f = fopen("hosts/test_assets/plugins/test_plugin/manifest.json", "r");
        if (f) {
            plugins_dir = "hosts/test_assets/plugins";
            src_dir = "hosts/python/src";
            fclose(f);
        } else {
            plugins_dir = "../test_assets/plugins";
            src_dir = "../python/src";
        }
    } else {
        fclose(f);
    }

#ifdef _WIN32
    _putenv_s("PYTHONPATH", src_dir);
#else
    setenv("PYTHONPATH", src_dir, 1);
#endif

    evoker_client_t* client = evoker_client_create(plugins_dir, NULL, NULL);
    assert(client != NULL);

    printf("Starting worker...\n");
    int started = evoker_client_start_worker(client, "python", worker_script);
    assert(started == 1);

    printf("Scanning...\n");
    char* manifest = evoker_client_scan(client);
    assert(manifest != NULL);
    assert(strstr(manifest, "test_plugin") != NULL);
    evoker_client_free_string(manifest);

    printf("Invoking...\n");
    char* result = evoker_client_invoke(client, "test_plugin", "hello_world", "{\"name\": \"C Developer\"}");
    assert(result != NULL);
    assert(strstr(result, "Hello, C Developer!") != NULL);
    evoker_client_free_string(result);

    evoker_client_destroy(client);
    printf("C Integration test passed!\n");

    return 0;
}
