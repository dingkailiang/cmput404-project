from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404,HttpResponseForbidden
from django.views import View
from django.conf import settings
from .settings import MAXIMUM_PAGE_SIZE,HOST_NAME,PROJECT_ROOT
from django.shortcuts import render, get_object_or_404,get_list_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
import os
from .models import  Author,Post, friend_request, Comment,Notify,Friend,PostImages,Node
from .forms import ProfileForm,ImageForm,PostForm
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
import sys
import json
import uuid
import requests
import datetime
from rest_framework.views import APIView
from django.core import serializers
from rest_framework.response import Response
from rest_framework import mixins,generics, status, permissions
import base64
from .serializers import AuthorSerializer,PostSerializer,CommentSerializer,PostPagination,CommentPagination,AddCommentQuerySerializer
from rest_framework.decorators import api_view
from .permissions import IsAuthenticatedNodeOrAdmin
from collections import OrderedDict
from .settings import MAXIMUM_PAGE_SIZE,HOST_NAME
from .comment_functions import getNodeAuth,getNodeAPIPrefix,friend_relation_validation,author_id_parse






class Send_Friendrequest(LoginRequiredMixin, View):
    """
    send friend request to remote server or our own server
    """
    queryset = Notify.objects.all()

    def get_object(self, model, pk):
        try:
            result =  model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise Http404
        return result

    def post(self, request):
        # get the friend on remote server
        # r = requests.get('http://127.0.0.1:8000/service/author/diqiu') # for test
        friend_hostname = request.POST["friend_host"]
        if friend_hostname[len(friend_hostname)-1]=="/":
            friend_hostname = friend_hostname[0:len(friend_hostname)-1]
        if "/api" in friend_hostname :
            friend_hostname = friend_hostname[0:len(friend_hostname)-3]
        if "/service" in friend_hostname :
            friend_hostname = friend_hostname[0:len(friend_hostname)-8]
        # print friend_hostname
        # return
        # print(getNodeAuth(friend_hostname))
        admin_auth=getNodeAuth(friend_hostname)
        print ("================")
        print (admin_auth)
        if(admin_auth["success"]):
            admin_auth = admin_auth["auth"]
        else:
            print("Error! getting remote server auth",friend_hostname,admin_auth["messages"])
            return
        # print(admin_auth)
        # return
        r = requests.get(request.POST["friend_url"], auth=admin_auth)
        if r.status_code==200:
            remote_friend = r.json()
        else:
            print("Error! pulling author info from remote server",request.POST["friend_url"],r.status_code)
            return HttpResponse(r, status=r.status_code)
        # print(remote_friend)
        # return

        # get the author on our server
        user = self.get_object(User, request.user.id)
        author = Author.objects.get(user=request.user)
        serializer = AuthorSerializer(author)

        # combines the info
        remote_request = OrderedDict()
        remote_request["query"] = "friendrequest"
        remote_request["author"] = serializer.data
        remote_request["author"]['id'] = remote_request["author"]['url']
        remote_request["friend"] = remote_friend

        # send friend request to remote server
        # r = requests.post(remote_friend["host"]+'service/friendrequest', data = remote_request)
        print("sending request to",friend_hostname+getNodeAPIPrefix(friend_hostname)["api_prefix"]+'friendrequest/')
        # return
        r = requests.post(
            friend_hostname+getNodeAPIPrefix(friend_hostname)["api_prefix"]+'friendrequest/',
            json=remote_request,
            auth=admin_auth
        )

        # store the follow relationship if success
        # print(r.status_code)
        if (r.status_code==200 or r.status_code==201):
            # varify if there is already an exist friend requests
            varify_result = Friend.objects.all()
            varify_result = varify_result.filter(requestee=remote_friend["url"])
            varify_result = varify_result.filter(requestee_id=author_id_parse(remote_friend["id"]))
            varify_result = varify_result.filter(requester=author)

            if(len(varify_result)<1):
                new_friend = Friend.objects.create(requestee=remote_friend["url"], requestee_id=author_id_parse(remote_friend["id"]), requestee_host=remote_friend["host"], requestee_displayName=remote_friend["displayName"],requester=author)
                new_friend.save()

        # return HttpResponse(json.dumps(serializer.data), status=status.HTTP_200_OK)
        # return HttpResponse(json.dumps(remote_request), status=status.HTTP_200_OK)
        # return HttpResponse(r, status=r.status_code)
        return HttpResponseRedirect(reverse('home'))

