from django.contrib import admin
from django.contrib.auth.models import User,UserManager
from .models import Author, Post, friend_request, Comment,Friend,Notify,PostImages,Node


admin.site.register(Author)
admin.site.register(Post)
admin.site.register(friend_request)
admin.site.register(Comment)
admin.site.register(Friend)
admin.site.register(Notify)
admin.site.register(PostImages)
admin.site.register(Node)
