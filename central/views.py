from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def seleccionar_modulo(request):
    return render(request, 'central/modulo_selector.html')
