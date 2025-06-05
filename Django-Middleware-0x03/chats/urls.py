from django.urls import path, include
from rest_framework_nested import routers
from .views import AuthViewSet, UserViewSet, ConversationViewSet, MessageViewSet

# Initialize main router
router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'auth', AuthViewSet, basename='auth')

# Create nested router for messages under conversations
# This allows URLs like: /conversations/1/messages/
conversations_router = routers.NestedDefaultRouter(
    router, r'conversations', lookup='conversation'
)
conversations_router.register(r'messages', MessageViewSet, basename='conversation-messages')

# Register standalone messages endpoint for general message operations
# This allows URLs like: /messages/
router.register(r'messages', MessageViewSet, basename='message')

# URL patterns
urlpatterns = [
    # Include main router URLs
    path('', include(router.urls)),
    # Include nested router URLs for conversation messages
    path('', include(conversations_router.urls)),
    # Optional: Add DRF's browsable API authentication
    # path('api-auth/', include('rest_framework.urls')),
]

# Optional: Add API versioning
# urlpatterns = [
#     path('api/v1/', include([
#         path('', include(router.urls)),
#         path('', include(conversations_router.urls)),
#     ])),
# ]
