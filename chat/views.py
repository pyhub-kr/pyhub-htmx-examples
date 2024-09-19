import asyncio
import functools
import logging
from contextlib import aclosing
from typing import List, AsyncGenerator, TypedDict, Optional, Dict
from uuid import uuid4

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.http import StreamingHttpResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.html import escapejs
from django.views import View

from .forms import MessageForm
from .llm import make_llm_response, LLMResponse


logger = logging.getLogger(__name__)


class ChatMessage(TypedDict):
    role: str
    content: str


@login_required
def index(request):
    return render(request, "chat/index.html")


class ChatLLMView(View):  # 컨셉 코드
    system_prompt = ""
    llm_vendor = "openai"
    llm_model = "gpt-4o"
    temperature = 1
    max_tokens = 1024
    list_template_name = "chat/_llm_message_list.html"
    template_name = "chat/_llm_message.html"

    # 정적인 설정 변경은 위 클래스 변수 설정을 오버라이딩하고
    # 동적인 설정 변경은 아래 메서드를 오버라이딩합니다.
    def get_system_prompt(self) -> str: return self.system_prompt
    def get_llm_vendor(self) -> str: return self.llm_vendor
    def get_temperature(self) -> float: return self.temperature
    def get_max_tokens(self) -> int: return self.max_tokens
    def get_llm_model(self) -> str: return self.llm_model
    def get_list_template_name(self): return self.list_template_name
    def get_template_name(self): return self.template_name

    # 메시지 저장소로서 세션을 활용. 메서드를 오버라이딩하여 모델 활용도 가능
    async def get_messages(self) -> List[ChatMessage]:
        messages = await self.request.session.aget("chat_messages", [])
        return messages

    async def set_messages(self, messages: List[ChatMessage]) -> None:
        await self.request.session.aset("chat_messages", messages)
        await self.request.session.asave()

    async def clear_messages(self) -> None:
        if await self.request.session.aexists("chat_messages"):
            await self.request.session.apop("chat_messages")
            await self.request.session.asave()

    async def get(self, request: HttpRequest) -> HttpResponse:
        messages = await self.get_messages()
        return render(request, self.get_list_template_name(), {"messages": messages})

    async def post(self, request: HttpRequest) -> HttpResponse:

        async def stream_response() -> AsyncGenerator[str, None]:
            user_text = request.POST.get("user_text", "")

            if user_text == "/clear":
                await self.clear_messages()
                yield "<p>세션에 저장된 메세지를 삭제했습니다. 새로 고침해주세요.</p>"
                return

            if user_text:
                # photos를 시스템에 저장했다면, URL을 통해 보여줄 수 있습니다.
                yield render_to_string(self.get_template_name(), {
                    "role": "user",
                    "content": user_text,
                })

            form = MessageForm(data=request.POST, files=request.FILES)
            if not form.is_valid():
                error_message: str = ", ".join([
                    f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()
                ])
                yield f'<p class="text-red-500">{error_message}</p>'
                return

            chat_history = await self.get_messages()

            user_text = form.cleaned_data["user_text"]
            photos: List[File] = form.cleaned_data["photos"]
            vendor, model = self.get_llm_vendor(), self.get_llm_model()
            llm_stream_response = await make_llm_response(
                vendor=vendor, model=model, system_prompt=self.get_system_prompt(), user_prompt=user_text,
                chat_history=chat_history, temperature=self.get_temperature(), max_tokens=self.get_max_tokens(), stream=True, files=photos,
            )

            is_first = True
            assistant_message_id: str = f"message-{uuid4().hex}"
            assistant_message = ""
            llm_chunk_response = LLMResponse()
            async for llm_chunk_response in llm_stream_response:
                if llm_chunk_response.text:
                    chunk_text = escapejs(llm_chunk_response.text)
                    assistant_message += chunk_text
                    yield render_to_string(
                        self.get_template_name(),
                        {
                            "role": "assistant",
                            "is_append": (not is_first),
                            "assistant_message_id": assistant_message_id,
                            "chunk_text": chunk_text,
                        }
                    )

                    if is_first:
                        is_first = False

            chat_history.append(ChatMessage(role="user", content=user_text))
            chat_history.append(ChatMessage(role="assistant", content=assistant_message))
            await self.set_messages(chat_history)

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


