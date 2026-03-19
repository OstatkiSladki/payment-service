from enum import Enum


class UsersRole(str, Enum):
  USER = "user"
  STAFF = "staff"
  ADMIN = "admin"


class StaffRole(str, Enum):
  STAFF = "staff"
  MANAGER = "manager"
  ADMIN = "admin"
  OWNER = "owner"
