#include <stdio.h>
#include <stdlib.h>
#include "evoker_client_c.h"

#ifndef EVOKER_TEST_ASSETS
#define EVOKER_TEST_ASSETS "../../test_assets"
#endif

#define ALWAYS_ASSERT(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "Assertion failed: %s\n", #cond); \
        if (client) evoker_client_destroy(client); \
        abort(); \
    } \
} while(0)

int main() {
    char plugins_dir[1024];
    snprintf(plugins_dir, sizeof(plugins_dir), "%s/plugins", EVOKER_TEST_ASSETS);
    const char* worker_script = "evoker.worker";

    evoker_client_t* client = evoker_client_create(plugins_dir, NULL, NULL);
    ALWAYS_ASSERT(client != NULL);

    printf("Starting C integration test...\n");
    int started = evoker_client_start_worker(client, "python", worker_script);
    ALWAYS_ASSERT(started);

    char* manifest_str = evoker_client_scan(client);
    ALWAYS_ASSERT(manifest_str != NULL);
    evoker_client_free_string(manifest_str);

    const char* kwargs_json = "{\"name\": \"C Developer\"}";
    char* result_str = evoker_client_invoke(client, "test_plugin", "hello_world", kwargs_json);
    ALWAYS_ASSERT(result_str != NULL);
    
    // Using string matching for simple JSON response
    ALWAYS_ASSERT(strstr(result_str, "Hello, C Developer!") != NULL);
    evoker_client_free_string(result_str);

    evoker_client_destroy(client);
    printf("Integration test passed successfully!\n");
    return 0;
}
