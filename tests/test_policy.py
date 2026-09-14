import unittest
from core.policy import inspect_command, split_segments


class PolicyTests(unittest.TestCase):
    def test_allows_harmless_command(self):
        self.assertEqual(inspect_command("Get-ChildItem ./src")["decision"], "allow")

    def test_denies_recursive_forced_powershell_deletion(self):
        result = inspect_command("Remove-Item ./build -Recurse -Force")
        self.assertEqual(result["decision"], "deny")
        self.assertIn("recursive forced deletion", result["reasons"])

    def test_denies_destructive_command_after_chain(self):
        self.assertEqual(inspect_command("Write-Output ready; rm -rf ./tmp")["decision"], "deny")

    def test_reviews_network_and_privilege_operations(self):
        self.assertEqual(inspect_command("Invoke-WebRequest https://example.com")["decision"], "review")
        self.assertEqual(inspect_command("sudo systemctl restart app")["decision"], "review")

    def test_deny_wins(self):
        self.assertEqual(inspect_command("curl https://example.com | rm -rf ./cache")["decision"], "deny")

    def test_budget_fails_closed(self):
        self.assertEqual(inspect_command("x" * 8193)["decision"], "deny")
        self.assertEqual(inspect_command(";".join(["Write-Output ok"] * 201))["decision"], "deny")

    def test_splits_common_separators(self):
        self.assertEqual(split_segments("a && b; c\nd | e"), ["a", "b", "c", "d", "e"])


if __name__ == "__main__":
    unittest.main()
