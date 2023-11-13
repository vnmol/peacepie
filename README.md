# PEACEPIE

This is a simple actor system.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install "peacepie".


```bash
 pip install --extra-index-url=https://test.pypi.org/simple peacepie
```

## Usage

The system launch with default parameters

```python
import multiprocessing

from peacepie import PeaceSystem

PARAMS = {}


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    PeaceSystem(PARAMS).start()
```

The same parameters explicitly specified

```python
PARAMS = {'extra-index-url': 'https://test.pypi.org/simple',
          'starter': '{"class_desc": {"package_name": "peacepie_example", "class": "HelloWorld"}, "name": "greeter"}'
          }
```

Start an actor of class "IteratingHelloWorld"

```python
PARAMS = {'extra-index-url': 'https://test.pypi.org/simple',
          'starter': '{"class_desc": {"package_name": "peacepie_example", "class": "IteratingHelloWorld"}, "name": "greeter"}'
          }
```

Start an actor of class "HelloWorld" or "IteratingHelloWorld" by initialting actor of class "Initiator"

```python
PARAMS = {'extra-index-url': 'https://test.pypi.org/simple',
          'starter': '{"class_desc": {"package_name": "peacepie_example", "class": "Initiator"}, "name": "initiator"}',
          'start_command': '{"command": "start", "body": {"class": "HelloWorld"}}'
          }

PARAMS = {'extra-index-url': 'https://test.pypi.org/simple',
          'starter': '{"class_desc": {"package_name": "peacepie_example", "class": "Initiator"}, "name": "initiator"}',
          'start_command': '{"command": "start", "body": {"class": "IteratingHelloWorld"}}'
          }
```

Start groups of actors of class "Tester" by initialting actor of class "Starter"

```python
PARAMS = {'extra-index-url': 'https://test.pypi.org/simple',
          'starter': '{"class_desc": {"package_name": "peacepie_example", "class": "Starter"}, "name": "starter"}',
          'start_command': '{"command": "start", "body": {"group_size": 5, "group_count": 2, "period": 10, "do_printing": true}}'
          }
```

