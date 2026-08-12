from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Event


def event_list(request):
    now = timezone.now()
    upcoming_events = Event.objects.filter(start_time__gte=now).order_by('start_time')
    past_events = Event.objects.filter(start_time__lt=now).order_by('-start_time')[:5]
    
    context = {
        'upcoming_events': upcoming_events,
        'past_events': past_events,
    }
    return render(request, 'content/event_list.html', context)


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return render(request, 'content/event_detail.html', {'event': event})