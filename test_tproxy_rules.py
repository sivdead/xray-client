import importlib.util
import pathlib
import subprocess
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("xray-client.py")
spec = importlib.util.spec_from_file_location("xray_client", MODULE_PATH)
xray_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xray_client)


class TproxyRulesTest(unittest.TestCase):
    def test_tailscale_cgnat_range_is_bypassed_before_redirect(self):
        client = object.__new__(xray_client.XrayClient)
        client.tun_port = 12345
        calls = []

        def record_iptables(*args):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        client._run_iptables = record_iptables
        client._get_xray_uid = lambda: 65534

        client._setup_tproxy_rules()

        tailscale_return = (
            "-t",
            "nat",
            "-A",
            xray_client.IPTABLES_CHAIN,
            "-d",
            "100.64.0.0/10",
            "-j",
            "RETURN",
        )
        redirect = (
            "-t",
            "nat",
            "-A",
            xray_client.IPTABLES_CHAIN,
            "-p",
            "tcp",
            "-j",
            "REDIRECT",
            "--to-ports",
            "12345",
        )

        self.assertIn(tailscale_return, calls)
        self.assertLess(calls.index(tailscale_return), calls.index(redirect))


if __name__ == "__main__":
    unittest.main()