def update():
    Post.objects.filter(temp=True).delete()
    for node in Node.objects.all():
        url = node.host+node.api_prefix+node.auth_post_url
        r = requests.get(url, auth=(node.auth_username, node.auth_password))
        if r.status_code == 200:

            # datajson = json.dumps(r.json())
            # datajson = json.loads(datajson)
            # postjson = datajson['posts']
            # serializer = PostSerializer(data=postjson,many=True)

            serializer = PostSerializer(data=r.json()['posts'],many=True)
            if serializer.is_valid():
                serializer.save()
            else:
                print(serializer.errors)
        else:
            print(r.status_code)

def can_see(post,author):
    if author.url in json.loads(post.visibleTo):
        return True
    if post.visibility == 'PRIVATE' and post.author != author:
        print("=======================\n",author.url, post.visibleTo)
        if author.url in post.visibleTo:
            return True
        return False
    if post.visibility == 'FRIENDS' and post.author != author:
        # print "==============="
        # print(post.author.url, post.author.host)
        # print "==============="
        friend_validation = friend_relation_validation(author.url, author.host, post.author.url, post.author.host)
        if friend_validation["success"] == True and friend_validation["friend_status"] == True:
            # a_remote_author["relationship"] = "friend"
            return True
        elif friend_validation["success"] == True and friend_validation["friend_status"] == False:
            # a_remote_author["relationship"] = "follow"
            # print("They are not friends",author.url, author.host, post.author.url, post.author.host)
            return False
        else:
            print("Error! friend validation:",friend_validation["messages"])
            return False

    return True

def prunning(posts,author):
    for post in posts.iterator():
        if not can_see(post,author):
            posts = posts.exclude(id =post.id)
    return posts

def home(request):
    update()
    form = PostForm()
    posts= Post.objects.filter(unlisted=False)

    viewer = None
    if(request.user.is_authenticated()):
        viewer = request.user.author
        posts = prunning(posts,viewer)
    else:
        posts = posts.filter(visibility='PUBLIC')
    author = viewer

    posts = posts.order_by('-published')

    notify = Notify.objects.filter(requestee=author)
    images = PostImages.objects.all()
    context = { 'posts': posts ,'form': form,'author':author,'Friend_request':notify,'images':images,'viewer':viewer}

    return render(request,'home.html',context)

def getFriendrequest(request):
    notify = Notify.objects.filter(requestee=request.user.author)


def stream(request,author_id):
    author = get_object_or_404(Author,pk=author_id)
    posts = Post.objects.filter(author=author).order_by('-published') | Post.objects.filter(visibility=3).order_by('-published')
    form = PostForm()
    visi = None
    images = PostImages.objects.all()
    context = { 'posts': posts ,'author':author,'form':form,'images':images, 'visi':visi}
    return render(request, 'self.html', context)


def profile(request,author_id):
    author = get_object_or_404(Author, pk=author_id)
    viewer = None
    if request.user.is_authenticated:
        viewer = request.user.author
    form = PostForm()
    if request.method == 'POST' and viewer.id == author.id:
        profile_form = ProfileForm(request.POST)
        image_form = ImageForm(request.POST,request.FILES)
        if profile_form.is_valid():
            author.displayName = profile_form.cleaned_data['displayName']
            author.user.email = profile_form.cleaned_data['email']
            author.github = profile_form.cleaned_data['github']
            author.bio = profile_form.cleaned_data['bio']
        else:
            print(profile_form.errors)
        if image_form.is_valid():
            author.img = image_form.cleaned_data['image']
        author.save()
        author.user.save()
    else:
        profile_form = ProfileForm()
    return render(request,'profile/profile.html',{'profile_form':profile_form,'form':form,'viewer':viewer,'author':author})


@login_required
def create_post_html(request):
    return render(request,'post/create_post.html',{'user':request.user})

# with open(settings.MEDIA_ROOT + "/images/" + str(datetime.datetime.now()) +str(count) ,'wb+') as destination:
#     for chunk in f.chunks():
#         destination.write(chunk)

