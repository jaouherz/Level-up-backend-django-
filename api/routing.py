from django.urls import path
from .consumers import OfferConsumer

websocket_urlpatterns = [
    path("ws/offers/", OfferConsumer.as_asgi()),
]
