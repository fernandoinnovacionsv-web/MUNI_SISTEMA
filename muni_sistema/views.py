from django.shortcuts import render

def seleccionar_modulo(request):
    return render(request, 'modulo_selector.html')
