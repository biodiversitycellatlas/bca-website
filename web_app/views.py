from django.shortcuts import render


def index(request):
	return render(request, "web_app/index.html")


def atlas(request):
    return render(request, "web_app/atlas.html")


def markers(request):
    return render(request, "web_app/markers.html")


def comparison(request):
    return render(request, "web_app/comparison.html")


def downloads(request):
    return render(request, "web_app/downloads.html")


def blog(request):
    return render(request, "web_app/blog.html")


def about(request):
    return render(request, "web_app/about.html")