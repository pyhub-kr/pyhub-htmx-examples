from typing import List, AsyncGenerator

from django.core.files import File
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .forms import MessageForm
from .llm import make_llm_response, LLMResponse


def index(request):
    return render(request, "chat/index.html")


@require_POST
async def message(request):
    async def stream_response() -> AsyncGenerator[str, None]:
        user_text = request.POST.get("user_text", "")
        if user_text:
            # photos를 시스템에 저장했다면, URL을 통해 보여줄 수 있습니다.
            yield f'<p><strong class="mr-1">사용자</strong><span class="text">{user_text}</span></p>'

        form = MessageForm(data=request.POST, files=request.FILES)
        if not form.is_valid():
            error_message: str = ", ".join([
                f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()
            ])
            yield f'<p class="text-red-500">{error_message}</p>'
            return

        user_text = form.cleaned_data["user_text"]
        photos: List[File] = form.cleaned_data["photos"]
        vendor, model = "openai", "gpt-4o"
        llm_stream_response = await make_llm_response(
            vendor=vendor, model=model, system_prompt="", user_prompt=user_text,
            chat_history=[], temperature=1.0, max_tokens=1024, stream=True, files=photos,
        )
        assistant_text = ""
        llm_chunk_response = LLMResponse()
        async for llm_chunk_response in llm_stream_response:
            if llm_chunk_response.text:
                assistant_text += llm_chunk_response.text
                yield f'''<p><strong class="mr-1">어시스턴트</strong>
                             <span class="text">{llm_chunk_response.text}</span></p>'''
        estimated_cost_usd = llm_chunk_response.get_cost_usd() or 0
        exchange_rate = 1300  # 현재 환율을 가정
        estimated_cost_krw = estimated_cost_usd * exchange_rate

        yield f"""
            <p class="mb-2 text-sm text-gray-500">
                입력 토큰: {llm_chunk_response.input_tokens},
                출력 토큰: {llm_chunk_response.output_tokens},
                예상 비용: ${estimated_cost_usd:.4f} USD (약 {estimated_cost_krw:.4f} 원)
            </p>
        """

    # SSE (Server-sent Events) 응답
    return StreamingHttpResponse(stream_response(), content_type="text/event-stream")

