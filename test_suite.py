"""
Test Suite for NASA API Integration

This script contains a collection of test cases for evaluating
the NASA API integration with the Model Context Protocol.
"""

import time
import json
import ollama
from nasa_tool import process_query

# Model to use for the test
MODEL_NAME = 'llama3.2:latest'

# Test cases with diverse queries
TEST_CASES = [
    {
        "id": 1,
        "category": "APOD",
        "query": "What is today's astronomy picture of the day?",
        "expected_api": "APOD",
        "description": "Basic query for Astronomy Picture of the Day"
    },
    {
        "id": 2,
        "category": "APOD",
        "query": "Show me NASA's picture from 2022-12-25",
        "expected_api": "APOD",
        "description": "APOD query with specific date"
    },
    {
        "id": 3,
        "category": "Mars Rover",
        "query": "What photos did Curiosity rover take recently?",
        "expected_api": "Mars",
        "description": "Basic Mars rover query"
    },
    {
        "id": 4,
        "category": "Mars Rover",
        "query": "Show me pictures from Perseverance rover on Mars",
        "expected_api": "Mars",
        "description": "Mars rover query with specific rover"
    },
    {
        "id": 5,
        "category": "Near Earth Objects",
        "query": "Are there any asteroids passing near Earth this week?",
        "expected_api": "NEO",
        "description": "Basic NEO query"
    },
    {
        "id": 6,
        "category": "Near Earth Objects",
        "query": "Tell me about potentially hazardous asteroids",
        "expected_api": "NEO",
        "description": "NEO query about hazardous objects"
    },
    {
        "id": 7,
        "category": "Earth Imagery",
        "query": "Show me images of Earth from space",
        "expected_api": "EPIC",
        "description": "Basic Earth imagery query"
    },
    {
        "id": 8,
        "category": "Earth Imagery",
        "query": "What does our planet look like from space?",
        "expected_api": "EPIC",
        "description": "Alternative phrasing for Earth imagery"
    },
    {
        "id": 9,
        "category": "Multi-Intent",
        "query": "Tell me about the Mars rover and show me today's astronomy picture",
        "expected_api": "APOD or Mars",
        "description": "Query with multiple possible API matches"
    },
    {
        "id": 10,
        "category": "Off-Topic",
        "query": "Tell me about black holes",
        "expected_api": None,
        "description": "Space query not specifically related to NASA APIs"
    }
]

def get_model_response(query, with_nasa_data=False):
    """
    Get response from the model with or without NASA API integration
    
    Args:
        query (str): User query
        with_nasa_data (bool): Whether to use NASA API integration
    
    Returns:
        str: The model's response
    """
    # Initialize conversation with system message
    messages = [{
        "role": "system", 
        "content": "You are a helpful AI assistant with knowledge about space and NASA."
    }]
    
    # Add user query
    messages.append({"role": "user", "content": query})
    
    if with_nasa_data:
        # Try to get NASA data first
        nasa_response = process_query(query)
        
        if nasa_response:
            return nasa_response["response"]
    
    # If no NASA data or not using NASA data, get response from model
    try:
        response = ollama.chat(model=MODEL_NAME, messages=messages)
        content = response.get('message', {}).get('content', '')
        return content
    except Exception as e:
        return f"Error: {str(e)}"

def test_nasa_integration():
    """Test NASA API integration by comparing responses with and without it"""
    results = []
    
    print(f"\nTesting NASA API integration with {len(TEST_CASES)} queries...")
    print(f"Model: {MODEL_NAME}")
    
    for case in TEST_CASES:
        print(f"\nTest #{case['id']}: {case['query']}")
        print(f"Category: {case['category']}")
        
        # Get response without NASA data
        print("Getting response without NASA API integration...")
        response_without = get_model_response(case['query'], with_nasa_data=False)
        
        # Get response with NASA data
        print("Getting response with NASA API integration...")
        response_with = get_model_response(case['query'], with_nasa_data=True)
        
        # Analyze if the response with NASA data is meaningfully different
        used_nasa_data = response_with != response_without
        contains_url = "http" in response_with.lower()
        
        results.append({
            **case,
            "response_without_integration": response_without,
            "response_with_integration": response_with,
            "used_nasa_data": used_nasa_data,
            "contains_url": contains_url
        })
        
        # Display comparison
        print(f"Used NASA data: {'Yes' if used_nasa_data else 'No'}")
        print(f"Contains URL: {'Yes' if contains_url else 'No'}")
        print("\n--- Response with NASA API integration ---")
        print(response_with[:300] + "..." if len(response_with) > 300 else response_with)
        print("\n--- Response without NASA API integration ---")
        print(response_without[:300] + "..." if len(response_without) > 300 else response_without)
        
        # Small pause to avoid rate limits
        time.sleep(1)
    
    return results

