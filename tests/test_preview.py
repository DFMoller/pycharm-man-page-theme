import os
import unittest
from unittest import mock

from preview import virtual_display_env


class VirtualDisplayEnvTest(unittest.TestCase):
    @mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0", "XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"})
    def test_wayland_variables_are_removed_and_display_replaced(self) -> None:
        env = virtual_display_env(":42")

        self.assertNotIn("WAYLAND_DISPLAY", env)
        self.assertNotIn("XDG_SESSION_TYPE", env)
        self.assertEqual(env["DISPLAY"], ":42")

    @mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"})
    def test_extra_variables_cannot_bring_wayland_back(self) -> None:
        env = virtual_display_env(":42", {"WAYLAND_DISPLAY": "wayland-1", "PYCHARM_PROPERTIES": "/x"})

        self.assertNotIn("WAYLAND_DISPLAY", env)
        self.assertEqual(env["PYCHARM_PROPERTIES"], "/x")


if __name__ == "__main__":
    unittest.main()
