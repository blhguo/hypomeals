#!/usr/bin/env python3

from meals.models import User
from django.contrib.auth.models import Group, Permission


User.objects.create_superuser(
    username="ece458", email="xc77@duke.edu", password="Hyp0Mea1s!"
)
view_only_user = User.objects.get_or_create(
    username="viewonly",
    first_name="ViewOnly",
    last_name="Perm",
    email="abc@example.com",
)[0]
view_only_user.set_password("Hyp0Mea1s!")

users_group = Group.objects.get_or_create(name="Users")[0]
view_perms = Permission.objects.filter(codename__startswith="view")

for perm in view_perms:
    users_group.permissions.add(perm)


view_only_user.groups.add(users_group)
view_only_user.save()
