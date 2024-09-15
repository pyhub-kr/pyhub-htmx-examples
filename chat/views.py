from django.core.files import File
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from typing import List

from .forms import MessageForm


def index(request):
    return render(request, "chat/index.html")


@require_POST
def message(request):
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

    res = f'<p>"{user_text}"를 입력하셨고, {len(photos)}장의 사진을 첨부하셨습니다.</p>'

    return HttpResponse(res)
