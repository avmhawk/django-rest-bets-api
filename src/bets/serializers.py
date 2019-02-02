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
    bets_created = serializers.HyperlinkedRelatedField(view_name='bet-list', many=True, read_only=True)
    bets_contributed = serializers.HyperlinkedRelatedField(view_name='bet-list', many=True, read_only=True)

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'profile', 'bets_created', 'bets_contributed')

    # def create(self, validated_data):
    #     # profile_data = validated_data.pop('profile')
    #     user = User.objects.create(**validated_data)
    #     # Profile.objects.create(user=user, **profile_data)
    #     return user

    # def update(self, validated_data):
    #     return


class UserField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return UserSerializer(value).data


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


# class CustomerSerializer(serializers.ModelSerializer):
#     """Customer(User with Wallet) serialization"""

#     wallet = WalletSerializer()
#     user = UserSerializer()
#     # (many=True, queryset=bets_models.Bet.objects.all())
#     bets_created = serializers.HyperlinkedRelatedField(view_name='bet-list', many=True, read_only=True)
#     bets_contributed = serializers.HyperlinkedRelatedField(view_name='bet-list', many=True, read_only=True)

#     class Meta:
#         model = bets_models.Customer
#         fields = (
#             'user',
#             'wallet',
#             'bets_created',
#             'bets_contributed'
#         )


class TeamSerializer(serializers.ModelSerializer):
    """Team"""

    class Meta:
        model = bets_models.Team
        fields = (
            'name',
            'is_active',
            'description'
        )


class TeamField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return TeamSerializer(value).data


class GameSerializer(serializers.ModelSerializer):
    """Game"""
    team_first = TeamSerializer()
    team_second = TeamSerializer()
    winner = TeamSerializer()

    class Meta:
        model = bets_models.Game
        fields = (
            'team_first',
            'team_second',
            'status',
            'winner'
        )


class GameField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return GameSerializer(value).data


class BetSerializer(serializers.ModelSerializer):
    """Bet"""
    game = GameField(queryset=bets_models.Game.objects.all())
    betted_on = TeamField(queryset=bets_models.Team.objects.all(), required=True)
    creator = UserField(queryset=bets_models.User.objects.all(), required=True)
    contributor = UserField(queryset=bets_models.User.objects.all(), required=False)
    wallet = WalletSerializer(required=False)

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
    @transaction.atomic()
    def create(self, validated_data):
        TRANSACTION_TYPE = 'be'

        value = validated_data['betted_on']
        wallet_from = validated_data.creator.profile.wallet
        wallet_to = bets_models.Wallet.objects.create()

        bets_models.Transaction.send(value, TRANSACTION_TYPE, wallet_to, wallet_from)
        validated_data['wallet'] = wallet_to

        return bets_models.Bet.create(**validated_data)

    @transaction.atomic()
    def update(self, instnance, validated_data):
        TRANSACTION_TYPE = 'be'
        value = self.betted_on
        wallet_to = self.wallet

        wallet_from = validated_data.contributor.profile.wallet
        bets_models.Transaction.send(value, TRANSACTION_TYPE, wallet_to, wallet_from)

        return self.update(contributor=validated_data.contributor)

    @transaction.atomic()
    def player_validation(self, data):
        pass

    def cancel_validation(self, data):
        # ставку можно отменить, если еще нет оппонента
        pass

    def validate(self, data):
        super().validate(data)
        print(data)
    #     print(validate)
    #     return False


# def game_is_active_validator(value):
#     game = Game.objects.get(pk=value)
#     if game.status not in ('new', 'act'):
#         raise serializers.ValidationError('Game is {0}'.format(game.status))
