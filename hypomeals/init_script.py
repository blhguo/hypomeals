#!/usr/bin/env python3

from meals.models import User
from django.contrib.auth.models import Group, Permission
import os

print("STARTING: Initializing database with auth info...")

user_password = os.getenv("DJANGO_USER_PASSWORD", "Hyp0Mea1s!")


if not User.objects.filter(username="admin").exists():
    superuser = User.objects.create_superuser(
        username="admin", email="xc77@duke.edu", password=user_password
    )
else:
    superuser = User.objects.get(username="admin")
    superuser.set_password(user_password)
    superuser.save()

print("Setting up permission system and groups...")

users_group = Group.objects.get_or_create(name="Users")[0]
admins_group = Group.objects.get_or_create(name="Admins")[0]
analysts_group = Group.objects.get_or_create(name="Analysts")[0]
product_managers_group = Group.objects.get_or_create(name="Product Managers")[0]
business_managers_group = Group.objects.get_or_create(name="Business Managers")[0]

core_data_perms = Permission.objects.filter(
    content_type__model__in={
        "sku",
        "ingredient",
        "formula",
        "formulaingredient",
        "manufacturingline",
        "skumanufacturingline",
        "productline",
    }
)
core_data_viewonly = core_data_perms.filter(codename__istartswith="view").all()
core_data_full = core_data_perms.all()

analyst_perms = Permission.objects.filter(
    content_type__model__in={"goal", "goalitem", "goalschedule", "sale", "customer"}
)
analyst_viewonly = analyst_perms.filter(codename__istartswith="view").all()
analyst_full = analyst_perms.all()

users_group.permissions.add(*core_data_viewonly)

analysts_group.permissions.add(*core_data_viewonly)
analysts_group.permissions.add(*analyst_viewonly)

product_managers_group.permissions.add(*core_data_full)
product_managers_group.permissions.add(*analyst_viewonly)

business_managers_group.permissions.add(*core_data_viewonly)
business_managers_group.permissions.add(
    *Permission.objects.filter(content_type__model__in={"goal", "goalitem"}).all()
)

print("SUCCESS: Database is ready for use.")
