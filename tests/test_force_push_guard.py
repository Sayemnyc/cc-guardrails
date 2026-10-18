import unittest

from _util import git, git_repo, run_hook


class ForcePushGuardTest(unittest.TestCase):
    def setUp(self):
        self.repo = git_repo()  # on main

    def code(self, cmd):
        return run_hook("force_push_guard.py", cmd, self.repo)[0]

    def test_blocks_force_push_to_main(self):
        for cmd in ["git push --force origin main", "git push -f origin main", "git push origin main --force",
                    "git push -uf origin main", "git push --force-with-lease origin main",
                    "git push --force-with-lease=main:abc123 origin main", "git push origin +main",
                    "git push origin +HEAD:main", "git push -f origin feature:main",
                    "git push -f origin HEAD:refs/heads/main", "git push --force", "git push -f origin",
                    "git push --force origin master", "git push --force --all origin", "git push --mirror -f",
                    "git -C . push -f origin main", "git status && git push -f origin main"]:
            self.assertEqual(self.code(cmd), 2, "should block: %s" % cmd)

    def test_allows_normal_pushes(self):
        for cmd in ["git push origin main", "git push", "git push -u origin main",
                    "git push --force origin feature", "git push origin +feature",
                    "git push -f origin main:feature", "git push --follow-tags origin main",
                    "git push -o ci.skip origin main"]:
            self.assertEqual(self.code(cmd), 0, "should allow: %s" % cmd)

    def test_bare_force_push_uses_current_branch(self):
        git(self.repo, "checkout", "-q", "-b", "feature")
        self.assertEqual(self.code("git push --force"), 0)
        self.assertEqual(self.code("git push -f origin HEAD"), 0)
        self.assertEqual(self.code("git push -f origin HEAD:main"), 2)


if __name__ == "__main__":
    unittest.main()