class EnglishTutorChatLLMView(ChatLLMView):
    system_prompt = """
        당신은 영어를 배우는 학생들을 돕는 AI 영어 튜터입니다.
        당신의 목표는 학생들의 영어 실력 향상을 돕고, 학습 동기를 부여하며 영어에 대한 자신감을 높이는 것입니다. 
    """.strip()
    llm_vendor = "openai"
    llm_model = "gpt-4o-mini"
    temperature = 1
    max_tokens = 4096


class MultiUserChatView(View):  # 기본 컨셉만 구현
    room_name: Optional[str] = "test-room"

    def get_room_name(self) -> str:
        # 채팅방 이름 획득 (채널 레이어 그룹명 규칙 : 100자 미만, 알파벳/숫자/하이픈/언더바/마침표)
        return self.room_name

    async def get(self, request: HttpRequest) -> HttpResponse:
        """
        SSE 연결을 설정하고 채팅 메시지를 스트리밍합니다.
        채널 레이어를 통해 실시간으로 메시지를 수신하고 클라이언트에게 전달합니다.
        """
        async def stream_response():
            channel_layer = get_channel_layer()
            if channel_layer is None:
                yield f"data: <p class='text-red-500'>CHANNEL_LAYERS default 설정이 누락되었습니다.</p>\n\n"
            else:
                channel_name = await channel_layer.new_channel()  # 현 클라이언트의 식별자 생성
                channel_receive = functools.partial(channel_layer.receive, channel_name)
                room_name = self.get_room_name()

                try:
                    await channel_layer.group_add(room_name, channel_name)  # 지정 그룹에 추가
                    while True:
                        try:
                            new_message: Dict = await asyncio.wait_for(channel_receive(), timeout=1)
                            # TODO: type에 따른 분기
                            formatted_message = "<p><strong class='mr-1'>{username}</strong>{text}</p></div>".format(
                              **new_message
                            )

                            yield f"data: {formatted_message}\n\n"
                        except asyncio.CancelledError:  # 웹브라우저 클라이언트와 연결 끊김
                            break
                        except asyncio.TimeoutError:
                            pass
                except Exception as e:
                    logger.error(f"Error in ChatSSEView: {e}")
                finally:
                    await channel_layer.group_discard("chat_group", channel_name)

        async def wrapped_stream_response():
            async with aclosing(stream_response()) as stream:
                async for item in stream:
                    yield item

        response = StreamingHttpResponse(
            wrapped_stream_response(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        return response

    async def post(self, request: HttpRequest) -> HttpResponse:
        """
        채팅 메시지에 대한 POST 요청을 처리합니다.
        폼을 검증하고, 메시지를 채널 레이어를 통해 전파한 후, HTTP 응답을 반환합니다.
        """

        username: str = await sync_to_async(
            lambda: request.user.username or "anonymous"
        )()
        room_name = self.get_room_name()
        form = MessageForm(data=request.POST, files=request.FILES)

        channel_layer = get_channel_layer()

        if channel_layer is None:
            return HttpResponse(
                "<div class='text-red-500'>CHANNEL_LAYERS default 설정이 누락되었습니다.</div>"
            )
        elif form.is_valid() is False:
            return HttpResponse(f"<div class='text-red-500'>{form.errors}</div>")
        else:
            user_text = form.cleaned_data["user_text"]
            # Channel Layer를 통해 채팅 메시지 전파
            await channel_layer.group_send(
                room_name,
                {"type": "chat.message", "username": username, "text": user_text},
            )
            return HttpResponse()
