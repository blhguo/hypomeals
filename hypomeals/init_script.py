#!/usr/bin/env python3

from meals.models import User
from django.contrib.auth.models import Group, Permission
import os

print("STARTING: Initializing database with auth info...")

user_password = os.getenv("DJANGO_USER_PASSWORD", "Hyp0Mea1s!")


if not User.objects.filter(username="ece458").exists():
    superuser = User.objects.create_superuser(
        username="ece458", email="xc77@duke.edu", password=user_password
    )
else:
    superuser = User.objects.get(username="ece458")
    superuser.set_password(user_password)
    superuser.save()
view_only_user = User.objects.get_or_create(
    username="viewonly",
    defaults={
        "first_name": "ViewOnly",
        "last_name": "Perm",
        "email": "abc@example.com",
    },
)[0]
view_only_user.set_password(user_password)

users_group = Group.objects.get_or_create(name="Users")[0]
view_perms = Permission.objects.filter(codename__startswith="view")

for perm in view_perms:
    users_group.permissions.add(perm)


view_only_user.groups.add(users_group)
view_only_user.save()

print("SUCCESS: Database is ready for use.")