@login_required
def create_post(request):
    """
    Create new post view
    """
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            data['id'] = uuid.uuid4()
            url = reverse("a_single_post_detail",kwargs={"post_id":data['id']})
            data['origin'] = HOST_NAME + url
            data['source'] = HOST_NAME + url
            new_post = Post.objects.create(author=request.user.author,**data)

            #https://www.youtube.com/watch?v=C9MDtQHwGYM
            for count,x in enumerate(request.FILES.getlist("files")):
                data['unlisted'] = True
                data['id'] = uuid.uuid4()
                new_post2 = Post.objects.create(author=request.user.author,**data)
                image = PostImages.objects.create(post=new_post2,post_image = x)
                image.save()

                new_post1 = Post.objects.get(id=new_post.id)

                path = image.post_image.url
                path = PROJECT_ROOT + path
                fp=open(path,'r+')
                # if post['contentType'] == 'image/png;base64':
                #     post['content'] = "data:image/png;base64, " + base64.b64encode(fp.read())
                # if post['contentType'] == 'image/jpeg;base64':
                #     post['content'] = "data:image/jpeg;base64, " + base64.b64encode(fp.read())

                new_post1.content = new_post1.content + '![](data:' + new_post1.contentType + ',' + base64.b64encode(fp.read()) + ')'
                new_post1.contentType = 'text/markdown'
                new_post1.save()





        else:
            print(form.errors)
            form = PostForm()
    return HttpResponseRedirect(reverse('home'))


@login_required
def manage_post(request):
    """
    post edit view
    """

    post = Post.objects.get(post_id=request.GET['post_id'])

    post_type = request.GET['post_type']

    return render(request,'post/manage_post.html',{'post':post, 'post_type2':post_type})

@login_required
def update_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save()
        else:
            print(form.errors)

    else:
        form = PostForm(instance=post)
    return HttpResponseRedirect(reverse('onePost',kwargs={'post_id':post_id,'author_id':post.author.id}))

# @login_required
# def update_post(request):
#     post = Post.objects.get(post_id=request.POST['post_id'])
#     new_post_text = request.POST['post_text']
#     new_can_view = request.POST['post_type']
#     new_post_type = request.POST['content_type']
#     post.post_text = new_post_text
#     post.can_view = new_can_view
#     post.post_type = new_post_type
#     post.save()

#     post_type2 = request.POST['post_type2']
#     # print post_type2
#     context = postContent(post_type2, request)
#     return render(request, 'stream/mystream.html', context)
#     #return HttpResponseRedirect(reverse('ViewMyStream'))

@login_required
def comment(request):
    if request.method == "POST":
        author = get_object_or_404(Author,pk=request.user.author.id)
        comment_text = request.POST['comment_text']
        comment_type = request.POST['content_type']
        post_id= request.POST['post_id']
        post = Post.objects.get(id = post_id)

        new_comment = Comment.objects.create(author=author,comment=comment_text,post=post,contentType=comment_type)

        host = post.author.host
        if host != HOST_NAME:
            data = OrderedDict()
            data['query'] = 'addComment'
            data['post'] = post.origin
            data['comment'] = CommentSerializer(instance=new_comment).data
            serializer = AddCommentQuerySerializer(data = data)
            if serializer.is_valid():
                if host[-1] == '/':
                    host = host[:-1]
                if "/api" in host:
                    host = host[0:len(host)-4]
                if "/service" in host :
                    host = host[0:len(host)-8]
                try:
                    node = Node.objects.get(host=host)
                except Node.DoesNotExist:
                    print(host + ' is not a conecting node')
                else:
                    newUrl = post.origin
                    if post.origin[len(post.origin)-1]=="/":
                        newUrl = post.origin[0:len(post.origin)-1]
                    #=======
                    newData = serializer.data
                    newData['comment']['author']['id'] = newData['comment']['author']['url']
                    print(newData)
                    r = requests.post(newUrl+'/comments/', auth=(node.auth_username, node.auth_password),json=newData)
                    #=======
                    #r = requests.post(newUrl+'/comments/', auth=(node.auth_username, node.auth_password),json=serializer.data)
                    if r.status_code//100 != 2:
                        print(r.status_code)
            else:
                print(serializer.errors)
    return HttpResponseRedirect(reverse('home'))