def analyze_results(results):
    """Analyze and print insights from the test results"""
    nasa_data_usage = sum(1 for r in results if r["used_nasa_data"])
    url_count = sum(1 for r in results if r["contains_url"])
    
    print("\n" + "="*50)
    print("Test Results Analysis")
    print("="*50)
    
    print(f"\nOut of {len(results)} queries:")
    print(f"- {nasa_data_usage} ({nasa_data_usage/len(results)*100:.1f}%) used NASA API data")
    print(f"- {url_count} ({url_count/len(results)*100:.1f}%) responses included URLs")
    
    print("\nResults by Category:")
    categories = {}
    for result in results:
        category = result["category"]
        if category not in categories:
            categories[category] = {"total": 0, "used_nasa_data": 0}
        
        categories[category]["total"] += 1
        if result["used_nasa_data"]:
            categories[category]["used_nasa_data"] += 1
    
    for category, data in categories.items():
        success_rate = data["used_nasa_data"] / data["total"] * 100
        print(f"- {category}: {data['used_nasa_data']}/{data['total']} queries used NASA data ({success_rate:.1f}%)")
    
    # Analyze content quality
    print("\nContent Quality Analysis:")
    for result in results:
        if result["used_nasa_data"]:
            response_with = result["response_with_integration"]
            response_without = result["response_without_integration"]
            
            with_length = len(response_with)
            without_length = len(response_without)
            
            length_diff = with_length - without_length
            length_percent = (length_diff / without_length * 100) if without_length > 0 else 0
            
            print(f"\nQuery #{result['id']}: {result['query'][:50]}...")
            print(f"- Response with NASA data: {with_length} characters")
            print(f"- Response without NASA data: {without_length} characters")
            print(f"- Difference: {length_diff} characters ({length_percent:.1f}%)")
            
            # Look for specific details that might be in one response but not the other
            specific_details = ["date", "title", "url", "description", "rover", "camera", "asteroid", "earth", "image"]
            details_found = []
            
            for detail in specific_details:
                detail_in_with = detail.lower() in response_with.lower()
                detail_in_without = detail.lower() in response_without.lower()
                
                if detail_in_with and not detail_in_without:
                    details_found.append(detail)
            
            if details_found:
                print(f"- Added specific details: {', '.join(details_found)}")

def save_results(results):
    """Save test results to file for further analysis"""
    # Format results for export
    export_data = {
        "summary": {
            "total_tests": len(results),
            "nasa_data_used": sum(1 for r in results if r["used_nasa_data"]),
            "urls_included": sum(1 for r in results if r["contains_url"])
        },
        "detailed_results": results
    }
    
    # Save to JSON file
    with open('nasa_integration_test_results.json', 'w') as f:
        json.dump(export_data, f, indent=2)
    
    # Generate markdown report
    report = f"""# NASA API Integration Test Results

## Summary
- Total test queries: {len(results)}
- Queries that used NASA data: {export_data['summary']['nasa_data_used']} ({export_data['summary']['nasa_data_used']/len(results)*100:.1f}%)
- Responses that included URLs: {export_data['summary']['urls_included']} ({export_data['summary']['urls_included']/len(results)*100:.1f}%)

## Detailed Results

| ID | Category | Query | Used NASA Data | Contains URL |
|----|----------|-------|---------------|-------------|
"""
    
    for result in results:
        nasa_data = "Yes" if result["used_nasa_data"] else "No"
        urls = "Yes" if result["contains_url"] else "No"
        report += f"| {result['id']} | {result['category']} | {result['query']} | {nasa_data} | {urls} |\n"
    
    report += """
    
    # Save markdown report
    with open('nasa_integration_test_report.md', 'w') as f:
        f.write(report)
    
    print(f"\nResults saved to nasa_integration_test_results.json and nasa_integration_test_report.md")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("NASA API Integration Test Suite")
    print("="*50)
    
    try:
        # Check if Ollama is available
        ollama.list()
        
        # Run tests
        print("\nRunning tests to compare responses with and without NASA API integration...")
        results = test_nasa_integration()
        
        # Analyze results
        analyze_results(results)
        
        # Save results
        save_results(results)
        
        print("\nTesting completed successfully!")
        
    except Exception as e:
        print(f"\nError during testing: {str(e)}") 
