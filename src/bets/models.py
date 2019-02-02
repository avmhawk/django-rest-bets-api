# encoding: utf-8
from django.db import transaction
from django.utils.timezone import now
from decimal import Decimal
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
# TODO: вынести валидаторы в отдельный файл:
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


def not_negative_value_validator(value):
    if value < 0:
        raise ValidationError('{0} is not greater than or equal to zero'.format(value))


def game_is_active_validator(value):
    game = Game.objects.get(pk=value)
    if game.status not in ('new', 'act'):
        raise ValidationError('Game is {0}'.format(game.status))


# Create your models here.
class Wallet(models.Model):
    # Везде используем DecimalField с точностью до 10го знака, в качестве полей для финансовой информации,
    # это упрощенная модель, продуктовая реализация делается по "банковскому стандарту" (вроде Сбер и ЦБ используют):
    # - Финансовые данные кладутся в BIGINT-ы, используется 37 знаков - 15 на целую часть, 22 на дробную,
    # - операции производять с числами вида: int(currency_value * 10**22) и хранить
    # - перед отправкой пользователю для показа данные "приводятся" обратным преобразованием и округлением до 2 знака
    # решение быстрое(любой "точные" тип данных с float-point априори медленный), не подвержено ошибкам округления и вообще True
    # но это, только если время будет.
    balance = models.DecimalField(max_digits=22, decimal_places=10, default=0, validators=[not_negative_value_validator])
    # currency - на потом
    is_active = models.BooleanField(default=True)  # возможно True
    # TODO: по хорошему надо добавить в миграцию restriction на единственность
    is_company_wallet = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=now, editable=False)
    # вторая очередь, можно реализовать схему, в которой будет понятно, как пользователь закидывал средства на счет:
    # is_terminal_wallet = models.BooleanField(default=False)

    # def withdraw(self, value):
    #     if not self.is_active or self.balance < value:
    #         raise 'unable to create transaction - not enough money'

    # TODO: подумать, во вторую очередь - нужно ли нам такое:
    # class Meta:
    #     verbose_name = 'Money wallet'
    #     verbose_name_plural = 'Money wallets'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    wallet = models.OneToOneField(Wallet, on_delete=models.CASCADE)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        wallet = Wallet.objects.create()
        Profile.objects.create(user=instance, wallet=wallet)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Transaction(models.Model):
    # TODO: BET = 'be', (BET, 0)...(BET, 'bet')
    TRANSACTION_COMISSIONS = (
        ('co', Decimal(0)),
        ('be', Decimal(0)),
        ('de', Decimal(0)),
        ('re', Decimal(0)),
        ('ga', Decimal(0.03))
    )
    TRANSACTION_TYPES = (
        # техническая "комиссионная транзакция", всегда должна идти с comission=0(иначе рекурсия),
        # возникает, если у любой другой транзакции была выставлена комиссия
        ('co', 'comission'),
        ('be', 'bet'),  # транзакция при создании "спора"
        ('de', 'deposit'),  # транзакция на пополнение счета пользователя
        ('re', 'refund'),  # возврат средств, если что-то пошло не так
        ('ga', 'gain'),  # выплата выигрыша
    )
    # TODO: подумать в сторону создания "бесконечного", служебного кошелька для транзакций,
    # пока реализована возможность кидать на кошелек пользователя "из ниоткуда":
    value = models.DecimalField(max_digits=22, decimal_places=10, default=0, validators=[not_negative_value_validator])
    type = models.CharField(choices=TRANSACTION_TYPES, max_length=2)
    wallet_from = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=True, blank=True, related_name='transaction_wallets_from')
    wallet_to = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transaction_wallets_to')
    # comission - логика зашита в тип транзакции, система менее гибкая, во вторую очередь можно завести
    # модельку Comissions, в которой прописать - пользователь, тип транзакции(по хорошему тоже отдельная моделька),
    # и персональная комиссия, если таковая отличается от дефолтной(!)

    created_at = models.DateTimeField(default=now, editable=False)

    @classmethod
    def deposit(cls, wallet_to, value):
        pass

    @transaction.atomic()
    @classmethod
    def send(cls, value, transaction_tyoe, wallet_to, wallet_from=None):
        value = cls.__hold_comission(wallet_from, value)
        wallet_from.balance -= value
        wallet_from.save()

        wallet_to.balance += value
        wallet_to.save()

    @classmethod
    def __hold_comission(cls, wallet_from, value, transaction_type):
        company_wallet = Wallet.objects.get(is_company_wallet=True)

        comission_percent = cls.TRANSACTION_COMISSIONS[transaction_type]
        if not comission_percent:
            return value

        comission = value * comission_percent
        transfer_value = value - comission

        cls.objects.create(value=comission, type='co', wallet_from=wallet_from, wallet_to=company_wallet)

        return transfer_value


class Team(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)  # возможно True
    description = models.TextField(blank=True)
    # location  # вторая очередь
    created_at = models.DateTimeField(default=now, editable=False)


class Game(models.Model):
    GAME_STATUSES = (
        ('await', 'Awaiting'),  # показывается, можно делать ставки
        ('start', 'Started'),  # ставки делать уже низя. показывать или нет - по желанию
        ('ended', 'Ended'),  # закончился, всем прилетели выигрыши
        ('cancl', 'Cancelled')  # отменили, мутки-мутные, всем возращаем их бабло.
    )
    team_first = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='game_teams_first')
    team_second = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='game_teams_second')
    status = models.CharField(choices=GAME_STATUSES, max_length=5, default='await')
    # по идее, если ничья, то поле остается None, а статус ended, если status=cancelled был проставлен после status=ended
    # то надо откатывать все транзакции и возвращать игрокам деньги.
    winner = models.ForeignKey(Team, on_delete=models.CASCADE, blank=True, null=True, related_name='game_winners')
    # не первой очередью, но надо впилить, чтобы ставки нельзя было делать
    # после начала матча!
    # begin_at
    # end_at

    created_at = models.DateTimeField(default=now, editable=False)

    # class Meta:
    #     verbose_name = 'Game'
    #     verbose_name_plural = 'Games'


class Bet(models.Model):
    BET_STATUSES = (
        ('new', 'New'),
        ('act', 'Active'),
        ('cls', 'Closed'),
        ('cnl', 'Cancelled')
    )
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    betted_on = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='teams_betted_on')
    # избыточно, так как можем считать по балансу, но это усложнение
    bet_value = models.DecimalField(max_digits=22, decimal_places=10, validators=[MinValueValidator(0)])
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bets_created')
    contributor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='bets_contributed')
    status = models.CharField(choices=BET_STATUSES, max_length=3, default='new')
    # OneToOne (ставка всегда связана с одним кошельком, как и пользователь)
    # wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    wallet = models.OneToOneField(Wallet, on_delete=models.CASCADE)

    created_at = models.DateTimeField(default=now, editable=False)