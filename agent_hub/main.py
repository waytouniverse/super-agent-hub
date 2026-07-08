"""Agent Hub 入口"""

import sys
import webbrowser
import argparse

import uvicorn

from .config import load


def main():
    parser = argparse.ArgumentParser(
        description="Agent Hub - 统一 AI Agent 工作台",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=["start", "version"],
        help="命令: start (启动服务), version (版本信息)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="绑定地址 (默认从配置读取)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="绑定端口 (默认 9527)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="不自动打开浏览器",
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="桌面模式（Tauri 内嵌，不打开浏览器）",
    )

    args = parser.parse_args()

    if args.command == "version":
        from . import __version__
        print(f"Agent Hub v{__version__}")
        return

    config = load()
    server_config = config.get("server", {})
    host = args.host or server_config.get("host", "127.0.0.1")
    port = args.port or server_config.get("port", 9527)
    url = f"http://{host}:{port}"

    if args.desktop:
        print(f"Agent Hub 桌面模式 → {url}")
    else:
        print(f"\n  Agent Hub")
        print(f"  统一 AI 工作台")
        print(f"\n  → 启动服务: {url}")
        print(f"  → 按 Ctrl+C 停止\n")
        if not args.no_browser:
            webbrowser.open(url)

    uvicorn.run(
        "agent_hub.server:app",
        host=host,
        port=port,
        log_level="warning" if args.desktop else "info",
        reload=False,
    )


if __name__ == "__main__":
    main()
