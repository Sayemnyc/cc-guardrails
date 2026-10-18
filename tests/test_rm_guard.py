import os
import tempfile
import unittest

from _util import run_hook


class RmGuardTest(unittest.TestCase):
    def setUp(self):
        self.project = os.path.realpath(tempfile.mkdtemp())
        os.makedirs(os.path.join(self.project, "build"))

    def assertBlocked(self, cmd, cwd=None):
        code, err = run_hook("rm_guard.py", cmd, cwd or self.project, self.project)
        self.assertEqual(code, 2, "should block: %s" % cmd)
        self.assertIn("cc-guardrails", err)

    def assertAllowed(self, cmd, cwd=None):
        code, err = run_hook("rm_guard.py", cmd, cwd or self.project, self.project)
        self.assertEqual(code, 0, "should allow: %s (%s)" % (cmd, err))

    def test_blocks_outside_project(self):
        for cmd in ["rm -rf /", "rm -rf ~", "rm -rf ~/Documents", "rm -rf $HOME/x", "rm -fr ..",
                    "rm -rf ../sibling", "rm -r -f /tmp/x", "rm --recursive --force /etc",
                    "sudo rm -rf /usr", "/bin/rm -rf /opt", "rm -rf /*", "rm -rf ../*",
                    "rm -rf .", "rm -rf build ~", "rm -rf build && rm -rf /var",
                    "cd / && rm -rf usr", "rm -rf $UNKNOWN_VAR/x", "rm -rf -- /"]:
            self.assertBlocked(cmd)

    def test_allows_inside_project(self):
        for cmd in ["rm -rf build", "rm -rf ./build/", "rm -rf build/*", "rm -rf *", "rm -rf node_modules dist",
                    "rm -rf %s/build" % self.project, "cd build && rm -rf cache", "rm -rf build 2>/dev/null",
                    "rm file.txt", "rm -f /tmp/not-recursive.txt", "echo rm -rf /", "ls -la"]:
            self.assertAllowed(cmd)

    def test_subdir_cwd_cannot_escape(self):
        sub = os.path.join(self.project, "build")
        self.assertAllowed("rm -rf ../src", cwd=sub)
        self.assertBlocked("rm -rf ../../", cwd=sub)

    def test_symlink_parent_out_of_project_is_blocked(self):
        outside = os.path.realpath(tempfile.mkdtemp())
        os.symlink(outside, os.path.join(self.project, "link"))
        self.assertAllowed("rm -rf link")          # removes only the link
        self.assertBlocked("rm -rf link/data")     # reaches through it


if __name__ == "__main__":
    unittest.main()
