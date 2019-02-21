from seaworthy.definitions import ContainerDefinition

container = ContainerDefinition(
	name='test_malaria_container',
	image='malaria',
	wait_patterns=[r'Booting worker'],
	create_kwargs={'ports': {'8000': None}},
	wait_timeout=20)

fixture = container.pytest_fixture('malaria_container')


def test_get(malaria_container):
	response = malaria_container.http_client().get('/')
	assert response.status_code == 200
	assert malaria_container.status() == 'running'
