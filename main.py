"""GitHub Artifact Release Assistant - start here.

    python main.py

starts the backend and opens the website in your browser.
Prerequisites: Python 3.10+, Git and the GitHub CLI (`gh auth login` done once).
"""

import argparse
import sys
import threading
import webbrowser

from config import DEFAULT_HOST, DEFAULT_PORT, FRONTEND_DIST
from server import make_server


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub Artifact Release Assistant")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser automatically")
    args = parser.parse_args()

    if not (FRONTEND_DIST / "index.html").exists():
        print("The website has not been built yet.")
        print("Run once:  cd frontend && npm install && npm run build")
        sys.exit(1)

    server = None
    for port in range(args.port, args.port + 10):
        try:
            server = make_server(DEFAULT_HOST, port)
            break
        except OSError:
            continue
    if server is None:
        print(f"Could not start the server: ports {args.port}-{args.port + 9} are all in use.")
        sys.exit(1)

    url = f"http://{DEFAULT_HOST}:{server.server_address[1]}"
    print("=" * 60)
    print(" GitHub Artifact Release Assistant")
    print(f" Open {url} in your browser (press Ctrl+C to stop)")
    print("=" * 60)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