'''
def postContent(post_type,request):
    comments = Comment.objects.all()

    if str(post_type)== "my_post":
            post = Post.objects.filter(author = request.user).order_by('-published')

    elif str(post_type)=="public_post":
        post= Post.objects.filter(visibility=0).order_by('-published')

    elif str(post_type) == "friend_post":
        myFriends= Profile.objects.get(user = request.user).friends.all()
        posts = Post.objects.all()
        post = []
        for friend in myFriends:
            friend_instance= User.objects.get(username=friend)
            friendPost = posts.filter(author = friend_instance)
            for i in friendPost:
                if (i.visibility == 0) or (i.visibility==1):
                    post.append(i)
    else:
        post= Post.objects.filter(visibility=0).order_by('-published')

    context = { 'posts': post , 'comments': comments, 'post_type': post_type}

    return context
'''

# @login_required
# def ViewMyStream(request):
#     Posts = Post.objects.order_by('-published')
#     comments = Comment.objects.all()

#     post_type = request.GET['post_type']
#     context = postContent(post_type,request)
#     return render(request, 'stream/user_stream.html', context)

@login_required
def delete_post(request,author_id,post_id):
    post = get_object_or_404(Post,author=author_id,id = post_id)
    if request.user.author.id == author_id:
        post.delete()
    return HttpResponseRedirect(reverse('stream',kwargs={'author_id': author_id}))




@login_required
def Add_friend(request):
    request_sender_id = request.POST['request_sender']
    request_receiver_id = request.POST['request_receiver']
    request_sender = User.objects.get(id=request_sender_id)
    request_receiver = User.objects.get(id=request_receiver_id)
    status = False
    new_request = friend_request.create(request_sender,request_receiver,status)
    new_request.save()


    return HttpResponseRedirect(reverse('profile'))
@login_required
def list_my_friend_request(request):
    friend_requests = friend_request.objects.get(request_receiver=request.user)
    #friend_requests = friend_request.objects.all()

    return JsonResponse(friend_requests,safe=False)

@login_required
def accept_friend(request):
    request_f = friend_request.objects.get(request_id=request.POST['request_id'])
    request_f.status = True
    request_f.save()
    profile_for_requester = Profile.objects.get(user=request_f.request_sender)
    profile_for_requestee = Profile.objects.get(user=request_f.request_receiver)
    profile_for_requester.friends.add(profile_for_requestee)
    profile_for_requestee.friends.add(profile_for_requester)
    profile_for_requester.save()
    profile_for_requestee.save()
    #profile.friends.add(request.request_sender)



    return HttpResponseRedirect(reverse('profile'))



@login_required
def AcceptFriendRequest(request):
    decide = request.POST['decide']
    requester_id = request.POST['requester_id']
    author = Author.objects.get(user=request.user)
    notify = Notify.objects.get(requestee=author,requester_id=requester_id)
    if decide == "Decline" :
        notify.delete()
        return HttpResponseRedirect(reverse('friendList',kwargs={'author_id': request.user.author.id}))

    friend = Friend.objects.create(requester=author,requestee=notify.requester,requestee_id = notify.requester_id,requestee_host = notify.requester_host,requestee_displayName= notify.requester_displayName)
    notify.delete()
    friend.save()

    notify = Notify.objects.filter(requestee=author)
    context={'user':request.user,'form':PostForm(),'author':author,'Friend_request':notify}
    # return render(request,'friend/friendList.html',context)
    return HttpResponseRedirect(reverse('friendList',kwargs={'author_id': request.user.author.id}))

@login_required
def DeleteFriend(request):
    if request.method == "POST":
        author_id = request.POST["author_id"]

    friend = Friend.objects.get(requester= request.user.author, requestee_id= author_id_parse(author_id))
    if friend:
        friend.delete()
        print ("success")
    '''
    author_id= author.id
    requester = Author.objects.get(id= requester_id)
    friend = Friend.objects.get(requester= requester, requestee_id= author_id)
    if friend:
        friend.delete()
        print ("ssssssss")
    #notify = Notify.objects.get(requestee=author,requester_id=requester_id)
    #friend = Friend.objects.create(requester=author,requestee=notify.requester,requestee_id = notify.requester_id)
    #notify.delete()
    #friend.save()
    '''
    #notify = Notify.objects.filter(requestee=author)
    context={'user':request.user,'form':PostForm()}
    # return render(request,'friend/friendList.html',context)
    return HttpResponseRedirect(reverse('friendList',kwargs={'author_id': request.user.author.id}))



