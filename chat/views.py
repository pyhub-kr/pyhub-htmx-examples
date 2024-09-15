from django.core.files import File
from django.http import HttpResponse
from django.shortcuts import render

from typing import List


def index(request):
    return render(request, "chat/index.html")


def message(request):
    user_text: str = request.POST.get("user_text", "")
    photos: List[File] = request.FILES.getlist("photos")

    res = f'"{user_text}"를 입력하셨고, {len(photos)}장의 사진을 첨부하셨습니다.<br/>'

    return HttpResponse(res)
