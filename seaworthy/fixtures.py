from seaworthy.definitions import ContainerDefinition
from seaworthy.containers.postgresql import PostgreSQLContainer


class DjangoContainer(ContainerDefinition):
    WAIT_PATTERNS = (r"Booting worker",)

    def __init__(self, name, db_url,
                 image="praekeltfoundation/malariaconnect"):
        super().__init__(name, image, self.WAIT_PATTERNS, wait_timeout=20)
        self.db_url = db_url

    def base_kwargs(self):
        return {
            "environment": {
                "DATABASE_URL": self.db_url,
                "ALLOWED_HOSTS": "0.0.0.0",
            },
            "ports": {
                "8000/tcp": ("127.0.0.1",),
            }
        }

postgresql_container = PostgreSQLContainer("postgresql")
postgresql_fixture, clean_postgresql_fixture = (
    postgresql_container.pytest_clean_fixtures("postgresql_container"))

django_container = DjangoContainer("django",
                                   postgresql_container.database_url())
django_fixture = django_container.pytest_fixture(
    "django_container",
    dependencies=["postgresql_container"])
# Allow all the fixtures to be imported like `from fixtures import *`
__all__ = [
    "clean_postgresql_fixture",
    "django_fixture",
    "postgresql_fixture",
]
