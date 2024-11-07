import asyncio
import re
from base64 import b64decode
from typing import Dict, Literal, Optional, List

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.files.base import ContentFile, File
from django.template.loader import render_to_string
from django.utils.datastructures import MultiValueDict
from django.utils.html import escapejs
from uuid import uuid4

from .forms import MessageForm
from .llm import make_llm_response, LLMResponse
from .views import ChatMessage


class ChatLLMConsumer(AsyncJsonWebsocketConsumer):
    system_prompt = ""
    llm_vendor = "openai"
    llm_model = "gpt-4o"
    temperature = 1
    max_tokens = 1024

    chat_messages_id = "chat-messages"
    template_name = "chat/_llm_message.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_messages = []

    async def connect(self):
        await self.accept()
        await self.reply(html="<p>WELCOME !!!</p>")

    async def disconnect(self, close_code):
        pass

    async def receive_json(self, request_dict: Dict, **kwargs):
        # HTMX websocket 요청에서는 "HEADERS" 키를 통해 HTMX 헤더가 전달됩니다.

        user_text = request_dict.get("user_text", "")

        if user_text == "/clear":
            self.chat_messages = []
            await self.reply(
                html="""
                    <script>
                        alert('세션에 저장된 메세지를 삭제했습니다. 페이지를 새로고침합니다.');
                        window.location.reload();
                    </script>
                """
            )
            return

        if user_text:
            await self.reply(context={"role": "user", "content": user_text})

        # 업로드된 파일이 base64 인코딩인지 확인하고, 이에 대한 디코딩 수행.
        files: MultiValueDict = self.decode_base64_files(request_dict)

        # 웹소켓 연결에서 파일 데이터를 업로드할려면? BASE64 직렬화
        form = MessageForm(data=request_dict, files=files)
        if not form.is_valid():
            error_message: str = ", ".join(
                [
                    f"{field}: {', '.join(errors)}"
                    for field, errors in form.errors.items()
                ]
            )
            await self.reply(html=f'<p class="text-red-500">{error_message}</p>')
            return

        user_text = form.cleaned_data["user_text"]
        photos: List[File] = form.cleaned_data["photos"]

        llm_stream_response = await make_llm_response(
            vendor=self.llm_vendor,
            model=self.llm_model,
            system_prompt=self.system_prompt,
            user_prompt=user_text,
            chat_history=self.chat_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            files=photos,
        )

        is_first = True
        assistant_message_id = f"message-{uuid4().hex}"
        assistant_message = ""
        llm_chunk_response = LLMResponse()
        async for llm_chunk_response in llm_stream_response:
            if llm_chunk_response.text:
                chunk_text = escapejs(llm_chunk_response.text)
                assistant_message += chunk_text
                await self.reply(
                    context={
                        "role": "assistant",
                        "is_append": (not is_first),
                        "assistant_message_id": assistant_message_id,
                        "chunk_text": chunk_text,
                    }
                )

                if is_first:
                    is_first = False

        self.chat_messages.append(ChatMessage(role="user", content=user_text))  # noqa
        self.chat_messages.append(
            ChatMessage(role="assistant", content=assistant_message)
        )

        estimated_cost_usd = llm_chunk_response.get_cost_usd() or 0
        exchange_rate = 1300  # 현재 환율을 가정
        estimated_cost_krw = estimated_cost_usd * exchange_rate

        await self.reply(
            html=f"""
                <p class="mb-2 text-sm text-gray-500">
                    {len(self.chat_messages)}건의 메시지,
                    입력 토큰: {llm_chunk_response.input_tokens},
                    출력 토큰: {llm_chunk_response.output_tokens},
                    예상 비용: ${estimated_cost_usd:.4f} USD (약 {estimated_cost_krw:.4f} 원)
                </p>
            """
        )

    async def reply(
        self,
        context: Optional[Dict] = None,
        html: Optional[str] = None,
    ) -> None:
        if context is not None:
            html = render_to_string(self.template_name, context)

        assert html is not None

        await self.send(
            f"""
                <div id="{self.chat_messages_id}" hx-swap-oob="beforeend">
                    {html}
                </div>
            """
        )

    @staticmethod
    def decode_base64_files(
        request_dict: Dict, field_name_postfix: str = "__base64"
    ) -> MultiValueDict:
        """base64로 인코딩된 파일 데이터를 디코딩하여 Django의 MultiValueDict 형태로 반환합니다.

        request_dict에서 field_name_postfix로 끝나는 필드를 찾아 base64로 인코딩된 파일 데이터를
        디코딩합니다. 현재는 이미지 파일만 처리합니다.

        Args:
            request_dict (Dict): 요청 데이터를 담고 있는 딕셔너리
            field_name_postfix (str, optional): base64 인코딩된 파일 필드를 식별하기 위한 접미사.
                기본값은 "__base64"

        Returns:
            MultiValueDict: 디코딩된 파일들을 담고 있는 Django의 MultiValueDict 객체.
                키는 원본 필드 이름(접미사 제외)이고, 값은 ContentFile 객체들의 리스트

        Examples:
            >>> files = decode_base64_files({
            ...     "photo__base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA..."
            ... })
            >>> files.getlist("photo")[0]  # ContentFile 객체 반환
        """

        files = MultiValueDict()
        for field_name in request_dict.keys():
            if field_name.endswith(field_name_postfix):
                file_field_name = re.sub(rf"{field_name_postfix}$", "", field_name)
                file_list: List[File] = []
                for base64_str in request_dict[field_name].split("||"):
                    # header 포맷 : data:image/png;base64,...
                    header, data = base64_str.split(",", 1)
                    matched = re.search(r"data:([^;]+);base64", header)
                    if matched and "image/" in matched.group(1):
                        extension: str = matched.group(1).split("/", 1)[-1]
                        file_name = f"{file_field_name}.{extension}"
                        file_list.append(ContentFile(b64decode(data), name=file_name))

                if file_list:
                    files.setlist(file_field_name, file_list)
        return files
