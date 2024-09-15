from typing import List, AsyncGenerator

from django.core.files import File
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .forms import MessageForm
from .llm import make_llm_response, LLMResponse


def index(request):
    return render(request, "chat/index.html")


@require_POST
async def message(request):
    form = MessageForm(data=request.POST,
                       files=request.FILES)
    if not form.is_valid():
        # 템플릿 렌더링 추천 (render or render_to_string)
        error_message: str = ", ".join(
            [f"{field}: {', '.join(errors)}"
             for field, errors in form.errors.items()]
        )
        return HttpResponse(f'<p class="text-red-500">{error_message}</p>')

    user_text = form.cleaned_data["user_text"]
    photos: List[File] = form.cleaned_data["photos"]

    vendor, model = "openai", "gpt-4o"
    llm_stream_response: AsyncGenerator[LLMResponse, None] = await make_llm_response(
        vendor=vendor, model=model, system_prompt="", user_prompt=user_text,
        chat_history=[], temperature=1.0, max_tokens=1024, stream=True, files=photos,
    )

    assistant_text = ""
    llm_chunk_response = LLMResponse()
    async for llm_chunk_response in llm_stream_response:
        if llm_chunk_response.text:
            assistant_text += llm_chunk_response.text

    estimated_cost_usd = llm_chunk_response.get_cost_usd() or 0
    exchange_rate = 1300  # 현재 환율을 가정
    estimated_cost_krw = estimated_cost_usd * exchange_rate

    # 템플릿 렌더링 추천 (render or render_to_string)
    return HttpResponse(f"""
        <p class="mb-2"><strong class="mr-1">사용자</strong><span class="text">{user_text}</span></p>
        <p><strong class="mr-1">어시스턴트</strong><span class="text">{assistant_text}</span></p>
        <p class="mb-2 text-sm text-gray-500">입력 토큰: {llm_chunk_response.input_tokens},
         출력 토큰: {llm_chunk_response.output_tokens},
         예상 비용: ${estimated_cost_usd:.4f} USD (약 {estimated_cost_krw:.4f} 원)</p>
    """)
