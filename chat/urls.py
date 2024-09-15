from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.index, name="index"),
    path("chat/llm/", views.ChatLLMView.as_view(), name="chat-llm"),
    path("chat/english-tutor/", views.EnglishTutorChatLLMView.as_view(), name="chat-english-tutor"),
]
