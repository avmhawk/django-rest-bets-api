from django.contrib.auth.models import User, Group
from rest_framework import viewsets, permissions, decorators, status, response
import bets.serializers as bets_serializers  # UserSerializer, GroupSerializer, GameSerializer
from bets.models import Game, Team, Bet, Transaction, Wallet


# TODO: вынести в permissions:
class ReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = bets_serializers.UserSerializer
    # permission_classes = [IsAccountAdminOrReadOnly]

    @decorators.action(detail=True, methods=['post'], permission_classes=(permissions.IsAdminUser,))
    def create_bet(self, request, pk=None, format=None):
        data = request.data
        data['creator'] = User.objects.get(pk)
        serializer = bets_serializers.BetSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(detail=True, methods=['put'], permission_classes=(permissions.IsAdminUser,))
    def deposite_to(self, request, pk=None, format=None):
        print(pk)
        user = User.objects.get(pk=pk)
        print(pk, user)
        print(pk, user.profile)
        print(user.profile.wallet)
        # TODO: проверки м ошибки
        data = request.data
        data['wallet'] = user.profile.wallet

        serializer = bets_serializers.DepositeToSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all().order_by('-created_at')
    serializer_class = bets_serializers.WalletSerializer

    permission_classes = (permissions.IsAdminUser, )


# class SnippetDetail(APIView):
#     """
#     Retrieve, update or delete a snippet instance.
#     """
#     def get_object(self, pk):
#         try:
#             return Snippet.objects.get(pk=pk)
#         except Snippet.DoesNotExist:
#             raise Http404

#     def get(self, request, pk, format=None):
#         snippet = self.get_object(pk)
#         serializer = SnippetSerializer(snippet)
#         return Response(serializer.data)

#     def put(self, request, pk, format=None):
#         snippet = self.get_object(pk)
#         serializer = SnippetSerializer(snippet, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def delete(self, request, pk, format=None):
#         snippet = self.get_object(pk)
#         snippet.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = bets_serializers.GroupSerializer


# class CustomerViewSet(viewsets.ModelViewSet):
#     """
#     API endpoint that allows users to be viewed or edited.
#     """
#     queryset = Customer.objects.all()  # .order_by('-date_joined')
#     serializer_class = bets_serializers.CustomerSerializer


class TeamViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows teams to be viewed or edited.
    """
    queryset = Team.objects.all()  # .order_by('-date_joined')
    serializer_class = bets_serializers.TeamSerializer
    # permission_classes = (permissions.IsAdminUser|ReadOnly, )


class GameViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows games to be viewed or edited by admins.
    """
    queryset = Game.objects.all()
    serializer_class = bets_serializers.GameSerializer
    # permission_classes = (permissions.IsAdminUser|ReadOnly, )

    @decorators.action(detail=True, methods=['put'], permission_classes=(permissions.IsAdminUser,))
    def cancel_game(self, request, pk=None, format=None):
        pass

    @decorators.action(detail=True, methods=['put'], permission_classes=(permissions.IsAdminUser,))
    def set_winner(self, request, pk=None, format=None):
        game = self.get_object(pk)
        serializer = bets_serializers.GameSerializer(game, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BetsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows bets to be viewed or edited.
    """
    queryset = Bet.objects.all()
    serializer_class = bets_serializers.BetSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, )

    # @decorators.action(detail=True, methods=['post'], permission_classes=(permissions.IsAuthenticatedOrReadOnly,))
    def create(self, request):
        # creator = request.user
        data = request.data
        data['creator'] = request.user
        serializer = bets_serializers.BetSerializer(data=request.data)

        if serializer.is_valid():
            print(serializer.data)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