def viewUnlistedPost(request, post_id):
    post = get_object_or_404(Post,pk = post_id)
    author = post.author
    viewer = None
    if request.user.is_authenticated:
        viewer = request.user.author
    form = PostForm()
    post.categories = '#'.join(json.loads(post.categories))
    post.visibleTo = ';'.join(json.loads(post.visibleTo))
    images = PostImages.objects.filter(post=post)
    context = {'post':post,'author':author,'form':form,'viewer':viewer,'images':images}
    return render(request,'post/shared_post.html',context)

### reference by: http://brainstorm.it/snippets/get_object_or_404-for-uuids/
def get_object_by_uuid_or_404(model, uuid_pk):
    """
    Calls get_object_or_404(model, pk=uuid_pk)
    but also prevents "badly formed hexadecimal UUID string" unhandled exception
    """
    try:
        uuid.UUID(uuid_pk)
    except Exception as e:
        raise Http404(str(e))
    return get_object_or_404(model, pk=uuid_pk)

@login_required
def friend_request_list(request):
    author = request.user.author
    friend_requests = author.notify.all()
    friend_requests = serializers.serialize('json',friend_requests)

    return JsonResponse(friend_requests,safe=False)

def friendList(request,author_id):
    author = Author.objects.get(pk=author_id)
    friend_requests = author.notify.all()

    viewer = None
    if request.user.is_authenticated:
        viewer = request.user.author

    following_list = author.follow.all()
    following_detail_list = []
    for f_author in following_list:
        # get the authentication of node
        # print(f_author.requester.host)
        admin_auth=getNodeAuth(f_author.requestee_host)
        if admin_auth["success"]:
            admin_auth = admin_auth["auth"]
        else:
            print(admin_auth["messages"])
            continue

        # get remote author info thr API
        # print(f_author.requestee, admin_auth)
        # return
        r = requests.get(f_author.requestee, auth=admin_auth)
        if r.status_code==200:
            a_remote_author = OrderedDict()
            a_remote_author = r.json()
        else:
            print("Error! getting author info from remote server",f_author.requestee, r.status_code)
            continue

        friend_validation = friend_relation_validation(author.url, author.host, a_remote_author["url"], a_remote_author["host"])
        if friend_validation["success"] == True and friend_validation["friend_status"] == True:
            a_remote_author["relationship"] = "friend"
        elif friend_validation["success"] == True and friend_validation["friend_status"] == False:
            a_remote_author["relationship"] = "follow"
        else:
            print(friend_validation["messages"])
            continue

        """
        # get remote author's following list
        r = requests.get(f_author.requestee+'/friends', auth=admin_auth)
        if r.status_code==200:
            remote_author_following_list = r.json()
            # print(remote_author_following_list)
            if author_id in remote_author_following_list["authors"]:
                # they are friend
                a_remote_author["relationship"] = "friend"
            else:
                a_remote_author["relationship"] = "follow"
            following_detail_list.append(a_remote_author)
        else:
            continue
        """
        following_detail_list.append(a_remote_author)

    context = {
        'author':author,
        'form':PostForm(),
        'viewer':viewer,
        'friend_requests':friend_requests,
        'following_list':following_detail_list
    }

    #,'Friend':friends,'Followed':follows
    return render(request,'friend/friendList.html',context)

def onePost(request,author_id,post_id):
	post = get_object_or_404(Post,pk = post_id,author=author_id)
	author = get_object_or_404(Author,pk = author_id)
	viewer = None
	if request.user.is_authenticated:
	    viewer = request.user.author
	form = PostForm()
	post.categories = '#'.join(json.loads(post.categories))
	post.visibleTo = ';'.join(json.loads(post.visibleTo))
	context = {'post':post,'author':author,'form':form,'viewer':viewer}
	return render(request,'post/onePost.html',context)
