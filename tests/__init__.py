"""
Basic test runner for Praier tests.
"""

import os
import sys

# Add the parent directory to the path so we can import praier
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    print("Running Praier tests...")
    print("=" * 40)

    try:
        # Run config tests
        print("Testing configuration module...")
        test_config.test_github_config_from_env()
        test_config.test_github_config_defaults()
        test_config.test_praier_config_from_env()
        test_config.test_praier_config_from_yaml()
        print("✓ Configuration tests passed!")

        # Run GitHub client tests
        print("\nTesting GitHub client module...")
        test_github_client.test_pull_request_creation()
        test_github_client.test_check_run_creation()
        test_github_client.test_workflow_run_creation()
        test_github_client.test_workflow_run_defaults()
        print("✓ GitHub client tests passed!")

        print("\n" + "=" * 40)
        print("All tests passed! 🎉")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
