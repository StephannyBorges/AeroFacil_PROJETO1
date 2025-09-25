from django.shortcuts import render

# Create your views here.
# Importações do Django
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

# Importação dos seus modelos
from .models import Trip, Booking, Aircraft

# --- VIEWS PÚBLICAS (Acessíveis a todos) ---

class HomePageView(TemplateView):
    """
    View para a página inicial.
    Exibe as 5 próximas viagens abertas para negociação.
    """
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Busca as próximas 5 viagens que ainda não partiram e estão abertas
        context['upcoming_trips'] = Trip.objects.filter(
            status='OPEN',
            departure_time__gte=timezone.now()
        ).order_by('departure_time')[:5]
        return context

class TripListView(ListView):
    """
    View para listar e filtrar as viagens (resultados da busca).
    Filtra por origem, destino e data.
    """
    model = Trip
    template_name = 'resultados.html'
    context_object_name = 'trips'
    paginate_by = 10 # Mostra 10 viagens por página

    def get_queryset(self):
        queryset = Trip.objects.filter(status='OPEN', departure_time__gte=timezone.now())
        
        # Parâmetros da busca (vindos da URL, ex: ?origin=Natal)
        origin = self.request.GET.get('origin')
        destination = self.request.GET.get('destination')
        date = self.request.GET.get('date')

        if origin:
            queryset = queryset.filter(origin__icontains=origin)
        
        if destination:
            queryset = queryset.filter(destination__icontains=destination)
            
        if date:
            queryset = queryset.filter(departure_time__date=date)
            
        return queryset.order_by('departure_time')

class TripDetailView(DetailView):
    """
    View para mostrar os detalhes de uma única viagem.
    """
    model = Trip
    template_name = 'detalhes.html'
    context_object_name = 'trip'


# --- LÓGICA DE RESERVA (INTERESSE) ---

class CreateBookingView(LoginRequiredMixin, CreateView):
    """
    Cria um registro de "Booking" (interesse) para uma viagem.
    Acessível apenas por usuários logados.
    """
    model = Booking
    fields = ['seats_requested', 'message_to_owner'] # Campos que o usuário preenche
    template_name = 'create_booking.html' # Um template com o formulário de interesse

    def form_valid(self, form):
        trip = get_object_or_404(Trip, pk=self.kwargs['trip_pk'])
        
        # Impede o dono de reservar a própria viagem
        if trip.owner == self.request.user:
            messages.error(self.request, "Você não pode reservar um assento na sua própria viagem.")
            return redirect('trip_detail', pk=trip.pk)
            
        # Impede reservas duplicadas
        if Booking.objects.filter(trip=trip, passenger=self.request.user).exists():
            messages.warning(self.request, "Você já demonstrou interesse nesta viagem.")
            return redirect('trip_detail', pk=trip.pk)

        form.instance.passenger = self.request.user
        form.instance.trip = trip
        messages.success(self.request, "Seu interesse foi registrado com sucesso! O proprietário entrará em contato.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('trip_detail', kwargs={'pk': self.kwargs['trip_pk']})


# --- VIEWS DO PAINEL DO DONO (Protegidas por Login) ---

class DashboardView(LoginRequiredMixin, ListView):
    """
    Painel principal para o dono ver as viagens que ele ofereceu.
    """
    model = Trip
    template_name = 'dashboard.html'
    context_object_name = 'owner_trips'
    
    def get_queryset(self):
        # Retorna apenas as viagens do usuário logado
        return Trip.objects.filter(owner=self.request.user).order_by('-departure_time')

class TripCreateView(LoginRequiredMixin, CreateView):
    """
    Formulário para o dono criar uma nova oferta de viagem.
    """
    model = Trip
    template_name = 'trip_form.html'
    fields = ['aircraft', 'origin', 'destination', 'departure_time', 'arrival_time', 'available_seats', 'description']
    success_url = reverse_lazy('dashboard')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Limita o campo 'aircraft' para mostrar apenas as aeronaves do usuário logado
        form.fields['aircraft'].queryset = Aircraft.objects.filter(owner=self.request.user)
        return form

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Sua viagem foi anunciada com sucesso!")
        return super().form_valid(form)

class TripUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Formulário para o dono editar uma oferta de viagem.
    """
    model = Trip
    template_name = 'trip_form.html'
    fields = ['aircraft', 'origin', 'destination', 'departure_time', 'arrival_time', 'available_seats', 'description', 'status']
    success_url = reverse_lazy('dashboard')

    def test_func(self):
        # Garante que apenas o dono da viagem possa editá-la
        trip = self.get_object()
        return self.request.user == trip.owner

    def form_valid(self, form):
        messages.success(self.request, "Viagem atualizada com sucesso!")
        return super().form_valid(form)

class TripDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Página de confirmação para deletar uma oferta de viagem.
    """
    model = Trip
    template_name = 'trip_confirm_delete.html'
    success_url = reverse_lazy('dashboard')

    def test_func(self):
        # Garante que apenas o dono da viagem possa deletá-la
        trip = self.get_object()
        return self.request.user == trip.owner
    
    def form_valid(self, form):
        messages.success(self.request, "Viagem removida com sucesso.")
        return super().form_valid(form)