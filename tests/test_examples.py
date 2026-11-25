from app.intake.service import inspect


def test_examples_are_downloadable_and_valid(client, clean):
    response=client.get('/examples/clean')
    assert response.status_code==200 and response.data==clean
    assert inspect(response.data)['rejected']==0


def test_unknown_example_is_404(client):
    assert client.get('/examples/unknown').status_code==404
