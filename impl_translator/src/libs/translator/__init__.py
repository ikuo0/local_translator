"""PDFMathTranslate-next adapter."""

import threading
from pathlib import Path

from pdf2zh_next.config.model import (
    BasicSettings,
    PDFSettings,
    SettingsModel,
    TranslationSettings,
)
from pdf2zh_next.config.translate_engine_model import OpenAISettings
from pdf2zh_next.high_level import do_translate_file


def translate_page(
    input_pdf: Path,
    output_dir: Path,
    host: str,
    model: str,
    interrupt_handler=None,
    qps: int = 4,
    pool_max_workers: int = 2,
    primary_font_family: str | None = "serif",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    settings = SettingsModel(
        basic=BasicSettings(input_files={str(input_pdf)}),
        translation=TranslationSettings(
            lang_in="en",
            lang_out="ja",
            output=str(output_dir),
            qps=qps,
            pool_max_workers=pool_max_workers,
            custom_system_prompt="/no_think",
            no_auto_extract_glossary=True,
            min_text_length=10,
            primary_font_family=primary_font_family,
        ),
        pdf=PDFSettings(
            no_dual=True,
            skip_clean=True,
            disable_rich_text_translate=True,
        ),
        translate_engine_settings=OpenAISettings(
            openai_base_url=f"{host}/v1",
            openai_model=model,
            openai_api_key="dummy",
        ),
    )
    settings.validate_settings()
    
    error_holder = {}
    
    def translate_worker():
        try:
            # OpenAI互換API（Ollama の /v1 エンドポイント）を使用
            # OpenAI APIには keep_alive パラメータがないため、
            # docker-compose.yml の OLLAMA_KEEP_ALIVE: "0" 環境変数が有効になり、
            # 各リクエスト後に即座にGPUメモリが解放される
            error_count = do_translate_file(settings, ignore_error=False)
            error_holder["error_count"] = error_count
        except Exception as error:
            error_holder["exception"] = error
    
    thread = threading.Thread(target=translate_worker, daemon=False)
    thread.start()
    
    while thread.is_alive():
        if interrupt_handler:
            interrupt_handler.check()
        thread.join(timeout=0.1)
    
    if "exception" in error_holder:
        error = error_holder["exception"]
        raise RuntimeError(f"PDFMathTranslate-next failed: {error}") from error
    
    error_count = error_holder.get("error_count", 0)
    if error_count:
        raise RuntimeError(f"PDFMathTranslate-next reported {error_count} error(s)")
    
    results = list(output_dir.glob("*.mono.pdf"))
    if len(results) != 1:
        raise RuntimeError(
            f"Expected one translated PDF, found {len(results)} in {output_dir}"
        )
    return results[0]
