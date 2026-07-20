import pytest

from pharmacy_os.core.di import Container


class Service:
    pass


def test_singleton_is_cached() -> None:
    c = Container()
    c.register_singleton(Service, lambda _c: Service())
    assert c.resolve(Service) is c.resolve(Service)


def test_factory_is_fresh_each_time() -> None:
    c = Container()
    c.register_factory(Service, lambda _c: Service())
    assert c.resolve(Service) is not c.resolve(Service)


def test_instance_registration() -> None:
    c = Container()
    obj = Service()
    c.register_instance(Service, obj)
    assert c.resolve(Service) is obj


def test_unknown_key_raises() -> None:
    with pytest.raises(KeyError):
        Container().resolve(Service)
