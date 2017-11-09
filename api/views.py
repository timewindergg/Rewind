from django.shortcuts import render
from django.http import JsonResponse

def test(request):
    return JsonResponse([{
        "id": "1",
        "username": "samsepi0l"
      }, {
        "id": "2",
        "username": "D0loresH4ze"
      }], safe=False)
