"""ccode 图片生成 API 客户端。

使用 openai SDK（OpenAI-compatible）。
- 文生图：POST /v1/images/generations
- 图生图：POST /v1/images/edits（openai SDK client.images.edit()）

ccode 模型说明：
  gpt-image-2      基础版，不支持 size 参数，b64_json 带 data: 前缀
  gpt-image-2-pro  高级版，支持 size，b64_json 纯 base64
"""
from __future__ import annotations

import io
import logging
from typing import Any

from fastapi import HTTPException
from openai import APIStatusError, APITimeoutError, OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# 基础版模型不支持 size 参数
_MODELS_NO_SIZE = {"gpt-image-2"}


def _get_client() -> OpenAI:
    if not settings.image_api_key:
        raise HTTPException(status_code=503, detail="IMAGE_API_KEY 未配置，请联系管理员")
    return OpenAI(
        api_key=settings.image_api_key,
        base_url=settings.image_api_base_url,
        timeout=float(settings.image_api_timeout),
    )


def _supports_size(model: str) -> bool:
    return model not in _MODELS_NO_SIZE


def _normalize(raw: Any, model: str) -> dict:
    """将 openai SDK 响应归一化为统一结构。
    兼容两种 b64_json 格式：
      - 带前缀：data:image/png;base64,<base64>  （ccode gpt-image-2 基础版）
      - 纯 base64                               （ccode gpt-image-2-pro）
    """
    images: list[dict] = []
    for item in raw.data:
        url: str | None = getattr(item, "url", None)
        b64_raw: str | None = getattr(item, "b64_json", None)
        revised: str | None = getattr(item, "revised_prompt", None)

        b64_json: str | None = None
        data_url: str | None = None

        if b64_raw:
            if b64_raw.startswith("data:"):
                # 已经是完整 data URL，直接用；同时提取纯 base64
                data_url = b64_raw
                # 去掉 "data:image/xxx;base64," 前缀
                comma = b64_raw.find(",")
                b64_json = b64_raw[comma + 1:] if comma != -1 else b64_raw
            else:
                b64_json = b64_raw
                data_url = f"data:image/png;base64,{b64_raw}"
            logger.debug("image as base64 (len=%d)", len(b64_json or ""))

        images.append({"url": url, "b64_json": b64_json, "data_url": data_url, "revised_prompt": revised})
    return {"images": images, "model": model, "provider": "ccode"}


def _extract_error(exc: APIStatusError) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            return err["message"]
        if body.get("message"):
            return body["message"]
    return getattr(exc, "message", None) or str(exc)


def _handle_api_error(exc: Exception) -> None:
    if isinstance(exc, APITimeoutError):
        raise HTTPException(status_code=504, detail="图片生成超时，请稍后重试")
    if isinstance(exc, APIStatusError):
        msg = _extract_error(exc)
        logger.warning("ccode API error: status=%d msg=%.200s", exc.status_code, msg)
        raise HTTPException(status_code=422, detail=msg)
    if isinstance(exc, HTTPException):
        raise exc
    logger.error("unexpected error: %s", exc)
    raise HTTPException(status_code=500, detail="图片生成失败，请稍后重试")


def _single_text_to_image(
    client: OpenAI,
    *,
    model: str,
    full_prompt: str,
    size: str,
    quality: str,
) -> list[dict]:
    """单次出一张图，返回归一化后的图片列表。供并发调用。"""
    kwargs: dict[str, Any] = {"model": model, "prompt": full_prompt, "n": 1}
    if size and _supports_size(model):
        kwargs["size"] = size
    if quality.strip():
        kwargs["quality"] = quality
    resp = client.images.generate(**kwargs)
    return _normalize(resp, model)["images"]


def generate_text_to_image(
    *,
    model: str,
    prompt: str,
    negative_prompt: str = "",
    size: str = "1024x1024",
    n: int = 1,
    quality: str = "",
) -> dict:
    """文生图：调用 /v1/images/generations。

    gpt-image-2 系列每次只返回 1 张（n 参数无效），
    若 n > 1 则并发发起 n 次单张请求后合并结果。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = _get_client()
    n = max(1, min(int(n), 4))

    full_prompt = prompt
    if negative_prompt.strip():
        full_prompt = f"{prompt}\n\nAvoid: {negative_prompt}"

    logger.info("text-to-image: model=%s size=%s n=%d", model, size if _supports_size(model) else "N/A", n)
    try:
        if n == 1:
            images = _single_text_to_image(
                client, model=model, full_prompt=full_prompt, size=size, quality=quality
            )
        else:
            # 并发发起 n 次，每次出 1 张，再合并（API 不支持 n>1）
            all_images: list[dict] = []
            with ThreadPoolExecutor(max_workers=n) as executor:
                futures = [
                    executor.submit(
                        _single_text_to_image,
                        client,
                        model=model,
                        full_prompt=full_prompt,
                        size=size,
                        quality=quality,
                    )
                    for _ in range(n)
                ]
                for future in as_completed(futures):
                    all_images.extend(future.result())
            images = all_images
        return {"images": images, "model": model, "provider": "ccode"}
    except Exception as exc:
        _handle_api_error(exc)


def generate_image_to_image(
    *,
    model: str,
    image_bytes: bytes,
    image_filename: str,
    image_content_type: str,
    prompt: str,
    negative_prompt: str = "",
    size: str = "1024x1024",
) -> dict:
    """图生图：调用 /v1/images/edits（OpenAI images.edit()）。"""
    client = _get_client()

    full_prompt = prompt
    if negative_prompt.strip():
        full_prompt = f"{prompt}\n\nAvoid: {negative_prompt}"

    # openai SDK FileTypes: (filename, bytes, content_type)
    image_file = (image_filename, io.BytesIO(image_bytes), image_content_type)

    kwargs: dict[str, Any] = {"model": model, "image": image_file, "prompt": full_prompt}
    if size and _supports_size(model):
        kwargs["size"] = size

    logger.info("image-to-image: model=%s size=%s", model, size if _supports_size(model) else "N/A")
    try:
        resp = client.images.edit(**kwargs)
        return _normalize(resp, model)
    except Exception as exc:
        _handle_api_error(exc)
