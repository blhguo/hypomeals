"""
A series of functions / classes to aid authentication and permission checking
"""


def user_is_staff(user) -> bool:
    return user.is_staff


def user_has_perm(user, perm=None) -> bool:
    if not perm:
        return False
    return user.has_perm(perm)