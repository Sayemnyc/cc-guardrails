import os
import unittest

from _util import git, git_repo, run_hook, write

# Built by concatenation so this file never matches the patterns it tests.
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
FAKE_ANTHROPIC = "sk-ant-" + "api03-" + "x" * 40
FAKE_GITHUB = "ghp_" + "a" * 36


class SecretGuardTest(unittest.TestCase):
    def setUp(self):
        self.repo = git_repo()

    def run_cmd(self, cmd, cwd=None):
        return run_hook("secret_guard.py", cmd, cwd or self.repo)

    def assertBlocked(self, cmd, cwd=None):
        code, err = self.run_cmd(cmd, cwd)
        self.assertEqual(code, 2, "should block: %s" % cmd)
        return err

    def assertAllowed(self, cmd, cwd=None):
        code, err = self.run_cmd(cmd, cwd)
        self.assertEqual(code, 0, "should allow: %s (%s)" % (cmd, err))

    def test_blocks_env_files(self):
        write(os.path.join(self.repo, ".env"), "DEBUG=1\n")
        write(os.path.join(self.repo, "app", ".env.production"), "X=1\n")
        self.assertIn(".env", self.assertBlocked("git add .env"))
        self.assertBlocked("git add .")
        self.assertBlocked("git add -A")
        self.assertBlocked("git add app")
        self.assertBlocked("git add .env.production", cwd=os.path.join(self.repo, "app"))
        self.assertBlocked("git -C app add .")
        self.assertBlocked("cd app && git add -A")

    def test_allows_env_example_and_ignored_env(self):
        write(os.path.join(self.repo, ".env.example"), "API_KEY=\n")
        self.assertAllowed("git add .env.example")
        write(os.path.join(self.repo, ".env"), "SECRET=1\n")
        write(os.path.join(self.repo, ".gitignore"), ".env\n")
        self.assertAllowed("git add .")  # git itself skips ignored files

    def test_blocks_files_with_keys(self):
        write(os.path.join(self.repo, "config.py"), 'AWS = "%s"\n' % FAKE_AWS)
        write(os.path.join(self.repo, "client.js"), "const k = '%s';\n" % FAKE_ANTHROPIC)
        write(os.path.join(self.repo, "ci.yml"), "token: %s\n" % FAKE_GITHUB)
        write(os.path.join(self.repo, "settings.py"), 'api_key = "%s"\n' % ("Zq9" * 10))
        for f in ("config.py", "client.js", "ci.yml", "settings.py"):
            self.assertBlocked("git add " + f)

    def test_allows_clean_files(self):
        write(os.path.join(self.repo, "main.py"), 'import os\nKEY = os.environ["API_KEY"]\n')
        self.assertAllowed("git add main.py")
        self.assertAllowed("git add . && git commit -m 'add main'")
        self.assertAllowed("git status")

    def test_blocks_commit_of_already_staged_secret(self):
        write(os.path.join(self.repo, "keys.txt"), FAKE_AWS + "\n")
        git(self.repo, "add", "keys.txt")
        self.assertBlocked("git commit -m 'oops'")

    def test_blocks_commit_all_of_tracked_file_that_gained_a_key(self):
        write(os.path.join(self.repo, "app.py"), "print('hi')\n")
        git(self.repo, "add", "app.py")
        git(self.repo, "commit", "-q", "-m", "app")
        write(os.path.join(self.repo, "app.py"), "KEY = '%s'\n" % FAKE_ANTHROPIC)
        self.assertAllowed("git commit -m 'nothing staged'")
        self.assertBlocked("git commit -am 'oops'")


if __name__ == "__main__":
    unittest.main()
