import json
import asyncio
import aiohttp
from typing import List, Dict

async def run_single_test(session: aiohttp.ClientSession, test: Dict) -> Dict:
    test_result = {
        "id": test["id"],
        "input": test["input"],
        "results": {}
    }
    
    # Create tasks for all locales in this test
    async def test_locale(locale: str, expected: str):
        async with session.post(
            "http://localhost:8000/completion/v2/rephrase/test",
            json={
                "text": test["input"],
                "locale": locale,
                "completion_task_type": "fix_grammar",
                "uid": "test_user"
            }
        ) as response:
            actual = (await response.json())["text"]
            return locale, {
                "passed": actual == expected,
                "expected": expected,
                "actual": actual
            }
    
    # Run all locales for this test in parallel
    tasks = [test_locale(locale, expected) for locale, expected in test["expected_outputs"].items()]
    locale_results = await asyncio.gather(*tasks)
    
    # Store results
    for locale, result in locale_results:
        test_result["results"][locale] = result
    
    # Print results immediately after each test
    print(f"\nTest {test['id']}:")
    print(f"Input: {test['input']}")
    for locale, result in test_result["results"].items():
        print(f"\n{locale}:")
        print(f"Passed: {result['passed']}")
        if not result['passed']:
            print(f"Expected: {result['expected']}")
            print(f"Actual: {result['actual']}")
    
    return test_result

async def run_tests():
    # Load test cases
    with open('app/tests/cases/test_locale_set.json', 'r') as f:
        test_cases = json.load(f)
    
    # Create a session for all requests
    async with aiohttp.ClientSession() as session:
        # Run tests in order, but locales in parallel
        results = []
        for test in test_cases:
            result = await run_single_test(session, test)
            results.append(result)
    
    return results

if __name__ == "__main__":
    asyncio.run(run_tests())