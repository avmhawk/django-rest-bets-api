# encoding: utf-8
from django.db import transaction
from django.contrib.auth.models import User, Group
from rest_framework import serializers

import bets.models as bets_models  # import Customer, Wallet, Transaction, Team, Game, Bet,


class WalletSerializer(serializers.ModelSerializer):
    """Wallet seralization"""

    class Meta:
        model = bets_models.Wallet
        fields = ('balance', )


# TODO: поботать что такое HyperlinkedModelSerializer и чем от ModelSerializer отличается
class ProfileSerializer(serializers.ModelSerializer):
    wallet = WalletSerializer()

    class Meta:
        model = bets_models.Profile
        fields = ('wallet',)


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)
    # ?:
    # bets_created = serializers.HyperlinkedRelatedField(view_name='bet-list', many=True, read_only=True)
    # bets_contributed = serializers.HyperlinkedRelatedField(view_name='bet-list', many=True, read_only=True)

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'profile')  # , 'bets_created', 'bets_contributed')n


class UserField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return UserSerializer(value).data

    def use_pk_only_optimization(self):
        return False


class DepositeToSerializer(serializers.Serializer):
    deposite = serializers.DecimalField(
        max_digits=22, decimal_places=10, validators=(bets_models.not_negative_value_validator,)
    )

    class Meta:
        fields = ('deposite', )


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class TeamSerializer(serializers.ModelSerializer):
    """Team"""

    class Meta:
        model = bets_models.Team
        fields = ('name', 'is_active', 'description')


class TeamField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return TeamSerializer(value).data

    def use_pk_only_optimization(self):
        return False


class GameSerializer(serializers.ModelSerializer):
    """Game"""
    team_first = TeamField(queryset=bets_models.Team.objects.all(), required=True)
    team_second = TeamField(queryset=bets_models.Team.objects.all(), required=True)
    # с полями джанго не умеет
    winner = TeamField(queryset=bets_models.Team.objects.all(), required=False)
    # winner = TeamSerializer(required=False)

    class Meta:
        model = bets_models.Game
        fields = (
            'team_first',
            'team_second',
            'status',
            'winner'
        )

    def validate_winner(self, value):
        if not value:
            return
        return value.id in {self.team_first.id, self.team_second.id}


class GameField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return GameSerializer(value).data

    def use_pk_only_optimization(self):
        return False


class BetSerializer(serializers.ModelSerializer):
    """Bet"""
    game = GameField(queryset=bets_models.Game.objects.all(), required=True)
    betted_on = TeamField(queryset=bets_models.Team.objects.all(), required=True)
    creator = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    contributor = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    wallet = WalletSerializer(required=False, read_only=True)
    bet_value = serializers.DecimalField(max_digits=22, decimal_places=10, required=True)
    # TODO: добавить контекст, в list оставить только game, betted_on, creator_id, contr_id

    class Meta:
        model = bets_models.Bet
        fields = (
            'game',
            'betted_on',
            'bet_value',
            'creator',
            'contributor',
            'status',
            'wallet',
        )

    # def to_internal_value(self, data):
    # @transaction.atomic()
    def create(self, validated_data):
        TRANSACTION_TYPE = 'be'
        # creator = User.objects.get(pk=validated_data['creator'])
        value = validated_data['bet_value']
        wallet_from = validated_data['creator'].profile.wallet
        wallet_to = bets_models.Wallet.objects.create()

        bets_models.Transaction.send(value, TRANSACTION_TYPE, wallet_to, wallet_from)
        validated_data['wallet'] = wallet_to

        return bets_models.Bet.objects.create(**validated_data)

    # @transaction.atomic()
    def update(self, instance, validated_data):
        TRANSACTION_TYPE = 'be'

        if 'contributor' in validated_data:
            value = instance.bet_value
            wallet_to = instance.wallet
            wallet_from = validated_data.contributor.profile.wallet

            bets_models.Transaction.send(value, TRANSACTION_TYPE, wallet_to, wallet_from)
            instance.contributor = validated_data['contributor']
            instance.save()

        if 'cancel' in validated_data:
            instance.close()

        return instance

    # @transaction.atomic()
    def player_validation(self, data):
        pass

    def cancel_validation(self, data):
        # ставку можно отменить, если еще нет оппонента
        pass

    # def validate(self, data):
    #     super().validate(data)
    #     print(data)
    #     print(validate)
    #     return False


# def game_is_active_validator(value):
#     game = Game.objects.get(pk=value)
#     if game.status not in ('new', 'act'):
#         raise serializers.ValidationError('Game is {0}'.format(game.status))
