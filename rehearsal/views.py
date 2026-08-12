from django.shortcuts import render, get_object_or_404
from .models import ChoirMember, RehearsalSession


def rehearsal_list(request):
    sessions = RehearsalSession.objects.all()
    members_by_part = {
        'Soprano': ChoirMember.objects.filter(voice_part='soprano', is_active=True),
        'Alto': ChoirMember.objects.filter(voice_part='alto', is_active=True),
        'Tenor': ChoirMember.objects.filter(voice_part='tenor', is_active=True),
        'Bass': ChoirMember.objects.filter(voice_part='bass', is_active=True),
    }
    
    context = {
        'sessions': sessions,
        'members_by_part': members_by_part,
    }
    return render(request, 'rehearsal/rehearsal_list.html', context)


def rehearsal_detail(request, pk):
    session = get_object_or_404(RehearsalSession, pk=pk)
    return render(request, 'rehearsal/rehearsal_detail.html', {'session': session})