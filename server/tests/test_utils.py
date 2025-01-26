import pytest
from rabbitmq_server.utils import double_number

def test_double_number_positive():
    assert double_number(10) == 20

def test_double_number_zero():
    assert double_number(0) == 0

def test_double_number_negative():
    assert double_number(-5) == -10

def test_double_number_large():
    assert double_number(1000000) == 2000000

def test_double_number_float():
    assert double_number(2.0) == 4
