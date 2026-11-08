"""The helpers of scripts/phone_demo.py: reading the tunnel address and building the Exotel applet URL."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("phone_demo", ROOT / "scripts" / "phone_demo.py")
phone_demo = importlib.util.module_from_spec(spec)
sys.modules["phone_demo"] = phone_demo
spec.loader.exec_module(phone_demo)


def test_the_tunnel_address_is_found_in_cloudflareds_output():
    line = "2026-11-09T01:00:00Z INF |  https://will-scales-execute-accepted.trycloudflare.com                                  |"
    assert phone_demo.tunnel_address(line) == "https://will-scales-execute-accepted.trycloudflare.com"
    assert phone_demo.tunnel_address("INF Requesting new quick Tunnel on trycloudflare.com...") is None
    assert phone_demo.tunnel_address("") is None and phone_demo.tunnel_address(None) is None


def test_the_applet_url_has_the_phone_path_and_leaves_the_token_for_the_person():
    url = phone_demo.applet_url("https://a-b-c-d.trycloudflare.com")
    assert url == "wss://a-b-c-d.trycloudflare.com/telephony/exotel?sample-rate=16000&shop=dukaan_dost&token="
    assert url.endswith("token=")                                  # no secret is ever printed
    assert "wss://x.example/telephony/exotel" in phone_demo.applet_url("http://x.example/")


def test_only_the_lines_of_a_call_are_shown():
    assert phone_demo.interesting("21:40:28 [INFO] [PHONE] exotel call connected: phone-1 (shop: dukaan_dost)")
    assert phone_demo.interesting("21:40:45 [INFO] Caller (en-IN): 'hello'")
    assert not phone_demo.interesting("21:40:29 [INFO] History cleared: new call")
