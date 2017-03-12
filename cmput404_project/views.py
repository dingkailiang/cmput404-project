from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import os
from .models import Profile, Post
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
import sys

'''
def reg_complete(request):
    return render(request, 'registration/registration_complete.html' ,{'what':'Reg Completed!'})
'''

@login_required
def home(request):
    return HttpResponseRedirect(reverse('profile'))

@login_required
def profile(request):
    try:
        profile = Profile.objects.get(user_id=request.user.id)
        user = User.objects.get(id=request.user.id)
    except (KeyError, Profile.DoesNotExist):
        # profile no found create new
        profile = Profile.create(request.user)
        profile.save()
    else:
        # print profile
        pass

    return render(request,'profile/profile.html',{'user':request.user, 'request_by':request.user})

def view_profile(request, username):
    user = get_object_or_404(User, username=username)
    # profile = Profile.objects.get(user_id=user.id)
    print(username)

    return render(request,'profile/profile.html',{'user':user, 'request_by':request.user})

@login_required
def profile_edit(request):
    """
    Profile edit view

    """

    try:
        profile = Profile.objects.get(user_id=request.user.id)
    except (KeyError, Profile.DoesNotExist):
        # profile no found create new
        profile = Profile.create(request.user)
        profile.save()
    else:
        # print profile
        pass

    return render(request,'profile/profile_edit.html',{'user':request.user})


@login_required
def profile_update(request):
    """
    POST handler for profile update

    """

    try:
        profile = Profile.objects.get(user_id=request.user.id)
        user = User.objects.get(id=request.user.id)
    except (KeyError, Profile.DoesNotExist):
        # profile no found create new
        profile = Profile.create(request.user)
    else:
        # print profile
        pass

    user.email = request.POST['user_email']
    user.save()
    profile.github = request.POST['github']
    profile.bio = request.POST['bio']
    profile.save()

    return HttpResponseRedirect(reverse('profile'))

@login_required
def create_post_html(request):
    return render(request,'post/create_post.html',{'user':request.user})

# @login_required
def view_all_posts(request):
    Posts = Post.objects.filter(can_view=0).order_by('-pub_datetime')
    context = { 'posts':Posts}
    return render(request,'post/view_all_posts.html',context)

@login_required
def create_post(request):
    """
    Create new post view

    """

    user = User.objects.get(id=request.user.id)
    can_view = request.POST['post_type']
    post_text = request.POST['POST_TEXT']
    new_post = Post.create(request.user,post_text,can_view)
    #==========
       #image = request.FILES['file']
       #new_post = Post.create(request.user,post_text,can_view,image)
    #=========
    new_post.save()

    return HttpResponseRedirect(reverse('profile'))

    # new_post = Post.create(request.user,"a new one")
    # new_post.save()
    #
    # return HttpResponseRedirect(reverse('profile'))

@login_required
def ViewMyStream(request):
    Posts = Post.objects.filter(author=request.user.id).order_by('-pub_datetime')
    context = { 'posts': Posts }

    return render(request, 'stream/mystream.html', context)

@login_required
def delete_post(request):
    myPost = request.GET['post_id']
    allPost = Post.objects.all()
    for i in allPost:
        if (str(i.post_id) == str(myPost)):
            i.delete()
    return HttpResponseRedirect(reverse('ViewMyStream'))
