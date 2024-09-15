# chat/llm.py


import base64
import dataclasses
import logging
from typing import List, Optional, Dict, AsyncGenerator, Union

import openai
from django.conf import settings
from django.core.files.base import File

logger = logging.getLogger(__name__)


openai_async_client = openai.AsyncClient(api_key=settings.OPENAI_API_KEY)

# default: "http://localhost:11434"
# ollama_async_client = ollama.AsyncClient(host=settings.OLLAMA_HOST)


@dataclasses.dataclass
class LLMResponse:
    vendor: Optional[str] = None
    model: Optional[str] = None
    text: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    PRICES = {
        # https://openai.com/api/pricing/ : 가격은 수시로 바뀔 수 있습니다.
        # 1M Tokens, USD
        ("openai", "o1-preview"): (15, 60),
        ("openai", "o1-mini"): (3, 12),
        ("openai", "gpt-4o"): (5, 15),
        ("openai", "gpt-4o-mini"): (0.15, 0.6),
    }
    TOKENS_UNIT = 1_000_000

    def get_cost_usd(self) -> Optional[float]:
        try:
            input_price_per_1m, output_price_per_1m = self.PRICES[
                (self.vendor, self.model)
            ]
        except KeyError:
            logger.error(f"가격 정보 등록이 필요합니다. : {self.vendor}, {self.model}")
            return None

        input_cost = (self.input_tokens or 0) / self.TOKENS_UNIT * input_price_per_1m
        output_cost = (self.output_tokens or 0) / self.TOKENS_UNIT * output_price_per_1m
        estimated_cost_usd = input_cost + output_cost
        return estimated_cost_usd


async def make_llm_response(
    vendor: str,
    model: str,
    system_prompt: str = "",
    user_prompt: str = "",
    chat_history: List[Dict[str, str]] = None,
    temperature: float = 1.0,
    max_tokens: int = 1024,
    stream: bool = True,
    files: List[File] = None,
) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
    messages = chat_history.copy() if chat_history else []

    try:
        handler = {
            "openai": _make_openai_response,
            # "ollama": _make_ollama_response,
        }[vendor]
    except KeyError:
        logger.error(f"유효하지 않은 LLM 벤더: {vendor}")
        raise ValueError(f"유효하지 않은 LLM 벤더: {vendor}")

    try:
        return await handler(
            model,
            system_prompt,
            user_prompt,
            messages,
            temperature,
            max_tokens,
            stream,
            files,
        )
    except Exception as e:
        logger.exception(e)
        return _make_error_response(vendor, model, stream)


async def _make_openai_response(
    model,
    system_prompt,
    user_prompt,
    messages,
    temperature,
    max_tokens,
    stream,
    files: List[File] = None,
):
    if system_prompt:
        messages.insert(
            0,
            {"role": "system", "content": system_prompt},
        )

    if user_prompt:
        if not files:
            messages.append({"role": "user", "content": user_prompt})
        else:
            # refs: https://platform.openai.com/docs/guides/vision
            encoded_files = []
            for file in files:
                try:
                    if file.content_type.startswith("image/"):
                        prefix = f"data:{file.content_type};base64,"
                        b64_data = base64.b64encode(file.read()).decode("utf-8")
                        encoded_files.append(
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"{prefix}{b64_data}",
                                    # "auto" (default), "low" or "high"
                                    "detail": "low",
                                },
                            }
                        )
                    else:
                        logger.warning(f"파일이 이미지가 아닙니다: {file.name}")
                except Exception as e:
                    logger.warning(
                        f"파일 처리 중 오류 발생: {file.name}, 오류: {str(e)}"
                    )
            messages.append(
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_prompt}, *encoded_files],
                }
            )

    stream_options = {"include_usage": True} if stream else None
    response = await openai_async_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        stream_options=stream_options,
    )

    if not stream:
        return LLMResponse(
            vendor="openai",
            model=model,
            text=response.choices[0].message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

    async def generator():
        async for chunk in response:
            text = chunk.choices[0].delta.content if chunk.choices else None
            input_tokens = chunk.usage.prompt_tokens if chunk.usage else None
            output_tokens = chunk.usage.completion_tokens if chunk.usage else None

            if any((text, input_tokens, output_tokens)):
                yield LLMResponse(
                    vendor="openai",
                    model=model,
                    text=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

    return generator()


# async def _make_ollama_response(
#     model,
#     system_prompt,
#     user_prompt,
#     messages,
#     temperature,
#     max_tokens,
#     stream,
#     files: List[File] = None,
# ):
#     if files:
#         logger.warning("Ollama에서는 이미지 멀티 모달을 지원하지 않습니다.")
#
#     if system_prompt:
#         messages.insert(
#             0,
#             {"role": "system", "content": system_prompt},
#         )
#
#     if user_prompt:
#         messages.append({"role": "user", "content": user_prompt})
#
#     response = await ollama_async_client.chat(
#         model=model,
#         messages=messages,
#         options={
#             "temperature": temperature,
#             "num_predict": max_tokens,
#         },
#         stream=stream,
#     )
#
#     if not stream:
#         text = response["message"]["content"]
#         if files:
#             text += " (에러: ollama에서는 이미지 멀티 모달을 지원하지 않습니다.)"
#         # Ollama API는 현재 토큰 사용량을 제공하지 않습니다
#         return LLMResponse(vendor="ollama", model=model, text=text)
#     else:
#
#         async def generator():
#             async for part in response:
#                 chunk_text = part["message"]["content"]
#                 if chunk_text:
#                     yield LLMResponse(vendor="ollama", model=model, text=chunk_text)
#             if files:
#                 yield LLMResponse(
#                     vendor="ollama", model=model,
#                     text=" (에러: ollama에서는 이미지 멀티 모달을 지원하지 않습니다.)"
#                 )
#
#         return generator()


def _make_error_response(vendor: str, model: str, stream: bool):
    error_response = LLMResponse(
        vendor=vendor, model=model, text="LLM 수행 중에 오류가 발생했습니다."
    )
    if not stream:
        return error_response
    else:

        async def generator():
            yield error_response

        return generator()
