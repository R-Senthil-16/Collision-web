#!/usr/bin/env node
/**
 * Node.js Test Runner for Integration Tests
 * 
 * Runs integration tests from command line using Node.js environment
 */

// Import required modules
const fetch = require('node-fetch');
const { io } = require('socket.io-client');

// Polyfill for browser APIs in Node.js
global.fetch = fetch;
global.io = io;

// Import the test suite
const IntegrationTestSuite = require('./src/test/integration-tests.js');

async function runTests() {
    console.log('Starting Integration Tests from Node.js...');
    console.log('Make sure the backend server is running on http://localhost:5000\n');
    
    const testSuite = new IntegrationTestSuite();
    
    try {
        const results = await testSuite.runAllTests();
        
        const passed = results.filter(r => r.status === 'PASS').length;
        const failed = results.filter(r => r.status === 'FAIL').length;
        const skipped = results.filter(r => r.status === 'SKIP').length;
        
        console.log('\n=== Final Summary ===');
        console.log(`Total: ${results.length}, Passed: ${passed}, Failed: ${failed}, Skipped: ${skipped}`);
        
        // Exit with error code if any tests failed
        if (failed > 0) {
            console.log('\n❌ Some tests failed!');
            process.exit(1);
        } else {
            console.log('\n✅ All tests passed!');
            process.exit(0);
        }
        
    } catch (error) {
        console.error('Test suite failed to run:', error);
        process.exit(1);
    }
}

// Check if required dependencies are available
async function checkDependencies() {
    try {
        // Check if backend server is running
        const response = await fetch('http://localhost:5000/api/health');
        if (!response.ok) {
            throw new Error(`Backend server returned ${response.status}`);
        }
        console.log('✅ Backend server is running');
        return true;
    } catch (error) {
        console.error('❌ Backend server is not accessible:', error.message);
        console.error('Please start the backend server first:');
        console.error('  cd raspberry-pi && python test_server.py');
        return false;
    }
}

// Main execution
async function main() {
    console.log('Integration Test Runner');
    console.log('======================\n');
    
    // Check dependencies
    const dependenciesOk = await checkDependencies();
    if (!dependenciesOk) {
        process.exit(1);
    }
    
    // Run tests
    await runTests();
}

// Run if this file is executed directly
if (require.main === module) {
    main().catch(error => {
        console.error('Unexpected error:', error);
        process.exit(1);
    });
}

module.exports = { runTests, checkDependencies };