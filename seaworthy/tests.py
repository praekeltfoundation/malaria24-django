import pytest
from fixtures import *


class TestDjangoContainer:
    @pytest.mark.clean_postgresql_container
    def test_db_tables_created(self, django_container, postgresql_container):
        """
        When the Django container starts, it runs its migrations and some
        database tables are created in PostgreSQL.
        """
        django_logs = django_container.get_logs().decode("utf-8")
        assert "Running migrations" in django_logs

        psql_output = postgresql_container.exec_psql(
            ("SELECT COUNT(*) FROM information_schema.tables WHERE "
             "table_schema='public';")).output.decode('utf-8')

        count = int(psql_output.strip())
        assert count > 0

    def test_get(self, django_container):
        response = django_container.http_client().get('/')
        assert response.status_code == 200
        assert django_container.status() == 'running'
