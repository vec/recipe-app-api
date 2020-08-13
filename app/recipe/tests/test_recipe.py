from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe
from core.models import Tag
from core.models import Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPE_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Returs a recipe detail url"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Dope'):
    """Creates and returns a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Paperika'):
    """Creates and returns a sample Ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Creates and returns a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)
    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """Tests unauthenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required"""
        resource = self.client.get(RECIPE_URL)

        self.assertEquals(resource.status_code, status.HTTP_401_UNAUTHORIZED)


class PriceRecipeApiTests(TestCase):
    """Tests authenticated recipe API access"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@server.com',
            'pass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving recipes"""
        sample_recipe(user=self.user, title='recipe1')
        sample_recipe(user=self.user, title='recipe2')

        resource = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(resource.status_code, status.HTTP_200_OK)
        self.assertEqual(resource.data, serializer.data)

    def test_retrieve_recipes_limited_to_user(self):
        """Test retrieving recipes limited to user"""
        other_user = get_user_model().objects.create_user(
            'other_test@server.com',
            'pass123'
        )

        sample_recipe(user=self.user, title='recipe1')
        sample_recipe(user=other_user, title='recipe2')

        resource = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user).order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(len(resource.data), 1)
        self.assertEqual(resource.data, serializer.data)

    def test_retrieve_recipe_detail(self):
        """Test retrieving recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        resource = self.client.get(detail_url(recipe.id))

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(resource.status_code, status.HTTP_200_OK)
        self.assertEqual(resource.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': 5.00,
        }
        resource = self.client.post(RECIPE_URL, payload)

        self.assertEqual(resource.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=resource.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

        def test_create_recipe_with_tags(self):
            """Test creating recipe with tags"""
            tag1 = sample_tag(user=self.user, name='Vegan')
            tag2 = sample_tag(user=self.user, name='Dessert')
            payload = {
                'title': 'Avocado lime cheesecake',
                'time_minutes': 60,
                'tags': [tag1.id, tag2.id],
                'price': 20.00,
            }
            resource = self.client.post(RECIPE_URL, payload)

            self.assertEqual(resource.status_code, status.HTTP_201_CREATED)
            recipe = Recipe.objects.get(id=resource.data['id'])
            tags = recipe.tags.all()
            self.assertEqual(tags.count(), 2)
            self.assertIn(tag1, tags)
            self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        """Test creating recipe with ingredients"""
        ingredient1 = sample_ingredient(user=self.user, name='Prawns')
        ingredient2 = sample_ingredient(user=self.user, name='Ginger')
        payload = {
            'title': 'Thai prawns with red curry',
            'ingredients': [ingredient1.id, ingredient2.id],
            'time_minutes': 45,
            'price': 15.00
        }

        resource = self.client.post(RECIPE_URL, payload)

        self.assertEqual(resource.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=resource.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_recipe(self):
        """Test updating a recipe with patch"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Curry')

        payload = {'title': 'Chicken tikka', 'tags': [new_tag.id]}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        """Test updating a recipe with put"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))

        payload = {
            'title': 'Spaghetti carbonara',
            'time_minutes': 25,
            'price': 5.00
        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)
