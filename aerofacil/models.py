from django.db import models

# Create your models here.
# Importações necessárias do Django
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

# --- 1. MODELO DE USUÁRIO ---
# Estendemos o usuário padrão do Django para adicionar campos específicos.
class User(AbstractUser):
    """
    Modelo de Usuário customizado. Pode ser um passageiro ou um dono de aeronave.
    """
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, verbose_name="Foto de Perfil")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Número de Telefone")
    is_owner = models.BooleanField(default=False, verbose_name="É Dono de Aeronave?")

    def __str__(self):
        return self.get_full_name() or self.username

# --- 2. MODELO DE AERONAVE ---
# Armazena os detalhes das aeronaves que um dono possui.
class Aircraft(models.Model):
    """
    Representa uma aeronave pertencente a um usuário dono.
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='aircrafts', verbose_name="Proprietário")
    model_name = models.CharField(max_length=100, verbose_name="Modelo da Aeronave")
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)], verbose_name="Capacidade de Passageiros")
    photo = models.ImageField(upload_to='aircraft_pics/', null=True, blank=True, verbose_name="Foto da Aeronave")

    class Meta:
        verbose_name = "Aeronave"
        verbose_name_plural = "Aeronaves"

    def __str__(self):
        return f"{self.model_name} ({self.owner.username})"

# --- 3. MODELO DE VIAGEM (A "CARONA") ---
# O registro principal do sistema, representando a oferta de uma viagem.
class Trip(models.Model):
    """
    Representa a oferta de uma "carona" (viagem) de um ponto a outro.
    """
    STATUS_CHOICES = [
        ('OPEN', 'Aberta para negociação'),
        ('CLOSED', 'Fechada'),
        ('COMPLETED', 'Concluída'),
        ('CANCELLED', 'Cancelada'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips_offered', verbose_name="Dono da Viagem")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name='trips', verbose_name="Aeronave Utilizada")
    
    origin = models.CharField(max_length=100, verbose_name="Origem")
    destination = models.CharField(max_length=100, verbose_name="Destino")
    
    departure_time = models.DateTimeField(verbose_name="Data e Hora da Partida")
    arrival_time = models.DateTimeField(verbose_name="Data e Hora da Chegada (Estimada)")
    
    available_seats = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name="Assentos Disponíveis")
    description = models.TextField(blank=True, verbose_name="Descrição da Viagem")
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN', verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Viagem"
        verbose_name_plural = "Viagens"
        ordering = ['-departure_time']

    def __str__(self):
        return f"{self.origin} -> {self.destination} em {self.departure_time.strftime('%d/%m/%Y %H:%M')}"

# --- 4. MODELO DE RESERVA/INTERESSE ---
# Registra o interesse de um passageiro em uma viagem específica.
class Booking(models.Model):
    """
    Representa o interesse (reserva) de um passageiro em uma viagem.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('CONFIRMED', 'Confirmada pelo Dono'),
        ('REJECTED', 'Rejeitada pelo Dono'),
        ('CANCELLED', 'Cancelada pelo Passageiro'),
    ]
    
    passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', verbose_name="Passageiro")
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='bookings', verbose_name="Viagem")
    
    seats_requested = models.PositiveIntegerField(default=1, verbose_name="Assentos Solicitados")
    message_to_owner = models.TextField(blank=True, verbose_name="Mensagem para o Dono")
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Interesse de Reserva"
        verbose_name_plural = "Interesses de Reserva"
        # Garante que um passageiro só possa se inscrever uma vez por viagem
        unique_together = ('passenger', 'trip')

    def __str__(self):
        return f"Interesse de {self.passenger.username} na viagem {self.trip.id}"

# --- 5. MODELO DE AVALIAÇÃO ---
# Permite que um passageiro avalie uma viagem após sua conclusão.
class Review(models.Model):
    """
    Armazena a avaliação de uma viagem feita por um passageiro.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='reviews', verbose_name="Viagem")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given', verbose_name="Avaliador")
    
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Nota (1-5)")
    comment = models.TextField(blank=True, verbose_name="Comentário")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"
        unique_together = ('trip', 'reviewer')

    def __str__(self):
        return f"Avaliação de {self.reviewer.username} para a viagem {self.trip.id} - Nota: {self.rating}"