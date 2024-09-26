import logging
import logging.config
import os
import sys
from contextlib import asynccontextmanager

# 设置numexpr最大线程数，默认为CPU核心数
try:
    import numexpr

    n_cores = numexpr.utils.detect_number_of_cores()
    os.environ["NUMEXPR_MAX_THREADS"] = str(n_cores)
except:
    pass

from typing import Dict, List

import click
from fastapi import FastAPI

from aitutor.utils import build_logger

logger = build_logger()


def _set_app_event(app: FastAPI):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app.router.lifespan_context = lifespan


def run_api_server(run_mode: str = None):
    import uvicorn

    from aitutor.server.api_server.server_app import create_app
    from aitutor.server.utils import set_httpx_config
    from aitutor.settings import Settings
    from aitutor.utils import (
        get_config_dict,
        get_log_file,
        get_timestamp_ms,
    )

    logger.info(f"Api MODEL_PLATFORMS: {Settings.model_settings.MODEL_PLATFORMS}")
    set_httpx_config()
    app = create_app(run_mode=run_mode)
    _set_app_event(app)

    host = Settings.basic_settings.API_SERVER["host"]
    port = Settings.basic_settings.API_SERVER["port"]

    logging_conf = get_config_dict(
        "INFO",
        get_log_file(
            log_path=Settings.basic_settings.LOG_PATH,
            sub_dir=f"run_api_server_{get_timestamp_ms()}",
        ),
        1024 * 1024 * 1024 * 3,
        1024 * 1024 * 1024 * 3,
    )
    logging.config.dictConfig(logging_conf)  # type: ignore
    uvicorn.run(app, host=host, port=port)


def dump_server_info():
    import platform

    import langchain

    from aitutor import __version__
    from aitutor.server.utils import api_address
    from aitutor.settings import Settings

    print("\n")
    print("=" * 30 + "Aitutor Configuration" + "=" * 30)
    print(f"操作系统：{platform.platform()}.")
    print(f"python版本：{sys.version}")
    print(f"项目版本：{__version__}")
    print(f"langchain版本：{langchain.__version__}")
    print(f"数据目录：{Settings.AITUTOR_ROOT}")
    print("\n")

    print(f"当前使用的分词器：{Settings.kb_settings.TEXT_SPLITTER_NAME}")

    print(
        f"默认选用的 Embedding 名称： {Settings.model_settings.DEFAULT_EMBEDDING_MODEL}"
    )

    print("\n")
    print(f"服务端运行信息：")
    print(f"    aitutor Api Server: {api_address()}")
    print("=" * 30 + "Langchain-aitutor Configuration" + "=" * 30)
    print("\n")


def start_main_server():
    import signal

    from aitutor.settings import Settings
    from aitutor.utils import (
        get_config_dict,
        get_log_file,
        get_timestamp_ms,
    )

    logging_conf = get_config_dict(
        "INFO",
        get_log_file(
            log_path=Settings.basic_settings.LOG_PATH,
            sub_dir=f"start_main_server_{get_timestamp_ms()}",
        ),
        1024 * 1024 * 1024 * 3,
        1024 * 1024 * 1024 * 3,
    )
    logging.config.dictConfig(logging_conf)  # type: ignore

    def handler(signalname):
        def f(signal_received, frame):
            raise KeyboardInterrupt(f"{signalname} received")

        return f

    signal.signal(signal.SIGINT, handler("SIGINT"))
    signal.signal(signal.SIGTERM, handler("SIGTERM"))

    dump_server_info()

    logger.info(f"正在启动服务：")
    logger.info(f"如需查看 llm_api 日志，请前往 {Settings.basic_settings.LOG_PATH}")

    try:
        run_api_server()
    except Exception as e:
        logger.error(e)
        logger.warning("Caught KeyboardInterrupt! Setting stop event...")


@click.command(help="启动服务")
@click.option(
    "--api",
    "api",
    is_flag=True,
    help="run api.py",
)
def main(api):
    class args:
        ...

    args.api = api

    cwd = os.getcwd()
    sys.path.append(cwd)
    print("cwd:" + cwd)
    from aitutor.server.knowledge_base.migrate import create_tables

    create_tables()
    start_main_server()


if __name__ == "__main__":
    main()
