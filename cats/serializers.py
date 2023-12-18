from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

import datetime as dt

from .models import CHOICES, Achievement, AchievementCat, Cat, User


class UserSerializer(serializers.ModelSerializer):
    cats = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'cats')
        ref_name = 'ReadOnlyUsers'


class AchievementSerializer(serializers.ModelSerializer):
    achievement_name = serializers.CharField(source='name')

    class Meta:
        model = Achievement
        fields = ('id', 'achievement_name')


class CatSerializer(serializers.ModelSerializer):
    achievements = AchievementSerializer(many=True, required=False)
    color = serializers.ChoiceField(choices=CHOICES)
    # owner = serializers.PrimaryKeyRelatedField(read_only=True)

    # В этом случае поле owner всегда будет присутствовать
    # в словаре validated_data (и больше нет необходимости передавать
    # его значение в метод save() во вьюсете), но его нельзя будет использовать
    # в ответах сериализатора, даже если это поле будет явно указано в списке
    # необходимых полей: оно скрытое, такие поля не попадают в ответ.
    # owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    # Поле owner может быть использовано на выходе сериализатора,
    # но без передачи его значения в метод save() во вьюсете
    # тут уже не обойтись.
    owner = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )
    age = serializers.SerializerMethodField()

    class Meta:
        model = Cat
        fields = ('id', 'name', 'color', 'birth_year', 'achievements', 'owner',
                  'age')
        read_only_fields = ('owner',)
        validators = [
            # класс UniqueTogetherValidator всегда накладывает неявное
            # ограничение: все поля сериализатора, к которым применён
            # этот валидатор, обрабатываются как обязательные.
            # Поля со значением default — исключение:
            # они всегда предоставляют значение, даже если пользователь
            # не передал их в запросе.
            UniqueTogetherValidator(
                queryset=Cat.objects.all(),
                fields=('name', 'owner')
            )
        ]

    def get_age(self, obj):
        return dt.datetime.now().year - obj.birth_year

    def create(self, validated_data):
        if 'achievements' not in self.initial_data:  # type: ignore
            cat = Cat.objects.create(**validated_data)
            return cat
        else:
            achievements = validated_data.pop('achievements')
            cat = Cat.objects.create(**validated_data)
            for achievement in achievements:
                current_achievement, status = (
                    Achievement.objects.get_or_create(
                        **achievement)
                )
                AchievementCat.objects.create(
                    achievement=current_achievement, cat=cat)
            return cat

    def validate_birth_year(self, value):
        year = dt.date.today().year
        if not (year - 40 < value <= year):
            raise serializers.ValidationError('Проверьте год рождения!')
        return value

    def validate(self, data):
        if data['color'] == data['name']:
            raise serializers.ValidationError(
                'Имя не может совпадать с цветом!'
            )
        return data
