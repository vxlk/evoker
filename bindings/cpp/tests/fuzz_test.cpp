#include "evoker_client.hpp"
#include <cassert>
#include <iostream>
#include <random>

std::string generate_random_string(size_t length) {
    const char charset[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 <>&\"\'";
    std::string result;
    result.resize(length);
    std::mt19937 rng(1337);
    std::uniform_int_distribution<int> dist(0, sizeof(charset) - 2);
    for (size_t i = 0; i < length; ++i) {
        result[i] = charset[dist(rng)];
    }
    return result;
}

void test_fuzz_malformed_xml() {
    evoker::PluginClient dummy("");
    
    // Test 1: Totally invalid XML
    try {
        dummy.parse_xmlrpc_response("<<<>>>not xml");
        assert(false && "Should have thrown on invalid XML");
    } catch (const std::runtime_error&) {}
    
    // Test 2: Valid XML, missing methodResponse
    try {
        dummy.parse_xmlrpc_response("<someOtherTag></someOtherTag>");
        assert(false && "Should have thrown on missing methodResponse");
    } catch (const std::runtime_error&) {}

    // Test 3: XML Fault
    try {
        std::string fault_xml = R"(
        <methodResponse>
            <fault>
                <value>
                    <struct>
                        <member><name>faultCode</name><value><int>4</int></value></member>
                        <member><name>faultString</name><value><string>Too many parameters.</string></value></member>
                    </struct>
                </value>
            </fault>
        </methodResponse>
        )";
        dummy.parse_xmlrpc_response(fault_xml);
        assert(false && "Should have thrown XML-RPC fault");
    } catch (const std::runtime_error& e) {
        std::string err = e.what();
        assert(err.find("Too many parameters") != std::string::npos);
    }
    
    // Test 4: Random string junk in valid structure (property test)
    std::string random_junk = generate_random_string(100);
    std::string xml = "<?xml version=\"1.0\"?><methodResponse><params><param><value><string>" + random_junk + "</string></value></param></params></methodResponse>";
    try {
        nlohmann::json res = dummy.parse_xmlrpc_response(xml);
        // It shouldn't crash. It might parse the string (with entities if any happened to be valid)
    } catch (...) {
        // Failing to parse is fine, crashing is not.
    }
}

void test_billion_laughs_prevention() {
    evoker::PluginClient dummy("");
    
    // Test 5: Billion Laughs (Entity Expansion)
    std::string evil_xml = R"(
    <?xml version="1.0"?>
    <!DOCTYPE lolz [
     <!ENTITY lol "lol">
     <!ELEMENT lolz (#PCDATA)>
     <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
     <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
     <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
    ]>
    <methodResponse>
        <params><param><value><string>&lol3;</string></value></param></params>
    </methodResponse>
    )";

    // TinyXML2 is generally safe against Billion Laughs because it doesn't process DOCTYPE entities by default in a way that expands them recursively infinitely.
    // We just want to ensure it doesn't crash or hang here.
    try {
        dummy.parse_xmlrpc_response(evil_xml);
    } catch (...) {
        // Errors are fine, hangs/crashes are bad.
    }
}

int main() {
    test_fuzz_malformed_xml();
    test_billion_laughs_prevention();
    std::cout << "Fuzz & Security tests passed!" << std::endl;
    return 0;
}
